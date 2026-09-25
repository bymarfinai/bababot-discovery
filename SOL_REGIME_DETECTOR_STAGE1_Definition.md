# SOL 1H Bull / Bear / Sideways Detector — Stage 1 Definition Freeze

**Status:** FROZEN DEFINITION CONTRACT — no threshold optimization in Stage 1.

## 1. Objective

Create a causal market-regime layer for SOLUSDT that classifies every completed 1H candle into exactly one primary regime:

- `BULL`
- `BEAR`
- `SIDEWAYS`

and separately emits:

- `confidence` in [0, 1]
- `transition_flag` = true/false
- `context_4h` = bullish / bearish / balanced context from the last fully completed 4H candle.

The detector is not an entry strategy. It must be evaluated independently from trade outcome.

## 2. Timing / causality contract

At 1H candle close time `t`:

1. Only OHLCV data with timestamps <= `t` may be used.
2. A 1H regime label becomes actionable only at the next 1H open.
3. 4H features may use only a 4H candle whose close time <= `t`; partial 4H bars are forbidden.
4. Future return, future MFE/MAE, TP/SL result, or any later candle may never enter the classifier.
5. A swing pivot may be timestamped in the past, but it becomes usable only at its causal confirmation time.

## 3. Regime semantics

### BULL

BULL means **persistent upward price discovery**, not merely EMA-fast > EMA-slow.

A Bull state requires evidence from multiple independent families:

- **Structure:** confirmed swing sequence progresses upward (higher highs and higher lows).
- **Directional drift:** medium-horizon return / EMA slope is positive.
- **Acceptance:** price spends meaningful time above a local equilibrium rather than only wicking above it.
- **Efficiency:** net upward displacement is meaningful relative to path travelled.
- **Context:** 4H must not strongly contradict the 1H state.

A single large green candle is an impulse, not sufficient proof of BULL.

### BEAR

BEAR is the exact directional mirror of BULL:

- lower highs and lower lows,
- negative drift,
- acceptance below equilibrium,
- efficient downside displacement,
- no strongly contradictory completed 4H context.

### SIDEWAYS

SIDEWAYS is a **positively identified balance regime**. It is NOT the default remainder after Bull/Bear fail.

Evidence must come from balance/range behavior such as:

- low directional efficiency,
- repeated mean crossing,
- high candle / range overlap,
- contained rolling range relative to travelled path,
- no persistent confirmed swing progression,
- muted medium-horizon drift.

A market that has just broken a Bull structure but has not yet established balance must not instantly become SIDEWAYS.

## 4. Transition handling

`TRANSITION` is a flag, not a fourth primary class.

`transition_flag = true` when one or more of these is happening:

- current regime loses structural validity,
- directional score decays materially,
- opposite directional evidence appears,
- balance evidence is rising but has not yet confirmed SIDEWAYS,
- a new directional regime is forming but persistence confirmation is incomplete.

During transition, the detector keeps one of BULL / BEAR / SIDEWAYS as its primary state, but confidence is reduced.

This prevents one-candle flip-flopping while still exposing uncertainty to the strategy layer.

## 5. Swing-structure contract

Stage 2 must implement a single causal swing engine satisfying all rules below:

1. A swing high/low is confirmed only after the required right-side candles have closed.
2. Confirmation latency must be recorded explicitly.
3. Swing events must be stored by unique bar identity, not deduplicated only by price.
4. Structural sequence must be chronological and alternate high/low states where appropriate; HH/HL counts may not be accumulated from independent stale streams.
5. Equal-high / equal-low retests must remain observable as liquidity structure and must not disappear due to equal-price deduplication.
6. A **protected low** in BULL means the last causally confirmed structural low whose survival is required for the current bullish structure; it is not automatically “the latest low”.
7. Protected high in BEAR is symmetric.
8. Swing significance may be ATR-scaled, but ATR must be measured at the candidate/confirmation event using one frozen convention.

## 6. Directional / balance feature families reserved for Stage 2

No optimized thresholds are chosen here. Stage 2 may compute:

### Structure
- last confirmed swing high delta
- last confirmed swing low delta
- HH/HL/LH/LL sequence state
- structural break / reclaim state
- protected swing survival

### Trend / drift
- EMA slope normalized by price
- EMA slope normalized by ATR
- fast/slow EMA spread
- rolling return over frozen horizons
- price distance from equilibrium

### Directional efficiency
- absolute net displacement / summed absolute bar-to-bar movement
- directional persistence of closes

### Balance
- mean-cross count
- candle overlap ratio
- rolling range / travelled path
- compression / expansion state
- rolling high/low containment

### Volatility
- ATR percentile / normalized ATR
- range expansion vs prior window

### 4H context
- completed-4H drift
- completed-4H structure
- completed-4H equilibrium alignment

## 7. Scoring architecture reserved for Stage 3

The final classifier must use three competing evidence scores:

- `BullScore`
- `BearScore`
- `SidewaysScore`

The primary regime is determined by relative evidence plus hysteresis/persistence, not by a hard “if Bull else if Bear else Sideways” fallback.

Confidence must depend on score separation and evidence agreement.

Exact score weights and thresholds are NOT selected in Stage 1.

## 8. Non-negotiable validation tests reserved for Stage 5

A useful detector must demonstrate that regime labels separate subsequent market behavior without using that future behavior to create the labels.

For each class, later validation will compare:

- +1% first-hit vs -1% first-hit
- forward signed return
- MFE / MAE distribution
- realized volatility
- duration and transition frequency
- regime persistence
- strategy WR conditioned on regime

If Bull, Bear, and Sideways produce materially similar future distributions, the detector is rejected even if the labels look visually plausible.

## 9. Data split policy

- Development: 2023-01-01 through 2024-12-31
- Holdout: 2025-01-01 through 2025-12-31
- Final validation: 2026-01-01 onward

2025 and 2026 may not be used to choose Stage-2/3 thresholds or weights.

## 10. Stage-1 decision

The new SOL regime detector will NOT reuse V2/V2.5 classifications as ground truth.

Old code may contribute feature ideas only after audit.

**Stage 1 complete when this definition contract and the legacy audit are committed.**
