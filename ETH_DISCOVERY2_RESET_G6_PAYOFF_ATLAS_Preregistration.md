# ETH Discovery 2 Reset — G6 Fee-Adjusted Payoff Atlas Preregistration

**PREREGISTERED before result-bearing execution.**

## Frozen parent
G6 inherits the fully frozen, historically supported G2+G3+G4 lineage:
- ETHUSDT Binance Futures raw 5m;
- LONG;
- reference start **01:30 UTC (08:30 WIB)**;
- reference duration **R180**;
- execution horizon **E720**;
- first valid HIGH-side pressure;
- DIRECT B00 = first strict completed close > H after pressure;
- executable entry = **NEXT_OPEN** after completed B00.

G6 may not change clock, reference/execution duration, direction, pressure grammar, B00 grammar, or entry timing/price.

## Scientific question
> Given the frozen ETH-native entry, what does the post-entry payoff geometry actually look like after transaction cost, and where—if anywhere—do favorable excursion, adverse excursion, and time-to-target form a stable region that could justify a finite G7 management family?

G6 is an **atlas / diagnostic experiment only**. It does not select or promote a trading strategy and does not open a live-management gate.

## Data partitions
Use the same frozen historical partitions:
- External: 2020-01-01 to 2022-01-01;
- Development: 2022-01-01 to 2025-01-01;
- Reference Validation: 2025-01-01 to 2026-07-30.

Unlike selection experiments, G6 is descriptive by design. The same frozen calculations are reported for all three partitions to assess whether the payoff shape itself is stable. No parameter is chosen from holdouts.

## Fixed economics
- Notional: **$500** per trade.
- Round-trip trading cost: **$0.75** per trade.
- No compounding.
- No additional slippage model.
- Fee break-even gross return = **0.15%** of entry price.
- Per-trade fee break-even distance in R units:
  `fee_be_R = 0.0015 * entry_price / R`.

## Path window
For each frozen NEXT_OPEN entry, inspect every complete 5m bar from the entry bar through the earlier of:
1. the frozen execution end, or
2. entry + 720 minutes.

No artificial TP or SL terminates the atlas path.

## Causal ambiguity rule
For any first-hit comparison between a favorable target and adverse threshold:
- if both are first touched on the same 5m bar, ordering is unknown;
- classify as **AMBIGUOUS**, never as a favorable win.

This conservative rule is frozen.

## Favorable target ladder
Report target-reach diagnostics for:
- 0.05R
- 0.08R
- 0.10R
- 0.12R
- 0.15R
- 0.20R
- 0.30R
- 0.40R
- 0.60R
- 0.80R
- 1.00R
- 1.25R
- 1.50R
- 2.00R
- 2.50R
- 3.00R
- 4.00R
- 5.00R

The upper levels are diagnostics, not candidate exits.

For every target T report:
- reach count / rate;
- fee-adjusted nominal target profitability rate, i.e. fraction of all entries for which `T > fee_be_R` and T was reached;
- median and p75 time-to-target among reaches;
- median and p75 **maximum adverse excursion before first target reach** (`MAE_before_T`, in R);
- p90 `MAE_before_T` among reaches.

## Time-sliced MFE / MAE atlas
At horizons:
- 15m
- 30m
- 60m
- 120m
- 240m
- 480m
- 720m

report across all entries:
- median / p25 / p75 / p90 MFE_R;
- median / p25 / p75 / p90 MAE_R, where MAE_R is positive adverse distance below entry;
- proportion with MFE_R above that trade's fee break-even R;
- proportion with net mark-to-market > 0 at the horizon after $0.75 cost.

## First-hit matrix
For favorable targets:
- 0.15R
- 0.20R
- 0.30R
- 0.40R
- 0.60R
- 0.80R
- 1.00R
- 1.50R
- 2.00R

and adverse thresholds:
- 0.05R
- 0.08R
- 0.10R
- 0.12R
- 0.15R
- 0.20R
- 0.30R
- 0.40R
- 0.60R
- 0.80R
- 1.00R

report:
- favorable-first count/rate;
- adverse-first count/rate;
- ambiguous count/rate;
- neither count/rate through the frozen path window.

## Fee-survival diagnostics
For each partition report the distribution of:
- R / entry in percent;
- fee_be_R;
- full-window MFE_R;
- full-window MAE_R;
- terminal gross return and net PnL if marked at execution end with no bracket.

Also report:
- proportion whose maximum favorable excursion ever exceeds fee break-even;
- proportion whose terminal mark-to-market is net-positive after fee;
- median excess MFE beyond fee break-even, conditional on clearing fee.

## Development stability cuts
Without selecting parameters, split Development entries into four chronological near-equal blocks and report for each block:
- median fee_be_R;
- median full-window MFE_R;
- median full-window MAE_R;
- P(MFE >= fee break-even);
- P(MFE >= 0.30R), 0.60R, 1.00R, 1.50R, 2.00R;
- terminal net-positive rate.

## Cross-partition shape flags
For each major target 0.30R / 0.60R / 1.00R / 1.50R / 2.00R, label the payoff shape **STABLE** descriptively if:
- reach rate differs by no more than 15 percentage points between any two partitions; and
- all three partitions have at least 20 reaches at that target when possible.

For first-hit pairs, no winner is selected. The report should highlight broad regions where favorable-first is consistently > adverse-first across all three partitions.

## Decision status
G6 has no pass/fail strategy gate. Its status is:
- `ETH_DISCOVERY2_RESET_G6_ATLAS_COMPLETE` if calculations and frozen lineage invariants complete successfully;
- otherwise technical failure.

The scientific verdict must explicitly state whether the atlas suggests:
1. a stable fee-adjusted payoff region worth preregistering in G7;
2. only weak / unstable payoff geometry;
3. or no plausible static first-hit region after cost.

Any G7 coordinates must be justified from broad atlas plateaus, not copied from BTC, SOL, Z6, or the single best cell.

Research/shadow only. No live promotion or profit guarantee.
