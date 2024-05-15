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

    lnd = Lnd(arguments.lnddir, arguments.grpc, arguments.tls_cert_path, arguments.macaroon_path)
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

        chp = policy.strategy.execute(channel)

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

        inbound_fee_ppm_changed = lnd.supports_inbound_fees() \
            and is_defined(chp.inbound_fee_ppm) \
            and my_policy.inbound_fee_rate_milli_msat != chp.inbound_fee_ppm \
            and abs(my_policy.inbound_fee_rate_milli_msat - chp.inbound_fee_ppm) >= min_fee_ppm_delta

        inbound_base_fee_changed = lnd.supports_inbound_fees() \
            and is_defined(chp.inbound_base_fee_msat) \
            and my_policy.inbound_fee_base_msat != chp.inbound_base_fee_msat

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
                    if min_fee_ppm_delta > abs(chp.inbound_fee_ppm - my_policy.inbound_fee_rate_milli_msat):
                        s = s + ' (min_fee_ppm_delta=%d)' % min_fee_ppm_delta
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

    return True

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
    parser.add_argument("--electrum-server",
                        dest="electrum_server",
                        help="(optional, no default) electrum server host:port[:s]. Needed for onchain_fee. Append ':s' for SSL connection")
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
