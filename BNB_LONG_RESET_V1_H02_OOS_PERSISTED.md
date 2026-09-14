# BNB LONG Reset V1 — H02 Untouched OOS PERSISTED

## Verdict

**OOS_PASS**

Frozen before exposure:
- Habitat: **02:00–03:00 WIB**
- LONG only
- Primary: **`rv_ratio_60_240__HIGH`**
- Secondary: **`efficiency_60m__HIGH`**
- HIGH cutoff: causal percentile **>= 2/3**
- Same-anchor rolling history: previous **60** observations, minimum history 40
- OOS: **2025-01-01 through 2026-07-30 WIB**
- OOS gate prereg commit: `94b085576b176ddb18d9fe03e9912d965e268095`
- No OOS retuning, rescue filter, anchor exclusion, threshold change, or hour change was performed.

Workflow provenance:
- GitHub Actions run: **34805242473**
- Trigger/head SHA: `ef35b4a01d9eeb791752d40b1b22285464b770e9`
- Artifact ID: **10332433048**
- Artifact SHA256: **f7c4000ff06edb5693235956bb0b576aa0cbbded98cb165ac9a35bab1543de5c**
- Data coverage: **100.0000%**

Dollar figures use the standing reference **$10 margin × 50x = $500 notional** and are raw structural-return equivalents, not executable/net trading PnL. TP/SL, fees, slippage, overlap execution, liquidation mechanics, and final holding period are still not applied.

## Pooled untouched OOS economics

| Metric | OOS result |
|---|---:|
| All H02 OOS events | 2,304 |
| Frozen-character signals | **269** |
| Unique signal days | **171** |
| Approx signals/week | **3.27** |
| WR | **57.62%** |
| Mean return/signal | **+0.0806%** |
| Median return/signal | **+0.0956%** |
| PF | **1.361** |
| Raw $/signal @ $500 | **+$0.40** |
| Raw cumulative equivalent | **+$108.38** |
| Gross positive equivalent | **+$408.44** |
| Gross negative equivalent | **-$300.06** |
| Avg winning signal | **+$2.64** |
| Avg losing signal | **-$2.63** |
| Raw max DD equivalent | **-$89.36** |
| Max loss streak | **9** |
| Pooled OOS gate | **PASS** |

Frozen pooled gate was N >=120, WR >55%, mean >0, PF >=1.20. All four conditions pass.

## Development → OOS retention

Frozen Development primary + secondary had N=483, WR=60.25%, mean=+0.1470%, PF=1.642, raw DD=-$75.88, and max loss streak 8.

| Metric | Development | OOS | Change / retention |
|---|---:|---:|---:|
| WR | 60.25% | **57.62%** | **-2.63 pp** |
| Mean return | +0.1470% | **+0.0806%** | **54.8% retained** |
| PF | 1.642 | **1.361** | **82.9% retained** |
| Signals/week | ~3.09 | **3.27** | broadly stable |
| Raw max DD @ $500 | -$75.88 | **-$89.36** | worse by ~17.8% |
| Max loss streak | 8 | **9** | +1 |

The edge degraded out of sample, as expected, but remained above every preregistered mandatory OOS gate.

## Calendar-block robustness

| Block | N | WR | Mean | PF | Raw $/signal | Raw total | Raw DD | LS | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **2025** | 159 | 57.23% | **+0.0176%** | **1.057** | +$0.09 | +$13.96 | -$89.36 | 7 | **PASS** |
| **2026 through Jul-30** | 110 | 58.18% | **+0.1717%** | **2.699** | +$0.86 | +$94.42 | -$12.74 | 9 | **PASS** |

Both blocks satisfy the frozen minimum N>=40, WR>=52%, positive mean, PF>=1.05.

Important: **2025 is only narrowly positive**. PF 1.057 is just above the 1.05 block floor, while 2026 is much stronger. OOS therefore passes, but the result is not uniformly strong across time.

## Diagnostic horizons

| Horizon | N | WR | Mean | PF | Raw $/signal | Raw total | Raw DD | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **60m** | 269 | 57.99% | +0.0500% | 1.269 | +$0.25 | +$67.30 | -$53.32 | **PASS** |
| **120m** | 269 | 57.62% | +0.0312% | 1.104 | +$0.16 | +$41.94 | -$153.07 | **PASS** |
| **240m** | 269 | **59.48%** | **+0.1605%** | **1.605** | **+$0.80** | **+$215.89** | -$75.35 | **PASS** |

**3/3 horizons pass** the frozen horizon-support gate. 240m remains the strongest diagnostic horizon, but this does not authorize choosing 240m as final hold; that belongs to trade construction.

## Quarter-hour anchor robustness

| Entry WIB | N | WR | Mean | PF | Raw $/signal | Raw total | Raw DD | LS | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **02:00** | 61 | 57.38% | +0.1847% | 1.933 | +$0.92 | +$56.33 | -$17.31 | 3 | **PASS** |
| **02:15** | 68 | 52.94% | +0.0946% | 1.478 | +$0.47 | +$32.16 | -$21.71 | 5 | **PASS** |
| **02:30** | 74 | 58.11% | **-0.0433%** | **0.853** | **-$0.22** | **-$16.01** | -$67.49 | 4 | **FAIL** |
| **02:45** | 66 | **62.12%** | +0.1088% | 1.566 | +$0.54 | +$35.91 | -$20.97 | 4 | **PASS** |

Frozen anchor rule required 3/4 supportive anchors, therefore **anchor gate PASS (3/4)**.

The **02:30 anchor is negative OOS despite 58.11% WR** because losses are larger than wins. It is not removed now; dropping it after OOS would be prohibited post-hoc optimization.

## OOS quarter map

| Quarter | N | WR | Mean | PF | Raw $/signal | Raw total | Positive? |
|---|---:|---:|---:|---:|---:|---:|---|
| 2025Q1 | 31 | 54.84% | +0.1156% | 1.470 | +$0.58 | +$17.91 | YES |
| 2025Q2 | 46 | 56.52% | **-0.1144%** | 0.617 | -$0.57 | -$26.32 | NO |
| 2025Q3 | 34 | 64.71% | **+0.3145%** | 3.488 | +$1.57 | +$53.46 | YES |
| 2025Q4 | 48 | 54.17% | **-0.1296%** | 0.732 | -$0.65 | -$31.10 | NO |
| 2026Q1 | 47 | 63.83% | +0.1691% | 2.328 | +$0.85 | +$39.73 | YES |
| 2026Q2 | 44 | 61.36% | **+0.2536%** | 4.292 | +$1.27 | +$55.79 | YES |
| 2026Q3 through Jul-30 | 19 | 36.84% | -0.0116% | 0.873 | -$0.06 | -$1.10 | NO |

Positive-mean quarters: **4/7**. The preregistered quarter diagnostic guardrail was >=4/7, therefore **CLEAN** (not a mandatory PASS/FAIL gate).

## Final locked OOS verdict

Mandatory gates:
- Pooled: **PASS**
- 2025 / 2026 calendar blocks: **PASS**
- Horizons: **PASS (3/3)**
- Anchors: **PASS (3/4)**
- Quarter diagnostic: **CLEAN (4/7 positive)**

Therefore the frozen H02 character is promoted to:

**OOS_PASS → TRADE_CONSTRUCTION**

The frozen structural character remains:

**BNBUSDT LONG · 02:00–03:00 WIB · `rv_ratio_60_240__HIGH` + `efficiency_60m__HIGH`**

No new-hour discovery is reopened. No OOS rescue is permitted. Next stage must convert this structural edge into an executable rule set and test actual economics including entry mechanics, hold/TP/SL, overlap, fees, slippage, leverage, and READY-TO-TRADE validation.

Research/shadow only.
