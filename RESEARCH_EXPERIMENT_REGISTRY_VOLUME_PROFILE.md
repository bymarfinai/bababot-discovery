# BabaBot Research Registry — Volume Profile Track

Purpose: prevent repeating or post-hoc rescuing POC/VAH/VAL experiments.

## VP1 — Previous-day POC / VAH / VAL failed-auction reclaim on fixed H1 clocks — REJECT

Frozen design:
- BTCUSDT USD-M perpetual;
- signal / decision timeframe = 1H;
- no 1m data;
- previous UTC day profile constructed only from 288 completed 5m candles;
- 100 equal-width price bins spanning previous-day low/high;
- each 5m candle base volume allocated across intersected bins proportional to high-low overlap;
- POC = maximum-volume bin center, lowest-price bin wins exact ties;
- Value Area = contiguous 70% volume region expanded from POC, choosing the larger adjacent-volume side each step, lower side wins exact ties;
- fixed event clocks only: 04/08/18/19 UTC = 11:00/15:00/01:00/02:00 WIB;
- LONG = event low below prior-day VAL, no simultaneous VAH sweep, completed H1 close back inside value area;
- SHORT = event high above prior-day VAH, no simultaneous VAL sweep, completed H1 close back inside value area;
- entry diagnostics begin next1H open.

Diagnostics:
1. +1H/+3H directional follow-through;
2. POC magnet: POC target before event extreme, max6H, adverse-first same-hour ambiguity;
3. full value-area rotation to opposite VA boundary before event extreme;
4. executable net RR1:1 after 0.15% round-trip fee, structural SL at event extreme, max6H.

Evidence coverage:
- 2020-01-01 through 2026-08-18 completed data;
- 697,536 5m rows;
- 58,128 complete 1H rows;
- 2,422 complete previous-day profiles;
- 1,133 qualifying H1 events.

Side aggregate results:
- Reference validation LONG: N93, +3H44.09%, POC eligible85 / target36 = 42.35%, full-VA 11.83%, net1:1 WR21.51%, PnL -$160.47.
- Reference validation SHORT: N110, +3H50.91%, POC eligible99 / target36 = 36.36%, full-VA17.27%, net1:1 WR25.45%, PnL -$160.95.
- External untouched 2020-2021 LONG: N169, +3H54.44%, POC eligible148 / target59 = 39.86%, full-VA20.71%, net1:1 WR30.77%, PnL -$329.77.
- External untouched 2020-2021 SHORT: N170, +3H48.24%, POC eligible157 / target63 = 40.13%, full-VA15.88%, net1:1 WR32.35%, PnL -$210.10.
- August LONG: N4, +3H100%, POC rate75% (3/4), but sample tiny and net1:1 PnL -$0.45.
- August SHORT: N9, +3H44.44%, POC rate37.50%, net1:1 WR22.22%, PnL -$8.60.

External POC blocks:
- LONG: 47.37%, 28.95%, 44.74%, 38.24%.
- SHORT: 47.37%, 32.50%, 50.00%, 31.71%.

Best-looking predefined clock cells were not robust enough to promote. Examples:
- Validation 15:00 SHORT: N31, +3H70.97%, POC45.16%, net1:1 WR38.71%, PnL -$9.74.
- External 01:00 LONG: N29, +3H65.52%, POC64.00%, net1:1 WR51.72%, PnL -$46.90.
- External 01:00 SHORT: N37, +3H64.86%, POC57.14%, net1:1 WR51.35%, PnL +$13.50.
These are descriptive only because they were observed after running the fixed 8-cell matrix and fail transfer / aggregate support.

Verdicts:
- `VP1_POC_ROTATION_SUPPORTED=FAIL`
- `VP1_80_CANDIDATE=FAIL`
- `VP1_EXECUTION_SUPPORTED=FAIL`

Interpretation: a previous-day VAL/VAH failed auction does not reliably rotate to previous-day POC before revisiting the event extreme on these fixed 1H clocks. POC hit-before-adverse is only ~36-42% in reference validation and ~40% external. Full value-area rotation is rarer (~12-21%). Net 1:1 execution fails decisively.

Do not rescue VP1 by changing bin count, Value Area percentage, previous-day definition, clock set, side, distance filters, weekday filters, structural stop, or target on the same evidence. Any future Volume Profile experiment must use a materially different information set or profile horizon, e.g. a fully preregistered previous-session profile, and must not reuse VP1 results for threshold selection.
