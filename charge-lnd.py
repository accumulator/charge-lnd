#!/usr/bin/env python3

import argparse
import configparser
import sys
import os

import colorama
colorama.init()

from lnd import Lnd
from matcher import Matcher
from electrum import Electrum
import fmt

MAX_CHANNEL_CAPACITY = 16777215

def debug(message):
    sys.stderr.write(message + "\n")

def main():
    argument_parser = get_argument_parser()
    arguments = argument_parser.parse_args()

    lnd = Lnd(arguments.lnddir, arguments.grpc)

    if arguments.electrum_server:
        Electrum.set_server(arguments.electrum_server)

    config = configparser.ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]})
    config.read(arguments.config)

    if not os.path.exists(arguments.config):
        debug("Config file not found")
        return False

    matcher = Matcher(lnd, config)

    channels = lnd.get_channels()
    for channel in channels:
        policy = matcher.get_policy(channel)

        (new_base_fee_msat, new_fee_ppm) = policy.execute(channel)

        if channel.chan_id in lnd.feereport:
            (current_base_fee_msat, current_fee_ppm) = lnd.feereport[channel.chan_id]

        fee_ppm_changed = new_fee_ppm and current_fee_ppm != new_fee_ppm
        base_fee_changed = new_base_fee_msat and current_base_fee_msat != new_base_fee_msat
        is_changed = fee_ppm_changed or base_fee_changed

        if is_changed or arguments.verbose:
            print (
                fmt.col_lo(fmt.print_chanid(channel.chan_id).ljust(14)) +
                fmt.print_node(lnd.get_node_info(channel.remote_pubkey))
                )

        if is_changed and not arguments.dry_run:
            lnd.update_chan_policy(channel.chan_id, new_base_fee_msat, new_fee_ppm)

        if is_changed or arguments.verbose:
            print("  policy:        %s" % fmt.col_hi(policy.name) )
            print("  strategy:      %s" % fmt.col_hi(policy.config.get('strategy')) )
            if new_base_fee_msat is not None:
                s = ''
                if base_fee_changed:
                    s = ' ➜ ' + fmt.col_hi(new_base_fee_msat)
                print("  base_fee_msat: %s%s" % (fmt.col_hi(current_base_fee_msat), s) )
            if new_fee_ppm is not None:
                s = ''
                if fee_ppm_changed:
                    s = ' ➜ ' + fmt.col_hi(new_fee_ppm)
                print("  fee_ppm:       %s%s" % (fmt.col_hi(current_fee_ppm), s) )

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
    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        help="Be more verbose")
    parser.add_argument("-c", "--config",
                        default="charge.config",
                        help="(default: charge.config) path to config file")
    return parser


success = main()
if success:
    sys.exit(0)
sys.exit(1)
