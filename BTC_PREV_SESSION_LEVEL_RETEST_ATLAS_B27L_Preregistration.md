# B27L — Previous-Session Level Retest Atlas (Preregistration)

## Purpose
Faithfully measure the screenshot-style repeated retests of completed previous-session High/Low levels before the next-session first breakout. This is a structural diagnostic, not a trading strategy.

## Frozen data and partitions
- BTCUSDT 5m source used by the existing research stack.
- Same frozen partitions as prior experiments: external, development, reference_validation, august.
- Weekdays only.
- Fixed UTC sessions, unchanged from B26B/B26C:
  - Asia 00:00–08:00
  - London 08:00–13:30
  - New York 13:30–20:00
- Transitions:
  - ASIA_TO_LONDON: completed Asia High/Low observed during London.
  - LONDON_TO_NEWYORK: completed London High/Low observed during New York.

## Observation timeframes
- 15m
- 1H
Active-session bars are anchored to active-session start. If a session length leaves a final partial bar (London/NY on 1H), that final session-close partial bar is retained and flagged; this prevents mixing data from the next session.

## Frozen retest zones
Two independently reported tolerances:
- ±0.10% of the previous-session High/Low.
- ±0.20% of the previous-session High/Low.

For a frozen level L and tolerance t, the zone is [L*(1-t), L*(1+t)].

A HIGH retest occurs when an active-session bar range intersects the High zone while that bar has not already produced a strict close breakout above the original High level.
A LOW retest occurs when an active-session bar range intersects the Low zone while that bar has not already produced a strict close breakdown below the original Low level.

Distinct-visit rule: consecutive active-TF bars that continue intersecting the same zone count as ONE retest. A new retest is counted only after at least one active-TF bar no longer intersects that zone and price later re-enters it.

A bar may intersect both High and Low zones; both visits are recorded because this experiment measures reachability, not unknown intrabar ordering. Such bars are flagged.

## Direction classification
Observe the active session chronologically and stop at the first strict close-through event:
- BULL: first strict close > frozen previous-session High.
- BEAR: first strict close < frozen previous-session Low.
- NO_BREAK: neither strict close-through occurs before active-session end.

The breakout bar itself is NOT counted as an additional retest of the side it breaks.
All High/Low retest counts are therefore causal counts accumulated strictly before the classified first breakout (or through session end for NO_BREAK).

## Required outputs
For every TF × tolerance × transition × partition × direction:
- event count N;
- High retest mean, median, P75, max;
- Low retest mean, median, P75, max;
- shares with High retests >=1, >=2, >=3, >=4;
- shares with Low retests >=1, >=2, >=3, >=4;
- exact (High retests, Low retests) combination frequencies.

Persist raw day-level events with previous-session levels, direction, breakout timestamp, High/Low retest counts, both-zone-bar count, and partial-bar flags.

## Interpretation rule
This is forensic/diagnostic only. No retest-count bucket may be promoted to a trading rule from this result without a new additive preregistered experiment.

Research only; live BBC unchanged.
