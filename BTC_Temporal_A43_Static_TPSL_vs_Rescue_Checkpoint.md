# BTC Temporal A4.3 — Static TP/SL vs Rescue Checkpoint

**Date:** 2026-08-16  
**Status:** COMPLETE — static TP/SL frontier compared apples-to-apples with frozen A4.2 rescue  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** same frozen 971-day window, 139 Tuesdays  
**Entry:** SELL every Tuesday exact 06:00 WIB  
**Max hold:** 240m  
**Fee:** 0.15% round trip per position  
**Sizing:** $500 notional ($10 margin x 50)  
**Intrabar ambiguity:** conservative SL first

## Static sweep

TP and SL were swept independently from **0.20% to 1.20% in 0.05% steps** = **441 static configurations**. No Tuesday entry was filtered.

Chronological split:
- discovery: first 83 Tuesdays
- validation: last 56 Tuesdays

## Core comparison

| Strategy | Full WR | Full net PnL | PF | Max DD | Positive blocks |
|---|---:|---:|---:|---:|---:|
| Static 0.50 / 0.50 | 61.87% | -$7.90 | 0.949 | $37.95 | 3/8 |
| Frozen A4.2 rescue on 0.50 / 0.50 | **65.47%** | **+$11.50** | **1.086** | **$23.43** | 4/8 |
| Static 0.55 / 0.80 | **65.47%** | +$1.39 | 1.008 | $38.80 | 4/8 |
| Static 0.65 / 0.80 | 61.15% | +$11.62 | 1.064 | $31.32 | 5/8 |
| Static 0.80 / 0.80 | 58.27% | +$23.21 | 1.120 | $28.01 | 5/8 |
| Static 1.20 / 0.80 | 53.96% | **+$57.87** | **1.285** | $32.81 | **6/8** |

## Key finding 1 — yes, static TP/SL can match rescue headline WR

The **highest-WR profitable static configuration** in all 441 configs was:

- TP = **0.55%**
- SL = **0.80%**
- RR = 0.688
- full WR = **65.47%** = exactly the same as frozen rescue
- full PnL = **+$1.39**
- PF = 1.008
- max DD = $38.80

But this configuration was weak chronologically:
- discovery: WR 59.04%, PnL **-$29.84**
- validation: WR 75.00%, PnL +$31.23

Thus the same headline WR is largely produced by a favorable later regime and a wider loss allowance; it does not reproduce the rescue economics.

## Key finding 2 — rescue is better if the objective is high WR plus acceptable economics

Frozen A4.2 rescue:
- full WR = **65.47%**
- PnL = **+$11.50**
- PF = 1.086
- DD = **$23.43**

Versus static 0.55/0.80 at same WR:
- PnL = +$1.39
- PF = 1.008
- DD = $38.80

So the post-entry rescue adds genuine path-dependent value beyond simply widening the static SL.

## Key finding 3 — if objective is maximum money, static geometry wins decisively

Best full-sample and also the only configuration positive in both discovery and validation was:

### Static TP 1.20% / SL 0.80% (RR 1.5)
Full 139:
- WR: **53.96%**
- PnL: **+$57.87**
- expectancy: +$0.416/trade
- PF: **1.285**
- DD: $32.81
- positive blocks: **6/8**

Discovery 83:
- PnL: **+$1.18**
- WR: 44.58%

Validation 56:
- PnL: **+$56.69**
- WR: 67.86%
- PF: 1.954

The discovery edge is tiny, so this still shows material regime dependence, but it is stronger economically than all 0.5-class geometries.

## Key finding 4 — around the old 0.50% geometry

Best static configuration in the local 0.35–0.65 region was:
- TP 0.65 / SL 0.50
- WR 56.12%
- PnL +$9.84
- PF 1.056
- DD $30.84

This nearly matches the rescue PnL (+$11.50) but with substantially lower WR (56.12% vs 65.47%).

Another relevant point:
- TP 0.65 / SL 0.80
- WR 61.15%
- PnL +$11.62
- PF 1.064

This matches rescue PnL closely but still has lower WR and higher DD.

## Static WR/PnL frontier

Among all 441 static configs with positive full-history PnL:
- WR >= 55%: 78 configs; best PnL TP1.00/SL0.80 = +$39.07, WR55.40%
- WR >= 60%: 12 configs; best PnL TP0.65/SL0.80 = +$11.62, WR61.15%
- WR >= 62%: 2 configs; best PnL TP0.60/SL0.80 = +$4.91, WR63.31%
- WR >= 65%: **1 config only**; TP0.55/SL0.80 = +$1.39, WR65.47%
- WR >= 67%: **0 profitable configs**
- WR >= 70%: **0 profitable configs**

High WR can be manufactured with tiny TP / huge SL, but is economically bad. Example:
- TP0.20 / SL0.90
- WR **83.45%**
- PnL **-$73.11**
- PF 0.284

Therefore WR alone must not be optimized.

## Verdict

The user hypothesis is partially confirmed:

1. **Yes**, changing static TP/SL can reproduce the same 65.47% headline WR as the A4.2 rescue.
2. **No**, it does not reproduce the same quality: at identical WR the rescue produces about 8x the net PnL (+$11.50 vs +$1.39) and much lower DD ($23.43 vs $38.80).
3. If the objective is **maximum net PnL rather than high WR**, static **1.20/0.80** is currently much stronger than rescue.
4. If the objective is **high WR + positive economics**, frozen rescue remains better than the tested static frontier.
5. No static TP/SL in the 441-config grid achieved >=67% full-history WR while remaining profitable.

## Next research implication

Do not choose between static geometry and rescue yet. The strongest next candidate is a **hybrid**:

`Tuesday 06:00 SELL -> economically superior base TP/SL geometry -> early causal rescue only when the initial thesis clearly fails`

The next clean test should compare rescue logic on a stronger static base (especially 0.65/0.80, 0.80/0.80, and 1.20/0.80) without retuning the rescue detector first.
