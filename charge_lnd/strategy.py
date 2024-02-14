#!/usr/bin/env python3
import sys
import functools

from . import fmt
from .config import Config
from .electrum import Electrum

edges_cache = None

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

def calculate_slices(max_value, current_value, num_slices):
    # Calculate the size of each slice
    slice_size = max_value // max(num_slices, 10)

    # Find the slice number containing the current_value
    current_slice = min(current_value // slice_size, num_slices - 1)

    # Determine the upper value of the current slice without going over
    slice_point = max(1, min(current_slice * slice_size, max_value))

    return slice_point

def get_ratio(channel, policy, **kwargs):
    if policy.getbool('sum_peer_chans', False):
        lnd = kwargs['lnd']
        shared_chans=lnd.get_shared_channels(channel.remote_pubkey)
        local_balance = 0
        remote_balance = 0
        for c in (shared_chans):
            # Include balance of all active channels with peer
            if c.active:
                local_balance += c.local_balance
                remote_balance += c.remote_balance
        total_balance = local_balance + remote_balance
        if total_balance == 0:
            # Sum inactive channels because the node is likely offline with no active channels.
            # When they come back online their fees won't be changed.
            for c in (shared_chans):
                if not c.active:
                    local_balance += c.local_balance
                    remote_balance += c.remote_balance
        total_balance = local_balance + remote_balance
        ratio = local_balance/total_balance
    else:
        ratio = channel.local_balance/(channel.local_balance + channel.remote_balance)

    return ratio

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
                                    self.effective_max_htlc_msat(channel),
                                    self.policy.getint('time_lock_delta') )
            # disabled = False by default
            if len(result) == 5:
                result = result + ( False, )

            return result
        except Exception as e:
            debug("Error executing strategy '%s'. (Error=%s)" % (strategy, str(e)) )
            return strategy_ignore(channel, self.policy) + (False,)

    def effective_max_htlc_msat(self, channel):
        result = self.policy.getint('max_htlc_msat')

        slices = self.policy.getint('max_htlc_proportional_slices')
        if slices:
            result = calculate_slices(channel.capacity, channel.local_balance, slices) * 1000

        ratio = self.policy.getfloat('max_htlc_msat_ratio')
        if ratio:
            ratio = max(0,min(1,ratio))
            channel_cap = channel.capacity
            channel_cap = channel_cap - channel.remote_constraints.chan_reserve_sat
            ratiomax = int(ratio * channel_cap * 1000)
            if not result:
                result = ratiomax
            else:
                result = min(ratiomax,result)
        return result

@strategy(name = 'ignore')
def strategy_ignore(channel, policy, **kwargs):
    return (None, None, None, None, None)

@strategy(name = 'ignore_fees')
def strategy_ignore_fees(channel, policy, **kwargs):
    return (None, None)

@strategy(name = 'static')
def strategy_static(channel, policy, **kwargs):
    return (policy.getint('base_fee_msat'), policy.getint('fee_ppm'))

@strategy(name = 'proportional')
def strategy_proportional(channel, policy, **kwargs):
    if policy.getint('min_fee_ppm_delta',-1) < 0:
        policy.set('min_fee_ppm_delta', 10) # set delta to 10 if not defined
    ppm_min = policy.getint('min_fee_ppm')
    ppm_max = policy.getint('max_fee_ppm')
    if ppm_min is None or ppm_max is None:
        raise Exception('proportional strategy requires min_fee_ppm and max_fee_ppm properties')

    ratio = get_ratio(channel, policy, **kwargs)

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

@strategy(name = 'proportional_peer_inbound')
def strategy_proportional_peer_inbound(channel, policy, **kwargs):
    lnd = kwargs['lnd']
    chan_info = lnd.get_chan_info(channel.chan_id)
    my_pubkey = lnd.get_own_pubkey()

    peer_node_id = chan_info.node1_pub if chan_info.node2_pub == my_pubkey else chan_info.node2_pub

    # avoid having to fetch get_edges() multiple times
    global edges_cache

    if not edges_cache:
        edges_list = lnd.get_edges()
        # cache only the data we need
        edges = []
        for edge in edges_list:
            the_edge = {
                "node1_pub": edge.node1_pub,
                "node2_pub": edge.node2_pub,
                'capacity': edge.capacity,
                "node1_policy": {
                   'fee_rate_milli_msat': edge.node1_policy.fee_rate_milli_msat,
                   'max_htlc_msat': edge.node1_policy.max_htlc_msat
                },
                "node2_policy": {
                   'fee_rate_milli_msat': edge.node2_policy.fee_rate_milli_msat,
                   'max_htlc_msat': edge.node2_policy.max_htlc_msat
                }
            }
            edges.append(the_edge)
        edges_cache = edges
    else:
        edges = edges_cache

    peer_inbound = []

    total_peer_capacity = 0
    ppm_avg = 0

    for edge in edges:
        if edge['node1_pub'] == peer_node_id:
            if edge['node2_pub'] == my_pubkey:
                # ignore this edge if it's shared between our node and peer
                continue
            inbound = {
                #'capacity': edge['capacity'],
                # We will use the max_htlc_msat // 1000 as the estimated capacity
                'capacity': edge['node2_policy']['max_htlc_msat'] // 1000,
                # We will take node2_policy because we want inbound policy, not outbound
                'fee_rate_milli_msat': edge['node2_policy']['fee_rate_milli_msat']
            }
            total_peer_capacity += inbound['capacity']
            peer_inbound.append(inbound)
        elif edge['node2_pub'] == peer_node_id:
            if edge['node1_pub'] == my_pubkey:
                # ignore this edge if it's shared between our node and peer
                continue
            inbound = {
                #'capacity': edge['capacity'],
                # We will use the max_htlc_msat // 1000 as the estimated capacity
                'capacity': edge['node1_policy']['max_htlc_msat'] // 1000,
                # We will take node1_policy because we want inbound policy, not outbound
                'fee_rate_milli_msat': edge['node1_policy']['fee_rate_milli_msat']
            }
            peer_inbound.append(inbound)
            total_peer_capacity += inbound['capacity']

    # Calculate the weighted average inbound fee by multiplying each fee by
    # the adjusted ratio and taking the sum.

    fee_avg_calc_cutoff_ppm = policy.getint('fee_avg_calc_cutoff_ppm')

    for inbound in peer_inbound:
        if inbound['fee_rate_milli_msat'] >= fee_avg_calc_cutoff_ppm:
            # ignore fee rate values over max_usable_ppm in our calculation
            continue
        ppm_avg += int((inbound['capacity']/total_peer_capacity)*inbound['fee_rate_milli_msat'])

    # Use the same channel ratio calculation as proportional strategy
    ratio = get_ratio(channel, policy, **kwargs)

    ppm_min = policy.getint('min_fee_ppm')
    ppm_max = policy.getint('max_fee_ppm')
    avg_fee_ppm_multiplier = policy.getfloat('avg_fee_ppm_multiplier')
    upper_fee_ppm_multiplier = policy.getfloat('upper_fee_ppm_multiplier')

    if ppm_min is None or ppm_max is None or avg_fee_ppm_multiplier is None or upper_fee_ppm_multiplier is None:
        raise Exception('proportional inbound weighted strategy requires min_fee_ppm, max_fee_ppm, avg_fee_ppm_multiplier, and upper_fee_ppm_multiplier properties')

    if ppm_min >= ppm_max:
        raise Exception('ppm_min should be less than ppm_max')

    # The avg_fee_ppm_multiplier can tweak the ppm_avg to be slightly
    # lower or higher, changing the center-point of the calculation.
    # You might do this if you think the average values are all
    # too cheap or too expensive. We will also make sure the average
    # is not lower than ppm_min here, or higher than ppm_max.
    # It's probably perfectly fine to leave this multiplier at 1.

    ppm_avg = min(ppm_max, max(ppm_min, ppm_avg * avg_fee_ppm_multiplier))

    # The upper_fee_ppm_multiplier sets the upper maximum when calculating
    # the ppm when the local balance proportion drops below 0.5. A value
    # of 2 means that the upper maximum is double the ppm_avg. If you
    # wanted to increase fees more aggressively as the local balance falls,
    # you could choose a higher multiplier.
    # It's probably perfectly fine to leave this multiplier at 2.

    ppm_upper = ppm_avg * upper_fee_ppm_multiplier

    # When the ratio is near half, we want the ppm to be exactly
    # the ppm_avg. When the ratio is lower, we want a higher ppm that
    # is between ppm_avg and ppm_upper. When the ratio is higher,
    # we want a lower ppm between ppm_avg and ppm_min. Since the range
    # between can be unequal, e.g. average = 500, min = 400, max
    # = 3000, we don't want to make the 0.5 ratio be the middle
    # of the range 400 - 3000. It's much larger than the target
    # average of 500. So we calculate the two sides separately.

    if ratio < 0.5:
        ppm = int(ppm_upper + 2 * (ppm_avg - ppm_upper) * ratio)
    elif ratio > 0.5:
        ppm = int(ppm_min + 2 * (ppm_avg - ppm_min) * (1 - ratio))
    else:
        ppm = ppm_avg

    # Cap it to the max
    ppm = min(ppm, ppm_max)

    # clamp to 0..inf
    ppm = max(ppm, 0)

    return (policy.getint('base_fee_msat'), ppm)

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

    if policy.getint('min_fee_ppm_delta',-1) < 0:
        policy.set('min_fee_ppm_delta', 10) # set delta to 10 if not defined

    numblocks = policy.getint('onchain_fee_numblocks', 6)
    sat_per_byte = Electrum.get_fee_estimate(numblocks)
    if sat_per_byte < 1:
        return (None, None, None, None, None)
    reference_payment = policy.getfloat('onchain_fee_btc', 0.1)
    fee_ppm = int((0.01 / reference_payment) * (223 * sat_per_byte))
    return (policy.getint('base_fee_msat'), fee_ppm)

@strategy(name = 'use_config')
def strategy_use_config(channel, policy, **kwargs):
    from .policy import Policies

    rule_file = policy.get('config_file')
    if not rule_file:
        raise Exception("missing `config_file` property for strategy 'use_config'")

    config = Config(rule_file.replace('file://',''))
    policies = Policies(kwargs['lnd'], config)

    ext_policy = policies.get_policy_for(channel)
    if not ext_policy:
        return (None,None)

    r = ext_policy.strategy.execute(channel)

    # propagate values other than direct channel properties
    policy.name = '%s (from %s)' % (ext_policy.name, rule_file)
    policy.set('strategy', ext_policy.get('strategy'))
    if ext_policy.getint('min_fee_ppm_delta',-1) != -1:
        policy.set('min_fee_ppm_delta', ext_policy.getint('min_fee_ppm_delta'))

    return r

@strategy(name = 'disable')
def strategy_disable(channel, policy, **kwargs):
    lnd = kwargs['lnd']
    if not lnd.min_version(0,13):
        raise Exception("Cannot use strategy 'disable', lnd must be at least version 0.13.0")

    return strategy_ignore(channel, policy) + ( True, )
