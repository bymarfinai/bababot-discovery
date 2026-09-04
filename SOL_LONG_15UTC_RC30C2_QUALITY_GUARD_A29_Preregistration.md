# SOL LONG 15:00 UTC RC30_C2 Quality Guard — A29 Preregistration

## Frozen baseline
- R360/15 parent A20 unchanged.
- Exact A27 RC30_C2 trigger/lifecycle unchanged.
- A23 and A27 remain rejected; A29 only tests whether an A28-derived quality guard can remove false-positive RC30_C2 triggers.

## A28 robust causal features used
Central Development rescue vs non-rescue medians, replicated in Central External/RefVal and topology supports:
- signal_close_R: 0.098 vs 0.057 (4/4 supports)
- signal_body_R: 0.049 vs 0.030 (4/4 supports)

Fixed midpoint thresholds, rounded once before OOS:
- signal close threshold = **0.08R**
- signal body threshold = **0.04R**

## Candidate family
1. `Q_CLOSE08`: execute RC30_C2 only if signal close >= H+0.08R.
2. `Q_BODY04`: execute RC30_C2 only if signal-bar body >= +0.04R.
3. `Q_CLOSE08_BODY04`: require both.

No other feature, threshold, clock, or neighboring value may be tested in A29.

## Development gate
- recovery N >=40;
- recovery PF >1.20 raw and >1.05 at 5bps;
- recovery expectancy/net >0 raw/stress;
- parent overlay PF and net improve raw/stress;
- episode WR > parent WR;
- rescue rate >=30%;
- >=4/6 adequate Development blocks positive raw and >=4/6 positive 5bps.

One Development winner only, ranked by stress overlay-net improvement, stress overlay PF, episode WR uplift, then larger N.

## Frozen OOS gate
Exact R360/15 in both External and RefVal:
- recovery net >0 raw/stress;
- overlay PF and net improve raw/stress;
- episode WR > parent WR.
Supports R360/16 and R300/15: >=3/4 positive recovery net raw and >=3/4 positive stress, and >=3/4 positive overlay-net improvement raw/stress.

No OOS retuning. Research only; live Baba Bot unchanged.