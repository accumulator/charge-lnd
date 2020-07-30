# charge-lnd

This script matches your open channels against a number of customizable criteria and applies a channel policy based on the matching section.

## Installation

This script needs a moderately recent lnd (https://github.com/lightningnetwork/lnd) instance running.

You don't need to have full admin rights to use charge-lnd. The following access rights are used:
- `offchain:read`
- `offchain:write`
- `onchain:read`
- `info:read`

You can create a suitably limited macaroon by issueing:

```
$ lncli bakemacaroon offchain:read offchain:write onchain:read info:read --save_to=~/.lnd/data/chain/bitcoin/mainnet/charge-lnd.macaroon
```

By default this script connects to `localhost:10009`, using the macaroon file in `~/.lnd/data/chain/bitcoin/mainnet/charge-lnd.macaroon`. If `charge-lnd.macaroon` is not found, `admin.macaroon` will be tried.

If you need to change this, please have a look at the optional arguments `--grpc` and `--lnddir`.

You need to install Python. The gRPC dependencies can be installed by running:

```
$ pip install -r requirements.txt
```

On some systems using Python 3, use pip3 instead:

```
$ pip3 install -r requirements.txt
```

## Usage

charge-lnd takes only a minimal set of parameters:

```
usage: charge-lnd.py [-h] [--lnddir LNDDIR] [--grpc GRPC]
                     [--electrum-server ELECTRUM_SERVER] [-c CONFIG]

optional arguments:
  -h, --help            show this help message and exit
  --lnddir LNDDIR       (default ~/.lnd) lnd directory
  --grpc GRPC           (default localhost:10009) lnd gRPC endpoint
  --electrum-server ELECTRUM_SERVER
                        (no default) electrum server host:port
  -c CONFIG, --config CONFIG
                        (default: charge.config) path to config file
```

All policies are defined using an INI style config file (defaults to `charge.config` in the current directory)

Each `[section]` defined in the config file describes a policy.
A single policy consists of;
- a set of properties to match against the channel/node
- a fee strategy

The defined properties are compared against the channels and associated nodes.
The fee strategy then defines how to set the channel fees.

For example:
```
[example-policy]
chan.min_capacity = 500000

strategy = static
base_fee_msat = 1000
fee_ppm = 10
```

This policy matches the channels against the `chan.min_capacity` property. Only channels with at least 500000 sats total capacity will match.

If a channel matches this policy, the `static` strategy is then used, which takes the `base_fee_msat` and `fee_ppm`  properties defined in the policy and applies them to the channel.

There is a special `[default]` section, that will be used if none of the policies matches a channel. The `[default]` section only contains a strategy, not any matching properties.

All policies are evaluated top to bottom. The first matching policy is applied (except for the default policy).
A more elaborate example can be found in the [charge.config.example](charge.config.example) file.

### properties

Currently available properties:
- **chan.id** (match on channel IDs (list))
- **chan.initiator** (match on initiator status)
- **chan.max_ratio** (match on channel ratio)
- **chan.min_ratio** (match on channel ratio)
- **chan.min_capacity** (match on channel capacity)
- **chan.max_capacity** (match on channel capacity)
- **chan.min_base_fee_msat** (match on channel peer policy)
- **chan.max_base_fee_msat** (match on channel peer policy)
- **chan.min_fee_ppm** (match on channel peer policy)
- **chan.max_fee_ppm** (match on channel peer policy)
- **chan.private** (match on channel private flag)
- **node.id** (match on node pubkeys (list))
- **node.min_channels** (match on node # of channels)
- **node.max_channels** (match on node # of channels)
- **node.min_sats** (match on node total capacity)
- **node.max_sats** (match on node total capacity)

### strategies
- **ignore** (ignores the channel)
- **static** (sets fixed base fee and fee rate values. properties: **base_fee_msat**, **fee_ppm**)
- **match_peer** (sets the same base fee and fee rate values as the peer)
- **cost** (calculate cost for opening channel, and set ppm to cover cost when channel depletes. properties: **cost_factor**)
- **onchain_fee** (sets the fees to a % equivalent of a standard onchain payment of **onchain_fee_btc** BTC within **onchain_fee_numblocks** blocks.
  Requires --electrum-server to be specified. **base_fee_msat** is used if defined.)

## Contributing

Contributions are highly welcome!
Feel free to submit issues and pull requests on https://github.com/accumulator/charge-lnd/

Please also consider opening a channel with my node, or sending tips via keysend:

* accumulator : `0266ad254117f16f16c3457e081e6207e91c5e414477a208cf4d9c633322799038@89.99.0.115:9735`
