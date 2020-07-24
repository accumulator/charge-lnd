#!/usr/bin/env python3
import sys
from electrum import Electrum

def debug(message):
    sys.stderr.write(message + "\n")

class Policy:
    def __init__(self, lnd, name, config):
        self.lnd = lnd
        self.name = name
        self.config = config

    def execute(self, channel):
        map = {
            'ignore'      : self.strategy_ignore,
            'static'      : self.strategy_static,
            'match_peer'  : self.strategy_match_peer,
            'onchain_fee' : self.strategy_onchain_fee,
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

    def strategy_onchain_fee(self, channel):
        if not Electrum.host or not Electrum.port:
            debug("No electrum server specified, cannot use strategy 'onchain_fee'")
            sys.exit(1)
        numblocks = self.config.getint('onchain_fee_numblocks',6)
        sat_per_byte = Electrum.get_fee_estimate(numblocks)
        if sat_per_byte < 1:
            return (None,None)
        reference_payment = self.config.getfloat('onchain_fee_btc', 0.1)
        fee_ppm = int((0.01 / reference_payment) * (223 * sat_per_byte))
        return (self.config.getint('base_fee_msat'), fee_ppm)
