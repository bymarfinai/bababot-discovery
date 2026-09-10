# ETH Economic-First E5 — E2 Strength-Band Regime Map Preregistration

**PREREGISTERED before result-bearing execution.**

## Why E5 exists
E2 found a genuine raw economic anchor:

**17:00 UTC / MOMENTUM / lookback360m / hold720m**

Development: net +$481.58, expectancy +$0.62/trade, PF1.155, but WR47.63% and DD$315.

E3/E4 showed that globally searching for unusually strong-drive reversal cells can produce attractive Development results that fail historical replication. More importantly, the E3 grid showed that restricting the E2 anchor to causal strength>=0.50 destroys its economics (approximately N388 / WR47.42% / net -$7.77 / PF0.996).

Therefore E5 asks the narrow question:

> **Where inside the E2 anchor's causal drive-strength distribution does its economic payoff actually come from, and does the preferred response switch from momentum to reversal across strength regimes?**

## Frozen coordinates
- clock: **17:00 UTC (00:00 WIB)**;
- pre-entry lookback: **360m**;
- forward hold: **720m**;
- weekday anchors only;
- $500 fixed notional;
- $0.75 round-trip cost;
- no compounding;
- no H/L/range/breakout/retest/EMA/Fibonacci.

## Causal strength score
Exactly the E3 definition:
- drive = open(t)/open(t-360m)-1;
- abs_drive = abs(drive);
- strength percentile at t uses only earlier same-clock/lookback weekday observations;
- trailing history at most previous 60 valid observations;
- require at least 40 previous observations;
- strength_pct = fraction of previous observations with abs_drive <= current abs_drive.

## Exclusive strength bands
Every eligible event belongs to exactly one band:
1. `B0_20`: 0.00 <= strength < 0.20
2. `B20_40`: 0.20 <= strength < 0.40
3. `B40_60`: 0.40 <= strength < 0.60
4. `B60_80`: 0.60 <= strength < 0.80
5. `B80_100`: 0.80 <= strength <= 1.00

These are regime bins, not cumulative thresholds.

## Response modes
For each band test only:
- MOMENTUM: LONG after positive drive, SHORT after negative drive;
- REVERSAL: SHORT after positive drive, LONG after negative drive.

Total Development candidates: **5 bands × 2 modes = 10**.

## PnL
Linear USDT-margined fixed-notional PnL:
- LONG return = `(exit-entry)/entry`;
- SHORT return = `(entry-exit)/entry`;
- gross PnL = $500 × return;
- net PnL = gross PnL - $0.75;
- net win = net PnL >0.

## Metrics
For each candidate report:
- N;
- net WR;
- gross/net PnL;
- expectancy;
- PF;
- max DD;
- max loss/win streak;
- four chronological block PnLs and WRs.

Also report the five-band MOMENTUM and REVERSAL atlas side by side.

## Development candidate gate
A promotable band-response candidate must satisfy ALL:
- >= **100** trades;
- net WR >= **52.0%**;
- net PnL >0;
- expectancy >= **+$0.50/trade**;
- PF >= **1.15**;
- max DD <= **$120**;
- max loss streak <= **8**;
- >= **3/4** chronological blocks with positive net PnL.

Because the family contains only ten preregistered candidates, no extra parameter-neighbor gate is imposed. Strength bands are intentionally allowed to represent distinct regimes.

## Selection
Among candidates passing the Development gate, rank lexicographically by:
1. highest expectancy / net-per-100;
2. highest WR;
3. highest PF;
4. lowest max DD;
5. lowest max loss streak;
6. higher N;
7. lower band ordinal;
8. MOMENTUM before REVERSAL only as final deterministic tie-break.

No second-best substitution after holdout failure.

## Historical replication
Freeze one selected band+mode unchanged and evaluate External and Reference Validation independently.

Each holdout must satisfy:
- >= **50** trades;
- net WR >= **50.5%**;
- net PnL >0;
- expectancy >0;
- PF >=1.05;
- max loss streak <=10.

Both must pass independently. Pooled results are descriptive only.

## Decision
- no Development candidate: `ETH_ECONOMIC_FIRST_E5_NO_DEV_CANDIDATE`;
- selected candidate but either holdout fails: `ETH_ECONOMIC_FIRST_E5_CANDIDATE_NOT_REPLICATED`;
- both holdouts pass: `ETH_ECONOMIC_FIRST_E5_SUPPORTED`.

E5 is designed to identify the actual economic regime inside E2, not to manufacture a higher WR by filtering until sample size disappears.

Research/shadow only. No live promotion or profit guarantee.
