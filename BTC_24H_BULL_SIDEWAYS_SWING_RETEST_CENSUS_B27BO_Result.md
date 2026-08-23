# B27BO — BTC 24H BULL→SIDEWAYS Swing-Retest Census — Result

**Audit status: PASS.** BULL→SIDEWAYS swing-retest census only; no trading direction or economics were used.

Parent identity reproduced: **532 BULL-origin episodes = 281 RESUME + 251 TRANSITION**. Frozen boundary is the prior completed BULL state latest confirmed swing low.

A defended retest is a completed 4H SIDEWAYS bar whose low reaches/sweeps the frozen swing low but whose close remains above it. Consecutive defended-retest bars collapse into one distinct visit. A break is the first completed 4H SIDEWAYS close below the frozen swing low.

## Pooled OOS — episodes that eventually close-break the swing low during SIDEWAYS

- Close-break episodes: **97**.
- Distinct defended retests before break: **0x 79 (81.4%), 1x 16 (16.5%), 2x 2 (2.1%), 3+ 0 (0.0%)**.
- Median distinct retests: **0.0**; P75 **0.0**; P90 **1.0**; max **2**.
- Median first close-break age: **1.0 bars / 4h**; P75 **2.0 bars**; P90 **3.4 bars**; max **10 bars**.

### By eventual detector outcome

- RESUME despite a close-break during SIDEWAYS (N=41): 0x 33 (80.5%), 1x 7 (17.1%), 2x 1 (2.4%), 3+ 0 (0.0%).
- TRANSITION after a close-break during SIDEWAYS (N=56): 0x 46 (82.1%), 1x 9 (16.1%), 2x 1 (1.8%), 3+ 0 (0.0%).

## Pooled OOS — no 4H close-break during SIDEWAYS

- N **216**; distinct defended retests across the whole SIDEWAYS episode: 0x 182 (84.3%), 1x 32 (14.8%), 2x 2 (0.9%), 3+ 0 (0.0%).

## OOS partition stability

| Partition | Break N | 0 retest | 1 retest | 2 retests | 3+ retests | Median | Median break age |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 62 | 75.8% | 21.0% | 3.2% | 0.0% | 0.0 | 1.0 bars |
| reference_validation | 35 | 91.4% | 8.6% | 0.0% | 0.0% | 0.0 | 1.0 bars |

## Frozen census gate

- Exact source/detector/parent identity: **PASS**.
- Frozen swing-low boundary available >=95% pooled OOS: **PASS**.
- Pooled-OOS close-break N >=30: **PASS**.
- Retests counted strictly before first close-break: **PASS**.

**Frozen verdict: `B27BO_BULL_SWING_RETEST_CENSUS_COMPLETE`.**

Interpretation: this is a structural retest-count census only. It does not prove accumulation/reaccumulation or promote a new detector rule.

Research only. Live BBC unchanged.
