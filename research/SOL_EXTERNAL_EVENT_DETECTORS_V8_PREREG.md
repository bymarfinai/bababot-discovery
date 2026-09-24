# SOL External Event Detectors V8 — Preregistration

## Purpose
Test whether established event-onset algorithms from external open-source/research ecosystems can define a better SOL entry trigger than BabaBot's current broad NEW_LONG_BUILD parent state.

External method families reviewed before implementation:
- symmetric CUSUM event sampling (AFML/mlfinpy-style event filtering);
- Directional Change confirmation events and overshoot framework;
- Page-Hinkley online mean-shift detection;
- Bayesian Online Changepoint Detection (BOCD) via run-length reset.

Trend-scanning was reviewed but is not used as an entry trigger because forward-looking trend-scanning is a labeling technique; backward-looking use would describe an existing trend rather than directly identify a new event.

## Data / execution
- SOLUSDT USD-M futures.
- Existing repository 5m loader.
- Detectors operate on completed 15m closes/returns.
- Signal is known only at completed 15m close.
- Entry = next 15m open.
- One active position at a time.
- Same-5m TP+SL ambiguity = loss.
- Max hold = 24 hours for every exit configuration.
- Round-trip cost = 0.15%.
- Notional = USD500.

## Context modes
Every detector configuration is evaluated in two frozen modes:
1. EVENT_ONLY — detector event is sufficient to seed an entry.
2. EVENT_IN_NEW_LONG_STATE — event is eligible only when the previously-defined causal NEW_LONG_BUILD broad derivatives state is active at the signal close.

The external detector is the trigger; NEW_LONG_BUILD may only act as context.

## Frozen detector families

### A. CUSUM_UP
Adapted from the symmetric CUSUM event-filter concept.
- input = completed 15m log return;
- dynamic threshold = alpha × trailing 96-bar return standard deviation, shifted one bar;
- positive accumulator only is traded; negative accumulator is maintained/reset but never traded LONG;
- trigger resets both accumulators.
Frozen alpha grid: 1.0, 1.5, 2.0, 2.5, 3.0.

### B. DIRECTIONAL_CHANGE_UP
Adapted from causal Directional Change confirmation logic.
- maintain current local extremum online;
- LONG trigger = upturn confirmation after price rises theta from the currently-known trough;
- trading uses confirmation timestamp, never hindsight extremum timestamp.
Frozen theta grid: 0.50%, 0.75%, 1.00%, 1.25%, 1.50%.

### C. PAGE_HINKLEY_UP
Adapted from River's online Page-Hinkley increase detector.
- input = 15m log return divided by trailing 96-bar std shifted one bar;
- minimum instances = 32;
- alpha forgetting = 0.9999;
- up-drift only;
- detector resets after a trigger.
Frozen (delta, threshold) grid:
- (0.00, 5)
- (0.05, 5)
- (0.05, 10)
- (0.10, 10)
- (0.10, 15).

### D. BOCD_UP
Adapted from Adams-MacKay / open-source BOCD implementations.
- input = same standardized 15m return;
- online Gaussian unknown-mean model with fixed observation variance 1;
- run-length posterior truncated at 256 states for computational feasibility;
- LONG change event requires most-likely run length to reset from >=16 on prior bar to <=3 now;
- current completed 1h return must be positive to assign LONG direction.
Frozen constant hazards:
- 1/48
- 1/96
- 1/192.

## Exit grid
All exits obey TP >= 1% and reward:risk >= 1:1.
- TP1 / SL1
- TP1.5 / SL1
- TP1.5 / SL1.5
- TP2 / SL1
- TP2 / SL1.5
- TP2 / SL2
- TP3 / SL1.5
- TP3 / SL2
- TP3 / SL3

## Time discipline
- Selection period: calendar 2023 only.
- Validation period: calendar 2024.
- Reference transfer: 2025 and 2026 through available data.
- Parameters, exit, and context mode are selected per detector family using 2023 only.
- No 2024/2025/2026 rescue tuning.

## 2023 family selection
For each detector family choose one frozen candidate among its parameter × context × exit grid.
Eligibility on 2023:
- >=1 executed trade/day;
- positive after-cost expectancy.
Ranking among eligible candidates:
1. highest WR;
2. highest net expectancy/trade;
3. higher frequency.
If no eligible candidate exists, select the >=1/day frontier by highest WR and mark NO_POSITIVE_2023.

## Validation gates
FULL_GATE on 2024:
- WR >=70%;
- >=1 executed trade/day;
- positive expectancy.

NEAR_GATE on 2024:
- WR >=65%;
- >=1 executed trade/day;
- positive expectancy.

All frozen family candidates are still reported on 2025/2026 for diagnostic transfer, but only candidates that passed a 2024 gate are considered promotable.

## Final target
The BabaBot target remains:
- WR >70%;
- >=1 trade/day;
- TP >=1%;
- RR >=1:1;
- positive expectancy;
- robust across years.

No lowering of this final target is authorized by V8.