# ETH B27DX — S5B Zone-Native Fixed-Exit Portfolio Lock — Preregistration

## Purpose
Evaluate the first fully frozen ETH-native LONG portfolio after lifecycle, clock, entry and fixed-target geometry have each been calibrated causally and independently.

S5B performs **no parameter optimization**. It constructs candidate trades from the frozen zone rules, applies the global one-ETH-position lock, and reports actual portfolio frequency and economics.

## Frozen zone rules
All zones use R300 / X360 and completed-close F35 invalidation.

| Execution clock | Entry | Fixed target |
|---:|---:|---:|
| 05:00 UTC | F80 | E30 |
| 09:00 UTC | F80 | E25 |
| 10:00 UTC | F75 | E25 |
| 16:00 UTC | F90 | E25 |

The entries were frozen from S2 zone-native robust entry families. The targets were frozen from S5A target-family medians. No S5B result may change them.

## Causal trade semantics
- exact corrected B27DX session/event grammar;
- entry is the first eligible pre-terminal retrace fill returned by the frozen scorer;
- exit evaluation begins on the next 5m bar after the fill bar, matching the ETH scorer;
- target is a resting limit: first later bar high >= target exits at target and records exit timestamp at that bar start;
- F35 invalidation is known only after a completed close below F35; exit timestamp is that bar start + 5 minutes, exit price is the completed close;
- otherwise time exit at X360 execution-end open.

Before portfolio locking, every zone/partition 0-bps candidate stream must reproduce the existing `score_config` N, WR, PF, expectancy and net for the exact frozen configuration. Any mismatch is a hard failure.

## Global one-position lock
One ETH LONG position maximum across the four zones.

- process candidates by causal entry timestamp;
- earliest eligible entry is accepted;
- any later candidate with `entry_ts < active exit_ts` is skipped;
- a new entry is allowed at/after prior `exit_ts`;
- exact same-timestamp ties use the preregistered non-performance order: **05:00 → 09:00 → 10:00 → 16:00 UTC**.

No hindsight ranking or expected-return priority is allowed.

## Partitions
Score separately:
- external;
- development;
- reference_validation;

Also report `POOLED_MAJOR` across those three partitions, exactly paralleling the BTC B27DX portfolio convention.

## Metrics
For candidate and accepted streams report:
- N, wins, WR, PF, expectancy, net;
- max consecutive loss streak;
- accepted/skipped count and retention;
- contribution by zone;
- exact same-timestamp tie count;
- actual accepted trades/week based on calendar duration of each partition and pooled major duration.

## Execution stress
Using the exact same candidate paths and lock decisions, rescore pooled-major at 0, 2, 5 and 10 bps adverse execution stress:
- LONG entry execution price worsens by +bps;
- fixed target limit price is unchanged;
- non-target exit execution price worsens by -bps;
- fee remains $0.40 round trip.

This is ETH execution-stress analysis and is not claimed to be identical to BTC runner stop-slippage sensitivity.

## Frozen benchmark gates
BTC B27DX LONG final benchmark:
- WR 71.9%;
- PF 2.22;
- expectancy +$1.26/trade;
- max loss streak 3.

S5B reports:
- `BTC_QUALITY_0BPS_PASS` only if pooled-major accepted WR >= 71.9%, PF >= 2.22, expectancy >= $1.26, net > 0 and max loss streak <= 3;
- `ETH_2PW_FREQUENCY_PASS` only if pooled-major actual accepted trade rate >= 2.00/week.

For 5-bps diagnostic, compare against the BTC B27DX published 5-bps figures (WR 68.9%, PF 2.09) but do not call it exact execution parity because the stress models differ.

## Decision states
- `ETH_S5B_BTC_QUALITY_AND_2PW_SUPPORTED`
- `ETH_S5B_BTC_QUALITY_SUPPORTED_FREQUENCY_SHORT`
- `ETH_S5B_FREQUENCY_SUPPORTED_QUALITY_SHORT`
- `ETH_S5B_BOTH_TARGETS_SHORT`

## Guardrails
No parameter search, no zone dropping, no runner selection, no stop adjustment, no leverage adjustment and no live BBC changes in S5B.
