# SOL Regime Stage 4C — Derivatives / Positioning Discovery

Date: 2026-09-26  
Status: **COMPLETE — derivatives add information, but no Bear replacement passes robustness**  
Branch: `research/sol-regime-stage4c`

## Objective

Stage 4C tests whether information economically different from OHLCV can solve
the remaining Bear-direction bottleneck.

Frozen components:

- Stage 1C ground truth,
- Stage 4 adaptive Bull head,
- conflict policy: Bull + Bear evidence -> TRANSITION,
- no 2026 tuning.

Primary derivative families:

1. perpetual premium index,
2. funding-rate level and change,
3. OI / positioning where historical coverage permits.

The Stage 4B Broad Exhaustion price precursor is used as the permissive Bear
pre-gate:

- `ret4 >= 1.053869%`
- `accel4v12 >= 0.877085%`
- `distLow8 >= 3.046480%`

Derivatives are allowed to **filter** this precursor. They are not allowed to
create Bear calls from nothing.

---

## A. Data audit

### Premium index

Binance premium-index 1H history was available continuously over the research
window.

Loaded:

- 25,428 hourly observations,
- 2023-11-01 through 2026-09-25 11:00 UTC.

Features tested included:

- current premium,
- 8H / 24H average and maximum,
- 24H z-score,
- 4H / 8H premium change,
- rolling 720H percentile,
- hourly premium range.

### Funding

Historical SOLUSDT funding-rate records were available across the full research
window.

Loaded:

- 3,455 funding observations,
- sufficient warm-up before DEV.

Features tested included:

- current and previous funding,
- funding delta,
- rolling 3/6/9-event mean,
- positive-funding persistence,
- 30-event z-score,
- 90-event percentile.

### Open interest

The Binance Open Interest Statistics REST endpoint only exposes the latest
~30 days, so OI cannot be used in DEV/2025 model selection on the same footing
as the other features.

Therefore:

- OI is **excluded from formal Stage 4C selection**;
- recent OI is used only as an exploratory OOS diagnostic;
- historical Public Data metrics should be acquired separately before OI can
  enter a production research gate.

---

## B. Premium-index result

Premium features can produce attractive DEV improvements but do not transfer
reliably.

Example DEV-selected filter:

- low current premium-range.

Broad Exhaustion base precision:

- DEV: **18.21%**
- VAL 2025: **16.52%**
- OOS 2026: **14.72%**

A representative low-premium-range filter improved DEV precision to about
**23–24%**, but:

- 2025 fell back around / below the unfiltered Broad baseline,
- OOS could deteriorate sharply.

### Verdict

**Premium index alone = FAIL as a robust Bear discriminator.**

---

## C. Funding deterioration is the strongest new derivative feature

The most interesting stable orientation is **not high funding itself**.

It is:

> **funding falling after an already-strong rally.**

Among DEV-derived thresholds, the 75th-percentile funding-drop candidate was:

`fund_delta <= -0.00003828`

where `fund_delta = latest funding - previous funding`.

Combined rule:

- Broad Exhaustion price precursor,
- funding delta <= -0.00003828,
- frozen Stage 4 Bull conflict -> TRANSITION.

### Annual results after conflict handling

| Period | Bear n | Precision | Recall | Lift |
|---|---:|---:|---:|---:|
| DEV | 258 | **25.58%** | 4.91% | **1.803x** |
| VAL 2025 | 207 | **17.87%** | 2.70% | **1.141x** |
| OOS 2026 | 83 | **20.48%** | 2.37% | **1.827x** |

This is materially more selective than Broad Exhaustion alone.

Interpretation:

> After a strong / accelerated rally, a meaningful drop in funding may capture
> the beginning of long-crowding unwind rather than continued healthy
> continuation.

This is the first Stage 4C derivative feature with a consistent annual
orientation DEV -> VAL -> OOS.

---

## D. But quarterly robustness still fails

The same fixed funding-drop rule produces:

| Quarter | Precision | Lift |
|---|---:|---:|
| 2025 Q1 | 16.42% | **0.831x** |
| 2025 Q2 | 12.73% | **0.945x** |
| 2025 Q3 | 16.67% | 1.319x |
| 2025 Q4 | 24.59% | 1.459x |
| 2026 Q1 | 17.31% | 1.074x |
| 2026 Q2 | 28.00% | 2.580x |
| 2026 Q3 | 16.67% | 2.591x |

The annual result is strong, but Q1/Q2 2025 do not pass the >1x subperiod gate.

Other DEV-derived funding-drop thresholds (q65/q70/q80) were also tested.
None keeps every 2025 quarter above 1x.

### Verdict

Funding deterioration is **research-positive but not promotion-ready**.

---

## E. Funding + premium conjunction search

A larger search combined premium and funding features.

Protocol:

1. build rules only from DEV thresholds,
2. require improvement in both DEV subperiods,
3. shortlist DEV candidates,
4. validate on 2025,
5. only then inspect 2026.

One apparently attractive VAL candidate used:

- low 24H maximum premium,
- persistent positive funding.

It reached approximately:

- DEV precision: **28.19%**
- VAL precision: **22.58%**

but collapsed OOS:

- OOS precision: **5.88%**

Therefore it was rejected.

A stricter search then required:

- stable DEV H1 and H2,
- >2% annual improvement in 2025,
- **every 2025 quarter at or above its Bear base rate**.

Result:

> **0 of 603 DEV derivative candidates passed the full validation gate.**

This is the decisive Stage 4C result.

---

## F. Recent OI diagnostic — exploratory only

The API-accessible OI window yielded:

- 708 hourly OI observations,
- 20 recent Broad Exhaustion + no-Bull-conflict candidates,
- only **1** true Bear in that tiny candidate sample.

For that single true-Bear case:

- OI 4H change: about **-3.07%**
- OI 8H change: about **-3.14%**

while the false-Bear candidates had median OI changes around:

- +1.05% over 4H,
- +1.15% over 8H.

That pattern is economically interesting — rally followed by OI contraction —
but **n=1 true Bear is far too small for inference**.

### Verdict

OI remains a promising missing variable, but no statistical claim is made from
the recent API window.

---

# Stage 4C final verdict

## PASS as research insight

1. Derivatives positioning contains incremental Bear information.
2. **Funding deterioration after an overextended rally** is the strongest new
   signal found in Stage 4C.
3. The effect survives annual DEV -> 2025 -> 2026 directionally.
4. Premium level/range by itself is not sufficiently portable.
5. OI contraction is worth testing once full historical OI is available.

## FAIL as detector promotion

1. No funding threshold passes every 2025 quarter.
2. Premium + funding conjunctions can strongly overfit validation.
3. Zero derivatives candidates pass the strict DEV + all-2025-quarter gate.
4. Historical OI coverage is insufficient through the REST endpoint for fair
   DEV/VAL selection.

## Production / research decision

**Do not replace the Bear V1 fallback yet.**

Current state:

- **Bull Stage 4 adaptive head: PASS / frozen**
- **Bear V1: conservative fallback**
- **Stage 4B OHLCV replacements: rejected**
- **Stage 4C funding deterioration: keep as research feature, not final rule**
- **Stage 4C premium rules: rejected**
- **OI: requires full historical archive before formal evaluation**
- **TRANSITION / abstention remains mandatory**

## Next logical step

A next Bear-specific loop should obtain historical OI / positioning metrics and
test **sequencing**, not static thresholds:

1. price rally,
2. OI expansion / crowding,
3. funding or premium deterioration,
4. OI contraction / failed continuation,
5. downside confirmation.

This is a more economically coherent candidate mechanism than another flat
single-candle rule.
