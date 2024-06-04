#!/usr/bin/env python3

import argparse
import sys
import os

import colorama
colorama.init()

from .lnd import Lnd
from .policy import Policies
from .strategy import is_defined
from .config import Config
from .circuitbreaker import Circuitbreaker
import charge_lnd.fmt as fmt

def debug(message):
    sys.stderr.write(message + "\n")

def main():
    argument_parser = get_argument_parser()
    arguments = argument_parser.parse_args()

    if not os.path.exists(arguments.config):
        debug("Config file not found")
        return False

    config = Config(arguments.config)

    if arguments.check:
        debug("Configuration file is valid")
        return True

    # few systems are not utf-8, force so we don't bomb out
    sys.stdout.reconfigure(encoding='utf-8')

    lnd = Lnd(arguments.lnddir, arguments.grpc, arguments.tls_cert_path, arguments.macaroon_path)
    if not lnd.valid:
        debug("Could not connect to lnd gRPC endpoint")
        return False

    cb = None
    if arguments.circuitbreaker:
        cb = Circuitbreaker(arguments.circuitbreaker)
        if not cb.valid:
            debug("Could not connect to circuitbreaker gRPC endpoint")
            return False
        if cb.get_info().node_key != lnd.get_info().identity_pubkey:
            debug("node_key of circuitbreaker is different from pubkey of lnd")
            return False

    policies = Policies(lnd, config)

    my_pubkey = lnd.get_own_pubkey()

    channels = lnd.get_channels()
    for channel in channels:
        policy = policies.get_policy_for(channel)
        if not policy:
            continue

        chp = policy.strategy.execute(channel)

        if cb and is_defined(chp.circuitbreaker_params):
            cb.apply_params(chp.circuitbreaker_params, channel.remote_pubkey)

        if channel.chan_id in lnd.feereport:
            (current_base_fee_msat, current_fee_ppm) = lnd.feereport[channel.chan_id]

        chan_info = lnd.get_chan_info(channel.chan_id)
        if not chan_info:
            print ("could not lookup channel info for " + fmt.print_chanid(channel.chan_id).ljust(14) + ", skipping")
            continue

        my_policy = chan_info.node1_policy if chan_info.node1_pub == my_pubkey else chan_info.node2_policy

        min_fee_ppm_delta = policy.getint('min_fee_ppm_delta',0)

        fee_ppm_changed = is_defined(chp.fee_ppm) and current_fee_ppm != chp.fee_ppm and abs(current_fee_ppm - chp.fee_ppm) >= min_fee_ppm_delta
        base_fee_changed = is_defined(chp.base_fee_msat) and current_base_fee_msat != chp.base_fee_msat

        min_inbound_fee_ppm_delta = policy.getint('min_inbound_fee_ppm_delta', min_fee_ppm_delta)
        inbound_fee_ppm_changed = inbound_base_fee_changed = False
        if lnd.supports_inbound_fees():
            # If there is any definied inbound_level we recalculate the inbound fee rate.
            if is_defined(chp.inbound_level_ppm):
                chp.inbound_fee_ppm = min(0,
                    chp.inbound_level_ppm - (chp.fee_ppm if fee_ppm_changed else current_fee_ppm))

            # We'd like to avoid updating the inbound fee rate if the change is lower than the min delta,
            # even in the case other outbound properties have changed.
            # The goal is to minimize the gossip around the inbound fees, because at the moment there
            # are no updates for the incoming channel in the case of a FeeInsuffient error.
            # (https://github.com/lightningnetwork/lnd/pull/6967)
            # First we check if the base fee changed. In this case we will advance the inbound
            # fee anyway.
            inbound_base_fee_changed = is_defined(chp.inbound_base_fee_msat) \
                and my_policy.inbound_fee_base_msat != chp.inbound_base_fee_msat

            if is_defined(chp.inbound_fee_ppm) \
                and not inbound_base_fee_changed \
                and abs(my_policy.inbound_fee_rate_milli_msat - chp.inbound_fee_ppm) < min_inbound_fee_ppm_delta:

                chp.inbound_fee_ppm = my_policy.inbound_fee_rate_milli_msat

            inbound_fee_ppm_changed = is_defined(chp.inbound_fee_ppm) \
                and my_policy.inbound_fee_rate_milli_msat != chp.inbound_fee_ppm

        # We are using the local constraints as a floor for min_htlc and as a cap for max_htlc.
        # Otherwise, e.g. if min_htlc is too low, lnd cannot perform the whole policy update.
        if is_defined(chp.min_htlc_msat):
            chp.min_htlc_msat = max(chp.min_htlc_msat, channel.local_constraints.min_htlc_msat)
        if is_defined(chp.max_htlc_msat):
            chp.max_htlc_msat = min(chp.max_htlc_msat, channel.local_constraints.max_pending_amt_msat)

        min_htlc_changed = is_defined(chp.min_htlc_msat) and my_policy.min_htlc != chp.min_htlc_msat
        max_htlc_changed = is_defined(chp.max_htlc_msat) and my_policy.max_htlc_msat != chp.max_htlc_msat
        time_lock_delta_changed = is_defined(chp.time_lock_delta) and my_policy.time_lock_delta != chp.time_lock_delta
        is_changed = fee_ppm_changed or base_fee_changed or min_htlc_changed or max_htlc_changed or \
            time_lock_delta_changed or inbound_base_fee_changed or inbound_fee_ppm_changed

        chan_status_changed = False
        if lnd.min_version(0, 13) and channel.active and chp.disabled != my_policy.disabled and policy.get('strategy') != 'ignore':
            if not arguments.dry_run:
                lnd.update_chan_status(channel.chan_id, chp.disabled)
            chan_status_changed = True

        if is_changed or chan_status_changed or arguments.verbose:
            print (
                fmt.col_lo(fmt.print_chanid(channel.chan_id).ljust(14)) +
                fmt.print_node(lnd.get_node_info(channel.remote_pubkey))
                )

        if is_changed and not arguments.dry_run:
            lnd.update_chan_policy(channel.chan_id, chp)

        if is_changed or chan_status_changed or arguments.verbose:
            print("  policy:                  %s" % fmt.col_hi(policy.name) )
            print("  strategy:                %s" % fmt.col_hi(policy.get('strategy')) )
            if chan_status_changed or arguments.verbose:
                s = 'disabled' if my_policy.disabled else 'enabled'
                if chan_status_changed:
                    s = s + ' ➜ '
                    s = s + 'disabled' if chp.disabled else 'enabled'
                print("  channel status:          %s" % fmt.col_hi(s))
            if is_defined(chp.base_fee_msat) or arguments.verbose:
                s = ''
                if base_fee_changed:
                    s = ' ➜ ' + fmt.col_hi(chp.base_fee_msat)
                print("  base_fee_msat:           %s%s" % (fmt.col_hi(current_base_fee_msat), s) )
            if is_defined(chp.fee_ppm) or arguments.verbose:
                s = ''
                if fee_ppm_changed:
                    s = ' ➜ ' + fmt.col_hi(chp.fee_ppm)
                    if min_fee_ppm_delta > abs(chp.fee_ppm - current_fee_ppm):
                        s = s + ' (min_fee_ppm_delta=%d)' % min_fee_ppm_delta
                print("  fee_ppm:                 %s%s" % (fmt.col_hi(current_fee_ppm), s) )
            if is_defined(chp.inbound_base_fee_msat) or arguments.verbose:
                s = ''
                if inbound_base_fee_changed:
                    s = ' ➜ ' + fmt.col_hi(chp.inbound_base_fee_msat)
                print("  inbound_base_fee_msat:   %s%s" % (fmt.col_hi(my_policy.inbound_fee_base_msat), s) )
            if is_defined(chp.inbound_fee_ppm) or arguments.verbose:
                s = ''
                if inbound_fee_ppm_changed:
                    s = ' ➜ ' + fmt.col_hi(chp.inbound_fee_ppm)
                    if min_inbound_fee_ppm_delta > abs(chp.inbound_fee_ppm - my_policy.inbound_fee_rate_milli_msat):
                        s = s + ' (min_inbound_fee_ppm_delta=%d)' % min_inbound_fee_ppm_delta
                print("  inbound_fee_ppm:         %s%s" % (fmt.col_hi(my_policy.inbound_fee_rate_milli_msat), s) )
            if is_defined(chp.min_htlc_msat) or arguments.verbose:
                s = ''
                if min_htlc_changed:
                    s = ' ➜ ' + fmt.col_hi(chp.min_htlc_msat)
                print("  min_htlc_msat:           %s%s" % (fmt.col_hi(my_policy.min_htlc), s) )
            if is_defined(chp.max_htlc_msat) or arguments.verbose:
                s = ''
                if max_htlc_changed:
                    s = ' ➜ ' + fmt.col_hi(chp.max_htlc_msat)
                print("  max_htlc_msat:           %s%s" % (fmt.col_hi(my_policy.max_htlc_msat), s) )
            if is_defined(chp.time_lock_delta) or arguments.verbose:
                s = ''
                if time_lock_delta_changed:
                    s = ' ➜ ' + fmt.col_hi(chp.time_lock_delta)
                print("  time_lock_delta:         %s%s" % (fmt.col_hi(my_policy.time_lock_delta), s) )

    if cb:
         update_circuitbreaker(cb, lnd, arguments)

    return True

# Updates the circuitbreaker backend with all necessary limit changes.
def update_circuitbreaker(cb: Circuitbreaker, lnd: Lnd, arguments):
    clear_limits, update_limits = cb.get_limit_updates()

    # The for loop is only for printing the changes to the current state.
    for peer in clear_limits + list(update_limits.keys()):
        limit_current = cb.get_limit(peer)

        is_deleted = peer in clear_limits and limit_current is not None
        is_new = peer in update_limits and limit_current is None

        is_update_candidate = peer in update_limits and limit_current is not None
        is_updated = False
        if is_update_candidate:
            is_updated_rate = update_limits[peer].max_hourly_rate != limit_current.max_hourly_rate
            is_updated_pending = update_limits[peer].max_pending != limit_current.max_pending
            is_updated_mode = update_limits[peer].mode != limit_current.mode
            is_updated = any([is_updated_rate, is_updated_pending, is_updated_mode])

        is_changed = any([is_deleted, is_new, is_updated])

        if is_changed or (is_update_candidate and arguments.verbose):
            print(fmt.print_node(lnd.get_node_info(peer)))
            print("  service:                 circuitbreaker")

        if is_deleted:
            s = ' ➜ ' + fmt.col_hi("default")
            print("  max_hourly_rate:         %s%s" % (fmt.col_hi(limit_current.max_hourly_rate), s) )
            print("  max_pending:             %s%s" % (fmt.col_hi(limit_current.max_pending), s) )
            print("  mode:                    %s%s" % (fmt.col_hi(limit_current.mode), s) )

        if is_new:
            s = fmt.col_hi("default") + ' ➜ '
            print("  max_hourly_rate:         %s%s" % (s, fmt.col_hi(update_limits[peer].max_hourly_rate)) )
            print("  max_pending:             %s%s" % (s, fmt.col_hi(update_limits[peer].max_pending)) )
            print("  mode:                    %s%s" % (s, fmt.col_hi(update_limits[peer].mode)) )

        if is_updated or (is_update_candidate and arguments.verbose):
            if is_updated_rate or arguments.verbose:
                s = ''
                if is_updated_rate:
                    s = ' ➜ ' + fmt.col_hi(update_limits[peer].max_hourly_rate)
                print("  max_hourly_rate:         %s%s" % (fmt.col_hi(limit_current.max_hourly_rate), s) )

            if is_updated_pending or arguments.verbose:
                s = ''
                if is_updated_pending:
                    s = ' ➜ ' + fmt.col_hi(update_limits[peer].max_pending)
                print("  max_pending:             %s%s" % (fmt.col_hi(limit_current.max_pending), s) )

            if is_updated_mode or arguments.verbose:
                s = ''
                if is_updated_mode:
                    s = ' ➜ ' + fmt.col_hi(update_limits[peer].mode)
                print("  mode:                    %s%s" % (fmt.col_hi(limit_current.mode), s) )

    # Eventually, we are updating the circuitbreaker backend.
    if not arguments.dry_run:
        cb.clear_limits(clear_limits)
        cb.update_limits(update_limits)


def get_argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lnddir",
                        default="~/.lnd",
                        dest="lnddir",
                        help="(default ~/.lnd) lnd directory")
    parser.add_argument("--tlscert",
                        dest="tls_cert_path",
                        help="(default [lnddir]/tls.cert) path to lnd TLS certificate")
    parser.add_argument("--macaroon",
                        dest="macaroon_path",
                        help="(default [lnddir]/data/chain/bitcoin/mainnet/charge-lnd.macaroon) path to lnd auth macaroon")
    parser.add_argument("--grpc",
                        default="localhost:10009",
                        dest="grpc",
                        help="(default localhost:10009) lnd gRPC endpoint")
    parser.add_argument("--circuitbreaker",
                        dest="circuitbreaker",
                        help="(optional, no default) circuitbreaker gRPC endpoint host:port")
    parser.add_argument("--dry-run",
                        dest="dry_run",
                        action="store_true",
                        help="Do not perform actions (for testing), print what we would do to stdout")
    parser.add_argument("--check",
                        dest="check",
                        action="store_true",
                        help="Do not perform actions, only check config file for valid syntax")
    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        help="Be more verbose")
    parser.add_argument("-c", "--config",
                        required=True,
                        help="path to config file")
    return parser


success = main()
if success:
    sys.exit(0)
sys.exit(1)
