# BTC Temporal Friday15 — A6.47 to A6.50 Online Regime Risk Governor Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** PROVISIONAL BALANCED RISK-GOVERNOR CANDIDATE — NOT LIVE / NOT FRESH-OOS PROVEN  
**Parent/reference:** A6.33 Friday15 BUY provisional champion  
**Live BBC:** untouched

## Executive result

A6.47-A6.50 tested whether the structural Friday15 payoff inversion identified in A6.40-A6.46 can be detected causally online and used without deleting Friday occurrences.

The strongest conclusion is **not** that the detector creates a new directional signal. Instead, it works better as a **risk governor**:

- keep every Friday15 occurrence,
- keep the A6.33 BUY direction and management,
- maintain a causal shadow-health model from prior Friday outcomes,
- detect a DEFENSIVE regime using rolling prior-Friday response,
- require the current Friday to also show the already-defined pre-entry `stress_unwind` mechanism,
- then reduce notional to 50% for that occurrence only.

A6.50 results:

| Metric | A6.33 base | A6.50 half-risk governor |
|---|---:|---:|
| Friday occurrences | 138 | 138 |
| WR | 60.87% | 60.87% |
| PnL | +$141.025 | **+$149.305** |
| Expectancy | +$1.0219 | **+$1.0819** |
| PF | 1.720 | **1.825** |
| Max DD | $46.318 | **$33.413** |
| Max loss streak | 4 | **4** |

Validation (last 56 Fridays):
- base +$1.553, PF1.015, MDD $41.717
- A6.50 **+$14.458, PF1.159, MDD $28.812**

Discovery (first 82):
- base +$139.472
- A6.50 +$134.847
- delta -$4.625, entirely explained by one pre-DD false defensive+stress case that was a +$9.25 base winner and became +$4.625 at half risk.

Net full-sample uplift: **+$8.280**.

## A6.47 — first causal online response detector

Fixed memories:
- prior 13 Friday A6.33 average PnL,
- last 5 prior `stress_unwind` A6.33 outcomes,
- last 5 prior `stress_unwind` raw 120m returns.

All current-Friday flags used prior outcomes only; known DD dates were evaluation labels, never detector inputs.

Key result:
- prior-13-Friday health alone first flagged inside the structural DD on **2025-07-18**,
- flagged 29/39 = 74.36% of the DD period,
- only 7/74 pre-DD Fridays and 6/25 post-DD Fridays were flagged.

However the event-count conditional memory had a serious flaw: after stress-unwind events stopped occurring, old negative conditional events remained in the “last 5 events” memory indefinitely. Therefore the 2-vote detector stayed bad through 100% of the post-DD period.

**A6.47 event-count memory rejected for production.**

## A6.48 — time-decay + hysteresis repair

Replaced stale event-count memory with calendar-time memory.

Fixed architecture:
- FAST = prior 8 Friday A6.33 average PnL,
- SLOW = prior 13 Friday A6.33 average PnL,
- CONDITIONAL = stress-unwind outcomes occurring only inside the prior 13 calendar Fridays, minimum 2 events,
- conditional raw response = same rolling-13-week events at 120m,
- enter DEFENSIVE after 2 consecutive Fridays with FAST<0 plus at least one additional negative confirmation,
- exit DEFENSIVE after 2 consecutive Fridays with FAST>0 and SLOW>0.

Transitions:
1. 2024-06-14 -> DEFENSIVE (false historical regime)
2. 2024-08-02 -> NORMAL
3. **2025-07-11 -> DEFENSIVE**
4. **2026-03-27 -> NORMAL**

Structural-DD coverage:
- 30/39 Fridays = **76.92%** defensive
- defensive PnL inside DD = -$37.551
- non-defensive DD PnL = -$8.767

Post-DD:
- only 7/25 Fridays remained defensive before the state cleared,
- conditional memory naturally expired as stress-unwind stopped appearing.

Full-sample state separation:
- DEFENSIVE: N44, WR45.45%, PnL -$1.662, PF0.980
- NORMAL: N94, WR68.09%, PnL +$142.687, PF2.279

Important caution: the 2024 false defensive regime was profitable (+$17.390 across 7 Fridays), so the detector is a **risk-state estimate**, not a perfect bad-trade classifier.

## A6.49 — direction-switch test

Two-layer trigger:
- A6.48 state already DEFENSIVE before current entry, AND
- current Friday pre-entry `stress_unwind` true.

Only 9/138 Fridays qualified:
- 1 PRE_DD: 2024-07-19
- 8 during structural DD: 2025-07-18, 2025-08-01, 2025-08-29, 2025-10-17, 2025-11-14, 2025-11-21, 2025-12-26, 2026-01-02
- 0 POST_DD

No new SHORT parameter sweep. Tested inherited geometries only.

### Symmetric SHORT TP2.0 / SL0.7

Rejected as directional proof:
- full PnL +$139.331 vs base +$141.025
- delta -$1.694
- MDD improved to $34.512 but max loss streak worsened to 9
- switch-only PnL -$18.254 vs base same cases -$16.561

This directly rejects the claim that the detector reliably identifies a profitable continuation SHORT edge.

### Existing POSTSTOP SHORT TP1.5 / SL0.5

Numerically improved:
- full +$153.306
- PF1.827
- MDD $32.948
- validation +$26.334

But:
- switch-only still -$4.280
- WR only 33.33% on switch cases
- max loss streak increased from 4 to 9
- one PRE_DD +$9.25 BUY winner became -$3.25 SHORT

Interpretation: most uplift came from **smaller loss geometry**, not a newly proven SHORT direction edge. Therefore no direction flip is promoted.

## A6.50 — regime risk scaling

Instead of changing direction, preserve A6.33 exactly and reduce notional to **50%** only when:

`A6.48 DEFENSIVE` AND `current pre-entry stress_unwind`

All 138 Friday occurrences remain traded.

Only 9 occurrences are scaled.

Switch-case base PnL:
- PRE_DD one case: +$9.250
- DD eight cases: -$25.811 total

At half risk:
- PRE_DD one case: +$4.625
- DD eight cases: -$12.905 total

Thus the governor sacrifices $4.625 on the single historical false-positive winner but saves $12.906 during DD, net full uplift **+$8.280**.

Critically:
- sign of every occurrence is unchanged,
- WR stays 60.87%,
- max loss streak stays 4,
- max DD falls ~27.9%, from $46.318 to $33.413,
- validation becomes clearly positive.

## Causal / live-parity requirements

A deployable version would need:

1. **Shadow A6.33 health ledger**
   - Even when actual size is reduced, calculate the hypothetical full-size A6.33 outcome after each completed Friday occurrence.
   - Only completed PRIOR Friday outcomes update the next Friday's FAST/SLOW/conditional health.

2. **Current pre-entry stress_unwind**
   - 60m seller-led state: taker imbalance <0 and 60m return <0,
   - local expansion: 60m volume ratio >1 and range ratio >1 relative to the prior 24h baseline,
   - OI-value change over prior 60m <=0.
   - Every component must be known before the 15:00 WIB entry.

3. **No top-trader crowding requirement in A6.50**
   - Top-trader positioning was useful diagnostically in A6.45-A6.46 but is NOT needed by the A6.50 trigger.

4. **No occurrence deletion**
   - Friday15 is still traded every week.
   - Normal state = 100% standard notional.
   - DEFENSIVE + stress_unwind = 50% notional.

## Scientific verdict

- The response-function concept is supported.
- A6.47 proved an online prior-outcome detector can identify much of the weak regime, but sparse event-count memory was stale.
- A6.48 repaired memory causally with rolling calendar time and hysteresis.
- A6.49 rejected a strong directional SHORT interpretation.
- A6.50 supports the more conservative interpretation: **the detector estimates when confidence in the Friday BUY edge is lower, so it should govern risk rather than invent a new signal.**

### Current provisional balanced Friday reference

A6.50 is the strongest balanced **research candidate** after A6.33:
- N138
- WR60.87%
- PnL +$149.305
- expectancy +$1.0819/Friday
- PF1.825
- MDD $33.413
- max loss streak4
- validation +$14.458
- all occurrences retained

### But do NOT deploy yet

A6.50 was developed after observing the same 138-Friday sample and the known structural drawdown. The detector architecture is causal, but causal does not equal fresh-OOS.

Next proof should be one of:
1. fresh unseen Fridays after 2026-07-30,
2. transfer of the same risk-governor architecture to another temporal family without retuning,
3. strict forward shadow run before enabling live size changes.

**Live BBC remains untouched.**
