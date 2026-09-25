# SOL Regime Detector — Stage 2 Feature Engine Preregistration

**Status: FROZEN BEFORE EXECUTION**

Stage 2 builds causal features only. It does **not** assign BULL / BEAR / SIDEWAYS labels and does not optimize thresholds against future returns.

## Data
- SOLUSDT perpetual futures, Binance Vision monthly 5m klines.
- Fetch warmup: 2022-06-01.
- Feature output: 2023-01-01 through 2026-09-01 (latest complete month available at current project date).
- 1H candles require all 12 constituent 5m bars.
- 4H candles require all 48 constituent 5m bars.

## Frozen indicator conventions
- EMA fast = 7, EMA slow = 20.
- ATR = Wilder ATR(14).
- 1H rolling horizons: 3, 6, 12, 24 bars.
- Balance windows: 12 and 24 bars.
- Volatility percentile lookback = 168 1H bars.
- 4H context: EMA7/EMA20, ATR14, returns over 3 and 6 completed 4H bars, efficiency over 6 completed 4H bars.

These are feature definitions, not regime thresholds.

## Causal swing engine
Primary 1H structural engine:
- left bars = 5
- right bars = 5
- minimum prominence = 0.50 × ATR14 measured at the pivot candidate bar
- pivot becomes usable only on the confirmation bar, exactly 5 bars after the candidate
- raw candidate events are retained by unique (type, pivot timestamp), including equal-price retests
- structural state uses an alternating accepted sequence
- consecutive same-type candidates may update the active leg only when more extreme; previously emitted feature rows are never rewritten

4H structural context uses the same logic with:
- left bars = 3
- right bars = 3
- prominence = 0.50 × 4H ATR14

## Structural semantics
- latest HH delta = latest accepted swing high minus prior accepted swing high, normalized by ATR at decision time
- latest HL delta = latest accepted swing low minus prior accepted swing low, normalized by ATR
- structural state is BULL_SEQ only when the last two accepted highs are higher and the last two accepted lows are higher
- BEAR_SEQ is symmetric
- otherwise structure is MIXED / INSUFFICIENT
- protected low is the last confirmed low that preceded a confirmed higher-high break
- protected high is the last confirmed high that preceded a confirmed lower-low break

## Feature families
### Structure
- swing count
- last high / low distance
- HH/HL/LH/LL ATR-normalized deltas
- structural sequence state
- protected low/high distance
- break above last swing high / below last swing low
- raw pivot confirmation flags

### Trend / drift
- EMA7/EMA20 spread
- EMA7 and EMA20 slope normalized by price and ATR
- close distance to EMA7/EMA20
- rolling returns 3/6/12/24h

### Directional efficiency
- absolute net displacement / sum absolute close-to-close travel
- positive-close fraction
- negative-close fraction

### Balance
- EMA20 mean-cross count
- consecutive candle range-overlap ratio
- rolling high-low range / close-travel ratio

### Volatility
- ATR / close
- ATR / rolling median ATR
- ATR percentile over 168h

### 4H context
Only the **last fully completed 4H candle** available at the 1H decision close:
- EMA spread / slope
- close distance to EMA20
- 12h and 24h return
- 24h directional efficiency
- causal 4H swing structure
- source 4H close timestamp

## Mandatory Stage-2 audits
1. Raw 5m coverage >= 99.5%.
2. Every exported 1H bar contains exactly 12 5m bars.
3. Every used 4H context bar contains exactly 48 5m bars.
4. Accepted swing sequence alternates H/L.
5. Raw swing event identity is unique by type + pivot timestamp.
6. Confirmation delay equals frozen right-side bar count.
7. 4H context close timestamp <= 1H decision timestamp.
8. Prefix-causality test: recompute selected historical checkpoints using only data available up to each checkpoint; feature values at that checkpoint must match the full-run engine within numerical tolerance.
9. No forward return / TP / SL / future MFE-MAE fields exist in Stage-2 feature output.

Stage 2 passes only if all mandatory audits pass.
