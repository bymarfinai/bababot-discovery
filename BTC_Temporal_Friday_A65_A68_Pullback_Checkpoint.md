# BTC Temporal Friday 15 WIB — A6.5–A6.8 Pullback State Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** PROMISING FRIDAY-SPECIFIC CAUSAL PULLBACK CANDIDATE — NOT PRODUCTION / NOT FRESH OOS PROVEN  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** 2023-12-02 to 2026-07-30 exclusive (971 days)  
**Friday 15:00 occurrences:** 138  
**Data:** Binance Futures 5m  
**Sizing:** $10 margin × 50x = $500 fixed notional  
**Fee assumption:** 0.15% round trip  
**Live BBC:** untouched

---

## 1. Prior Friday reference

Friday15 raw directional tendency was already known:
- 30m: N138 / WR **64.49%** / avg +0.0564%
- 240m: N138 / WR **64.49%** / avg +0.1558%

However executable A6.0 geometry was unstable.
Fixed diagnostic parent used throughout this pass:
- BUY Friday exact 15:00 WIB 5m open
- TP **2.0%**
- SL **0.7%**
- max hold **360m / 6h**
- same-bar TP+SL ambiguity => adverse/SL first
- 0.15% roundtrip fee

A6.0 parent:
- N138
- WR **47.83%**
- PnL **+$64.630**
- expectancy +$0.4683/trade
- PF 1.266
- max DD $56.530
- loss streak 8
- discovery first82: **+$99.194**, WR54.88%, PF1.828
- validation last56: **-$34.563**, WR37.50%, PF0.719

Thus the problem was not lack of historical directional tendency; it was non-stationary executable conversion.

---

# 2. A6.5 — exact Saturday pre-pump gate transfer FAILED

The Saturday A7.25 primary low-quality BUY gate was transferred to Friday with **zero threshold tuning**:

`pre1>0 & pre4>0 & open>EMA20 & EMA20_60m_slope>0 & distance_to_previous_1h_high<=0.10%`

All EMA values ended at completed candle i-1.

Only 10/138 Friday occurrences were signaled.

### Full
Parent:
- 138 trades / WR47.83 / +$64.630

After skipping Saturday-gate signals:
- 128 trades / WR49.22 / **+$63.594**
- delta **-$1.036**

### Discovery
- 6 signals
- skipped subset PnL **-$8.964**
- retained strategy **+$108.157** vs parent +$99.194
- improvement +$8.963

### Validation
- 4 signals
- skipped subset PnL **+$10.000**
- 2 TP / 2 SL
- retained strategy **-$44.563** vs parent -$34.563
- deterioration **-$10.000**

Raw validation also showed the 4 signaled occurrences were not uniformly exhausted; at 360m they had WR75% and avg +0.45%.

**Verdict:** Saturday pre-pump exhaustion is not a universal BTC BUY gate. Friday has a different continuation/rebound structure.

---

# 3. A6.6 — Friday winner/loss atlas

A strict-causal Friday-specific atlas compared raw240 winners/losses and executable winners/losses using only pre-entry information.

## Raw 240m — full medians

| Feature | Winner | Loser |
|---|---:|---:|
| pre-1h return | **-0.163%** | -0.009% |
| pre-4h return | **-0.139%** | +0.133% |
| distance vs EMA20 | **-0.102%** | +0.032% |
| EMA20 slope 60m | **-0.084%** | +0.048% |
| distance to prev-1h high | 0.391% | 0.269% |
| 6h MFE median | **1.216%** | 0.311% |
| 6h MAE median | 0.317% | **1.251%** |

## Raw 240m — validation medians

| Feature | Winner | Loser |
|---|---:|---:|
| pre-1h return | **-0.101%** | +0.008% |
| pre-4h return | **-0.081%** | +0.121% |
| distance vs EMA20 | **-0.081%** | +0.001% |
| EMA20 slope 60m | **-0.087%** | +0.019% |
| 6h MFE median | **1.145%** | 0.217% |
| 6h MAE median | 0.292% | **1.372%** |

The qualitative direction therefore persisted across both chronological halves:

> Friday15 BUY winners tend to begin during a causal short-term pullback below/falling EMA state, not after an upward pre-pump.

### Strong quartile clue

Lowest quartile of distance to EMA20 (most below EMA20):
- full raw240 WR **82.35%**
- discovery raw240 WR **90.00%**
- validation raw240 WR **71.43%**

This quartile analysis was diagnostic only; its numeric boundaries were **not** used in the selected rule.

---

# 4. A6.7 — compact sign-only Friday pullback rules

To avoid a threshold optimizer, only sign-based rules were tested. Money geometry remained fixed at TP2.0 / SL0.7 / 6h.

## Selected interpretable candidate: `EMA7_20_PULLBACK`

At exact Friday 15:00 WIB entry open:
- `open < completed EMA7`
- `open < completed EMA20`
- EMA7 15m slope `< 0`
- EMA20 15m slope `< 0`

Causality:
- EMA values end at completed 5m candle `i-1`
- 15m slopes also end at `i-1`
- only the actual 15:00 open is used for current price comparison
- no current-candle close/high/low

### Full
- selected **63/138** occurrences
- coverage **45.65%**
- raw240 WR **77.78%**
- raw360 WR 74.60%
- executable WR **65.08%**
- PnL **+$113.791**
- expectancy **+$1.8062/trade**
- PF **2.509**
- max DD **$17.208**
- loss streak **3**

### Discovery first82
- selected N39
- raw240 WR **82.05%**
- executable WR **71.79%**
- PnL **+$102.955**
- expectancy +$2.6399/trade
- PF **3.916**
- DD $8.903
- loss streak 2

### Validation last56
- selected N24
- raw240 WR **70.83%**
- raw360 WR 66.67%
- executable WR **54.17%**
- PnL **+$10.836**
- expectancy +$0.4515/trade
- PF **1.270**
- DD $13.508
- loss streak 3

Thus the same fixed executable parent changes from validation **-$34.563** on all Friday occurrences to **+$10.836** on the causal pullback state.

Important caveat: A6.7 was formulated after inspecting A6.6 Friday atlas, which included both chronological halves. Therefore the last56 result is cross-period robustness evidence, **not pristine untouched OOS evidence**.

---

# 5. A6.8 — frozen robustness audit

The exact A6.7 rule was frozen; no condition or threshold was changed.

## Chronological blocks

Full selected strategy:
- B1 +$34.768
- B2 +$12.061
- B3 +$30.218
- B4 +$23.345
- B5 **-$4.712**
- B6 +$1.045
- B7 +$9.939
- B8 +$7.127

=> **7/8 positive blocks**.

## Calendar years

- 2023: N3 / WR100% / +$10.431 (tiny sample)
- 2024: N25 / WR68.0% / **+$75.865** / PF3.700
- 2025: N23 / WR60.87% / **+$12.653** / PF1.439
- 2026 through July: N12 / WR58.33% / **+$14.842** / PF1.804

The rule remains profitable in 2024, 2025, and 2026-to-date, although edge magnitude is much smaller after 2024.

## Exit reasons

- TP: 10
- SL: 15
- timeout: 38

Headline WR is therefore not driven only by TP hits; many timeout exits remain net-positive.

## Leave-one-trade-out

Removing any single selected trade leaves total PnL positive. Removing any one +$9.25 maximum winner leaves:
- PnL **+$104.541**
- WR64.52%
- PF2.386

No single trade explains the edge.

## Winner concentration stress

- remove largest 1 winner: **+$104.541**
- remove largest 3 winners: **+$86.041**
- remove largest 5 winners: **+$67.541**
- remove largest 10 winners: **+$21.291**

Even after removing the ten largest selected winners, aggregate PnL remains positive.

## Extra cost stress

Extra cost is in addition to the existing 0.15% roundtrip fee:

| Extra cost | PnL | WR | PF | Positive blocks |
|---|---:|---:|---:|---:|
| 0.00% | **+$113.791** | 65.08% | 2.509 | 7/8 |
| +0.02% | +$107.491 | 65.08% | 2.385 | 7/8 |
| +0.05% | +$98.041 | 63.49% | 2.212 | 6/8 |
| +0.10% | +$82.291 | 63.49% | 1.949 | 6/8 |
| +0.15% | +$66.541 | 57.14% | 1.717 | 6/8 |

The candidate is not fee-fragile under this stress framework.

---

# 6. Current Friday interpretation

The most coherent Friday mechanism after A6.8 is:

> **Friday 15:00 temporal rebound + short-term causal pullback state.**

Specifically:
- Friday15 supplies the temporal BUY prior.
- Price being below EMA7 and EMA20 indicates short-term discount/pullback at the decision open.
- Both EMA7 and EMA20 declining over the last completed 15m indicate the pullback is real rather than a single noisy tick.
- The Friday temporal edge then expresses as a rebound from that pullback.

This is deliberately different from the Saturday mechanism:
- **Saturday:** buying immediately after local pre-pump near the previous-hour high can be low quality.
- **Friday:** the strongest BUY subset appears when the market is already in short-term pullback below falling EMA7/20.

Thus EMA is useful as a **conditional state sensor**, not a standalone direction signal.

---

# 7. Current status

## Friday all-occurrence directional prior
Still valid historically:
- N138
- raw30 WR64.49%
- raw240 WR64.49%

But all-occurrence executable conversion remains unstable.

## New Friday-specific research candidate

`Friday15 BUY + EMA7_20_PULLBACK`

> N **63**  
> coverage **45.65%**  
> raw240 WR **77.78%**  
> executable WR **65.08%**  
> PnL **+$113.791**  
> expectancy **+$1.806/trade**  
> PF **2.509**  
> max DD **$17.208**  
> max loss streak **3**  
> **7/8 positive blocks**

This is materially stronger than the prior Friday A6.0 executable parent and is the first Friday-specific state in this research line to turn the previously negative last56 executable region positive without changing TP/SL/hold.

## What this does NOT prove

- It is not pristine future OOS, because the Friday atlas informed the sign-only rule.
- The selected sample is 63 trades, not 138.
- Validation economics are positive but modest relative to discovery.
- No live execution/slippage/funding microstructure parity audit has been done for this candidate.

Therefore classify as **promising / provisional research candidate**, not production-ready.

---

## Live implementation

No live trading code was changed. Research branch only; this checkpoint records the result on main.
