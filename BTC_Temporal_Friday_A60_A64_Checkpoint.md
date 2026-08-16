# BTC Temporal Friday A6.0–A6.4 — Research Checkpoint

**Date:** 2026-08-16  
**Status:** COMPLETE FOR FIXED-CLOCK / BASIC WALK-FORWARD STUDY — NO FROZEN CHAMPION  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** 2023-12-02 to 2026-07-30 exclusive (971 days)  
**Friday occurrences:** 138  
**Data:** Binance Futures 5m, 100% coverage  
**Sizing reference:** $10 margin × 50x = $500 notional, fixed sizing  
**Fee assumption:** 0.15% round-trip

## Why Friday was studied
A1 temporal discovery had shown a strong Friday afternoon BUY cluster, especially Friday 15:00 WIB:
- 30m directional WR 64.49%, average +0.0564%
- 240m directional WR 64.49%, average +0.1558%
- Friday 15–17 BUY formed a coherent historical cluster

The goal of A6 was to determine whether this directional tendency could become an executable money edge comparable to the frozen Tuesday engine.

---

# A6.0 — Friday 15:00 BUY money geometry

Every Friday exact 15:00 WIB BUY. Broad static grid:
- TP 0.30–2.00%
- SL 0.30–1.40%
- max hold 2h / 4h / 6h / 8h / 10h / 12h
- 1,152 configurations
- same-5m TP+SL ambiguity => SL first
- timeout exits actual price

Best full-history configuration:
**TP2.00 / SL0.70 / max6h**
- 138 trades
- WR 47.83%
- net +$64.63
- expectancy +$0.4683/trade
- PF 1.266
- max DD $56.53
- max loss streak 8
- 5/8 positive blocks

But chronological behavior was unstable:
- first 82 Fridays: **+$99.19**, WR 54.88%, PF 1.828
- last 56 Fridays: **-$34.56**, WR 37.50%, PF 0.719

**No one of the 1,152 geometries was profitable in both first-60% discovery and last-40% validation.**

Therefore the attractive full-history PnL is regime-dependent and is not accepted as a Friday parent champion.

---

# A6.1 — Friday 14:00–18:00 cluster stability

The afternoon cluster was expanded to 14/15/16/17/18 WIB using the same money grid.

Key Friday15 raw directional split:

First 82 Fridays:
- 30m WR 68.29%, avg +0.0693%
- 60m WR 65.85%, avg +0.0511%
- 120m WR 64.63%, avg +0.1946%
- 240m WR **71.95%**, avg +0.3048%
- 360m WR 67.07%, avg +0.4756%

Last 56 Fridays:
- 30m WR 58.93%, avg +0.0375%
- 60m WR 51.79%, avg -0.0039%
- 120m WR 44.64%, avg -0.0495%
- 240m WR 53.57%, avg -0.0624%
- 360m WR 48.21%, avg -0.1422%

Hours 16 and 17 showed the same broad deterioration at longer horizons. No hour 14–18 produced a geometry profitable in both chronological periods.

Interpretation: this was not merely a one-hour migration from 15 to 16 or 17. The historical afternoon impulse materially weakened / shortened in the later regime.

---

# A6.2 — all-Friday clock discovery -> validation

All 24 Friday clock-hours × 30/60/120/240/360m were scanned. Candidate hours were selected **using only the first 60% Fridays**.

Top discovery observations included:
- 16:00 /120m WR 73.17%, avg +0.2057%
- 15:00 /240m WR 71.95%, avg +0.3048%
- 16:00 /240m WR 68.29%, avg +0.2977%
- 15:00 /30m WR 68.29%, avg +0.0693%
- 17:00 /120m WR 65.85%, avg +0.1090%

Six preselected hours were 16, 15, 17, 08, 13 and 12 WIB.

After applying the executable money grid, **none of those preselected hours had a geometry profitable in both discovery and validation.**

Later-period diagnostics showed newer-looking positive raw tendencies such as Friday 04:00 and 23:00, but these were not strong in the discovery period. They are therefore treated as regime-migration clues, NOT validated edges and were not cherry-picked as new champions.

---

# A6.3 — causal walk-forward clock rotation

Every Friday, before trading, the selector ranked all 24 hours × fixed horizons using only prior Fridays. Tested:
- lookback 13 / 26 / 52 Fridays
- BUY-only clock rotation
- dynamic BUY/SELL direction
- mean and conservative LCB ranking
- exactly one trade per Friday in the forced variants
- fixed-horizon real exit, fee 0.15%

Best forced adaptive variant:
**BUY-only / prior 26 Fridays / mean score**
- 112 trades after warmup
- WR 46.43%
- net **+$2.47**
- expectancy +$0.022/trade
- PF **1.011**
- max DD $55.41
- max loss streak 7
- only **3/8 blocks positive**

This is effectively break-even and not a robust edge. Dynamic BUY/SELL variants were materially worse.

Conclusion: simple causal clock rotation does not rescue the Friday effect.

---

# A6.4 — Friday15 short-horizon executable geometry

Because the later regime still retained its clearest raw directional bias in the first ~30 minutes, a dedicated short-horizon grid was tested:
- TP 0.20–1.00% in 0.05 steps
- SL 0.20–1.00% in 0.05 steps
- max hold 30 / 45 / 60 / 90 / 120 minutes
- 1,445 configurations

Best full-history configuration was still negative:
**TP0.65 / SL0.50 / max120m**
- WR 52.17%
- net **-$22.45**
- PF 0.849
- max DD $34.23
- 4/8 blocks positive
- discovery +$8.09
- validation **-$30.54**

Across all 1,445 short-horizon configurations:
- **0** profitable in both discovery and validation
- **0** positive with >=6/8 blocks
- no profitable high-WR frontier

Thus the remaining ~30m directional tendency is too small / unstable to overcome the assumed 0.15% round-trip fee through simple TP/SL geometry.

---

# Friday verdict

Friday is **not rejected as meaningless**. The data show a genuine historical Friday afternoon tendency, but it is strongly non-stationary:
- strong first-period afternoon BUY behavior
- weakened / shortened later-period behavior
- apparent newer clock tendencies elsewhere in the day

What is NOT supported is a fixed executable Friday champion under the current tests.

Do not freeze or deploy Friday15 using a full-sample optimized TP/SL. Doing so would hide the severe discovery -> validation regime break.

Potential future revisit only if there is a separate causal regime-state mechanism that can explain when the Friday afternoon effect is active. Such a study should use pre-entry context and should not cherry-pick later-period clocks.

## Current ranking
- **Tuesday 06:00 SELL:** frozen champion, executable research edge.
- **Friday:** researched extensively; no robust executable champion yet.

Recommended next independent temporal engine: evaluate another A1 candidate (e.g. Saturday 18:00 BUY or Sunday 01:00 BUY) rather than forcing more complexity onto Friday at this stage.
