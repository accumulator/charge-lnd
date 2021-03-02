# charge-lnd

This script matches your open Lightning channels against a number of customizable criteria and applies channel fees based on the matching policy.

## Installation

This script needs a moderately recent LND (https://github.com/lightningnetwork/lnd) instance running.

You don't need to have full admin rights to use charge-lnd. The following access rights are used:
- `offchain:read`
- `offchain:write`
- `onchain:read`
- `info:read`

You can create a suitably limited macaroon by issueing:

```
$ lncli bakemacaroon offchain:read offchain:write onchain:read info:read --save_to=~/.lnd/data/chain/bitcoin/mainnet/charge-lnd.macaroon
```

By default charge-lnd connects to `localhost:10009`, using the macaroon file in `~/.lnd/data/chain/bitcoin/mainnet/charge-lnd.macaroon`. If `charge-lnd.macaroon` is not found, `admin.macaroon` will be tried.

If you need to change this, please have a look at the optional arguments `--grpc` and `--lnddir`.

Python and PIP should be made available on the system before installation.
The project and its dependencies can be installed by running:

```
$ pip install -U setuptools && pip install -r requirements.txt .
```

On some systems using Python 3, use pip3 instead:

```
$ pip3 install -U setuptools && pip3 install -r requirements.txt .
```

When running the install as `root`, `charge-lnd` will be installed to `/usr/local/bin`. Otherwise `charge-lnd` will be installed to `$HOME/.local/bin`.

## Usage

charge-lnd takes only a minimal set of parameters:

```
usage: charge-lnd [-h] [--lnddir LNDDIR] [--grpc GRPC]
                  [--electrum-server ELECTRUM_SERVER] [-c CONFIG]

optional arguments:
  -h, --help            show this help message and exit
  --lnddir LNDDIR       (default ~/.lnd) lnd directory
  --grpc GRPC           (default localhost:10009) lnd gRPC endpoint
  --electrum-server ELECTRUM_SERVER
                        (no default) electrum server host:port
  --dry-run             Do not perform actions (for testing), print what we would do to stdout
  -v, --verbose         Be more verbose
  -c CONFIG, --config CONFIG
                        path to config file
```

All policies are defined using an INI style config file.

Each `[policy-name]` defined in the config file describes a policy.
A single policy consists of;
- a set of criteria to match against the channel and/or node (e.g. minimum channel capacity)
- a fee strategy (how to calculate the new channel fees)

The defined criteria are compared against the open channels and associated nodes.
The fee strategy then executed to determine what the new channel fees should be.

There is a special `[default]` section, that will be used if none of the policies match a channel. The `[default]` section only contains a strategy, not any matching criteria.

All policies are evaluated top to bottom. The first matching policy is applied (except for the default policy).

A simple example:
```
[example-policy]
chan.min_capacity = 500000

strategy = static
base_fee_msat = 1000
fee_ppm = 10
```

This policy matches the channels against the `chan.min_capacity` criterium. Only channels with at least 500000 sats total capacity will match.

If a channel matches this policy, the `static` strategy is then used, which takes the `base_fee_msat` and `fee_ppm`  properties defined in the policy and applies them to the channel.

### More examples

Maintain a friends list with lower fees:
```
[friends]
node.id = file:///home/lnd/friends.list
strategy = static
base_fee_msat = 10
fee_ppm = 10
```

Use routing fees to nudge channel balances toward 50/50 channel ratios:
```
[discourage-routing-out-of-balance]
chan.max_ratio = 0.1
chan.min_capacity = 250000
strategy = static
base_fee_msat = 10000
fee_ppm = 500

[encourage-routing-to-balance]
chan.min_ratio = 0.9
chan.min_capacity = 250000
strategy = static
base_fee_msat = 1
fee_ppm = 2
```

More elaborate examples can be found in the [charge.config.example](charge.config.example) file.

### Properties

Currently available properties:

|Property|Description|Values|
|:--|:--|:--|
| **chan.id** |match on channel IDs - comma separated list of channel IDs and/or file references|<channel ID\|file url>[, <channel ID\|file url>..]|
| **chan.initiator** | match on initiator status, true if we are initiator|true\|false|
| **chan.private** | match on channel private flag|true\|false|
| **chan.max_ratio** | match on channel ratio|0..1|
| **chan.min_ratio** | match on channel ratio|0..1|
| **chan.min_capacity** | match on channel capacity|# of sats|
| **chan.max_capacity** | match on channel capacity|# of sats|
| **chan.min_age** | match on channel age|# of blocks|
| **chan.max_age** | match on channel age|# of blocks|
| **chan.min_base_fee_msat** | match on channel peer policy|# of msats|
| **chan.max_base_fee_msat** | match on channel peer policy|# of msats|
| **chan.min_fee_ppm** | match on channel peer policy|0..1000000 (parts per million)|
| **chan.max_fee_ppm** | match on channel peer policy|0..1000000 (parts per million)|
|||
| **node.id** | match on node pubkeys - comma separated list of node pubkeys and/or file references|<node pubkey\|file url>[, <node pubkey\|file url>..]|
| **node.min_channels** | match on number of channels the peer node has|# of channels|
| **node.max_channels** | match on number of channels the peer node has|# of channels|
| **node.min_capacity** | match on node total capacity|# of sats|
| **node.max_capacity** | match on node total capacity|# of sats|

File references should contain 1 item per line
### Strategies
Available strategies:

|Strategy|Description|Parameters|
|:--|:--|:--|
|**ignore** | ignores the channel||
|**static** | sets fixed base fee and fee rate values.| **base_fee_msat**<br>**fee_ppm**|
|**match_peer** | sets the same base fee and fee rate values as the peer||
|**cost** | calculate cost for opening channel, and set ppm to cover cost when channel depletes.|**base_fee_msat**<br>**cost_factor**|
|**onchain_fee** | sets the fees to a % equivalent of a standard onchain payment (Requires --electrum-server to be specified.)| **onchain_fee_btc** BTC<br>within **onchain_fee_numblocks** blocks.<br>**base_fee_msat** is used if defined.|
|**proportional** | sets fee ppm according to balancedness.|**base_fee_msat**<br>**min_fee_ppm**<br>**max_fee_ppm**|

All strategies (except the ignore strategy) will apply the following properties if defined:
- **min_htlc_msat**
- **max_htlc_msat**
- **time_lock_delta**

## Contributing

Contributions are highly welcome!
Feel free to submit issues and pull requests on https://github.com/accumulator/charge-lnd/

Please also consider opening a channel with my node, or sending tips via keysend:

* accumulator : `0266ad254117f16f16c3457e081e6207e91c5e414477a208cf4d9c633322799038@89.99.0.115:9735`
