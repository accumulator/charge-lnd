# charge-lnd

This script matches your open Lightning channels against a number of customizable criteria and applies channel fees based on the matching policy.

## Installation

See [INSTALL.md](/INSTALL.md)

## Usage

charge-lnd takes only a minimal set of parameters:

```
usage: charge-lnd [-h] [--lnddir LNDDIR] [--grpc GRPC] [--electrum-server ELECTRUM_SERVER]
                  [--dry-run] [--check] [-v] -c CONFIG

optional arguments:
  -h, --help            show this help message and exit
  --lnddir LNDDIR       (default ~/.lnd) lnd directory
  --tlscert TLS_CERT_PATH
                        (default [lnddir]/tls.cert) path to lnd TLS certificate
  --macaroon MACAROON_PATH
                        (default [lnddir]/data/chain/bitcoin/mainnet/charge-lnd.macaroon) path to lnd auth macaroons
  --grpc GRPC           (default localhost:10009) lnd gRPC endpoint
  --electrum-server ELECTRUM_SERVER
                        (optional, no default) electrum server host:port . Needed for
                        onchain_fee.
  --dry-run             Do not perform actions (for testing), print what we would do to
                        stdout
  --check               Do not perform actions, only check config file for valid syntax
  -v, --verbose         Be more verbose
  -c CONFIG, --config CONFIG
                        path to config file
```

All policies are defined using an INI style config file.

Each `[policy-name]` defined in the config file describes a policy.
A single policy consists of;
- a set of criteria to match against the channel and/or node (e.g. minimum channel capacity)
- a fee strategy (how to calculate the new channel fees)

The defined criteria are compared against the open channels and their associated nodes.
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

### Non-final policies

You can also define a 'non-final' policy. This is simply a policy without a strategy.
It allows you to set default values for properties used by later policies, e.g. `base_fee_msat`, `fee_ppm`, `min_fee_ppm_delta` etc.

Processing continues after matching a non-final policy.

Example:
```
[mydefaults]
chan.max_capacity = 5_000_000
min_fee_ppm_delta = 10
base_fee_msat = 2000

[someotherpolicy]
chan.min_capacity = 500_000
strategy = static
fee_ppm = 50
```

This will, for channels that match `mydefaults` and after that `someotherpolicy`, set fees to 2 sat base fee and 50 ppm, and uses a minimum fee delta of 10 when applying a fee change for that channel.

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

More elaborate examples can be found in the [examples](examples) folder.

## Properties

Currently available properties:

|Property|Description|Values|
|:--|:--|:--|
| **chan.id** |match on channel IDs - comma separated list of channel IDs and/or file references|<channel ID\|file url>[, <channel ID\|file url>..]|
| **chan.initiator** | match on initiator status, true if we are initiator|true\|false|
| **chan.private** | match on channel private flag|true\|false|
| **chan.min_capacity** | match on channel capacity|# of sats|
| **chan.max_capacity** | match on channel capacity|# of sats|
| **chan.min_age** | match on channel age|# of blocks|
| **chan.max_age** | match on channel age|# of blocks|
|||
|BALANCE||
| **chan.max_ratio** | match on channel ratio|0..1|
| **chan.min_ratio** | match on channel ratio|0..1|
| **chan.min_local_balance** | match on channel local balance|# of sats|
| **chan.max_local_balance** | match on channel local balance|# of sats|
| **chan.min_remote_balance** | match on channel remote balance|# of sats|
| **chan.max_remote_balance** | match on channel remote balance|# of sats|
|||
|PEER||
| **chan.min_base_fee_msat** | match on channel peer policy|# of msats|
| **chan.max_base_fee_msat** | match on channel peer policy|# of msats|
| **chan.min_fee_ppm** | match on channel peer policy|0..1000000 (parts per million)|
| **chan.max_fee_ppm** | match on channel peer policy|0..1000000 (parts per million)|
| **chan.disabled** | match on channel disabled by peer|true\|false|
|||
|ACTIVITY||
| **chan.activity_period** | define a time period for forwards|#s seconds or #m minutes or #h hours or #d days|
| **chan.activity_period_ignore_channel_age** | match on channel age less than activity_period |true\|false|
| **chan.min_htlcs_in** | match on minimal amount of HTLCs arriving in channel during activity period|# of htlcs|
| **chan.max_htlcs_in** | match on maximum amount of HTLCs arriving in channel during activity period|# of htlcs|
| **chan.min_htlcs_out** | match on minimal amount of HTLCs departing from channel during activity period|# of htlcs|
| **chan.max_htlcs_out** | match on maximum amount of HTLCs departing from channel during activity period|# of htlcs|
| **chan.min_sats_in** | match on minimal amount of sats arriving in channel during activity period|# of sats|
| **chan.max_sats_in** | match on maximum amount of sats arriving in channel during activity period|# of sats|
| **chan.min_sats_out** | match on minimal amount of sats departing from channel during activity period|# of sats|
| **chan.max_sats_out** | match on maximum amount of sats departing from channel during activity period|# of sats|
| **chan.min_htlcs_ratio** | match on amount of HTLCs ratio arriving in channel during activity period|0..1|
| **chan.max_htlcs_ratio** | match on amount of HTLCs ratio arriving in channel during activity period|0..1|
| **chan.min_sats_ratio** | match on amount of sats ratio arriving in channel during activity period|0..1|
| **chan.max_sats_ratio** | match on amount of sats ratio arriving in channel during activity period|0..1|
|||
|NODE||
| **node.id** | match on node pubkeys - comma separated list of node pubkeys and/or file references|<node pubkey\|file url>[, <node pubkey\|file url>..]|
| **node.min_channels** | match on number of channels the peer node has|# of channels|
| **node.max_channels** | match on number of channels the peer node has|# of channels|
| **node.min_shared_channels_active** | match on number of active channels the peer node has with us|# of channels|
| **node.max_shared_channels_active** | match on number of active channels the peer node has with us|# of channels|
| **node.min_shared_channels_inactive** | match on number of inactive channels the peer node has with us|# of channels|
| **node.max_shared_channels_inactive** | match on number of inactive channels the peer node has with us|# of channels|
| **node.min_capacity** | match on node total capacity|# of sats|
| **node.max_capacity** | match on node total capacity|# of sats|
| **node.min_shared_capacity_active** | match on node active shared capacity with us|# of sats|
| **node.max_shared_capacity_active** | match on node active shared capacity with us|# of sats|
| **node.min_shared_capacity_inactive** | match on node inactive shared capacity with us|# of sats|
| **node.max_shared_capacity_inactive** | match on node inactive shared capacity with us|# of sats|
| **node.max_shared_ratio** | match on channels ratio with us|0..1|
| **node.min_shared_ratio** | match on channels ratio with us |0..1|
| **node.max_shared_ratio_active** | match on active channels ratio with us|0..1|
| **node.min_shared_ratio_active** | match on active channels ratio with us |0..1|
| **node.max_shared_ratio_inactive** | match on inactive channels ratio with us|0..1|
| **node.min_shared_ratio_inactive** | match on inactive channels ratio with us|0..1|

File references should contain 1 item per line
### Strategies
Available strategies:

|Strategy|Description|Parameters|
|:--|:--|:--|
|**ignore** | ignores the channel completely||
|**ignore_fees** | don't make any fee changes, only update htlc size limits and time_lock_delta||
|**static** | sets fixed base fee and fee rate values.| **fee_ppm**|
|**match_peer** | sets the same base fee and fee rate values as the peer|if **base_fee_msat** or **fee_ppm** are set the override the peer values|
|**cost** | calculate cost for opening channel, and set ppm to cover cost when channel depletes.|**cost_factor**|
|**onchain_fee** | sets the fees to a % equivalent of a standard onchain payment (Requires --electrum-server to be specified.)| **onchain_fee_btc** BTC<br>within **onchain_fee_numblocks** blocks.|
|**proportional** | sets fee ppm according to balancedness.|**min_fee_ppm**<br>**max_fee_ppm**<br>**sum_peer_chans** consider all channels with peer for balance calculations|
|**disable** | disables the channel in the outgoing direction. Channel will be re-enabled again if it matches another policy (except when that policy uses an 'ignore' strategy).||
|**use_config** | process channel according to rules defined in another config file.|**config_file**|

All strategies (except the ignore strategy) will apply the following properties if defined:

|Property|Description|Values|
|:--|:--|:--|
| **base_fee_msat** | Base fee | # msat |
| **min_htlc_msat** | Minimum size (in msat) of HTLC to allow | # msat |
| **max_htlc_msat** | Maximum size (in msat) of HTLC to allow | # msat |
| **max_htlc_msat_ratio** | Maximum size of HTLC to allow as a fraction of total channel capacity | 0..1 |
| **time_lock_delta** | Time Lock Delta | # blocks |
| **min_fee_ppm_delta** | Minimum change in fees (ppm) before updating channel | ppm delta |


## Contributing

Contributions are highly welcome!
Feel free to [submit issues](https://github.com/accumulator/charge-lnd/issues) and [pull requests](https://github.com/accumulator/charge-lnd/pulls).
See [development guide](DEVELOPMENT-GUIDE.md) for help getting started.

Please also consider opening a channel with my node, or sending tips via keysend:

`0266ad254117f16f16c3457e081e6207e91c5e414477a208cf4d9c633322799038@lightning.channels.zijn.cool:9735`
