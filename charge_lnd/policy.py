#!/usr/bin/env python3
import sys
import re
import time
from .strategy import StrategyDelegate, DONTCARE
from . import fmt

def debug(message):
    sys.stderr.write(message + "\n")

def read_nodelist(url):
    with open(url.replace("file://",""),'r') as idfile:
        raw_ids = idfile.read().replace(',','\n').splitlines()
    node_list = []
    for raw_id in raw_ids:
        raw_id = raw_id.split('#')[0].strip()
        match = re.match("^([0-9a-z]{66})$", raw_id)
        if match:
            node_list.append(match.group(0))
        else:
            if raw_id.strip() == '':
                continue
            debug("Ignored: invalid node pubkey '%s' in '%s'" % (raw_id,url))
    return node_list

def read_chanlist(url):
    with open(url.replace("file://",""),'r') as idfile:
        raw_ids = idfile.read().replace(',','\n').splitlines()
    chan_list = []
    for raw_id in raw_ids:
        raw_id = raw_id.split('#')[0].strip()
        try:
            chan_id = fmt.parse_channel_id(raw_id)
            chan_list.append(chan_id)
        except:
            if raw_id.strip() == '':
                continue
            debug("Ignored: invalid channel id '%s' in '%s'" % (raw_id,url))

    return chan_list

class Policy:
    def __init__(self, lnd):
        self.lnd = lnd
        self.strategy = None
        self.name = None
        self.config = {}

    def apply(self, policy_name, policy_config):
        # mask over the collected config
        for k,v in policy_config.items():
            self.config[k] = v

        strategy = policy_config.get('strategy')
        if strategy: # final policy
            self.name = policy_name
            self.strategy = StrategyDelegate(self)
            return True

        # no strategy defined, so this policy is not final
        return False

    def _get(self, key, func, default=None):
        if not key in self.config:
            return default
        return func(self.config.get(key))

    def get(self, key, default=None):
        return self._get(key, str, default)

    def getint(self, key, default=None):
        return self._get(key, int, default)

    def getfloat(self, key, default=None):
        return self._get(key, float, default)

    def getbool(self, key, default=None):
        return self._get(key, bool, default)

    def set(self, key, value):
        self.config[key] = value


class Policies:
    def __init__(self, lnd, config):
        self.lnd = lnd
        self.config = config

    def get_policy_for(self, channel):
        # iterate policies, find channel match based on matchers. If no match, use default if defined
        policy = Policy(self.lnd)

        try:
            for policy_name in self.config.policies:
                policy_conf = self.config.get_config_for(policy_name)
                if self.eval_matchers(channel, policy_name, policy_conf):
                    final = policy.apply(policy_name, policy_conf)
                    if final:
                        return policy
        except Exception as e:
            debug("Error evaluating criteria for channel %s in policy '%s', ignoring channel. (Error=%s)" % (fmt.print_chanid(channel.chan_id), policy, str(e)))
            return None

        if self.config.default:
           if policy.apply('default', self.config.default):
               return policy

        return None

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
        multiple_chans_props = ['min_shared_channels_active','max_shared_channels_active',
                                'min_shared_channels_inactive','max_shared_channels_inactive',
                                'min_shared_capacity_active','max_shared_capacity_active',
                                'min_shared_capacity_inactive','max_shared_capacity_inactive',
                                'min_shared_ratio_active', 'max_shared_ratio_active',
                                'min_shared_ratio_inactive', 'max_shared_ratio_inactive',
                                'min_shared_ratio', 'max_shared_ratio']
        accepted = ['id',
                    'min_channels','max_channels',
                    'min_capacity','max_capacity'
                    ] + multiple_chans_props

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

        # Consider multiple channels per node policies
        if any(map(lambda n: "node." + n in config, multiple_chans_props)):

            shared_chans=self.lnd.get_shared_channels(channel.remote_pubkey)

            local_active_balance = remote_active_balance = active_total = 0
            local_inactive_balance = remote_inactive_balance = inactive_total = 0
            channels_active = channels_inactive = 0

            for chan in (shared_chans):
                if chan.active:
                    local_active_balance += chan.local_balance
                    remote_active_balance += chan.remote_balance
                    channels_active += 1
                else:
                    local_inactive_balance += chan.local_balance
                    remote_inactive_balance += chan.remote_balance
                    channels_inactive += 1

            active_total = local_active_balance + remote_active_balance
            inactive_total = local_inactive_balance + remote_inactive_balance
            all_total = active_total + inactive_total

            ratio_all = (local_active_balance + local_inactive_balance) / all_total

            # Cannot calculate the active ratio if the active total is 0
            if ('node.max_shared_ratio_active' in config \
                or 'node.min_shared_ratio_active' in config):
                if active_total <= 0:
                    return False

                ratio_active = local_active_balance / active_total

                if (lambda s: s in config and not config.getfloat(s) >= ratio_active) \
                   ('node.max_shared_ratio_active'): return False
                if (lambda s: s in config and not config.getfloat(s) <= ratio_active) \
                   ('node.min_shared_ratio_active'): return False

            if ('node.max_shared_ratio_inactive' in config \
                or 'node.min_shared_ratio_inactive' in config):
                # Cannot calculate the inactive ratio if the inactive total is 0
                if inactive_total <= 0:
                    return False

                ratio_inactive = local_inactive_balance / inactive_total

                if (lambda s: s in config and not config.getfloat(s) >= ratio_inactive) \
                   ('node.max_shared_ratio_inactive'): return False
                if (lambda s: s in config and not config.getfloat(s) <= ratio_inactive) \
                   ('node.min_shared_ratio_inactive'): return False

            if (lambda s: s in config and not config.getfloat(s) >= ratio_all) \
                ('node.max_shared_ratio'): return False
            if (lambda s: s in config and not config.getfloat(s) <= ratio_all) \
                ('node.min_shared_ratio'): return False

            if (lambda s: s in config and not config.getint(s) >= channels_active) \
                ('node.max_shared_channels_active'): return False
            if (lambda s: s in config and not config.getint(s) <= channels_active) \
                ('node.min_shared_channels_active'): return False
            if (lambda s: s in config and not config.getint(s) >= channels_inactive) \
                ('node.max_shared_channels_inactive'): return False
            if (lambda s: s in config and not config.getint(s) <= channels_inactive) \
                ('node.min_shared_channels_inactive'): return False

            if (lambda s: s in config and not config.getint(s) >= active_total) \
                ('node.max_shared_capacity_active'): return False
            if (lambda s: s in config and not config.getint(s) <= active_total) \
                ('node.min_shared_capacity_active'): return False
            if (lambda s: s in config and not config.getint(s) >= inactive_total) \
                ('node.max_shared_capacity_inactive'): return False
            if (lambda s: s in config and not config.getint(s) <= inactive_total) \
                ('node.min_shared_capacity_inactive'): return False

        return True

    def match_by_chan(self, channel, config):
        accepted = ['id','initiator','private',
                    'min_ratio','max_ratio',
                    'min_capacity','max_capacity',
                    'min_local_balance','max_local_balance',
                    'min_remote_balance','max_remote_balance',
                    'min_base_fee_msat','max_base_fee_msat',
                    'min_fee_ppm','max_fee_ppm',
                    'min_age','max_age',
                    'activity_period',
                    'min_htlcs_in', 'max_htlcs_in',
                    'min_htlcs_out', 'max_htlcs_out',
                    'min_sats_in', 'max_sats_in',
                    'min_sats_out', 'max_sats_out',
                    'activity_period_ignore_channel_age',
                    'max_htlcs_ratio', 'min_htlcs_ratio',
                    'max_sats_ratio', 'min_sats_ratio',
                    'disabled'
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
        if 'chan.max_local_balance' in config and not config.getint('chan.max_local_balance') >= channel.local_balance:
            return False
        if 'chan.min_local_balance' in config and not config.getint('chan.min_local_balance') <= channel.local_balance:
            return False
        if 'chan.max_remote_balance' in config and not config.getint('chan.max_remote_balance') >= channel.remote_balance:
            return False
        if 'chan.min_remote_balance' in config and not config.getint('chan.min_remote_balance') <= channel.remote_balance:
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
        if 'chan.disabled' in config and not config.getbool('chan.disabled') == peernode_policy.disabled:
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

        if 'chan.activity_period' in config:
            seconds = self.parse_activity_period(config.get('chan.activity_period'))
            fwds = self.lnd.get_forward_history(channel.chan_id, seconds)

            age_seconds = age * 10*60 # channel age estimate in seconds from age in blocks
            if not ('chan.activity_period_ignore_channel_age' in config and not config.getboolean('chan.activity_period_ignore_channel_age')):
                # don't trigger if channel age less than activity_period
                if age_seconds < seconds:
                    return False

            if 'chan.max_htlcs_in' in config:
                if fwds['htlc_in'] > config.getint('chan.max_htlcs_in'):
                    return False
            if 'chan.min_htlcs_in' in config:
                if fwds['htlc_in'] < config.getint('chan.min_htlcs_in'):
                    return False
            if 'chan.max_htlcs_out' in config:
                if fwds['htlc_out'] > config.getint('chan.max_htlcs_out'):
                    return False
            if 'chan.min_htlcs_out' in config:
                if fwds['htlc_out'] < config.getint('chan.min_htlcs_out'):
                    return False

            if 'chan.max_sats_in' in config:
                if fwds['sat_in'] > config.getint('chan.max_sats_in'):
                    return False
            if 'chan.min_sats_in' in config:
                if fwds['sat_in'] < config.getint('chan.min_sats_in'):
                    return False
            if 'chan.max_sats_out' in config:
                if fwds['sat_out'] > config.getint('chan.max_sats_out'):
                    return False
            if 'chan.min_sats_out' in config:
                if fwds['sat_out'] < config.getint('chan.min_sats_out'):
                    return False

            htlcs_total = fwds['htlc_in'] + fwds['htlc_out']
            htlcs_ratio = fwds['htlc_in'] / htlcs_total if htlcs_total else float('nan')
            if 'chan.max_htlcs_ratio' in config and not config.getfloat('chan.max_htlcs_ratio') >= htlcs_ratio:
                return False
            if 'chan.min_htlcs_ratio' in config and not config.getfloat('chan.min_htlcs_ratio') <= htlcs_ratio:
                return False

            sats_total = fwds['sat_in'] + fwds['sat_out']
            sats_ratio = fwds['sat_in'] / sats_total if sats_total else float('nan')
            if 'chan.max_sats_ratio' in config and not config.getfloat('chan.max_sats_ratio') >= sats_ratio:
                return False
            if 'chan.min_sats_ratio' in config and not config.getfloat('chan.min_sats_ratio') <= sats_ratio:
                return False

        return True

    # simple minutes/hours/days format, e.g. '5m', '3h'
    def parse_activity_period(self, period):
        seconds = 0
        try:
            seconds = int(period)
        except ValueError:
            mulmap = { 's': 1, 'm': 60, 'h': 60*60, 'd': 60*60*24 }
            multiplier = mulmap[period[-1]]
            seconds = int(period[:-1]) * multiplier

        return int(seconds)
