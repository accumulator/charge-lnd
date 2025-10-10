# Flow-Based Fee Strategy

The `flow_based` strategy implements an automated fee adjustment algorithm similar to Lightning Terminal's autofees feature. It dynamically adjusts channel fees based on forwarding performance, target throughput calculations, and liquidity levels.

## Overview

The flow-based strategy works by:

1. **Calculating Target Throughput**: Analyzes the top earning channels over a reference period to establish a target throughput benchmark
2. **Measuring Recent Performance**: Compares recent forwarding activity against the target throughput
3. **Adjusting Fees Incrementally**: Makes small percentage-based fee adjustments to optimize for target performance
4. **Applying Scarcity Pricing**: Increases fees when channel liquidity is low to signal scarcity

## How It Compares to Lightning Terminal Autofees

| Feature | Lightning Terminal | charge-lnd flow_based |
|---------|-------------------|----------------------|
| Target Calculation | Top 5 earners over 60 days | Configurable (default: top 5 over 60 days) |
| Adjustment Frequency | Every 3 days | Every charge-lnd run (configurable via cron) |
| Fee Adjustments | Small incremental changes | Configurable percentage adjustments |
| Scarcity Pricing | At 7/8 liquidity depletion | Configurable threshold (default: 1/8 remaining) |
| Channel Selection | All or specific channels | Policy-based matching with rich criteria |

## Strategy Parameters

### Basic Parameters

- `reference_period_days` (default: 60): Period in days to look back for calculating target throughput
- `analysis_period_days` (default: 7): Period in days to analyze recent performance
- `top_earners_count` (default: 5): Number of top earning channels to use for target calculation
- `fee_adjustment_pct` (default: 5.0): Percentage to adjust fees by each time
- `min_fee_ppm` (default: 1): Minimum fee rate in parts per million
- `max_fee_ppm` (default: 5000): Maximum fee rate in parts per million
- `base_fee_msat` (default: 1000): Base fee in millisatoshis

### Liquidity Management

- `liquidity_threshold` (default: 0.125): Local balance ratio below which scarcity pricing applies
- `scarcity_multiplier` (default: 1.2): Multiplier for fee increases when liquidity is low

## Flow-Based Matching Criteria

The strategy also introduces new matching criteria for policies:

### Throughput-Based Matching

- `chan.min_throughput_ratio`: Minimum ratio of recent throughput to target throughput
- `chan.max_throughput_ratio`: Maximum ratio of recent throughput to target throughput
- `chan.flow_reference_period`: Custom reference period for this policy (e.g., "30d", "14d")
- `chan.flow_analysis_period`: Custom analysis period for this policy (e.g., "3d", "7d")

### Earning-Based Matching

- `chan.min_earning_rank`: Minimum earning rank (1 = highest earner)
- `chan.max_earning_rank`: Maximum earning rank

## Example Configurations

### Basic Flow-Based Setup

```ini
[default]
strategy = flow_based
base_fee_msat = 1000
reference_period_days = 30
analysis_period_days = 7
fee_adjustment_pct = 8.0
min_fee_ppm = 5
max_fee_ppm = 2000
```

### Target High Performers

```ini
[top-earners]
chan.max_earning_rank = 5
strategy = flow_based
fee_adjustment_pct = 3.0  # Conservative for good performers
min_fee_ppm = 50
```

### Help Underperformers

```ini
[underperformers]
chan.max_throughput_ratio = 0.5
strategy = flow_based
base_fee_msat = 500
fee_adjustment_pct = 15.0  # Aggressive to improve performance
```

## Algorithm Details

### Target Throughput Calculation

1. Retrieve forwarding history for all channels over the reference period
2. Calculate total forwarded amount (sat_out) for each channel
3. Sort channels by forwarded amount (highest first)
4. Take the average of the top N earners as the target throughput

### Performance Analysis

1. Get recent forwarding history for the channel over the analysis period
2. Calculate performance ratio: `recent_throughput / target_throughput`
3. Apply fee adjustments based on performance:
   - If ratio < 0.8: Decrease fees (multiply by `1 - fee_adjustment_pct/100`)
   - If ratio > 1.2: Increase fees (multiply by `1 + fee_adjustment_pct/100`)
   - If 0.8 ≤ ratio ≤ 1.2: Minimal adjustment (multiply by 1.0)

### Scarcity Pricing

If the local balance ratio (`local_balance / capacity`) falls below the `liquidity_threshold`:
- Apply additional fee increase: `new_fee *= scarcity_multiplier`

### Bounds Enforcement

All calculated fees are constrained within `[min_fee_ppm, max_fee_ppm]` bounds.

## Best Practices

1. **Start Conservative**: Begin with smaller `fee_adjustment_pct` values (3-5%) and increase gradually
2. **Monitor Performance**: Watch how channels respond to fee changes over time
3. **Use Appropriate Periods**: Longer reference periods provide more stable targets; shorter analysis periods react faster to changes
4. **Combine with Static Policies**: Use static strategies for new channels, small channels, or special-purpose channels
5. **Set Reasonable Bounds**: Ensure `min_fee_ppm` and `max_fee_ppm` reflect your routing goals

## Troubleshooting

### Strategy Falls Back to Current Fees

If the flow-based calculation fails, the strategy will maintain current fees. Common causes:
- Insufficient forwarding history
- Network connectivity issues
- Invalid configuration parameters

### Fees Not Changing

Check that:
- Channels have sufficient age and forwarding history
- `fee_adjustment_pct` is not too small
- Calculated fees are not hitting min/max bounds
- Performance ratio is outside the stable range (0.8-1.2)

### Unexpected Fee Changes

Verify:
- Target throughput calculation is reasonable for your node
- Analysis period captures representative recent activity
- Scarcity pricing is not triggering unexpectedly
