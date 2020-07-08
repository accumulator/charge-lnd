#!/usr/bin/env python3
import sys

def debug(message):
    sys.stderr.write(message + "\n")

class Template:
    def __init__(self, lnd, name, config):
        self.lnd = lnd
        self.name = name
        self.config = config

    def execute(self, channel):
        map = {
            'ignore'     : self.strategy_ignore,
            'static'     : self.strategy_static,
            'match_peer' : self.strategy_match_peer,
        }
        strategy = self.config.get('strategy', 'ignore')
        if not strategy in map:
            debug("Unknown strategy '%s'" % strategy)
            sys.exit(1)

        return map[strategy](channel)

    def strategy_ignore(self, channel):
        return (None,None)

    def strategy_static(self, channel):
        return (self.config.getint('base_fee_msat'), self.config.getint('fee_ppm'))

    def strategy_match_peer(self, channel):
        chan_info = self.lnd.get_chan_info(channel.chan_id)
        my_pubkey = self.lnd.get_own_pubkey()
        peernode_policy = chan_info.node1_policy if chan_info.node2_pub == my_pubkey else chan_info.node2_policy
        return (peernode_policy.fee_base_msat, peernode_policy.fee_rate_milli_msat)
