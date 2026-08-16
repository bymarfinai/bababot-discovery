# BTC Temporal Saturday 18 WIB — A7.0 to A7.3 Research Checkpoint

**Date:** 2026-08-16  
**Status:** FROZEN RESEARCH PARENT — NOT YET LIVE PRODUCTION  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** 2023-12-02 to 2026-07-30 exclusive (971 days)  
**Saturday occurrences:** 139  
**Market data:** Binance Futures 5m, 279,648 / 279,648 rows (100%)  
**Entry:** every Saturday exact 18:00 WIB 5m open  
**Direction:** BUY  
**Sizing reference:** $10 margin × 50x = $500 fixed notional  
**Base fee assumption:** 0.15% round-trip = $0.75/trade  
**Same-5m TP+SL ambiguity:** SL first  
**Timeout:** actual observed close, no synthetic fill

This checkpoint records the independent Saturday engine study after Friday A6.0–A6.4 did not produce a robust executable champion.

---

## A7.0 — broad money geometry

Grid:
- TP 0.30% to 2.00%
- SL 0.30% to 1.40%
- max hold 2h / 4h / 6h / 8h / 10h / 12h
- 1,152 configurations
- chronological split: first 83 Saturdays discovery / last 56 validation

### Raw directional behavior

| Horizon | Full WR | Discovery WR | Validation WR | Full avg move |
|---|---:|---:|---:|---:|
| 30m | 51.08% | 53.01% | 48.21% | +0.0208% |
| 60m | 52.52% | 55.42% | 48.21% | +0.0083% |
| 120m | 59.71% | 57.83% | 62.50% | +0.0574% |
| 240m | **64.03%** | **60.24%** | **69.64%** | +0.0894% |
| 360m | 58.27% | 59.04% | 57.14% | +0.0777% |

Unlike Friday, the Saturday 4h directional tendency did **not** deteriorate in validation; it strengthened. The immediate problem was magnitude: the average 4h move remained below the assumed 0.15% round-trip fee.

A7.0's best 12h configuration was TP1.8 / SL1.1 / 12h:
- net +$17.40
- PF 1.087
- discovery +$21.55
- validation -$4.15
- only 3/8 positive blocks

No A7.0 configuration was positive in both discovery and validation. However the optimum was located at the maximum hold boundary and near the upper TP boundary, so the study was extended instead of stopping.

---

## A7.1 — boundary extension

Grid extension:
- TP 1.20% to 3.00%
- SL 0.70% to 1.50%
- max hold 8h / 12h / 16h / 20h / 24h
- 450 configurations

The extension materially changed the verdict. Long-hold runner geometries became positive in both chronological periods.

### Maximum-PnL example

TP3.0 / SL1.2 / 24h:
- 139 trades
- WR 50.36%
- net **+$110.07**
- expectancy +$0.7919/trade
- PF 1.414
- max DD $66.70
- max loss streak 5
- 5/8 positive blocks
- discovery +$43.24
- validation +$66.83

### Stable 20h example

TP3.0 / SL1.2 / 20h:
- net **+$82.19**
- PF 1.331
- max DD $48.49
- max loss streak 5
- **6/8 positive blocks**
- discovery **+$45.42**
- validation **+$36.78**

The result showed that Saturday is primarily a **slow runner / time-under-position edge**, not a short-horizon first-touch edge.

---

## A7.2 — local plateau test

Local grid around the promising region:
- TP 2.4 / 2.6 / 2.8 / 3.0 / 3.2 / 3.4 / 3.6 / 3.8 / 4.0%
- SL 1.0 / 1.1 / 1.2 / 1.3 / 1.4%
- max hold 18h / 20h / 22h / 24h
- 180 configurations

### Plateau evidence

For the **18h** slice:
- **45/45** configurations were profitable in the full sample
- **45/45** were profitable in both discovery and validation
- **41/45** also had >=6/8 positive chronological blocks

This is strong evidence that the result is a broad parameter plateau rather than one isolated optimized point.

At 20h:
- 45/45 cross-period positive
- 11/45 >=6/8 blocks

At 22h and 24h:
- 45/45 cross-period positive
- 0/45 >=6/8 blocks

Thus 18h was preferred over 20–24h for robustness despite some longer-hold configurations generating more full-sample PnL.

### Strong 18h examples before funding

**TP3.0 / SL1.1 / 18h**
- net +$104.51
- expectancy +$0.7519/trade
- PF 1.447
- max DD $35.92
- 6/8 blocks
- discovery +$61.94, exp +$0.7463
- validation +$42.58, exp +$0.7603

**TP3.0 / SL1.2 / 18h**
- net +$100.14
- PF 1.421
- max DD $37.95
- 6/8 blocks
- discovery +$53.94
- validation +$46.20

The near-equality of discovery and validation expectancy for TP3.0 / SL1.1 was especially encouraging.

---

## A7.3 — historical funding + extra execution-cost stress

Funding source:
- Binance Data Vision USD-M Futures monthly `fundingRate` archives for BTCUSDT
- columns observed: `calc_time`, `funding_interval_hours`, `last_funding_rate`
- 2,913 funding records over the evaluation period
- 0 missing archive months

For each simulated long, funding settlements were charged only while the position remained open. Position quantity was based on $500 / entry price. The BTCUSDT 5m open at settlement was used as a notional proxy. This is an approximation to the exchange mark-price funding calculation, but the difference is expected to be small relative to the strategy-level results.

### Funding effect

For the TP3.0 / SL1.1 / 18h configuration:
- 244 funding settlements crossed
- historical funding cost: **-$7.14 total**
- pre-funding net: +$104.51
- funding-adjusted net: **+$97.37**

Funding therefore reduces but does not remove the edge.

### Stress test across full 18h plateau

Extra execution cost below is **in addition to** the base 0.15% round-trip fee and historical funding.

| Extra cost | Cross-period positive configs | Robust configs (cross-period + >=6/8 blocks) |
|---:|---:|---:|
| 0.00% | 45/45 | 37/45 |
| +0.02% | 45/45 | 23/45 |
| +0.05% | 33/45 | 0/45 |
| +0.10% | 12/45 | 0/45 |
| +0.15% | 0/45 | 0/45 |

This makes the edge executable-looking but explicitly transaction-cost sensitive. It should not be modeled with arbitrary large slippage.

---

# Frozen Saturday research parent

For further rescue / management research, freeze the parent as:

## **Saturday 18:00 WIB BUY — TP2.6% / SL1.2% / max hold18h**

Reason for choosing this instead of the absolute highest-PnL geometry:
- sits inside the broad 18h plateau
- remains robust under historical funding and +0.02% additional execution-cost stress
- more conservative TP than the 3.0% boundary-style optimum
- discovery and validation remain independently positive under materially higher cost stress

### Parent economics with historical funding only
- 139 trades
- net **+$87.20**
- expectancy **+$0.6273/trade**
- WR **46.76%**
- PF **1.364**
- max DD **$45.12**
- max loss streak **7**
- **6/8 positive blocks**
- discovery: **+$52.67**, PF 1.349
- validation: **+$34.53**, PF 1.388
- funding: about **-$6.96 total**

### With +0.02% extra execution cost
- net **+$73.30**
- expectancy **+$0.5273/trade**
- PF **1.297**
- max DD **$52.02**
- **6/8 positive blocks**
- discovery **+$44.37**
- validation **+$28.93**

### Higher cost survival
From the funding-adjusted parent economics, a fixed +0.05% extra cost still leaves roughly +$52.45 full-sample, with both chronological halves positive; +0.10% still leaves roughly +$17.70 full-sample, again with both halves positive. The strategy approaches break-even at roughly +0.125% additional cost beyond the base 0.15% fee plus realized funding.

---

# Interpretation

Saturday differs materially from Friday:

**Friday**
- strong historical directional tendency
- clear deterioration / regime migration in the later period
- no robust executable parent found

**Saturday**
- 4h directional tendency strengthens in validation
- short / medium holds fail to monetize magnitude after fees
- allowing 18h creates a large cross-period TP/SL plateau
- actual historical funding does not eliminate the edge
- reasonable small extra execution cost leaves the edge positive

Therefore Saturday is promoted to a **frozen research parent** for the next stage.

It is **not yet a live-production rule**. Before live deployment it still needs:
1. exact live/backtest execution parity,
2. live funding handling,
3. slippage assumptions grounded in BTCUSDT order execution,
4. interaction / overlap rules with other temporal engines,
5. optional loss-management study to improve WR/DD without destroying expectancy.

## Current temporal engine ranking

1. **Tuesday 06:00 SELL** — frozen champion / strongest mature engine so far.
2. **Saturday 18:00 BUY** — frozen research parent, strong broad economic plateau; management optimization still open.
3. **Friday** — historical tendency but no robust executable champion under A6.0–A6.4.
