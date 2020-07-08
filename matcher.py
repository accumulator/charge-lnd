#!/usr/bin/env python3
import sys
from template import Template
import fmt

def debug(message):
    sys.stderr.write(message + "\n")

class Matcher:
    def __init__(self, lnd, config):
        self.lnd = lnd
        self.config = config
        self.default = None
        self.templates = []

        sections = config.sections()
        for s in sections:
            if s == 'default':
                self.default = config[s]
            else:
                if 'match' not in config[s]:
                    debug("template %s has no defined match key" % s)
                    sys.exit(1)
                self.templates.append(s)

    def get_template(self, channel):
        # iterate templates, find first match based on matchers. If no match, use default
        for template in self.templates:
            template_conf = self.config[template]
            if self.eval_matchers(channel, template_conf):
                return Template(self.lnd, template, template_conf)

        return Template(self.lnd, 'default', self.default);

    def eval_matchers(self, channel, template_conf):
        map = {
            'id'         : self.match_by_id,
            'initiator'  : self.match_by_initiator,
            'balance'    : self.match_by_balance,
            'peersize'   : self.match_by_peersize,
            'peerpolicy' : self.match_by_peerpolicy,
            'private'    : self.match_by_private
        }
        matches_template = True
        matchers = template_conf.getlist('match')
        for matcher in matchers:
            if not matcher in map:
                debug("Unknown matcher '%s'" % matcher)
                sys.exit(1)
            matches_template = matches_template and map[matcher](channel, template_conf)
        return matches_template

    def match_by_id(self, channel, config):
        if 'channels' in config and channel.chan_id in [fmt.parse_channel_id(x) for x in config.getlist('channels')]:
            return True
        if 'nodes' in config and channel.remote_pubkey in config.getlist('nodes'):
            return True
        return False

    def match_by_initiator(self, channel, config):
        if 'initiator' in config and channel.initiator == config.getboolean('initiator'):
            return True
        return False

    def match_by_balance(self, channel, config):
        ratio = channel.local_balance/(channel.local_balance + channel.remote_balance)
        matches = 'max_ratio' in config or 'min_ratio' in config or 'max_capacity' in config or 'min_capacity' in config
        if 'max_ratio' in config:
            matches = matches and config.getfloat('max_ratio') >= ratio
        if 'min_ratio' in config:
            matches = matches and config.getfloat('min_ratio') <= ratio
        if 'max_capacity' in config:
            matches = matches and config.getint('max_capacity') >= channel.capacity
        if 'min_capacity' in config:
            matches = matches and config.getint('min_capacity') <= channel.capacity

        return matches

    def match_by_peersize(self, channel, config):
        node_info = self.lnd.get_node_info(channel.remote_pubkey)
        matches = 'min_channels' in config or 'max_channels' in config or 'min_sats' in config or 'max_sats' in config
        if 'min_channels' in config:
            matches = matches and config.getint('min_channels') <= node_info.num_channels
        if 'max_channels' in config:
            matches = matches and config.getint('max_channels') >= node_info.num_channels
        if 'min_sats' in config:
            matches = matches and config.getint('min_sats') <= node_info.total_capacity
        if 'max_sats' in config:
            matches = matches and config.getint('max_sats') >= node_info.total_capacity

        return matches

    def match_by_peerpolicy(self, channel, config):
        chan_info = self.lnd.get_chan_info(channel.chan_id)
        my_pubkey = self.lnd.get_own_pubkey()
        peernode_policy = chan_info.node1_policy if chan_info.node2_pub == my_pubkey else chan_info.node2_policy
        matches = 'min_base_fee_msat' in config or 'max_base_fee_msat' in config or 'min_fee_ppm' in config or 'max_fee_ppm' in config
        if 'min_base_fee_msat' in config:
            matches = matches and config.getint('min_base_fee_msat') <= peernode_policy.fee_base_msat
        if 'max_base_fee_msat' in config:
            matches = matches and config.getint('max_base_fee_msat') >= peernode_policy.fee_base_msat
        if 'min_fee_ppm' in config:
            matches = matches and config.getint('min_fee_ppm') <= peernode_policy.fee_rate_milli_msat
        if 'max_fee_ppm' in config:
            matches = matches and config.getint('max_fee_ppm') >= peernode_policy.fee_rate_milli_msat

        return matches

    def match_by_private(self, channel, config):
        if 'private' in config:
            return channel.private == config.getboolean('private')
        return False

