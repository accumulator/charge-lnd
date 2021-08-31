#!/usr/bin/env python3

import argparse
import sys
import os

import colorama
colorama.init()

from .lnd import Lnd
from .policy import Policies
from .config import Config
from .electrum import Electrum
import charge_lnd.fmt as fmt

def debug(message):
    sys.stderr.write(message + "\n")

def main():
    argument_parser = get_argument_parser()
    arguments = argument_parser.parse_args()

    if arguments.electrum_server:
        Electrum.set_server(arguments.electrum_server)

    if not os.path.exists(arguments.config):
        debug("Config file not found")
        return False

    config = Config(arguments.config)

    if arguments.check:
        debug("Configuration file is valid")
        return True

    # few systems are not utf-8, force so we don't bomb out
    sys.stdout.reconfigure(encoding='utf-8')

    lnd = Lnd(arguments.lnddir, arguments.grpc)
    if not lnd.valid:
        debug("Could not connect to gRPC endpoint")
        return False

    policies = Policies(lnd, config)

    my_pubkey = lnd.get_own_pubkey()

    channels = lnd.get_channels()
    for channel in channels:
        policy = policies.get_policy_for(channel)
        if not policy:
            continue

        (new_base_fee_msat, new_fee_ppm, new_min_htlc, new_max_htlc, new_time_lock_delta, disable) = policy.strategy.execute(channel)

        if channel.chan_id in lnd.feereport:
            (current_base_fee_msat, current_fee_ppm) = lnd.feereport[channel.chan_id]

        chan_info = lnd.get_chan_info(channel.chan_id)
        my_policy = chan_info.node1_policy if chan_info.node1_pub == my_pubkey else chan_info.node2_policy

        min_fee_ppm_delta = policy.getint('min_fee_ppm_delta',0)

        fee_ppm_changed = new_fee_ppm is not None and current_fee_ppm != new_fee_ppm and abs(current_fee_ppm - new_fee_ppm) >= min_fee_ppm_delta

        base_fee_changed = new_base_fee_msat is not None and current_base_fee_msat != new_base_fee_msat
        min_htlc_changed = new_min_htlc is not None and my_policy.min_htlc != new_min_htlc
        max_htlc_changed = new_max_htlc is not None and my_policy.max_htlc_msat != new_max_htlc
        time_lock_delta_changed = new_time_lock_delta is not None and my_policy.time_lock_delta != new_time_lock_delta
        is_changed = fee_ppm_changed or base_fee_changed or min_htlc_changed or max_htlc_changed or time_lock_delta_changed

        chan_status_changed = False
        if lnd.min_version(0,13) and channel.active and disable != my_policy.disabled and policy.get('strategy') != 'ignore':
            if not arguments.dry_run:
                lnd.update_chan_status(channel.chan_id, disable)
            chan_status_changed = True

        if is_changed or chan_status_changed or arguments.verbose:
            print (
                fmt.col_lo(fmt.print_chanid(channel.chan_id).ljust(14)) +
                fmt.print_node(lnd.get_node_info(channel.remote_pubkey))
                )

        if is_changed and not arguments.dry_run:
            lnd.update_chan_policy(channel.chan_id, new_base_fee_msat, new_fee_ppm, new_min_htlc, new_max_htlc, new_time_lock_delta)

        if is_changed or chan_status_changed or arguments.verbose:
            print("  policy:          %s" % fmt.col_hi(policy.name) )
            print("  strategy:        %s" % fmt.col_hi(policy.get('strategy')) )
            if new_base_fee_msat is not None or arguments.verbose:
                s = ''
                if base_fee_changed:
                    s = ' ➜ ' + fmt.col_hi(new_base_fee_msat)
                print("  base_fee_msat:   %s%s" % (fmt.col_hi(current_base_fee_msat), s) )
            if new_fee_ppm is not None or arguments.verbose:
                s = ''
                if fee_ppm_changed:
                    s = ' ➜ ' + fmt.col_hi(new_fee_ppm)
                    if min_fee_ppm_delta > abs(new_fee_ppm - current_fee_ppm):
                        s = s + ' (min_fee_ppm_delta=%d)' % min_fee_ppm_delta
                print("  fee_ppm:         %s%s" % (fmt.col_hi(current_fee_ppm), s) )
            if new_min_htlc is not None or arguments.verbose:
                s = ''
                if min_htlc_changed:
                    s = ' ➜ ' + fmt.col_hi(new_min_htlc)
                print("  min_htlc_msat:   %s%s" % (fmt.col_hi(my_policy.min_htlc), s) )
            if new_max_htlc is not None or arguments.verbose:
                s = ''
                if max_htlc_changed:
                    s = ' ➜ ' + fmt.col_hi(new_max_htlc)
                print("  max_htlc_msat:   %s%s" % (fmt.col_hi(my_policy.max_htlc_msat), s) )
            if new_time_lock_delta is not None or arguments.verbose:
                s = ''
                if time_lock_delta_changed:
                    s = ' ➜ ' + fmt.col_hi(new_time_lock_delta)
                print("  time_lock_delta: %s%s" % (fmt.col_hi(my_policy.time_lock_delta), s) )

    return True

def get_argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lnddir",
                        default="~/.lnd",
                        dest="lnddir",
                        help="(default ~/.lnd) lnd directory")
    parser.add_argument("--grpc",
                        default="localhost:10009",
                        dest="grpc",
                        help="(default localhost:10009) lnd gRPC endpoint")
    parser.add_argument("--electrum-server",
                        dest="electrum_server",
                        help="(optional, no default) electrum server host:port . Needed for onchain_fee.")
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
