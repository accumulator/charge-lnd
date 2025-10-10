#!/usr/bin/env python3
import sys
import functools
from typing import Optional, Union
from types import SimpleNamespace

from . import fmt
from .config import Config
from .circuitbreaker import CircuitbreakerParams

def debug(message):
    sys.stderr.write(message + "\n")

KEEP='keep'
DONTCARE='dontcare'
DEFAULT_CONF_TARGET=6

def is_defined(x):
    return x not in [KEEP, DONTCARE] and x is not None

class ChanParams(SimpleNamespace):
    base_fee_msat: Optional[Union[str, int]] = DONTCARE
    fee_ppm: Optional[Union[str, int]] = DONTCARE
    min_htlc_msat: Optional[Union[str, int]] = DONTCARE
    max_htlc_msat: Optional[Union[str, int]] = DONTCARE
    time_lock_delta: Optional[Union[str, int]] = DONTCARE
    inbound_base_fee_msat: Optional[Union[str, int]] = DONTCARE
    inbound_fee_ppm: Optional[Union[str, int]] = DONTCARE
    inbound_level_ppm: Optional[Union[str, int]] = DONTCARE
    disabled: Optional[Union[str, bool]] = DONTCARE
    circuitbreaker_params: Optional[Union[str, CircuitbreakerParams]] = DONTCARE

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
            if result.min_htlc_msat == DONTCARE:
                result.min_htlc_msat = self.policy.getint('min_htlc_msat')
            if result.max_htlc_msat == DONTCARE:
                result.max_htlc_msat = self.effective_max_htlc_msat(channel)
            if result.time_lock_delta == DONTCARE:
                result.time_lock_delta = self.policy.getint('time_lock_delta')
            if result.disabled == DONTCARE:
                result.disabled = False
            if result.circuitbreaker_params == DONTCARE:
                result.circuitbreaker_params = CircuitbreakerParams(
                    max_hourly_rate=self.policy.getint('cb_max_hourly_rate'),
                    max_pending=self.policy.getint('cb_max_pending'),
                    mode=self.policy.getint('cb_mode'),
                    clear_limit=self.policy.getbool('cb_clear_limit')
                )

            return result
        except Exception as e:
            debug("Error executing strategy '%s'. (Error=%s)" % (strategy, str(e)) )
            return strategy_ignore(channel, self.policy)

    def effective_max_htlc_msat(self, channel):
        result = self.policy.getint('max_htlc_msat')
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
    return ChanParams(
        base_fee_msat=KEEP,
        fee_ppm=KEEP,
        min_htlc_msat=KEEP,
        max_htlc_msat=KEEP,
        time_lock_delta=KEEP,
        inbound_base_fee_msat=KEEP,
        inbound_fee_ppm=KEEP,
        disabled=KEEP,
        circuitbreaker_params=KEEP
    )

@strategy(name = 'ignore_fees')
def strategy_ignore_fees(channel, policy, **kwargs):
    return ChanParams(
        base_fee_msat=KEEP,
        fee_ppm=KEEP,
        inbound_base_fee_msat=KEEP,
        inbound_fee_ppm=KEEP
    )

@strategy(name = 'static')
def strategy_static(channel, policy, **kwargs):
    return ChanParams(
        base_fee_msat=policy.getint('base_fee_msat'),
        fee_ppm=policy.getint('fee_ppm'),
        inbound_base_fee_msat=policy.getint('inbound_base_fee_msat'),
        inbound_fee_ppm=policy.getint('inbound_fee_ppm'),
        inbound_level_ppm=policy.getint('inbound_level_ppm'),
    )

@strategy(name = 'proportional')
def strategy_proportional(channel, policy, **kwargs):
    lnd = kwargs['lnd']
    
    if policy.getint('min_fee_ppm_delta',-1) < 0:
        policy.set('min_fee_ppm_delta', 10) # set delta to 10 if not defined
    ppm_min = policy.getint('min_fee_ppm')
    ppm_max = policy.getint('max_fee_ppm')
    if ppm_min is None or ppm_max is None:
        raise Exception('proportional strategy requires min_fee_ppm and max_fee_ppm properties')

    if policy.getbool('sum_peer_chans', False):
        metrics = lnd.get_peer_metrics(channel.remote_pubkey)    
        
        local_balance = metrics.local_active_balance_total() 
        remote_balance = metrics.remote_active_balance_total() 
        total_balance = local_balance + remote_balance
        
        if metrics.channels_active == 0:
            # Sum inactive channels because the node is likely offline with no active channels.
            # When they come back online their fees won't be changed.
            local_balance += metrics.local_inactive_balance_total()
            remote_balance += metrics.remote_inactive_balance_total()
        total_balance = local_balance + remote_balance
        ratio = local_balance/total_balance
    else:
        metrics = lnd.get_chan_metrics(channel.chan_id)
        
        local_balance = metrics.local_balance_total()
        remote_balance = metrics.remote_balance_total()
        ratio = local_balance/(local_balance + remote_balance)

    ppm = int(ppm_min + (1.0 - ratio) * (ppm_max - ppm_min))
    # clamp to 0..inf
    ppm = max(ppm,0)

    return ChanParams(
        base_fee_msat=policy.getint('base_fee_msat'),
        fee_ppm=ppm,
        inbound_base_fee_msat=policy.getint('inbound_base_fee_msat'),
        inbound_fee_ppm=policy.getint('inbound_fee_ppm'),
        inbound_level_ppm=policy.getint('inbound_level_ppm'),
    )

@strategy(name = 'match_peer')
def strategy_match_peer(channel, policy, **kwargs):
    lnd = kwargs['lnd']
    chan_info = lnd.get_chan_info(channel.chan_id)
    my_pubkey = lnd.get_own_pubkey()
    peernode_policy = chan_info.node1_policy if chan_info.node2_pub == my_pubkey else chan_info.node2_policy

    return ChanParams(
        base_fee_msat=policy.getint('base_fee_msat', peernode_policy.fee_base_msat),
        fee_ppm=policy.getint('fee_ppm', peernode_policy.fee_rate_milli_msat),
        inbound_base_fee_msat=policy.getint('inbound_base_fee_msat', peernode_policy.inbound_fee_base_msat),
        inbound_fee_ppm=policy.getint('inbound_fee_ppm', peernode_policy.inbound_fee_rate_milli_msat)
    )

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

    return ChanParams(
        base_fee_msat=policy.getint('base_fee_msat'),
        fee_ppm=ppm,
        inbound_base_fee_msat=policy.getint('inbound_base_fee_msat'),
        inbound_fee_ppm=policy.getint('inbound_fee_ppm'),
        inbound_level_ppm=policy.getint('inbound_level_ppm'),
    )


@strategy(name = 'onchain_fee')
def strategy_onchain_fee(channel, policy, **kwargs):
    lnd = kwargs['lnd']
    if policy.getint('min_fee_ppm_delta',-1) < 0:
        policy.set('min_fee_ppm_delta', 10) # set delta to 10 if not defined

    numblocks = policy.getint('onchain_fee_numblocks', DEFAULT_CONF_TARGET)
    sat_per_byte = lnd.get_fee_estimate(numblocks)
    if sat_per_byte < 1:
        return (None, None, None, None, None)
    reference_payment = policy.getfloat('onchain_fee_btc', 0.1)
    fee_ppm = int((0.01 / reference_payment) * (223 * sat_per_byte))

    return ChanParams(
        base_fee_msat=policy.getint('base_fee_msat'),
        fee_ppm=fee_ppm,
        inbound_base_fee_msat=policy.getint('inbound_base_fee_msat'),
        inbound_fee_ppm=policy.getint('inbound_fee_ppm'),
        inbound_level_ppm=policy.getint('inbound_level_ppm'),
    )


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
        return ChanParams()

    r = ext_policy.strategy.execute(channel)

    # propagate values other than direct channel properties
    policy.name = '%s (from %s)' % (ext_policy.name, rule_file)
    policy.set('strategy', ext_policy.get('strategy'))
    if ext_policy.getint('min_fee_ppm_delta',-1) != -1:
        policy.set('min_fee_ppm_delta', ext_policy.getint('min_fee_ppm_delta'))

    return r

@strategy(name = 'flow_based')
def strategy_flow_based(channel, policy, **kwargs):
    """
    Flow-based fee strategy similar to Lightning Terminal's autofees.

    Adjusts fees based on:
    1. Target throughput calculated from top earning channels
    2. Recent forwarding performance vs target
    3. Channel liquidity levels (scarcity pricing)
    4. Incremental adjustments to avoid fee volatility
    """
    lnd = kwargs['lnd']

    # Configuration parameters with defaults
    reference_period_days = policy.getint('reference_period_days', 60)
    analysis_period_days = policy.getint('analysis_period_days', 7)
    top_earners_count = policy.getint('top_earners_count', 5)
    fee_adjustment_pct = policy.getfloat('fee_adjustment_pct', 5.0)
    liquidity_threshold = policy.getfloat('liquidity_threshold', 0.125)  # 1/8
    scarcity_multiplier = policy.getfloat('scarcity_multiplier', 1.2)
    min_fee_ppm = policy.getint('min_fee_ppm', 1)
    max_fee_ppm = policy.getint('max_fee_ppm', 5000)
    base_fee_msat = policy.getint('base_fee_msat', 1000)
    # Peer consistency option
    sum_peer_chans = policy.getbool('sum_peer_chans', False)

    # Get current fee as starting point
    current_fee_ppm = policy.getint('fee_ppm', 100)  # fallback if not set
    if channel.chan_id in lnd.feereport:
        (_, current_fee_ppm) = lnd.feereport[channel.chan_id]

    try:
        # Calculate target throughput from top earning channels
        target_throughput = _calculate_target_throughput(
            lnd, reference_period_days, top_earners_count
        )

        # Get recent forwarding performance
        if sum_peer_chans:
            # Calculate performance for all channels to this peer combined
            peer_channels = lnd.get_peer_channels(channel.remote_pubkey)
            recent_performance = sum(_get_recent_performance(lnd, ch.chan_id, analysis_period_days)
                                   for ch in peer_channels)
            # Use peer metrics for liquidity calculation
            peer_metrics = lnd.get_peer_metrics(channel.remote_pubkey)
            total_local = peer_metrics.local_active_balance_total()
            total_capacity = total_local + peer_metrics.remote_active_balance_total()
            local_ratio = total_local / total_capacity if total_capacity > 0 else 0
        else:
            # Calculate performance for this channel only
            recent_performance = _get_recent_performance(
                lnd, channel.chan_id, analysis_period_days
            )
            # Use individual channel liquidity
            local_ratio = channel.local_balance / channel.capacity if channel.capacity > 0 else 0

        # Calculate fee adjustment based on performance vs target
        performance_ratio = recent_performance / target_throughput if target_throughput > 0 else 0

        # Base fee adjustment logic
        if performance_ratio < 0.8:  # Underperforming - lower fees to attract traffic
            adjustment_factor = 1.0 - (fee_adjustment_pct / 100.0)
        elif performance_ratio > 1.2:  # Overperforming - raise fees to capture value
            adjustment_factor = 1.0 + (fee_adjustment_pct / 100.0)
        else:  # Performing within target range - minimal adjustment
            adjustment_factor = 1.0

        # Apply scarcity pricing if liquidity is low
        if local_ratio < liquidity_threshold:
            adjustment_factor *= scarcity_multiplier

        # Calculate new fee
        new_fee_ppm = int(current_fee_ppm * adjustment_factor)

        # Apply bounds
        new_fee_ppm = max(min_fee_ppm, min(max_fee_ppm, new_fee_ppm))

        return ChanParams(
            base_fee_msat=base_fee_msat,
            fee_ppm=new_fee_ppm,
            inbound_base_fee_msat=policy.getint('inbound_base_fee_msat'),
            inbound_fee_ppm=policy.getint('inbound_fee_ppm'),
            inbound_level_ppm=policy.getint('inbound_level_ppm'),
        )

    except Exception as e:
        # Fallback to current fees if calculation fails
        debug(f"Flow-based strategy failed for channel {channel.chan_id}: {str(e)}")
        return ChanParams(
            base_fee_msat=base_fee_msat,
            fee_ppm=current_fee_ppm,
            inbound_base_fee_msat=policy.getint('inbound_base_fee_msat'),
            inbound_fee_ppm=policy.getint('inbound_fee_ppm'),
            inbound_level_ppm=policy.getint('inbound_level_ppm'),
        )


def _calculate_target_throughput(lnd, reference_period_days, top_earners_count):
    """Calculate target throughput based on top earning channels."""
    reference_seconds = reference_period_days * 24 * 60 * 60

    # Get all channels and their forwarding history
    channels = lnd.get_channels()
    channel_earnings = []

    for channel in channels:
        fwd_history = lnd.get_forward_history(channel.chan_id, reference_seconds)
        # Calculate earnings (simplified - could be more sophisticated)
        total_forwarded = fwd_history['sat_out']
        channel_earnings.append(total_forwarded)

    if not channel_earnings:
        return 0

    # Sort and get top earners
    channel_earnings.sort(reverse=True)
    top_earners = channel_earnings[:min(top_earners_count, len(channel_earnings))]

    # Calculate average of top earners as target
    if top_earners:
        return sum(top_earners) / len(top_earners)
    else:
        return 0


def _get_recent_performance(lnd, chan_id, analysis_period_days):
    """Get recent forwarding performance for a specific channel."""
    analysis_seconds = analysis_period_days * 24 * 60 * 60
    fwd_history = lnd.get_forward_history(chan_id, analysis_seconds)
    return fwd_history['sat_out']


@strategy(name = 'disable')
def strategy_disable(channel, policy, **kwargs):
    lnd = kwargs['lnd']
    if not lnd.min_version(0,13):
        raise Exception("Cannot use strategy 'disable', lnd must be at least version 0.13.0")

    chanparams = strategy_ignore(channel, policy)
    chanparams.disabled=True
    # We want to allow changes to the Circuitbreaker params, such as blocking incoming htlcs.
    chanparams.circuitbreaker_params = DONTCARE
    return chanparams
