# BTC Temporal Friday F6.18 — Bearish Displacement Protection Checkpoint

**Status:** COMPLETE — SAME-SAMPLE PROVISIONAL PASS  
**Research only; live BBC untouched. Existing F6.12/F6.9/F6.5 definitions unchanged.**

## Purpose
F6.16 showed that post-+1R `taker<0 + below EMA7` can convert losses to profits, but it falsely acts on too many eventual winners. F6.17 found that true givebacks more often show a decisive bearish displacement candle rather than a noisy/wicky healthy pullback.

## Causal timing
- Friday15 BUY parent unchanged: TP +2.0%, SL -0.7%, max hold 6h.
- First +1R hit is only recognized when that 5m milestone candle completes.
- Observe milestone bar plus the next three completed 5m bars.
- Decision is made at the next actual 5m open (same timing as F6.16).
- All F6.18 candidates require the F6.16 alert: median taker over the four known bars < 0 AND latest completed close < EMA7.

## Frozen displacement definition
No body threshold sweep was performed.

`STRONG_BODY = bearish real body > 2 × (upper wick + lower wick)`

This is a geometric body-dominance definition (body > two-thirds of total candle range), frozen before execution.

Predeclared candidates:
1. `D1_STRONG_BODY`
2. `D2_STRONG_BODY_RANGE_EXPAND`: D1 + latest range > median range of prior three known bars
3. `D3_STRONG_BODY_BREAK_PRIOR_LOW`: D1 + latest close < previous completed 5m low
4. `D4_STRONG_BODY_EMA20_LOSS`: D1 + latest close < EMA20

No alternate body ratio, wick threshold, decision timing, EMA, or range horizon was swept.

## Benchmark parity
Parent:
- N 138
- 66W / 72L
- WR 47.83%
- PnL +$64.630
- PF 1.266
- DD $56.530

Existing FIB5 + EARLY10 + F6.5 stack:
- N 138
- WR 47.83%
- PnL **+$105.818**
- PF **1.525**
- DD **$30.295**

F6.16 active P1 alert parity: **16**.

## Results

| Rule | Actions | W cut | true +1R GB | Loss→profit | Incremental | D | V | PnL | WR | PF | DD | Screen |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| D1 strong body | 9 | 4 | 5 | 5 | +$12.635 | +$4.724 | +$7.911 | +$118.453 | 51.45% | 1.653 | $28.699 | PASS |
| D2 + range expand | 2 | 1 | 1 | 1 | +$2.569 | -$1.873 | +$4.442 | +$108.388 | 48.55% | 1.550 | $32.168 | FAIL |
| **D3 + break prior low** | **7** | **2** | **5** | **5** | **+$17.413** | **+$9.502** | **+$7.911** | **+$123.232** | **51.45%** | **1.680** | **$28.699** | **PASS** |
| D4 + EMA20 loss | 4 | 2 | 2 | 2 | +$5.791 | -$2.121 | +$7.911 | +$111.609 | 49.28% | 1.575 | $28.699 | FAIL |

## Best predeclared candidate — D3
Exact rule:

After first +1R, at the frozen F6.16 decision time, protect/exit at the actual decision open iff:
1. median taker over the four completed post-+1R bars < 0;
2. latest completed close < EMA7;
3. latest 5m candle is bearish and its real body > 2 × total wicks;
4. latest completed close < the previous completed 5m candle low.

Results layered after existing FIB5 → EARLY10 → F6.5 priority:
- **7 actions** = Discovery 5 / Validation 2
- **5 true +1R givebacks caught**
- **5 loss→positive conversions**
- **2 eventual winners acted**, but both exits remain profitable
- **0 winner→nonpositive conversions**
- Incremental **+$17.413**
- Discovery **+$9.502**
- Validation **+$7.911**
- Existing stack PnL **+$105.818 → +$123.232**
- WR **47.83% → 51.45%**
- PF **1.525 → 1.680**
- DD **$30.295 → $28.699**

## Mechanism interpretation
F6.18 supports the F6.17 distinction:

`+1R achieved → buyer flow fades → EMA7 acceptance lost → strong bearish displacement → previous 5m low breaks`

is materially more failure-like than merely `flow<0 + below EMA7`.

A temporary EMA7 loss or negative taker flow is often a healthy pullback. The prior-low break combined with body dominance is the useful confirmation that sellers are not merely testing the trend but are actually displacing price downward.

Range expansion and EMA20 loss are not required; adding either as mandatory confirmation becomes too restrictive and/or loses Discovery economics.

## Guardrail
This is **not independent OOS confirmation**. F6.18 was motivated by F6.17 morphology discovered on the same historical sample. Freeze D3 exactly; do not tune body ratio, prior-low definition, EMA, or timing on this sample.

Current true-OOS Fridays after the original cutoff must be replayed unchanged, but they only provide confirmation if the frozen D3 state actually triggers. Zero triggers would be non-informative, not a PASS or FAIL.
