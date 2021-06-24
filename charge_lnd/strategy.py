#!/usr/bin/env python3
import sys
import functools

from . import fmt
from .electrum import Electrum

def debug(message):
    sys.stderr.write(message + "\n")


def strategy(_func=None,*,name):
    def register_strategy(func):
        @functools.wraps(func)
        def call_strategy(*args, **kwargs):
            return func(*args, **kwargs)
        StrategyDelegate.STRATEGIES[name] = func
        return call_strategy
    return register_strategy


class StrategyDelegate:
    STRATEGIES = {}
    def __init__(self, policy):
        self.policy = policy

    def execute(self, channel):
        strategy = self.policy.get('strategy', 'ignore')
        if strategy not in StrategyDelegate.STRATEGIES:
            debug("Unknown strategy '%s' in policy '%s'" % (strategy, self.policy.name))

        try:
            result = StrategyDelegate.STRATEGIES[strategy](channel, self.policy, name=self.policy.name, lnd=self.policy.lnd)
            # set policy htlc limits if not overruled by the strategy
            if len(result) == 2:
                result = result + ( self.policy.getint('min_htlc_msat'),
                                    self.policy.getint('max_htlc_msat'),
                                    self.policy.getint('time_lock_delta') )
            return result
        except Exception as e:
            debug("Error executing strategy '%s'. (Error=%s)" % (strategy, str(e)) )
            return strategy_ignore(channel, self.policy)

@strategy(name = 'ignore')
def strategy_ignore(channel, policy, **kwargs):
    return (None, None, None, None, None)

@strategy(name = 'static')
def strategy_static(channel, policy, **kwargs):
    return (policy.getint('base_fee_msat'), policy.getint('fee_ppm'))

@strategy(name = 'proportional')
def strategy_proportional(channel, policy, **kwargs):
    if policy.getint('min_fee_ppm_delta',-1) < 0:
        policy.set('min_fee_ppm_delta', 5) # set delta to 5 if not defined
    ppm_min = policy.getint('min_fee_ppm')
    ppm_max = policy.getint('max_fee_ppm')
    if ppm_min is None or ppm_max is None:
        raise Exception('proportional strategy requires min_fee_ppm and max_fee_ppm properties')
    ratio = channel.local_balance/(channel.local_balance + channel.remote_balance)
    ppm = int(ppm_min + (1.0 - ratio) * (ppm_max - ppm_min))
    # clamp to 0..inf
    ppm = max(ppm,0)
    return (policy.getint('base_fee_msat'), ppm)

@strategy(name = 'match_peer')
def strategy_match_peer(channel, policy, **kwargs):
    lnd = kwargs['lnd']
    chan_info = lnd.get_chan_info(channel.chan_id)
    my_pubkey = lnd.get_own_pubkey()
    peernode_policy = chan_info.node1_policy if chan_info.node2_pub == my_pubkey else chan_info.node2_policy
    return (policy.getint('base_fee_msat', peernode_policy.fee_base_msat),
            policy.getint('fee_ppm', peernode_policy.fee_rate_milli_msat))

@strategy(name = 'cost')
def strategy_cost(channel, policy, **kwargs):
    lnd = kwargs['lnd']
    chan_info = lnd.get_chan_info(channel.chan_id)
    txid = chan_info.chan_point.split(':')[0]
    (block, tx, out) = fmt.lnd_to_cl_scid(channel.chan_id)
    txns = lnd.get_txns(start_height=block, end_height=block)
    chan_open_tx = None
    for tx in txns.transactions:
        if txid == tx.tx_hash:
            chan_open_tx = tx

    # only take channel-open cost into account. TODO: also support coop close & force close scenarios
    if chan_open_tx is not None:
        ppm = int(policy.getfloat('cost_factor', 1.0) * 1_000_000 * chan_open_tx.total_fees / chan_info.capacity)
    else:
        ppm = 1  # tx not found, incoming channel, default to 1
    return (policy.getint('base_fee_msat'), ppm)

@strategy(name = 'onchain_fee')
def strategy_onchain_fee(channel, policy, **kwargs):
    if not Electrum.host or not Electrum.port:
        raise Exception("No electrum server specified, cannot use strategy 'onchain_fee'")

    numblocks = policy.getint('onchain_fee_numblocks', 6)
    sat_per_byte = Electrum.get_fee_estimate(numblocks)
    if sat_per_byte < 1:
        return (None, None, None, None, None)
    reference_payment = policy.getfloat('onchain_fee_btc', 0.1)
    fee_ppm = int((0.01 / reference_payment) * (223 * sat_per_byte))
    return (policy.getint('base_fee_msat'), fee_ppm)
