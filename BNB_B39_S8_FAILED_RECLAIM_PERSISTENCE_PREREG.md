# BNB B39-S8 — Failed-Reclaim Persistence Character Preregistration

## Objective
Test whether persistence / failed reclaim after a frozen B39 D1 post-entry breach separates genuine failures from liquidity-dip winners better than the single-breach states audited in B39-S7.

S8 changes no detector, entry, target, structural floor, or price level.

## Frozen stack
- Detector: D1_FIRST5_DISPLACEMENT
- Signature:
  `8ae240e94d64707d2077a40f83f50f896e36a9ecf738ef74c1ec9c2f3c21d6b2`
- D1 condition:
  `p5_close_r > 0.20335748322474653`
- Entry:
  market at D1 confirmation close
- Target:
  anchor +1 event-R
- Structural floor:
  demand_low
- Deadline:
  24h from first touch
- Frozen signal parity:
  DEV 151 signals / 108 GE1R
  REF 101 signals / 83 GE1R

## Motivation frozen from S7
Single-breach states captured many losses but also falsely exited many eventual winners.
Among false-exited winners after CLOSE5_BELOW_D1_LOW:
- DEV 85.0% reclaimed D1-low within 15m
- REF 52.6% reclaimed within 15m

Therefore S8 tests persistence / failed reclaim only.

## Frozen levels
Exactly two levels:
1. D1_LOW = low of the completed D1 5m signal candle
2. ANCHOR = first-touch 15m close

No new numeric price threshold is introduced.

## Candidate persistence states
Exactly six candidates.

### D1-low family
1. `D1_TWO_CLOSES_BELOW`
   - first completed 5m close below D1_LOW
   - immediately next completed 5m close also below D1_LOW

2. `D1_NO_RECLAIM_15M`
   - after first completed 5m close below D1_LOW,
   - the next three completed 5m closes all remain below D1_LOW.

3. `D1_RECLAIM_ATTEMPT_REJECT`
   - after first completed 5m close below D1_LOW,
   - a subsequent bar within the next 15m trades to/above D1_LOW,
   - but closes below D1_LOW.
   - first such rejected reclaim is the signal.

### Anchor family
4. `ANCHOR_TWO_CLOSES_BELOW`
   - first completed 5m close below ANCHOR
   - immediately next completed 5m close also below ANCHOR

5. `ANCHOR_NO_RECLAIM_15M`
   - after first completed 5m close below ANCHOR,
   - the next three completed 5m closes all remain below ANCHOR.

6. `ANCHOR_RECLAIM_ATTEMPT_REJECT`
   - after first completed 5m close below ANCHOR,
   - a subsequent bar within the next 15m trades to/above ANCHOR,
   - but closes below ANCHOR.
   - first such rejected reclaim is the signal.

No alternate persistence lengths are searched.

## Causal ordering discipline
All persistence confirmation occurs after D1 entry.

A candidate signal is only clean if:
- initial breach occurs before target / demand-low floor;
- all confirmation bars required by the candidate complete before target / floor;
- if target or floor occurs on any confirmation bar, the candidate is not credited.

No same-bar ordering is invented.

## Counterfactual early exit
For a clean persistence signal:
- exit at its confirmation-bar close.
- R is measured against the original wide structural risk:
  `(exit - entry)/(entry - demand_low)`

Otherwise baseline wide-floor outcome remains unchanged.

## Required outputs
For DEV, REF, each year:
- signal count/rate
- loss capture
- winner false-exit
- signal precision for baseline loss
- median early-exit R on captured loss
- lead time to structural floor
- lead time to eventual target for false exits
- counterfactual expectancy / total R / PF / max DD
- comparison to frozen baseline
- comparison to corresponding S7 single-breach family

False-exit anatomy:
- whether false-exited winner reclaims the tested level within next 5m and 15m after persistence signal
- signal -> later target time
- adverse overshoot

## Advance rule
A persistence character may advance only if:
1. counterfactual expectancy improves over frozen baseline in BOTH DEV and REF;
2. loss-capture rate is meaningfully greater than winner false-exit rate;
3. it improves separation versus its corresponding S7 single-breach state;
4. annual results are not dependent on one isolated year;
5. no candidate is selected by retuning persistence length.

If none passes, retain the wide floor and stop forcing failure exits.
