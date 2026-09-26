# SOL Indicator Relationship Discovery — Stage 7 Preregistration

**Status:** FROZEN BEFORE RESULT-BEARING EXECUTION  
**Parent:** Stage 6 completed with replicated directional / expansion market states.  
**Purpose:** convert only frozen Stage-6 evidence into executable LONG / SHORT / NO-TRADE candidates and test the user's trading constraints.  
**Research only:** no live BabaBot strategy is modified here.

## 1. Frozen information set

Stage 7 may use only:
- Stage-6 mutually-exclusive market state;
- Stage-6 frozen regime overlay;
- the exact Stage-2 15m causal decision grid and 5m raw execution path.

No Stage-3/4/5/6 indicator threshold may be retuned in Stage 7.
BTC.D / USDT.D remain excluded after failing Stage-5B incremental replication.

## 2. Frozen rule families

### R1_CORE_DIRECTIONAL_STATES
LONG:
- DOWN_POSITION_BUILD
- HIGHLOC_SELL_ABSORPTION_LIKE

SHORT:
- POST_BREAKDOWN_UNWIND_30M
- UP_UNWIND_LIKE
- HIGHLOC_BUY_EXHAUSTION_LIKE

Everything else: NO TRADE.

### R2_DIRECTIONAL_PLUS_EXPANSION
LONG:
- DOWN_POSITION_BUILD

SHORT:
- POST_BREAKDOWN_UNWIND_30M
- UP_UNWIND_LIKE

These are the Stage-6 states that passed both directional and expansion replication gates.

### R3_STABLE_REGIME_CELLS
LONG:
- SIDEWAYS + HIGHLOC_BUY_BUILD
- TRANSITION + HIGHLOC_SELL_ABSORPTION_LIKE

SHORT:
- BULL + DELEVERAGING
- SIDEWAYS + HIGHLOC_BUY_EXHAUSTION_LIKE
- SIDEWAYS + DELEVERAGING
- TRANSITION + HIGHLOC_BUY_EXHAUSTION_LIKE

Everything else: NO TRADE.

### R4_CORE_PLUS_STABLE_ADDITIONS
Start with R1, then additionally allow:
- LONG: SIDEWAYS + HIGHLOC_BUY_BUILD
- SHORT: BULL + DELEVERAGING
- SHORT: SIDEWAYS + DELEVERAGING

The other stable Stage-6 cells already overlap R1 in the same direction.

There is no rule search beyond these four preregistered families.

## 3. Execution clock

Primary execution is deliberately the same causal anchor used throughout Indicator Relationship Discovery:

- decision grid: every 15 minutes;
- signal uses only information fully completed at decision time `t`;
- entry: raw SOLUSDT 5m **open at `t`**;
- this is the first tradable raw-bar open after the completed 15m information set;
- no same-signal-bar close entry;
- no 1H waiting delay is introduced in the primary Stage-7 test because this research track was explicitly designed to test earlier detection than hourly monitoring.

## 4. Position policy

- maximum one active position;
- while a position is active, all new LONG and SHORT signals are ignored;
- no pyramiding;
- no reversal while active;
- no cooldown after exit;
- when a position has exited by a decision timestamp, a new signal at that timestamp may enter;
- each partition is simulated independently so no position crosses a DEV / validation boundary.

## 5. Exit policy

Maximum holding time: **4 hours**, matching the frozen Stage-2 primary horizon.

At each completed 5m execution bar:
- LONG TP if high reaches `entry * (1+TP)`;
- LONG SL if low reaches `entry * (1-SL)`;
- SHORT TP if low reaches `entry * (1-TP)`;
- SHORT SL if high reaches `entry * (1+SL)`.

If TP and SL are both observed in the same 5m bar, intrabar order is unknowable:
- count conservatively as **SL**.

If neither barrier is reached by the 4h horizon:
- exit at the final 5m close ending exactly at the 4h boundary;
- exit reason = TIME.

## 6. Frozen TP / SL grid

User constraint:
- TP >= 1.00%
- reward/risk >= 1:1

Frozen DEV-only grid:

| TP | SL | RR |
|---:|---:|---:|
| 1.00% | 1.00% | 1.00 |
| 1.25% | 1.00% | 1.25 |
| 1.25% | 1.25% | 1.00 |
| 1.50% | 1.00% | 1.50 |
| 1.50% | 1.25% | 1.20 |
| 1.50% | 1.50% | 1.00 |
| 2.00% | 1.00% | 2.00 |
| 2.00% | 1.25% | 1.60 |
| 2.00% | 1.50% | 1.33 |

No other TP/SL is tested in Stage 7.

## 7. Costs

Primary net economics:
- round-trip trading cost = **0.15%** of notional.

Stress diagnostic:
- round-trip cost = **0.25%**.

Reference notional for USD reporting:
- **$500 per trade**, unlevered linear notional.

Costs do not change barrier geometry. They are subtracted from realized gross return after exit.

## 8. Metrics

For every simulation:
- raw signal count;
- executed trades;
- trades/day;
- TP count;
- SL count;
- TIME count;
- same-bar SL count;
- **target WR = TP / all executed trades**; TIME is a failure for the user's +1% target objective;
- resolved WR = TP / (TP+SL), reported only as secondary;
- economic win rate = net PnL > 0 / all trades;
- net expectancy per trade;
- profit factor;
- total net PnL at $500 notional;
- max loss streak;
- median hold minutes;
- LONG / SHORT side breakdown.

## 9. Frozen family selection

Family selection uses **DEV only** and fixed TP=1.00% / SL=1.00%.

Primary family eligibility:
- trades/day >= 1.00;
- net expectancy > 0;
- PF > 1.

Among eligible families:
1. highest target WR;
2. higher net expectancy;
3. higher trades/day;
4. lexical rule-name tie-break.

If no family is economically eligible:
- diagnostic leader = highest target WR among families with trades/day >=1;
- if none reaches 1/day, highest trades/day.
A diagnostic leader is not a promotion.

2025 and 2026 are not used to select the rule family.

## 10. Frozen TP/SL selection

Only the DEV-selected family proceeds to the TP/SL grid.

A DEV configuration is **TARGET_ELIGIBLE** only if:
- trades/day >= 1.00;
- target WR >= 70.0%;
- TP >= 1.00%;
- RR >= 1.00;
- net expectancy > 0;
- PF > 1.

If multiple are eligible:
1. highest target WR;
2. higher net expectancy;
3. higher trades/day;
4. higher RR;
5. lexical configuration tie-break.

If none is TARGET_ELIGIBLE:
- choose a diagnostic configuration only among configurations with trades/day >=1;
- highest target WR, then net expectancy, then RR.
- it remains explicitly NON-PROMOTABLE regardless of validation behavior.

## 11. Validation / promotion gate

The exact DEV-selected family + TP/SL is frozen and then run untouched on:
- 2025;
- 2026 frozen data.

Promotion requires **all three partitions** to meet:
- trades/day >= 1.00;
- target WR >= 70.0%;
- net expectancy > 0;
- PF > 1.

Additionally:
- 2025 and 2026 must not change direction mapping;
- no threshold rescue or side deletion is allowed after validation is observed.

If DEV itself has no TARGET_ELIGIBLE configuration, Stage 7 cannot promote any signal rule.

## 12. Side diagnostics

LONG-only and SHORT-only metrics are reported for the frozen selected configuration.

They are diagnostics only:
- Stage 7 does not delete the weaker side after seeing validation;
- any future asymmetric redesign requires a new preregistered stage.

## 13. Guardrail

Stage 7 answers:
> Can the frozen market grammar already produce a tradeable rule meeting >=1 trade/day, >=70% target-hit WR, TP>=1%, RR>=1:1, one active position, with positive net economics?

It does not force a winner.

**STAGE7_FROZEN_BEFORE_RESULTS**
