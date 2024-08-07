# charge-lnd

This script matches your open Lightning channels against a number of customizable criteria and applies channel fees based on the matching policy.

## Installation

See [INSTALL.md](/INSTALL.md)

## Usage

charge-lnd takes only a minimal set of parameters:

```
usage: charge-lnd [-h] [--lnddir LNDDIR] [--tlscert TLS_CERT_PATH] [--macaroon MACAROON_PATH] [--grpc GRPC]
                  [--circuitbreaker CIRCUITBREAKER] [--dry-run] [--check] [-v] [-vv] -c CONFIG

optional arguments:
  -h, --help            show this help message and exit
  --lnddir LNDDIR       (default ~/.lnd) lnd directory
  --tlscert TLS_CERT_PATH
                        (default [lnddir]/tls.cert) path to lnd TLS certificate
  --macaroon MACAROON_PATH
                        (default [lnddir]/data/chain/bitcoin/mainnet/charge-lnd.macaroon) path to lnd auth macaroons
  --grpc GRPC           (default localhost:10009) lnd gRPC endpoint
  --circuitbreaker CIRCUITBREAKER
                        (optional, no default) circuitbreaker gRPC endpoint host:port
  --dry-run             Do not perform actions (for testing), print what we would do to
                        stdout
  --check               Do not perform actions, only check config file for valid syntax
  -v, --verbose         Be more verbose
  -vv, --very-verbose   Be very verbose, print every matched policy
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

If at least lnd 0.18 is used, charge-lnd also supports the experimental support of inbound fees. By default, lnd only supports negative inbound fees on the inbound channel, which then act as a “discount” on the outbound fees of the outgoing channel. However, the entire forward fee cannot become negative.

Example with inbound fees:
```
[example-policy]
chan.min_capacity = 500000

strategy = static
base_fee_msat = 1000
fee_ppm = 2000
inbound_base_fee_msat = -500
inbound_fee_ppm = -1000
```

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
inbound_base_fee_msat = -8000
inbound_fee_ppm = -400

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
| **chan.min_count_pending_htlcs** | match on the number of pending HTLCs in the channel| # pending htlcs|
| **chan.max_count_pending_htlcs** | match on the number of pending HTLCs in the channel| # pending htlcs|
| **chan.min_next_pending_htlc_expiry** | match on the blocks until the next HTLC in the channel expires| # blocks|
| **chan.max_next_pending_htlc_expiry** | match on the blocks until the next HTLC in the channel expires| # blocks|
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
|||
|ONCHAIN||
| **onchain.conf_target** | defines the confirmation target that is used for the determination of the onchain fee rate (default: 6)|# blocks|
| **onchain.min_fee_rate** | match on the onchain fee rate|# sat per vbyte|
| **onchain.max_fee_rate** |  match on the onchain fee rate|# sat per vbyte|
| **onchain.synced_to_chain** |  match on the synced to chain. False if lnd is not synced to chain for 5 minutes.|true\|false|


File references should contain 1 item per line
### Strategies
Available strategies:

|Strategy|Description|Parameters|
|:--|:--|:--|
|**ignore** | ignores the channel completely||
|**ignore_fees** | don't make any fee changes, only update htlc size limits and time_lock_delta||
|**static** | sets fixed base fee and fee rate values for the outbound and inbound side.| **fee_ppm**<br>**base_fee_msat**<br>**inbound_fee_ppm**<br>**inbound_base_fee_msat**<br>**inbound_level_ppm** if set we calculate `inbound_fee_ppm = min(0,inbound_level_ppm - fee_ppm)`|
|**match_peer** | sets the same base fee and fee rate values as the peer for the outbound and inbound side.|if **base_fee_msat**, **fee_ppm**, **inbound_base_fee_msat** or **inbound_fee_ppm**  are set the override the peer values|
|**cost** | calculate cost for opening channel, and set ppm to cover cost when channel depletes.|**cost_factor**|
|**onchain_fee** | sets the fees to a % equivalent of a standard onchain payment. We use lnd's internal fee estimate, which is usually based on bitcoind's fee estimate.| **onchain_fee_btc** BTC<br>within **onchain_fee_numblocks** blocks.|
|**proportional** | sets outbound fee ppm according to balancedness. Inbound Fees are set like using strategy **static**.|**min_fee_ppm**<br>**max_fee_ppm**<br>**sum_peer_chans** consider all channels with peer for balance calculations|
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
| **min_fee_ppm_delta** | Minimum change in fees (ppm) before updating channel (default: 0) | ppm delta |
| **min_inbound_fee_ppm_delta** | Minimum change in inbound fees (ppm) before updating channel (default: min_fee_ppm_delta) | ppm delta |
| **cb_max_hourly_rate** | Circuitbreaker: maximum number of incoming htlcs per hour | # hourly rate |
| **cb_max_pending** | Circuitbreaker: maximum number of incoming htlcs at the same time | # incoming pending htlcs |
| **cb_mode** | Circuitbreaker: mode (0 - FAIL; 1 - QUEUE; 2 - QUEUE_PEER_INITIATED; 3 - BLOCK) | 0..3 |
| **cb_clear_limit** | Circuitbreaker: delete the peer limit and fallback to the default limit | true |

### Circuitbreaker Support
Optionally, it is also possible to dynamically control the [circuitbreaker](https://github.com/lightningequipment/circuitbreaker) limits for individual peers. However, the default limit of the circuitbreaker cannot currently be changed with `charge-lnd`.

### One channel for the peer

If any of the properties `cb_max_hourly_rate`, `cb_max_pending`, or `cb_mode` are set, the node limit will be adjusted. It should be noted that 0 for the first two properties is interpreted as infinite. Those properties that are not currently set will be set according to the respective default limits. If no node limit is to be set, but a limit has already been set, the reset to the default limit can be performed by setting `cb_clear_limit`.

### Multiple channels for the peer

It can happen that different properties for individual channels are chosen when there are multiple channels with one peer. Since the circuitbreaker monitors its limits at the peer level, we aggregate the properties into a node limit:
- `cb_max_hourly_rate` and `cb_max_pending` are added, considering that 0 corresponds to infinite.
- `cb_mode` is set to the most conservative mode, i.e., the first mode from the following list is used: `MODE_BLOCK`, `MODE_FAIL`, `MODE_QUEUE`, `MODE_QUEUE_PEER_INITIATED`.
- The node limit will be deleted if `cb_clear_limit` is set for a channel.

## Contributing

Contributions are highly welcome!
Feel free to [submit issues](https://github.com/accumulator/charge-lnd/issues) and [pull requests](https://github.com/accumulator/charge-lnd/pulls).
See [development guide](DEVELOPMENT-GUIDE.md) for help getting started.

Please also consider opening a channel with my node, or sending tips via keysend:

`0266ad254117f16f16c3457e081e6207e91c5e414477a208cf4d9c633322799038@lightning.channels.zijn.cool:9735`
