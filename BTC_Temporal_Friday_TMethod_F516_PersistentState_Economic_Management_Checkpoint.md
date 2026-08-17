# BTC Friday15 T-Method — F5.16 Persistent-State Economic Management

**Date:** 2026-08-17 WIB  
**Status:** F5.16 FAIL — NO DISCOVERY-QUALIFYING PERSISTENT MANAGEMENT RULE  
**Live BBC:** untouched

## Objective

F5.15 showed that trajectory persistence after the frozen F5.12 `HIDDEN_CORE_EMA` first warning separates eventual BUY deterioration much better than acting immediately on the first warning. F5.16 tested whether this persistence is economically actionable while keeping every Friday BUY entry.

Hard constraints:
- all **138 / 138 Friday15 BUY entries retained**;
- frozen parent TP2.0 / SL0.7 / hold360m;
- frozen F5.12 warning unchanged;
- no SHORT;
- no entry filtering;
- no fitted threshold sweep;
- only two predeclared persistence states:
  - `P15`: exact F5.12 warning remains continuously true through +15m after first warning;
  - `P20`: exact warning remains continuously true through +20m;
- management begins only at that causal +15m / +20m decision open;
- if parent has exited or warning recovered before the persistence point, HOLD parent.

Management policies:
1. `HALF_RISK_STOP`: SL -0.70% -> -0.35%
2. `BE_IF_GREEN`
3. `LOCK_HALF_GAIN`
4. `PARTIAL50`
5. `PARTIAL50_HALF_RISK`

Discovery selection gate:
- >=5 actual changed outcomes;
- positive discovery PnL uplift.

Validation is report-only. Milestone PASS additionally required positive validation uplift, positive full uplift, and no worse full max drawdown.

## Frozen parent

All 138 Fridays:
- WR **47.83%**
- PnL **+$64.630**
- expectancy **+$0.4683/trade**
- PF **1.266**
- max DD **$56.530**
- max loss streak 8

Discovery N82:
- PnL **+$99.194**

Validation N56:
- PnL **-$34.563**

## Milestone verdict

`discovery_rank = []`

No P15/P20 policy produced positive discovery uplift with >=5 changed outcomes. Therefore no rule was selected for validation promotion.

> **F5.16 = FAIL / NO DISCOVERY PERSISTENT MANAGEMENT CANDIDATE.**

However, persistence materially improves the economics versus first-warning management and reveals a useful chronology effect.

## Closest result — P15 + HALF_RISK_STOP

Persistent states:
- discovery: 9
- validation: 11
- full: 20

Actual changed outcomes:
- discovery: 6
- validation: 8
- full: 14

Discovery:
- parent +$99.194
- managed +$95.741
- delta **-$3.453**
- DD worsens by $1.877
- 4 improved / 2 damaged
- rescue gain +$6.430
- damage -$9.882

Validation:
- parent -$34.563
- managed -$26.899
- delta **+$7.664**
- DD improves by **$3.500**
- 7 improved / 1 damaged
- rescue gain +$12.250
- damage -$4.586

Full:
- parent +$64.630
- managed **+$68.843**
- delta **+$4.213**
- PF 1.266 -> **1.297**
- max DD $56.530 -> **$53.030**
- 11 improved / 3 damaged
- parent SL actions: 11
- parent TP actions: **0**

This is economically much better than F5.14 first-warning half-risk management, but chronology is inverted: it hurts the strong discovery era and helps the weak validation era.

## P20 + HALF_RISK_STOP

Persistent states:
- discovery 6
- validation 9
- full 15

Actual changed outcomes:
- discovery 4
- validation 7
- full 11

Discovery:
- delta **-$0.516**
- DD improves by $1.060

Validation:
- delta **+$4.574**
- DD improves by $1.305

Full:
- PnL $64.630 -> **$68.690**
- delta **+$4.060**
- PF 1.266 -> **1.294**
- max DD $56.530 -> **$55.225**
- 9 improved / 2 damaged
- parent SL actions: 9
- parent TP actions: **0**

P20 is even closer to neutral in discovery but has only 4 changed discovery outcomes, below the minimum action gate.

## Other management families

### Break-even if green

P15 full delta: **-$15.357**  
P20 full delta: **-$3.960**

Still clips timeout runners and does not create stable expectancy.

### Lock half current gain

P15 full delta: **-$29.860**  
P20 full delta: **-$20.421**

Rejected. Profit-lock remains too destructive to runners.

### Partial 50%

P15 full delta: **-$10.520**  
P20 full delta: **-$4.393**

Drawdown reduction does not compensate for expectancy loss.

### Partial 50% + half-risk

P15 full delta: **-$8.413**  
P20 full delta: **-$2.363**

P20 validation is mildly positive (+$0.770), but discovery remains negative and full expectancy remains below parent.

## Interpretation

F5.15 persistence was real, and F5.16 confirms that waiting for persistence sharply reduces the economic damage of acting on the first warning. In particular, persistent-state half-risk management:
- mostly targets eventual parent SLs;
- avoids changing any eventual parent TP in the P15/P20 half-risk results;
- improves the weak validation period materially;
- improves full-history PnL and drawdown.

But the same action does **not** improve the discovery period. Therefore it cannot be promoted as a stable causal champion.

The chronology suggests that Friday market behavior changed: the later validation regime benefits from persistent-warning risk reduction much more than the earlier discovery regime. This should be investigated as a regime/era effect rather than solved by tuning another stop or persistence minute on the same sample.

## Scientific next question

Do not optimize P15/P20 or the -0.35% stop further on these same 138 Fridays.

The justified next milestone is a **regime-attribution forensic**:

> What observable pre-entry / early-trade regime changed between the discovery era (where persistent half-risk hurts) and validation era (where it helps), and can that regime be detected causally?

This should compare the P15/P20 half-risk action cohort across chronology using pre-existing regime variables only, then determine whether the action should be governed by a causal regime state rather than calendar-era knowledge.

No live code was changed.
