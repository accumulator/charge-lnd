#!/usr/bin/env python3
import sys
from . import fmt
from .electrum import Electrum

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
            'cost'        : self.strategy_cost,
            'onchain_fee' : self.strategy_onchain_fee,
            'proportional': self.strategy_proportional
        }
        strategy = self.config.get('strategy', 'ignore')
        if strategy not in map:
            debug("Unknown strategy '%s'" % strategy)
            strategy = 'ignore'

        try:
            return map[strategy](channel)
        except Exception as e:
            debug("Error executing strategy '%s'. (Error=%s)" % (strategy, str(e)) )
            return self.strategy_ignore(channel)

    def strategy_ignore(self, channel):
        return (None, None, None, None, None)

    def strategy_static(self, channel):
        return (self.config.getint('base_fee_msat'),
                self.config.getint('fee_ppm'),
                self.config.getint('min_htlc_msat'),
                self.config.getint('max_htlc_msat'),
                self.config.getint('time_lock_delta'))

    def strategy_proportional(self, channel):
        ppm_min = self.config.getint('min_fee_ppm')
        ppm_max = self.config.getint('max_fee_ppm')
        if ppm_min is None or ppm_max is None:
            raise Exception('proportional strategy requires min_fee_ppm and max_fee_ppm properties')
        ratio = channel.local_balance/(channel.local_balance + channel.remote_balance)
        ppm = int(ppm_min + (1.0 - ratio) * (ppm_max - ppm_min))
        # clamp to 0..inf
        ppm = max(ppm,0)
        return (self.config.getint('base_fee_msat'),
                ppm,
                self.config.getint('min_htlc_msat'),
                self.config.getint('max_htlc_msat'),
                self.config.getint('time_lock_delta'))

    def strategy_match_peer(self, channel):
        chan_info = self.lnd.get_chan_info(channel.chan_id)
        my_pubkey = self.lnd.get_own_pubkey()
        peernode_policy = chan_info.node1_policy if chan_info.node2_pub == my_pubkey else chan_info.node2_policy
        return (self.config.getint('base_fee_msat', peernode_policy.fee_base_msat),
                self.config.getint('fee_ppm', peernode_policy.fee_rate_milli_msat),
                self.config.getint('min_htlc_msat'),
                self.config.getint('max_htlc_msat'),
                self.config.getint('time_lock_delta'))

    def strategy_cost(self, channel):
        chan_info = self.lnd.get_chan_info(channel.chan_id)
        txid = chan_info.chan_point.split(':')[0]
        (block, tx, out) = fmt.lnd_to_cl_scid(channel.chan_id)
        txns = self.lnd.get_txns(start_height=block, end_height=block)
        chan_open_tx = None
        for tx in txns.transactions:
            if txid == tx.tx_hash:
                chan_open_tx = tx

        # only take channel-open cost into account. TODO: also support coop close & force close scenarios
        if chan_open_tx is not None:
            ppm = int(self.config.getfloat('cost_factor', 1.0) * 1_000_000 * chan_open_tx.total_fees / chan_info.capacity)
        else:
            ppm = 1  # tx not found, incoming channel, default to 1
        return (self.config.getint('base_fee_msat'),
                ppm,
                self.config.getint('min_htlc_msat'),
                self.config.getint('max_htlc_msat'),
                self.config.getint('time_lock_delta'))

    def strategy_onchain_fee(self, channel):
        if not Electrum.host or not Electrum.port:
            raise Exception("No electrum server specified, cannot use strategy 'onchain_fee'")

        numblocks = self.config.getint('onchain_fee_numblocks', 6)
        sat_per_byte = Electrum.get_fee_estimate(numblocks)
        if sat_per_byte < 1:
            return (None, None)
        reference_payment = self.config.getfloat('onchain_fee_btc', 0.1)
        fee_ppm = int((0.01 / reference_payment) * (223 * sat_per_byte))
        return (self.config.getint('base_fee_msat'),
                fee_ppm,
                self.config.getint('min_htlc_msat'),
                self.config.getint('max_htlc_msat'),
                self.config.getint('time_lock_delta'))
