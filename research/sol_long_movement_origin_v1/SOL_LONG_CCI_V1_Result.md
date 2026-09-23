# SOL LONG Movement-Origin V1 — Coiled Continuation Ignition

**Status: STRONG_HISTORICAL_CHARACTER_FOUND__NEEDS_FRESH_FORWARD_CONFIRMATION**

## Why this reset exists
Previous SOL discovery started from a narrow pre-existing setup universe (147 LONG examples). This study resets the unit of discovery to the full hourly market path.

## Data universe
- SOLUSDT USD-M futures
- 1H candles
- 2023-01-01 through 2026-09-23
- 32,680 continuous hourly candles
- no gaps in the assembled series

## Causal execution
All state and trigger variables use only completed candles through signal hour `t`.
Entry is the **next 1H open**.
TP/SL monitoring begins after the signal candle.
No selected primary event had a same-1H TP/SL ordering ambiguity.

## Independent episode construction
Candidate state observations separated by <=6 hours are treated as one state episode.
Only the first qualifying trigger inside an episode is used.
This removes the inflated WR that occurs when many adjacent hourly anchors from the same move are counted as separate trades.

## Final simple character

### State: COILED CONTINUATION
1. **7-day realized range <= 12%**
   - `range7 = (high168 - low168) / close <= 0.12`
2. **Price is in the top 20% of the 7-day range**
   - `loc7 = (close - low168)/(high168-low168) >= 0.80`
3. **The last 24h has already expanded to >=60% of the 7-day range**
   - `range24 / range168 >= 0.60`

Interpretation: SOL is still in a relatively compressed 7-day habitat, but price has migrated to the upper end and a fresh 24h expansion is underway.

### Trigger: ACCEPTANCE NEAR THE HIGH, NOT BLOW-OFF
4. **Close is no more than 1% below the prior 24h high**
   - `close / prior24h_high - 1 >= -0.01`
5. **The 24h-vs-7d expansion ratio has not accelerated by >4 percentage points in the last 3h**
   - `(range24/range168)_t - (range24/range168)_{t-3h} <= 0.04`

Interpretation: price is accepted near the high, but the move is not an accelerating vertical chase.

## Primary economic test
- LONG at next 1H open
- TP: **+4.0%**
- SL: **-2.5%**
- maximum horizon: **96 hours**
- TP/SL ratio: **1.60 : 1**

### Results
- Fired independent episodes: **23**
- Wins: **18**
- Losses: **4**
- No-hit by 96h: **1**
- Same-candle ambiguities: **0**
- Decided WR: **18/22 = 81.82%**
- Win rate over all fired episodes: **18/23 = 78.26%**
- Wilson 95% interval for decided WR: approximately **61.5% to 92.7%**

Year:
- 2023: 3W / 1L / 1 no-hit -> 75.0% decided
- 2024: 5W / 1L -> 83.33%
- 2025: 6W / 1L -> 85.71%
- 2026: 4W / 1L -> 80.0%

Gross expectancy using TP/SL R and ignoring the mark-to-market value of the single no-hit:
- reward = 4/2.5 = **1.60R**
- decided expectancy = **+1.127R per decided event**
- if the no-hit is conservatively treated as 0R, realized hit-based total = **+24.8R / 23 fired events = +1.078R per fired event**
- fees/slippage are not included in these figures.

## Scale consistency
Same fixed character and trigger:

### +3% / -2%, 72h
- 18W / 5L
- **78.26% WR**
- 2023 80.0%
- 2024 83.3%
- 2025 71.4%
- 2026 80.0%

### +5% / -2.5%, 120h
- 17W / 5L / 1 no-hit
- **77.27% decided WR**
- 2023 75.0%
- 2024 83.3%
- 2025 85.7%
- 2026 60.0%

### +6% / -3%, 168h
- 15W / 7L / 1 no-hit
- **68.18% decided WR**

The edge is strongest around the +3% to +5% continuation zone, which is economically coherent with SOL's weekly range.

## Threshold robustness
The state is not supported by one magic cut:
- 7d range cap around **11%-13%** remained viable in sensitivity tests.
- upper-range location around **>=80%** remained viable.
- 24h/7d expansion share around **60%-65%** remained viable.

Representative +3%/-2% episode tests:
- 7d range <=11%, loc >=80%, share >=60%: 80% / 75% / 80% across DEV / 2025 / 2026
- <=12%, >=80%, >=60%: 81.8% / 71.4% / 83.3%
- <=13%, >=80%, >=60%: 76.9% / 71.4% / 83.3%
- <=12%, >=80%, >=65%: 80% / 71.4% / 83.3%

## What failed
A pure downside-sweep LONG hypothesis did **not** explain SOL's large upside legs.
Across the broad hourly universe, sweep-only states had weak WR near/below baseline.
The higher-quality character is **continuation after compression and acceptance near the weekly high**, not generic bottom fishing.

## Structural interpretation
The recurring sequence is:

`7D COMPRESSION -> PRICE MIGRATES TO UPPER RANGE -> 24H EXPANSION -> ACCEPTANCE WITHIN ~1% OF 24H HIGH -> EXPANSION STABILIZES -> CONTINUATION LONG`

This is best thought of as **Coiled Continuation Ignition (CCI)**.

## Important validation status
This character was discovered through iterative historical research. Although year-by-year temporal results are stable and 2026 confirms the same mechanism, 2026 is **not a pristine untouched holdout** because the research process inspected 2026 during iteration.

Therefore:
- historical character: **strong**
- economic consistency: **strong**
- ready-to-encode detector candidate: **yes**
- claim of guaranteed/live 80% future WR: **no**
- next scientific requirement: freeze CCI V1 and test on genuinely unseen future data or an untouched external venue/market-history slice without changing thresholds.
