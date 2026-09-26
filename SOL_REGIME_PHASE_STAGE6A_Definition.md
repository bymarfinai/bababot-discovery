# SOL Regime + Phase Detector V2 — Stage 6A Taxonomy Freeze

**Status:** FROZEN DEFINITION CONTRACT

Stage 6A defines the phase taxonomy only. It does **not** optimize thresholds, fit weights, use forward returns, or label 2025/2026.

The purpose is to separate:

> **what direction / regime the market appears to be in**

from:

> **where the market currently is inside that directional lifecycle**

This distinction is required because Stage 5 / 5F showed that directional recognition alone did not create reliable +1%/-1% continuation edge.

---

## 1. Core architecture

The V2 architecture is:

`REGIME CONTEXT -> PHASE STATE -> EVENT / ENTRY QUALITY`

The layers are intentionally separate.

### Regime context
Possible context:
- BULL
- BEAR
- SIDEWAYS
- uncertain / mixed evidence

The failed V1 Bull/Bear detector is **not ground truth**. Its score/state may be used later as one causal input, but Stage 6B/6C must be able to form phase evidence from raw causal features independently.

### Phase state
Directional lifecycle:
- EARLY_EXPANSION
- HEALTHY_CONTINUATION
- MATURE_TREND
- EXHAUSTION
- TRANSITION

Sideways lifecycle:
- COMPRESSION
- BALANCED_RANGE
- EXPANSION_ATTEMPT

`TRANSITION` is shared across directional and sideways contexts when the current state is losing internal consistency and a new state has not yet causally established itself.

---

## 2. Non-negotiable causality contract

At completed 1H candle close `t`:

1. Only completed 1H candles with close time <= `t` may be used.
2. 4H context may only use fully completed 4H candles.
3. A phase label becomes actionable only at the next 1H open.
4. Future return, TP/SL outcome, future MFE/MAE, future swing confirmation, or later phase persistence may not be used to label the current bar.
5. An event that occurred historically but is confirmed later becomes usable only at its causal confirmation time.
6. Event age is measured from the first bar at which that event was causally observable.
7. No centered rolling window, ZigZag with future pivots, or retrospectively edited swing path is allowed.
8. Stage 6A contains no tuned numeric thresholds beyond semantic examples. Numeric boundaries belong to a separately preregistered later stage.

---

# 3. Directional phase taxonomy

The following definitions are symmetric for BULL and BEAR.

For BULL examples below, reverse all directions for BEAR.

---

## 3.1 EARLY_EXPANSION

### Meaning

A directional move has **just escaped balance / local containment** and is beginning price discovery.

This is the earliest directional phase. It must not require a mature HH/HL chain.

### Required semantic evidence families

An Early Expansion candidate should show several of:

- recent directional displacement or impulse,
- recent break from a prior local range / swing boundary,
- increasing realized range or ATR versus recent baseline,
- directional close persistence,
- directional efficiency rising,
- limited elapsed time since expansion began,
- limited already-consumed directional distance,
- no major opposite rejection yet.

### What Early Expansion is NOT

- not merely one large green/red candle,
- not a move that has already travelled far from equilibrium,
- not a trend that has existed for many bars,
- not a retrospective swing label requiring many hours of right-side confirmation.

### Key semantic test

> **Has directional expansion recently begun, with a meaningful amount of potential move still unconsumed?**

---

## 3.2 HEALTHY_CONTINUATION

### Meaning

A directional move is established and is still demonstrating **renewable directional demand/supply**, not just historical trend.

Healthy Continuation is the phase most relevant to a continuation-style BabaBot entry.

### Required semantic evidence families

A candidate should show a combination of:

- directional structure remains intact,
- favorable progress renews after pauses/pullbacks,
- pullback depth is controlled relative to prior expansion,
- price reclaims / re-accepts directional equilibrium after retracement,
- favorable excursion continues to make incremental progress,
- directional efficiency remains positive,
- adverse excursion since the last impulse is contained,
- trend age / extension is not yet extreme,
- no strong rejection / failed continuation signature.

### Important distinction from EARLY_EXPANSION

EARLY_EXPANSION:
> the move is newly escaping.

HEALTHY_CONTINUATION:
> the move has already established itself and successfully renews progress after interruption.

### Key semantic test

> **Is the trend proving that it can continue from the current location, not merely proving that it existed?**

---

## 3.3 MATURE_TREND

### Meaning

Directional structure remains valid, but the move has already consumed substantial **time, distance, or excursion budget**.

Mature Trend is not automatically bearish in a Bull regime or bullish in a Bear regime. It means:

> continuation may still occur, but marginal continuation quality is no longer assumed to be high.

### Required semantic evidence families

A candidate may show:

- persistent directional structure,
- older impulse / break age,
- substantial cumulative directional displacement,
- large distance from anchor/equilibrium or protected structure,
- repeated continuation legs already completed,
- diminishing incremental MFE per unit of time,
- reduced directional acceleration,
- deeper or slower pullbacks than earlier in the move,
- 4H context already fully aligned and extended.

### Key semantic test

> **Is the directional thesis still intact, but much of the easy directional move already behind us?**

Mature Trend must remain distinguishable from EXHAUSTION:

- Mature = extended but still functioning.
- Exhaustion = extension plus evidence that new directional progress is failing / being rejected.

---

## 3.4 EXHAUSTION

### Meaning

The market may still look directionally bullish/bearish by conventional structure, but **incremental directional progress is deteriorating relative to the extension already consumed**.

This is deliberately orthogonal to regime.

A market may therefore be:

> `regime_context=BULL` + `phase=EXHAUSTION`

without contradiction.

### Required semantic evidence families

Exhaustion should require evidence from at least two distinct ideas:

### A. Stretch / consumed move
Examples:
- unusually large aligned return already travelled,
- extreme distance from equilibrium,
- high excursion since expansion start,
- old trend age,
- multiple completed directional legs.

### B. Deteriorating marginal progress
Examples:
- new highs/lows add little favorable excursion,
- directional efficiency falls,
- price spends more path length for less net progress,
- repeated failed fresh-break attempts,
- pullbacks deepen,
- reclaim quality weakens.

### C. Rejection / climax evidence
Examples:
- large directional wick after extension,
- terminal range expansion without follow-through,
- volume/range climax followed by failure,
- failed acceptance beyond a prior extreme,
- return back through short-term equilibrium after fresh extreme.

A single “overbought/oversold” indicator is not sufficient.

### Key semantic test

> **Has price already travelled materially in this direction while evidence of additional directional payoff is deteriorating?**

This is the phase specifically motivated by Stage 5F and prior repo findings that chasing an already stretched trend can produce mean-reversion instead of continuation.

---

## 3.5 TRANSITION

### Meaning

The prior phase/regime logic is losing validity, but a new stable phase is not yet causally established.

Transition is **not equivalent to Sideways**.

### Evidence families

Examples:
- directional structure weakens or protected structure fails,
- opposite directional score rises,
- balance evidence rises rapidly,
- directional efficiency collapses,
- failed break/reclaim occurs,
- incumbent directional impulse no longer renews,
- compression appears after directional expansion,
- conflicting 1H and fully-completed 4H evidence.

### Key semantic test

> **Is the previous state no longer internally coherent, while the next state is still unresolved?**

Transition must be explicit so the detector is not forced to call every uncertain bar SIDEWAYS.

---

# 4. Sideways phase taxonomy

Sideways is not homogeneous.

---

## 4.1 COMPRESSION

### Meaning

Range and volatility are contracting and directional information is weak.

Semantic evidence:
- falling normalized ATR / range,
- narrow rolling range,
- high overlap,
- low directional efficiency,
- low net displacement,
- repeated mean crossing,
- no persistent range escape.

### Key question

> **Is market energy being stored rather than expressed directionally?**

---

## 4.2 BALANCED_RANGE

### Meaning

Price is actively rotating inside an established balance zone.

Semantic evidence:
- repeated two-sided traversal,
- high overlap,
- stable range boundaries,
- repeated mean crossing,
- no sustained acceptance outside the range,
- directional impulses repeatedly fade.

Unlike Compression, Balanced Range does not require volatility to be especially low.

### Key question

> **Is price moving, but repeatedly auctioning both directions without persistent escape?**

---

## 4.3 EXPANSION_ATTEMPT

### Meaning

A market classified as balance/compression is attempting to resolve directionally, but the attempt has not yet earned EARLY_EXPANSION status.

Semantic evidence:
- range boundary violation or directional impulse,
- volatility begins expanding,
- directional efficiency improves,
- one-sided closes emerge,
- but acceptance/persistence outside balance remains unconfirmed.

Expansion Attempt may:
- succeed -> EARLY_EXPANSION,
- fail -> BALANCED_RANGE,
- fail violently -> TRANSITION / opposite attempt.

### Key question

> **Is balance beginning to break, but not yet proven as genuine directional expansion?**

---

# 5. Phase is not just "age"

Time since impulse/break is an important feature, but phase may not be assigned from age alone.

Example:

- a 3-hour-old move can already be exhausted after a violent +8% expansion,
- a 20-hour trend can remain healthy if pullbacks are controlled and marginal progress persists.

Therefore phase must combine:

> **age + consumed distance + renewal quality + rejection/failure evidence**

not just elapsed bars.

---

# 6. Phase is not just "regime"

A BULL context may contain:

- EARLY_EXPANSION
- HEALTHY_CONTINUATION
- MATURE_TREND
- EXHAUSTION
- TRANSITION

Likewise BEAR.

This is a central architectural rule.

Stage 6C must never implement:

`if BULL then HEALTHY_CONTINUATION`

or any equivalent shortcut.

---

# 7. Frozen phase evidence dimensions for Stage 6B

Stage 6B is authorized to compute these causal feature families.

## 7.1 Event clocks / age

- hours since latest directional impulse start
- hours since latest range/swing break
- hours since raw score directional switch
- hours since last accepted structural renewal
- hours since last pullback start/end
- regime-state age
- phase-candidate age

## 7.2 Consumed directional move

Side-normalized:
- aligned return since impulse
- aligned return since break
- aligned MFE since impulse
- aligned MFE since break
- total favorable distance travelled
- distance from pre-expansion equilibrium
- distance from EMA20 / slower anchor in ATR units
- distance from protected swing

## 7.3 Marginal progress / renewal

- new favorable excursion over trailing 1/3/6/12H
- favorable excursion increment divided by prior favorable excursion
- time since last fresh extreme
- fresh-extreme frequency
- break distance beyond prior extreme
- closes accepting beyond prior extreme
- progress per unit path length

## 7.4 Pullback quality

- pullback depth vs preceding impulse
- pullback duration
- pullback adverse excursion
- pullback efficiency
- reclaim distance
- reclaim body / close location
- post-reclaim favorable progress
- failed reclaim count

## 7.5 Directional efficiency / persistence

- signed efficiency
- aligned close fraction
- directional path efficiency
- EMA slope / spread
- repeated equilibrium crossing
- candle overlap
- aligned body fraction

## 7.6 Stretch / maturity

- cumulative aligned move in ATR units
- trend age
- number of directional legs / renewals
- distance from equilibrium
- 1H vs completed-4H extension agreement
- percentile of aligned displacement vs trailing history

## 7.7 Exhaustion / rejection

- wick against direction after fresh extreme
- failed break beyond prior extreme
- close back inside prior range
- range climax without follow-through
- volume climax without follow-through
- decreasing MFE increments
- increasing MAE / pullback depth
- efficiency decay
- short-term equilibrium loss after extension

## 7.8 Volatility state

- ATR level / percentile
- ATR slope
- realized range expansion/contraction
- compression duration
- volatility burst age

## 7.9 Sideways-specific balance

- rolling containment
- range width
- mean-cross count
- overlap ratio
- boundary-touch count
- failed escape count
- balance age
- compression slope

---

# 8. Reserved Stage 6C outputs

Stage 6C may later produce independent evidence scores:

- EarlyExpansionScore
- HealthyContinuationScore
- MatureTrendScore
- ExhaustionScore
- TransitionScore
- CompressionScore
- BalancedRangeScore
- ExpansionAttemptScore

Possible auxiliary quality scores:
- RemainingEnergyScore
- ContinuationQualityScore
- ReversalRiskScore

These are **reserved names only**. Weights and thresholds are not chosen in Stage 6A.

---

# 9. Phase precedence contract

Stage 6C must explicitly handle competing evidence.

Semantic precedence:

1. Strong invalidation / contradictory state -> TRANSITION candidate.
2. If balance context:
   - COMPRESSION / BALANCED_RANGE / EXPANSION_ATTEMPT compete.
3. If directional context:
   - EARLY_EXPANSION / HEALTHY_CONTINUATION / MATURE_TREND / EXHAUSTION compete.
4. EXHAUSTION may override MATURE when marginal-progress failure/rejection evidence is sufficiently strong.
5. HEALTHY_CONTINUATION may not be assigned solely from trend direction.
6. EARLY_EXPANSION may not be assigned after large consumed move solely because a new swing confirmation just appeared.

Exact thresholds belong to Stage 6C.

---

# 10. Development / validation policy

Because Stage 5/5F outcomes are now known, 2023-2024 are **development data** for V2.

They are no longer eligible to be described as pristine validation for the redesigned detector.

Policy:

- 2023-2024: V2 development / phase discovery
- 2025: first frozen external holdout for V2
- 2026: final validation only after 2025 passes
- no threshold may be adjusted after inspecting 2025 and still be called the same frozen V2 model.

Stage 6B/6C may use 2023-2024 only.

---

# 11. Stage 6A success condition

Stage 6A is complete when:

1. the phase taxonomy is frozen,
2. directional and sideways phase semantics are explicit,
3. phase is declared orthogonal to regime,
4. V1 Bull/Bear is not treated as ground truth,
5. causal feature families for Stage 6B are frozen,
6. no numeric optimization or forward-outcome fitting occurs.

**Stage 6A outcome: DEFINITION ONLY — no claim yet that any phase predicts trading outcomes.**
