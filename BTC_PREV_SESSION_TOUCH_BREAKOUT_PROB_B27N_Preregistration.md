# B27N — Previous-Session Touch Count -> Breakout Probability

## Purpose
Test one causal diagnostic question using the already frozen B27M previous-session level detector:

- After completed previous-session HIGH has already received at least 1 / 2 / 3 / 4 distinct retests during the active session, what is the probability the first strict breakout is BULL (close above previous-session HIGH)?
- Symmetrically, after completed previous-session LOW has already received at least 1 / 2 / 3 / 4 distinct retests, what is the probability the first strict breakout is BEAR (close below previous-session LOW)?

This is diagnostic only, not yet a trading rule.

## Frozen source and definitions
Use `BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27M_Events.csv` without changing any B27M event labels.

Primary configuration:
- timeframe: 15m
- level zone tolerance: ±0.20%
- transitions: ASIA_TO_LONDON and LONDON_TO_NEWYORK, both included
- previous-session HIGH/LOW is fixed only after the previous session completes
- distinct retest = a new visit to the zone after leaving it; consecutive zone-intersecting bars are one visit
- BULL = first strict active-TF close above completed previous-session HIGH
- BEAR = first strict active-TF close below completed previous-session LOW
- NO_BREAK = neither side gets a strict close-through before the active session ends

Secondary diagnostic:
- same calculation on 1h, tolerance ±0.20%

## Threshold logic
For each threshold k in {1,2,3,4}:
- HIGH-k eligible if final `high_retests >= k`. Because B27M counts stop at the first breakout, reaching this count necessarily happened before the recorded terminal direction.
- LOW-k eligible if final `low_retests >= k`.

For HIGH-k report among all eligible sessions:
- P(BULL)
- P(BEAR)
- P(NO_BREAK)

For LOW-k report among all eligible sessions:
- P(BEAR)
- P(BULL)
- P(NO_BREAK)

Also report N. Do not exclude NO_BREAK from the primary probability denominator.

## Frozen partitions
Use B27M partitions unchanged: external, development, reference_validation, august.

## Outputs
Persist:
- `BTC_PREV_SESSION_TOUCH_BREAKOUT_PROB_B27N_Result.md`
- `BTC_PREV_SESSION_TOUCH_BREAKOUT_PROB_B27N_Summary.csv`

No post-hoc promotion of a threshold to a trading rule. Research only; live BBC unchanged.
