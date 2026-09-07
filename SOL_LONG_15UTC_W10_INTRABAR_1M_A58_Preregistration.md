# SOL LONG 15:00 UTC W10 Intrabar 1m Decomposition — A58 Preregistration

## Purpose

A55 found that M2 failed-breaks are preceded by weak separation from `H`; A57 showed that 5m warning-candle shape and the prior 1–2 completed 5m candles do not produce a robust replicated discrete loss-confirmation motif.

A58 asks a narrower question:

> Inside the **first W10 warning 5m candle** (`H < 5m close <= H+0.10R` after confirmed breakout), does the causal 1-minute path during minutes 1–4 distinguish eventual structural FAILED_BREAK from eventual E40 TARGET?

A58 is **conditional anatomy only**. The W10 cohort is defined by the completed 5m candle, so the cohort label is not known during minute 1–4. Any replicated 1m motif from A58 must be revalidated in a future A59 across all live post-breakout 1m opportunities without conditioning on the future 5m W10 close before it can become executable.

No exit rule is changed in A58.

## Frozen parent and W10 cohort

- Pair: SOLUSDT
- Clock: 15:00 UTC
- Reference: R360
- Entry: `E0_RESTING_H`
- Target: `H + 0.40R`
- Parent mechanics: frozen A2/A17 simulator
- W10 definition: frozen A53 `G3_POST_H10` first warning state, i.e. confirmed breakout and completed 5m close `H < close <= H+0.10R` while parent remains live.
- Partitions: Development / External / Reference Validation.

Expected A57 W10 cohort counts:
- Development: 300 total = 233 FAILED_BREAK, 63 E40 TARGET, 4 unresolved TIME.
- External: 192 total = 133 FAILED_BREAK, 54 E40 TARGET, 5 unresolved TIME.
- Reference Validation: 184 total = 134 FAILED_BREAK, 48 E40 TARGET, 2 unresolved TIME.

Primary discrimination excludes unresolved TIME but reports it.

## 1m data source and feasibility gate

Use Binance Vision USD-M futures monthly klines from the same source family as frozen 5m SOL research:

`SOLUSDT / 1m / monthly klines`

Only months containing frozen W10 warning candles need to be downloaded.

For every W10 5m candle at timestamp `T`, A58 requires exactly five 1m candles at:
- `T+0m`
- `T+1m`
- `T+2m`
- `T+3m`
- `T+4m`

The five 1m candles must reconstruct the frozen 5m candle:
- aggregate open = 5m open
- aggregate high = 5m high
- aggregate low = 5m low
- aggregate close = 5m close

Tolerance: absolute difference <= `max(1e-8, 1e-10 * abs(5m value))` per OHLC field.

Feasibility requires:
1. >=99% exact five-bar availability in each partition;
2. >=99% 1m→5m OHLC parity in each partition;
3. no duplicate 1m timestamps in any used window.

If this fails, status is `SOL_LONG_15UTC_W10_INTRABAR_1M_A58_DATA_FAIL` and no anatomy is interpreted.

## Observation times

Only causal cumulative states after completed 1m candles are inspected:

- `K1`: after first 1m close (1 minute into W10 candle)
- `K2`: after second 1m close
- `K3`: after third 1m close
- `K4`: after fourth 1m close

Minute 5 is excluded from candidate discovery because that is the completed W10 5m close already studied in A55/A57.

## Frozen binary 1m motifs

All price thresholds are inherited from frozen structural levels `H`, `H+0.05R`, and `H+0.10R`. No neighboring threshold grid is allowed.

At each K where defined:

1. `ANY_CLOSE_LE_H_BY_K`
   - at least one completed 1m close so far is `<= H`.

2. `CURRENT_CLOSE_LE_H`
   - latest completed 1m close is `<= H`.

3. `NO_CLOSE_ABOVE_H10_BY_K`
   - no completed 1m close so far is `> H+0.10R`.

4. `NO_HIGH_ABOVE_H10_BY_K`
   - no completed 1m high so far is `> H+0.10R`.

5. `TWO_PLUS_NEAR_H10_BY_K` (K2+ only)
   - at least two completed 1m closes so far satisfy `H < close <= H+0.10R`.

6. `TWO_PLUS_NEAR_H05_BY_K` (K2+ only)
   - at least two completed 1m closes so far satisfy `H < close <= H+0.05R`.

7. `REJECT_H10_TO_H05_BY_K`
   - cumulative 1m high has reached at least `H+0.10R`, while latest completed 1m close is `<= H+0.05R`.
   - latest close may be below H; this is intentionally a rejection/drawdown state rather than a reclaim-only state.

8. `H_LOSS_THEN_RECLAIM_BY_K` (K2+ only)
   - a prior completed 1m close in the same W10 candle was `<=H`, and latest completed 1m close is `>H`.

9. `LAST2_LOWER_CLOSES` (K2+ only)
   - latest 1m close < immediately previous 1m close.

10. `LAST2_LOWER_HIGHS` (K2+ only)
    - latest 1m high < immediately previous 1m high.

11. `CURRENT_BEARISH`
    - latest 1m close < latest 1m open.

No combinations beyond the ten fixed path motifs above plus `CURRENT_BEARISH` are tested.

## Report-only continuous anatomy

At K1–K4 A58 also reports, without deriving thresholds:
- latest close relative to H / R;
- cumulative max high extension above H / R;
- cumulative min low relative to H / R;
- cumulative rejection from max high to latest close / R;
- cumulative path range / R;
- latest signed 1m body / R;
- latest 1m range / R;
- count of closes `<=H`;
- count of closes in H05;
- count of closes in H10.

Continuous features cannot authorize A59 unless a separate threshold-derivation preregistration is later created.

## Development gate for binary motifs

For each K × motif, compare FAILED_BREAK vs E40 TARGET within the frozen W10 cohort.

A Development motif is eligible for OOS inspection only if:
1. FAILED_BREAK N >=200 and E40 TARGET N >=50 after valid 1m parity filtering;
2. fail hit rate >=30%;
3. target hit rate <=25%;
4. fail-target gap >=20 percentage points;
5. fail/target hit-rate ratio >=2.00x (infinite if target hit is zero);
6. bad-direction appears in at least 5 of 6 Development half-year blocks where each block contains >=10 fail and >=3 target observations.

## OOS replication gate

Independently in both External and Reference Validation:
- fail hit > target hit;
- fail hit >=20%;
- target hit <=35%;
- gap >=15pp;
- ratio >=1.50x;
- at least 100 failed-break and 35 E40 target observations after parity filtering in each partition.

## Selection rule

If multiple binary motifs replicate:
1. earliest causal minute K1 before K2 before K3 before K4;
2. at same K, lower target hit rate;
3. then larger Development gap;
4. then higher Development fail hit rate.

No composite motif is created posthoc.

## Interpretation rule

A replicated A58 motif means only:

> conditional on this 5m candle eventually being the first W10 warning, the 1m path contains earlier outcome information.

It does **not** mean the motif is executable live, because W10 cohort membership is only known at the 5m close. A59 must replay the selected fixed motif over every live post-breakout 1m opportunity without future W10 conditioning and then test next-1m-open or next-5m-open economics under a separately preregistered execution rule.

## Possible statuses

- `SOL_LONG_15UTC_W10_INTRABAR_1M_A58_SUPPORTED_FOR_A59`
- `SOL_LONG_15UTC_W10_INTRABAR_1M_A58_INCONCLUSIVE`
- `SOL_LONG_15UTC_W10_INTRABAR_1M_A58_DATA_FAIL`
- `SOL_LONG_15UTC_W10_INTRABAR_1M_A58_RECONCILIATION_FAIL`

Research only. Live Baba Bot remains unchanged.
