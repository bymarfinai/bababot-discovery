# BTC Friday15 T-Method — F5.18 Frozen Slow-Health Shadow Check

**Date:** 2026-08-17 WIB  
**Status:** F5.18 NEUTRAL — FROZEN SHADOW GATE NOT EXERCISED POST-SAMPLE  
**Live BBC:** untouched

## Frozen architecture

F5.17 identified `SLOW13 < 0` as the strongest causal chronology clue, but did not promote it because discovery had zero negative-SLOW13 P15 action cases.

Before inspecting post-2026-07-30 persistence details, F5.18 froze exactly:

`Friday15 BUY -> F5.12 HIDDEN_CORE_EMA warning -> P15 continuous persistence -> prior 13 completed frozen-Friday parent average PnL < 0 -> HALF_RISK_STOP -0.35%`

Otherwise HOLD the frozen parent:
- BUY every Friday 15:00 WIB;
- TP +2.00%;
- SL -0.70%;
- max hold 6h;
- $500 reference notional;
- 0.15% round-trip fee.

No SHORT, no entry filtering, no threshold tuning, and no calendar-era labels.

The health ledger is causal: the current Friday's SLOW13 uses only completed full-size frozen-parent outcomes from prior Fridays. The current Friday outcome updates health only for the next Friday.

## Post-sample dates

Checked:
- 2026-07-31
- 2026-08-07
- 2026-08-14

These dates are post the 138-Friday research sample ending before 2026-07-30. They are treated as a **shadow/post-sample check**, not overstated as pristine unseen OOS because aggregate outcomes from these dates had already been viewed in other Friday research branches.

## Reproduction gate

Before checking the three post-sample Fridays, the script reproduced the historical frozen parent:
- N138
- 66 wins
- PnL approximately +$64.630

Reproduction passed.

## Per-Friday result

### 2026-07-31
- SLOW13: **-$0.231 average PnL/Friday**
- SLOW13 negative: yes
- parent: **SL, -$4.250**
- F5.12 first warning: **none**
- P15 persistent: no
- shadow gate: **OFF**
- delta vs parent: **$0.000**

### 2026-08-07
- SLOW13: **-$1.269 average PnL/Friday**
- SLOW13 negative: yes
- parent: timeout, **+$4.663**
- first warning: **none**
- P15 persistent: no
- shadow gate: **OFF**
- delta: **$0.000**

### 2026-08-14
- SLOW13: **-$0.842 average PnL/Friday**
- SLOW13 negative: yes
- parent: timeout, **-$2.725**
- first warning: **none**
- P15 persistent: no
- shadow gate: **OFF**
- delta: **$0.000**

## Aggregate post-sample result

Frozen parent:
- N **3**
- wins/losses **1 / 2**
- WR **33.33%**
- PnL **-$2.3119**
- PF **0.669**
- max DD **$4.25**

F5.18 shadow:
- N **3**
- wins/losses **1 / 2**
- WR **33.33%**
- PnL **-$2.3119**
- PF **0.669**
- max DD **$4.25**

Shadow uplift: **$0.000**.

## Interpretation

All three post-sample Fridays were already in negative slow-health state, so the first half of the F5.17 regime hypothesis was present.

However, none produced the frozen F5.12 `HIDDEN_CORE_EMA` warning. Therefore none could reach P15 persistence and no defensive action was justified.

This is useful neutral evidence:
- the SLOW13 state does **not** by itself de-risk every weak-era Friday;
- the architecture still requires current-trade hidden-state deterioration and persistence;
- the shadow rule did not damage the one post-sample winner because it stayed inactive;
- but there is also zero post-sample evidence yet about whether an activated SLOW13+P15 action helps.

F5.18 therefore **cannot validate or reject** the F5.17 shadow hypothesis.

## Scientific verdict

**NEUTRAL / NOT EXERCISED.**

Do not retune the warning or persistence requirement because three post-sample dates produced zero actions. Removing P15 or weakening F5.12 just to force an action would contaminate the frozen hypothesis.

The legitimate Friday continuation is forward shadow accumulation:
- keep calculating full-size frozen parent outcomes for the SLOW13 ledger;
- keep evaluating the frozen F5.12 warning and P15 persistence;
- record the first future occurrence where both `SLOW13 < 0` and P15 persistence are true;
- only then obtain new economic evidence for the -0.35% defensive action.

Until such an occurrence exists, F5.17 remains a causal regime clue rather than a proven management upgrade.

**Live BBC remains untouched.**
