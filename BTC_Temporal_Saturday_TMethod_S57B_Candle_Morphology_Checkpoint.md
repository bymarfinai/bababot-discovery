# BTC Temporal Saturday T-Method S5.7B — Candle Morphology & Sequence Atlas

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — FORENSIC PASS; CANDLE MORPHOLOGY CONTAINS SIGNAL, NO ACTION PROMOTED  
**Research only:** live BBC untouched

## Frozen parity
- +0.50 hinge trades: **89** = 61 future-deep / 28 shallow
- First <=+0.40 giveback candles: **81**
- Rebuild-first >=+0.50 candles: **34**
- Static parent all-trade PnL: **+$87.200**
- A7.19 full-coverage PnL: **+$103.383**

## Fixed morphology taxonomy
No candle-definition sweep was used.
- `DOJI_LIKE`: body/range <=20%
- `STRONG_BODY`: body/range >=70%
- `CLOSE_TOP_Q` / `CLOSE_BOTTOM_Q`: close location >=75% / <=25%
- `LOWER_WICK_DOM` / `UPPER_WICK_DOM`: wick >=50% of candle range
- BULL / BEAR
- ENGULF / INSIDE / OUTSIDE relative to previous completed 5m candle

## 1. Main finding — +0.50 hinge rejection matters
At the first completed +0.50 hinge candle, future deep runners show a more accepted bullish structure:
- body ratio median deep/shallow: **0.632 / 0.540**; direction DEEP_HIGH in both chronology halves
- upper-wick ratio median: **0.302 / 0.406**; direction DEEP_LOW in both halves
- close-location median: **0.698 / 0.594**; direction DEEP_HIGH in both halves
- range as % entry is also slightly higher for deep runners in both halves

### Fixed label: `HINGE05::UPPER_WICK_DOM`
- N **16**
- future deep **43.75%**
- no dominant upper wick: N73 / deep **73.97%**
- Discovery: N10 / deep **40.0%** vs complement **77.27%**
- Validation: N6 / deep **50.0%** vs complement **68.97%**

This is the cleanest fixed candle-pattern clue in S5.7B. A large upper wick at the exact candle that first proves +0.50 is consistent with **rejection / weak acceptance**, while a more body-supported close is more runner-like.

Important economic guardrail: the upper-wick-dominant cohort is still profitable under A7.19; this is **not** evidence for an immediate cut. It is a confidence/failure-context clue only.

## 2. Doji is NOT the answer
### Hinge doji-like
- N10 / deep **70.0%**
- Discovery **71.4%**, Validation **66.7%**
- essentially no separation from non-doji hinge candles

### Giveback doji-like
- N5, all in discovery; deep **40%**
- no validation observations, therefore unusable

### Rebuild doji-like
- N3 / deep **100%**
- sample far too small

Conclusion: classical `doji` label does not provide a robust Saturday selector on this sample.

## 3. Giveback candle morphology
Future deep runners tend to have a **smaller body ratio** at the <=+0.40 giveback than shallow runners:
- full median: **0.598 deep vs 0.715 shallow**
- same DEEP_LOW direction in discovery and validation

They also show:
- more upper wick at giveback in both halves;
- larger range-vs-previous and body-vs-previous in both halves.

### `GIVEBACK40::INSIDE`
- N19 / deep **52.63%**
- complement deep **72.58%**
- Discovery: **55.56% vs 72.73%**
- Validation: **50.0% vs 72.22%**

The direction is stable, but economics are not: A7.19 PnL is positive in discovery and negative in validation for the inside-bar cohort. Therefore this remains forensic only.

### `GIVEBACK40::BEAR`
Formally passes the fixed-label separation rule, but is not useful: **79 of 81** giveback candles are bearish, leaving only two non-bear comparators. Treat this as a taxonomy artifact, not a tradable signal.

## 4. Rebuild candle morphology
`REBUILD50_FIRST` itself remains extremely runner-like (34 trades, 30 deep). Morphology inside that already-selected cohort has limited additional discrimination because shallow N is only 4.

The one continuous feature with the same direction in both halves is rebuild candle **range_pct_entry**:
- deep median roughly **0.20%** of entry
- shallow roughly **0.12%**
- Discovery AUC **0.833**
- Validation AUC **0.625**

Promising as descriptive strength evidence, but too few shallow rebuild cases for a rule.

## 5. Sequence morphology
For all 34 rebuild-first trades, the giveback -> rebuild transition is bearish-to-bullish for both deep and shallow groups. Therefore simply labeling a bullish recovery candle adds no information.

The exact body/wick changes are not sufficiently stable given only 4 shallow rebuild cases. No sequence-candle action is promoted.

## S5.7B verdict
**PASS as forensic knowledge.** Candle morphology contains real information, concentrated mainly at the +0.50 hinge.

The strongest new clue is:
> `+0.50 hinge + dominant upper wick` = materially weaker runner acceptance in both discovery and validation.

The complementary positive clue is continuous rather than a classic candlestick name:
> deeper runners tend to have a larger hinge body, smaller upper wick, and a close nearer the candle high.

`Doji`, `hammer`, or generic candlestick names should not be used blindly.

## Research decision
- Do **not** cut a trade merely because the +0.50 hinge has an upper-wick rejection; its A7.19 economics remain positive.
- Do **not** tune wick thresholds or combine body + wick + close-location post hoc on this sample.
- Preserve `HINGE05::UPPER_WICK_DOM` as a predeclared candidate context for a dedicated chronology/management interaction test if continuing.
- A7.19 remains the official full-coverage Saturday champion; A7.26 remains the preserved selective benchmark.
