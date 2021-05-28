#!/usr/bin/env python3
import sys
import re
from .policy import Policy
from . import fmt

def debug(message):
    sys.stderr.write(message + "\n")

def read_nodelist(url):
    with open(url.replace("file://",""),'r') as idfile:
        raw_ids = idfile.read().splitlines()
    node_list = []
    for raw_id in raw_ids:
        raw_id = raw_id.split('#')[0]
        match = re.match("^([0-9a-z]{66})", raw_id)
        if match:
            node_list.append(match.group(0))
        else:
            if raw_id.strip() == '':
                continue
            debug("Ignored: invalid node pubkey '%s' in '%s'" % (raw_id,url))
    return node_list

def read_chanlist(url):
    with open(url.replace("file://",""),'r') as idfile:
        raw_ids = idfile.read().splitlines()
    chan_list = []
    for raw_id in raw_ids:
        raw_id = raw_id.split('#')[0]
        try:
            chan_id = fmt.parse_channel_id(raw_id)
            chan_list.append(chan_id)
        except:
            if raw_id.strip() == '':
                continue
            debug("Ignored: invalid channel id '%s' in '%s'" % (raw_id,url))

    return chan_list

class Matcher:
    def __init__(self, lnd, config):
        self.lnd = lnd
        self.config = config
        self.default = None
        self.policies = []

        sections = config.sections()
        for s in sections:
            if s == 'default':
                self.default = config[s]
            else:
                self.policies.append(s)

    def get_policy(self, channel):
        # iterate policies, find first match based on matchers. If no match, use default
        try:
            for policy in self.policies:
                policy_conf = self.config[policy]
                if self.eval_matchers(channel, policy, policy_conf):
                    return Policy(self.lnd, policy, policy_conf)
        except Exception as e:
            debug("Error evaluating criteria for channel %s in policy '%s', ignoring channel. (Error=%s)" % (fmt.print_chanid(channel.chan_id), policy, str(e)))
            return None

        return Policy(self.lnd, 'default', self.default);

    def eval_matchers(self, channel, policy, policy_conf):
        map = {
            'chan'  : self.match_by_chan,
            'node'  : self.match_by_node
        }
        namespaces = []
        for key in policy_conf.keys():
            keyns = key.split(".")
            if len(keyns) > 1:
                namespaces.append(keyns[0])

        matches_policy = True
        for ns in namespaces:
            if not ns in map:
                debug("Unknown namespace '%s' in policy '%s'" % (ns,policy))
                return False
            matches_policy = matches_policy and map[ns](channel, policy_conf)
        return matches_policy

    def match_by_node(self, channel, config):
        accepted = ['id',
                    'min_channels','max_channels',
                    'min_capacity','max_capacity'
                    ]
        for key in config.keys():
            if key.split(".")[0] == 'node' and key.split(".")[1] not in accepted:
                raise Exception("Unknown property '%s'" % key)

        if 'node.id' in config:
            # expand file:// entries
            config_items = config.getlist('node.id')
            node_list = []
            for item in config_items:
                if item.startswith('file://'):
                    node_list = node_list + read_nodelist(item)
                else:
                    node_list.append(item)
            # Do the matching
            if not channel.remote_pubkey in node_list:
                return False

        node_info = self.lnd.get_node_info(channel.remote_pubkey)

        if 'node.min_channels' in config and not config.getint('node.min_channels') <= node_info.num_channels:
            return False
        if 'node.max_channels' in config and not config.getint('node.max_channels') >= node_info.num_channels:
            return False
        if 'node.min_capacity' in config and not config.getint('node.min_capacity') <= node_info.total_capacity:
            return False
        if 'node.max_capacity' in config and not config.getint('node.max_capacity') >= node_info.total_capacity:
            return False

        return True

    def match_by_chan(self, channel, config):
        accepted = ['id','initiator','private',
                    'min_ratio','max_ratio',
                    'min_capacity','max_capacity',
                    'min_base_fee_msat','max_base_fee_msat',
                    'min_fee_ppm','max_fee_ppm',
                    'min_age','max_age'
                    ]
        for key in config.keys():
            if key.split(".")[0] == 'chan' and key.split(".")[1] not in accepted:
                raise Exception("Unknown property '%s'" % key)

        if 'chan.id' in config:
            # expand file:// entries
            config_items = config.getlist('chan.id')
            chan_list = []
            for item in config_items:
                if item.startswith('file://'):
                    chan_list = chan_list + read_chanlist(item)
                else:
                    chan_list.append(fmt.parse_channel_id(item))

            if not channel.chan_id in chan_list:
                return False

        if 'chan.initiator' in config and not channel.initiator == config.getboolean('chan.initiator'):
            return False
        if 'chan.private' in config and not channel.private == config.getboolean('chan.private'):
            return False

        ratio = channel.local_balance/(channel.local_balance + channel.remote_balance)
        if 'chan.max_ratio' in config and not config.getfloat('chan.max_ratio') >= ratio:
            return False
        if 'chan.min_ratio' in config and not config.getfloat('chan.min_ratio') <= ratio:
            return False
        if 'chan.max_capacity' in config and not config.getint('chan.max_capacity') >= channel.capacity:
            return False
        if 'chan.min_capacity' in config and not config.getint('chan.min_capacity') <= channel.capacity:
            return False

        chan_info = self.lnd.get_chan_info(channel.chan_id)
        if not chan_info:
            return False
        my_pubkey = self.lnd.get_own_pubkey()
        peernode_policy = chan_info.node1_policy if chan_info.node2_pub == my_pubkey else chan_info.node2_policy

        if 'chan.min_base_fee_msat' in config and not config.getint('chan.min_base_fee_msat') <= peernode_policy.fee_base_msat:
            return False
        if 'chan.max_base_fee_msat' in config and not config.getint('chan.max_base_fee_msat') >= peernode_policy.fee_base_msat:
            return False
        if 'chan.min_fee_ppm' in config and not config.getint('chan.min_fee_ppm') <= peernode_policy.fee_rate_milli_msat:
            return False
        if 'chan.max_fee_ppm' in config and not config.getint('chan.max_fee_ppm') >= peernode_policy.fee_rate_milli_msat:
            return False

        info = self.lnd.get_info()
        if not info:
            return False
        (block,tx,output) = fmt.lnd_to_cl_scid(channel.chan_id)
        age = info.block_height - block
        if 'chan.min_age' in config and not config.getint('chan.min_age') <= age:
            return False
        if 'chan.max_age' in config and not config.getint('chan.max_age') >= age:
            return False

        return True
