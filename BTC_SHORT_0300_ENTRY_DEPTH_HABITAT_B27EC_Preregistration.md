# B27EC — BTC SHORT 03:00 UTC Entry-Depth Habitat — Preregistration

## Purpose
Test whether the already-supported bearish structural sequence from B27DR has a better executable entry depth at the 03:00 UTC reference clock than F15. This is **not** a new structure search and **not** a clock search.

## Frozen clock and structure
- Reference start: **03:00 UTC**.
- Reference duration: 5h30.
- Execution duration: 6h30 immediately after reference.
- Weekdays only.
- Frozen prior range H/L.
- First Low pressure visit K1 while High opposite visits = 0.
- Causal leave from the K1 Low-touch episode.
- Entry opportunity must occur strictly before H2 / Low revisit or opposite High break.
- Same-bar rejection confirmation: the completed raw 5m touch bar must close below the tested entry fraction.
- Entry is the **next raw 5m open** only.
- Entry must satisfy L < entry < F65.
- Target remains E20_DOWN = L - 0.20R.
- Invalidation remains completed raw5m close > F65 = L + 0.65R.
- TP has priority if TP and invalidation are both observable in the same completed bar, matching B27AD/B27DR fixed economics.
- Session-end next-5m-open exit if unresolved.
- $500 illustrative notional; $0.40 round-trip fee.

## Only variable allowed
Entry-touch depth, frozen grid:
- **F05 = L + 0.05R**
- **F15 = L + 0.15R** (B27DR control)
- **F25 = L + 0.25R**
- **F35 = L + 0.35R**

No EMA, ATR, volume, wick/body, regime, weekday subtype, additional clock, confirmation delay, or management optimization is allowed.

## Parity gate
The F15 row at 03:00 UTC must reproduce B27DR exactly within persisted tolerances before any alternative depth is interpreted:
- external N=19, WR≈73.7%, net≈+$13.51
- development N=37, WR≈83.8%, net≈+$17.92
- reference_validation N=11, WR≈54.5%, net≈-$4.15
- pooled-major N=67, WR≈76.1%, net≈+$27.29

If parity fails, stop.

## Selection protocol
Selection uses **development only**. A depth is development-eligible only if:
- N >= 20
- WR >= 70%
- PF >= 1.30
- expectancy > 0

Among eligible depths, select highest PF; tie-break WR, expectancy, N, then shallower fraction.

External and reference_validation are untouched by selection.

## Independent replication gate
Selected depth must satisfy **both**:
- external: N>=15, WR>=65%, PF>=1.20, expectancy>0
- reference_validation: N>=10, WR>=65%, PF>=1.20, expectancy>0

## Chronological stability
Pooled-major selected trades are split into four equal chronological blocks. At least 3/4 blocks must have positive net PnL and PF>1.

## Slippage stress
Apply adverse slippage to both fills at 0/2/5/10 bps per fill. At 5 bps the selected depth must retain:
- WR >= 65%
- PF >= 1.20
- net > 0

## Portfolio compatibility
Only if all prior gates pass, merge the selected depth with the frozen current control portfolio LONG B27DQ + SHORT20 under the same chronological one-BTC-position lock. Require:
- portfolio net > control net
- portfolio WR >= 70%
- portfolio PF >= 1.80
- displaced current trades <= 5
- incremental selected-depth net > 0

## Interpretation
A PASS means the **same frozen bearish structure** has a better entry habitat at 03:00 UTC. It does not authorize retuning the structure or other clocks. The next clock is tested only after this milestone is concluded.

Research only. Live trading remains unchanged.