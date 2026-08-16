# BTC Temporal Saturday 18 WIB — Pre-entry Exhaustion Research Checkpoint (A7.24–A7.27)

**Date:** 2026-08-17 WIB  
**Status:** PROMISING SELECTIVE PRE-ENTRY GATE — NOT PROMOTED OVER A7.19, NOT PRODUCTION/OOS PROVEN  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** 2023-12-02 to 2026-07-30 exclusive (971 days)  
**Saturday occurrences:** 139  
**Data:** Binance Futures 5m  
**Sizing:** $10 margin × 50x = $500 fixed notional  
**Fee assumption:** 0.15% round trip  
**Funding:** canonical historical BTCUSDT methodology  
**Live BBC:** untouched

---

## 1. Reference champions entering this pass

### Frozen parent
Saturday 18:00 WIB BUY / TP2.6% / SL1.2% / max18h:
- 139 entries
- WR 46.76%
- PnL +$87.20
- expectancy +$0.6273/trade
- PF 1.364
- max DD $45.12
- loss streak 7
- 6/8 positive blocks

### A7.19 full-coverage management champion
Same 139 entries and same base geometry, plus strict-causal 240m shallow-runner failure exit:
- 139 entries
- WR **50.36%**
- PnL **+$103.383**
- expectancy **+$0.7438/trade**
- PF **1.462**
- max DD **$33.136**
- loss streak **5**
- 6/8 positive blocks

A7.19 remains the official full-coverage Saturday research champion after this pass.

---

## 2. Target of A7.24–A7.27

The unresolved large loss family from A7.12 was:

`A1_WRONG_WAY_BEFORE_0.3`

Definition:
- funding-adjusted parent trade ends non-positive
- trade never establishes meaningful BUY impulse above +0.3% first
- adverse -0.3% occurs before favorable +0.3%

Counts:
- full: **25** A1 losses
- discovery first83: **13**
- validation last56: **12**

Goal: determine whether these occurrences can be recognized **before entry**, rather than cutting them after entry. This matters because A7.14 already showed that a 60m post-entry failure classifier can be accurate yet economically harmful when used for direct CUT/FLIP.

---

## 3. Strict-causal pre-entry repair

A7.24 did not reuse the legacy `prectx()` EMA values, because the legacy helper referenced EMA at index `i`, which includes the entry candle close.

For all A7.24+ pre-entry work:
- all EMA values end at completed 5m candle `i-1`
- all EMA slopes end at `i-1`
- all taker/range/volume windows use completed candles before entry
- only the actual 18:00 open price at `i` is allowed at decision time
- no entry-candle close/high/low is used to decide whether to enter

Thus the gate is causally implementable at the 18:00 decision.

---

## 4. A7.24 — falling-knife hypothesis falsified

Initial hypothesis: A1 losses might be Saturday BUYs entered while price was already falling.

The data showed the opposite.

### Full-sample medians: A1 vs eventual winner

| Pre-entry feature | A1 loss | Winner |
|---|---:|---:|
| pre-1h return | **+0.072%** | **-0.060%** |
| pre-4h return | **+0.170%** | **-0.096%** |
| pre-24h return | +0.396% | +0.209% |
| distance vs strict EMA20 | **+0.041%** | **-0.023%** |
| EMA20 slope 60m | **+0.051%** | **-0.025%** |
| distance to prior-1h high | **0.083%** | **0.172%** |
| day position | 0.578 | 0.451 |

This directional relationship was visible in both discovery and validation.

Interpretation:

> A1 is more consistent with **BUY after a local pre-pump / stretched state near the previous-hour high**, while many valid Saturday winners begin after a pullback or below a declining/flat short-term EMA state.

All predeclared falling-knife rules had poor A1 precision and were rejected.

---

## 5. A7.25 — pre-pump exhaustion classifier

A small interpretable family was tested; no large parameter sweep.

Most useful mechanistic state:

`PUMP_TREND_NEAR_PH`

At 18:00 BUY decision:
- pre-1h return > 0
- pre-4h return > 0
- current open above strict completed-candle EMA20
- EMA20 60m slope > 0
- current open is within **0.10%** of prior-1h high

Classification only:

### Discovery
- 8 signals
- 3 A1 hits
- 1 eventual winner false positive
- 4 other-loss signals
- **87.5% any-loss precision**

### Validation
- 8 signals
- 3 A1 hits
- 3 eventual winner false positives
- 2 other-loss signals
- **62.5% any-loss precision**

### Full
- 16 signals
- 6 A1 hits
- 6 other losses
- 4 winners
- **75.0% any-loss precision**
- winner false-positive rate among all winners: about 6.15%

This is not a pure A1 detector; it is better interpreted as a **pre-entry low-quality Saturday BUY state**.

---

## 6. A7.26 — economic action test

Primary frozen state: `PUMP_TREND_NEAR_PH` above.

Compared with A7.19:

### A. SKIP signaled occurrence

- 16/139 skipped
- retained trades: **123**
- occurrence coverage: **88.49%**
- WR: **52.03%**
- PnL: **+$109.587**
- expectancy: **+$0.8910/trade**
- PF: **1.536**
- max DD: **$28.483**
- max loss streak: **6**
- 6/8 positive blocks

Relative to A7.19:
- WR +1.67 percentage points
- PnL **+$6.204**
- expectancy +$0.1472/trade
- PF +0.074
- DD improves by about $4.65
- loss streak worsens from 5 to 6
- trade coverage falls by 11.51%

### Chronological split

Discovery:
- A7.19: 83 trades / WR53.01 / +$66.588 / PF1.488
- skip gate: 75 trades / **WR54.67 / +$72.360 / PF1.567**
- PnL delta **+$5.772**

Validation:
- A7.19: 56 trades / WR46.43 / +$36.795 / PF1.420
- skip gate: 48 trades / **WR47.92 / +$37.227 / PF1.485**
- PnL delta **+$0.432**

The validation uplift is positive but small.

### B. Conditional delayed BUY instead of skip

On the same 16 pre-pump signals, entry was delayed while all non-signaled occurrences retained A7.19:

- 15m delay: PnL **+$97.668**, WR48.92%, delta **-$5.715**
- 30m delay: PnL **+$96.110**, WR48.92%, delta **-$7.273**
- 60m delay: PnL **+$97.940**, WR48.92%, delta **-$5.443**

All are worse than A7.19.

Conclusion:

> This state is not simply “correct direction but 15–60 minutes too early.” The signaled occurrences are, on average, lower-quality temporal BUY opportunities. Simple delay does not repair them.

---

## 7. A7.27 — robustness audit of the primary skip gate

### Prior-hour-high cap sensitivity

Holding all other primary conditions constant:

| Prior-high cap | Kept N | Coverage | WR | PnL | Validation PnL |
|---|---:|---:|---:|---:|---:|
| 0.08% | 125 | 89.93% | 52.00% | **+$110.006** | +$37.227 |
| **0.10% primary** | **123** | **88.49%** | **52.03%** | **+$109.587** | **+$37.227** |
| 0.12% | 120 | 86.33% | 51.67% | +$98.687 | +$26.327 |
| 0.15% | 112 | 80.58% | 53.57% | +$105.392 | +$33.946 |

Interpretation:
- 0.08–0.10% behaves similarly.
- expanding to 0.12% damages validation materially.
- 0.15% raises headline WR but removes too many occurrences and does not improve total PnL vs the tighter neighborhood.

This supports a **narrow local-exhaustion region near the prior-hour high**, not a broad “skip whenever price is high” rule.

### Pre-1h floor sensitivity

With prior-high cap fixed at 0.10%:

- pre1 >0.00: 123 trades / WR52.03 / +$109.587
- pre1 >0.03: exact same signals/result
- pre1 >0.05: 126 trades / WR52.38 / **+$113.563** / PF1.549 / DD$26.64

The >0.05 result is interesting and improves both chronological halves, but it was observed during robustness sensitivity after the primary rule had already been selected. It is therefore **post-hoc** and is NOT promoted as the new frozen rule in this checkpoint.

Do not retune this threshold further on the same 971-day sample.

### Leave-one-skip-out

Restoring any one of the 16 skipped occurrences leaves total PnL between roughly:
- **+$106.62** and **+$114.38**

Every leave-one-out result remains above A7.19 +$103.383.

Thus the primary uplift is not dependent on a single skipped trade.

### Year distribution of primary gate

Retained strategy:
- 2023: +$18.17 (only 4 retained trades)
- 2024: +$46.15
- 2025: **+$9.91**
- 2026 through July: +$35.36

Compared with A7.19, the gate improves the aggregate 2024–2025 region but **reduces 2026 performance**, because several 2026 pre-pump occurrences become valid winners. This is an important non-stationarity warning.

---

# 8. Final status after A7.27

## Full-coverage champion remains A7.19

> 139/139 occurrences traded  
> WR **50.36%**  
> PnL **+$103.383**  
> expectancy **+$0.7438/trade**  
> PF **1.462**  
> DD **$33.136**

This remains the cleaner Saturday champion because it preserves all entries and already has positive discovery/validation management uplift.

## Selective pre-entry candidate: A7.26 primary gate

> Skip only `PUMP_TREND_NEAR_PH` occurrences  
> 123/139 trades retained (**88.49% coverage**)  
> WR **52.03%**  
> PnL **+$109.587**  
> expectancy **+$0.8910/trade**  
> PF **1.536**  
> DD **$28.483**

This is promising because:
- it improves total PnL despite trading less
- discovery and validation PnL are both above A7.19
- local 0.08–0.10 prior-high thresholds behave similarly
- leave-one-skip-out remains above A7.19
- simple delayed entry fails, supporting a true quality-state interpretation rather than a trivial timing shift.

But it is **not promoted yet**, because:
- the hypothesis was discovered on the same 971-day BTC Saturday sample
- validation uplift of the primary rule is only +$0.432
- year behavior is mixed, especially weaker 2026
- the attractive pre1>0.05 sensitivity is post-hoc and must not be selected from this sample
- filtering reduces occurrence coverage to 88.49%.

## Correct next proof

Do NOT keep tuning BTC Saturday thresholds on this dataset.

The next useful evidence should be independent:
1. exact frozen-rule transfer to another asset on Saturday18, or
2. transfer to an independent BUY temporal cluster, or
3. truly unseen future Saturdays.

Success should require the frozen qualitative mechanism to transfer:

`temporal BUY + local pre-pump + rising/above EMA20 + near prior-hour high = lower-quality BUY occurrence`

without re-optimizing thresholds for the target sample.

---

## Live implementation

No live trading code was changed. Research branch only; checkpoint written to main.
