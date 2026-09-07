# SOL LONG 15:00 UTC Loss Confirmation Candle Anatomy — A55 Preregistration

## Purpose

A51 identified terminal structural failure, A52 identified broad warnings, A53 showed that immediate hard exits on warnings can sacrifice too much winner PnL, and A54 found no replicated fixed 5m secondary stall trigger after POST_H05.

A55 asks the user's literal question:

> Is there a **completed candle before the terminal failure candle** whose causal shape/state already says that this trade is likely heading to loss?

The object is a `LOSS_CONFIRMATION_CANDLE`: a completed 5m candle that is known before terminal failure, is distinguishable from a still-live eventual winner at the same trade age and structural state, and replicates outside Development.

A55 is anatomy only. It does not change an exit and it does not threshold-scan continuous features.

## Frozen parent

- Pair: SOLUSDT
- Clock: 15:00 UTC
- Reference: R360
- Entry: `E0_RESTING_H`
- Target: `H + 0.40R`
- Parent mechanics: exact A2/A17 simulator
- Partitions: Development, External, Reference Validation
- Raw expected parent counts: 601 / 281 / 337
- Raw expected losses: 357 / 166 / 187

## Failure mechanisms

### Primary: M2 failed breakout

Frozen definition:

1. breakout has been confirmed by a completed close `> H`;
2. the terminal structural failure candle is the first later completed 5m candle with `close <= H`.

Expected total M2 losses from A51: **539**.

### Secondary: M0 reference invalidation

Frozen definition:

1. breakout has not yet been confirmed;
2. terminal failure is the first completed 5m candle with `close < L`.

Expected total M0 losses from A51: **76**.

M1 timeout has no structural terminal failure candle and is excluded from Loss Confirmation Candle discovery.

## Fixed pre-terminal observation leads

For each structural loss, A55 inspects only these fixed completed-candle knowledge leads before the terminal failure is known:

- **15 minutes**
- **10 minutes**
- **5 minutes**

The 5-minute lead is the immediately preceding completed candle.

A snapshot is eligible only if it is already in the same structural state as the mechanism:

- M2 snapshot: breakout already confirmed and terminal failure has not yet occurred.
- M0 snapshot: breakout still unconfirmed and terminal reference invalidation has not yet occurred.

No post-terminal information is used as a feature.

## Matched winner control

Every eligible loss snapshot is compared with one deterministic eventual-positive parent control candle at the **same elapsed minutes since entry** and the **same structural state**.

Control matching rules are frozen:

1. same partition;
2. Development additionally requires the same fixed `dev_block` when possible; if none exists, that loss snapshot is unmatched rather than relaxing the block;
3. control parent raw PnL must be `> 0`;
4. control must still be live through the candidate candle close (target/exit may not have occurred on or before that candle);
5. M2 control must already have a confirmed breakout by that candle; M0 control must still be pre-break by that candle;
6. among eligible controls choose the nearest `execution_start` in absolute calendar time; ties choose earlier `execution_start`, then earlier `entry_ts`.

Control reuse is allowed but must be reported. The purpose is state/age matching, not independent-sample inference.

## Frozen candle features

All continuous prices are normalized by that trade's frozen `R` where applicable.

### Single-candle shape

- signed body / R
- absolute body / R
- full range / R
- upper wick / R
- lower wick / R
- close location within candle `[0,1]`
- body fraction of range
- upper-wick fraction of range
- lower-wick fraction of range

### Structural location

- close relative to H / R
- high relative to H / R
- low relative to H / R
- close relative to L / R

### One-candle transition versus immediately previous completed candle

- close change / R
- high change / R
- low change / R
- range change / R
- close-location change

### Fixed binary candle states

No numeric threshold is learned in A55. Binary states use sign, candle relationships, or levels already frozen in A51/A52:

- `BEARISH`: close < open
- `LOWER_CLOSE`: close < previous close
- `LOWER_HIGH`: high < previous high
- `LOWER_LOW`: low < previous low
- `INSIDE_BAR`: high <= previous high and low >= previous low
- `OUTSIDE_BAR`: high >= previous high and low <= previous low
- `M2_CLOSE_H05`: H < close <= H + 0.05R
- `M2_CLOSE_H10`: H < close <= H + 0.10R
- `M0_CLOSE_L25`: L <= close <= L + 0.25R
- `M0_CLOSE_L10`: L <= close <= L + 0.10R

No combinations of binary states are tested in A55.

## Continuous-feature discovery gate

For each mechanism × lead × continuous feature, compare the loss-confirmation snapshot with its matched winner control.

A Development feature is eligible for OOS inspection only if:

1. at least 40 matched M2 Development pairs (M0: at least 20);
2. absolute median gap / pooled-IQR effect >= **0.30**;
3. the same median-gap sign appears in at least **5 of 6** Development blocks for M2 when both sides have >=5 observations; for M0, because of smaller N, require at least **3 adequate blocks and same sign in all adequate blocks**.

OOS replication then requires independently in External and Reference Validation:

- same direction as Development;
- effect >= **0.10** in each;
- at least 20 matched M2 pairs in each partition (M0: at least 8).

A55 reports continuous separators but does not derive a numeric live threshold from them.

## Binary-state discovery gate

A Development binary state is eligible for OOS inspection only if:

1. loss hit rate >= **40%** for M2 (M0: >=30%);
2. loss hit rate minus matched-winner hit rate >= **20 percentage points**;
3. loss/winner hit-rate ratio >= **1.50x** (infinite if winner hit rate is zero);
4. M2: same bad-direction in at least 5/6 adequate Development blocks; M0: all of at least 3 adequate blocks.

OOS replication requires in both External and Reference Validation:

- loss hit > winner hit;
- gap >= **10 percentage points**;
- ratio >= **1.25x**;
- M2 loss hit >=20% (M0 >=15%).

## Selection rule

If multiple replicated characteristics exist, A55 does **not** optimize a composite.

The primary Loss Confirmation Candle family is selected by:

1. earliest causal lead: 15m before 10m before 5m;
2. within the same lead, prefer a replicated binary candle state over a continuous diagnostic because it is directly executable without deriving a new threshold;
3. ties: larger Development separation/effect.

No combination is permitted.

## Required outputs

- exact parent/mechanism reconciliation;
- matched-pair counts and control reuse;
- continuous feature table for Development and OOS;
- binary-state table for Development and OOS;
- Development block stability;
- per-lead snapshot coverage;
- explicit primary characteristic if supported;
- representative median candle anatomy for failures vs matched winners.

## Status

Possible final statuses:

- `SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_SUPPORTED_FOR_A56`
- `SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_INCONCLUSIVE`
- `SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_RECONCILIATION_FAIL`

If supported, A56 may derive/test only the frozen selected characteristic as an executable next-open guard. If only a continuous feature survives, A56 must preregister one threshold derivation rule from Development before OOS is opened.

Research only. Live Baba Bot remains unchanged.
