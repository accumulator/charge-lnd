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
        print (fmt.col_lo(fmt.print_chanid(channel.chan_id).ljust(14)) + fmt.print_node(lnd.get_node_info(channel.remote_pubkey)) + ' ➜ ' + fmt.col_hi(policy.name))
        (base_fee_msat, fee_ppm) = policy.execute(channel)
        if arguments.verbose:
            print("  strategy:      %s" % fmt.col_hi(policy.config.get('strategy')) )
            if base_fee_msat is not None:
                print("  base_fee_msat: %s" % fmt.col_hi(base_fee_msat) )
            if fee_ppm is not  None:
                print("  fee_ppm:       %s" % fmt.col_hi(fee_ppm) )
        if fee_ppm is not None or base_fee_msat is not None:
            lnd.update_chan_policy(channel.chan_id, base_fee_msat, fee_ppm, arguments.dry_run)

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
