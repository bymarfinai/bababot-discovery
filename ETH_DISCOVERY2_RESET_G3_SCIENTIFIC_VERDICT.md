# ETH Discovery 2 Reset — G3 Scientific Verdict

**Verdict: SUPPORTED.**

G3 rediscovered downstream structure on the frozen, historically supported G2 ETH-native geometry without inheriting the old Z2/Z3 retest rules or Z5 L06 entry.

## Frozen G2 parent
- Direction: **LONG**.
- Reference start: **01:30 UTC (08:30 WIB)**.
- Reference duration: **180m**.
- Execution horizon: **720m**.
- Reference: **01:30–04:30 UTC / 08:30–11:30 WIB**.
- Execution: **04:30–16:30 UTC / 11:30–23:30 WIB**.

## G3 structural family
Development-only comparison:
- DIRECT: first strict completed close > H after the frozen parent pressure signal;
- LEAVE: require a completed full leave (`high < H`) before B00;
- RETEST family: require leave, then a completed top-band close within dR of H, then B00;
- retest depths d = 0.01/0.02/0.05/0.10/0.15/0.20/0.30/0.40, with d=0.01 and d=0.40 as outer sentinels.

B00 itself was **not** counted as continuation success. X05/X10/X20 required a new post-B00 extension from the completed B00 close by +0.05R/+0.10R/+0.20R, on a later bar, before a completed close back below H. Same-bar target/re-entry ambiguity was conservatively not counted as success.

## Lineage sanity checks
Development parent pressure signals: **206**.
Frozen G2 same-side continuation count: **184**.
G3 DIRECT B00 count: **184**.

Therefore G3 reproduces the frozen G2 same-side breakouts exactly before adding any downstream classification.

## Development atlas
| Candidate | B00 N | Participation | X05 | X10 | X20 | Wilson X10 | Positive blocks | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **DIRECT** | **184** | **89.3%** | **62.0%** | **52.7%** | **44.0%** | **45.5%** | **4/4** | **PASS** |
| LEAVE | 123 | 59.7% | 62.6% | 52.8% | 43.1% | 44.1% | 4/4 | PASS |
| RETEST_D01 | 15 | 7.3% | 60.0% | 40.0% | 33.3% | 19.8% | 0/4 | FAIL |
| RETEST_D02 | 30 | 14.6% | 53.3% | 43.3% | 33.3% | 27.4% | 0/4 | FAIL |
| RETEST_D05 | 63 | 30.6% | 58.7% | 49.2% | 39.7% | 37.3% | 2/4 | FAIL |
| RETEST_D10 | 91 | 44.2% | 59.3% | 48.4% | 38.5% | 38.4% | 3/4 | FAIL |
| RETEST_D15 | 102 | 49.5% | 60.8% | 49.0% | 38.2% | 39.5% | 4/4 | FAIL |
| RETEST_D20 | 108 | 52.4% | 60.2% | 49.1% | 38.0% | 39.8% | 3/4 | FAIL |
| RETEST_D30 | 112 | 54.4% | 60.7% | 50.0% | 39.3% | 40.9% | 4/4 | PASS |
| RETEST_D40 | 114 | 55.3% | 61.4% | 50.9% | 40.4% | 41.8% | 4/4 | PASS |

Development-selected structure under the preregistered ranking: **DIRECT**.

DIRECT details:
- B00 triggers: **184 / 206 = 89.3%** of parent pressure signals.
- X05: **62.0%**.
- X10: **52.7%**.
- X20: **44.0%**.
- Wilson 95% lower bound for X10: **45.5%**.
- Median parent pressure → B00: **25 minutes**.
- Median B00 → X10 among X10 successes: **5 minutes**.
- Positive chronological blocks: **4/4**.
- Block X10 rates: **60.5%, 55.3%, 48.9%, 46.8%**.
- Block X20 rates: **53.5%, 42.6%, 42.6%, 38.3%**.

## Historical replication of frozen DIRECT structure
External:
- Parent pressure signals: **105**.
- B00 triggers: **88**.
- Participation: **83.8%**.
- X05: **60.2%**.
- X10: **55.7%**.
- X20: **45.5%**.
- Wilson X10: **45.3%**.
- **PASS**.

Reference Validation:
- Parent pressure signals: **101**.
- B00 triggers: **91**.
- Participation: **90.1%**.
- X05: **60.4%**.
- X10: **50.5%**.
- X20: **41.8%**.
- Wilson X10: **40.5%**.
- **PASS**.

Both independent historical replication gates passed unchanged.

## Scientific interpretation
G3 rejects the assumption that ETH needs an inherited leave/retest structure before breakout.

The additional LEAVE requirement removed roughly one third of Development B00 opportunities (184 → 123) while producing essentially no X10 improvement (52.7% → 52.8%) and slightly lower X20 (44.0% → 43.1%).

The retest-depth family was generally worse. Deeper retest variants recovered participation and some passed the minimum Development gate, but none beat DIRECT under the preregistered ranking. The d=0.40 sentinel was still below DIRECT on X10, X20, and Wilson X10, so there is no evidence that widening retest depth is the stronger next experiment.

The reset lineage therefore supports a simpler ETH-native downstream grammar:

**first valid HIGH-side pressure → first strict completed close above H (DIRECT B00)**

No leave/retest prerequisite is promoted.

The post-B00 path is fast when it works: median B00→X10 is only **5 minutes** in Development. This is important for entry discovery because excessive confirmation delay may surrender a meaningful fraction of the available extension.

## What G3 does NOT validate
G3 does not validate:
- NEXT_OPEN or any other entry timing;
- old Z5 L06 resting pullback entry;
- any TP/SL/hold rule;
- leverage, fee, PnL, expectancy, PF, drawdown, or live execution.

## Next valid experiment
The next stage should be **G4 ETH-native entry discovery** on the frozen parent:

**LONG / 01:30 UTC / R180 / E720 / first HIGH-side pressure → DIRECT B00**.

Because G3 shows median successful B00→X10 extension of only 5 minutes, G4 should explicitly compare immediate executable entry against shallow resting pullbacks rather than presuming the old L06 rule. Old L06 may be included only as a named historical control and must re-earn selection on the new geometry.

Research/shadow only. No live promotion.
