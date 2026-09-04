# SOL LONG 15:00 UTC RC30_C2 Target Conversion — A31 Preregistration

## Frozen baseline
- R360/15 A20 parent unchanged.
- Exact A27 RC30_C2 signal: second completed close > H within 30m after frozen parent-loss exit, execute next open.
- No A23 resting recovery and no A29 quality guard.

## A30 evidence
Among Central Development RC30_C2 recovery failures:
- 60.0% touched E10 before their frozen failed-reclaim exit;
- 34.3% touched E20;
- an E10 or E20 fill would have been sufficient to make the combined parent+recovery episode positive for 24.3% of all RC30_C2 failures;
- E30 rescue opportunity was only 11.4%, below the A30 materiality rule.
Therefore A31 tests only E10 and E20. No E15/E25/E30 or other target is allowed.

## Candidate family
1. `T10_FULL`: exact RC30_C2 re-entry, full recovery target = H+0.10R.
2. `T20_FULL`: exact RC30_C2 re-entry, full recovery target = H+0.20R.

Causal execution:
- if next-open re-entry is already >= candidate target, that candidate does not enter;
- target cannot be credited on the RC30_C2 signal bar or re-entry bar; target checking starts on the following 5m bar;
- after reclaim-confirmed entry, completed close <=H triggers next-open FAILED_RECLAIM exit;
- otherwise time exit at the same 720m post-parent-exit boundary;
- one recovery maximum per parent loss.

## Development gate
A candidate must have:
- recovery N >=60;
- recovery WR >=45%;
- standalone recovery PF >1.20 raw and >1.05 after 5bps;
- recovery expectancy/net >0 raw/stress;
- parent overlay PF and net improve raw/stress;
- episode WR > parent WR by >=5 percentage points;
- rescue rate >=35%;
- >=4/6 adequate Development blocks positive raw and >=4/6 positive stress.

Only one Development winner may open OOS, ranked by stress overlay-net improvement, stress overlay PF, episode-WR uplift, then larger target (payoff preservation).

## Frozen OOS gate
Exact R360/15 in both External and RefVal:
- recovery net >0 raw/stress;
- overlay PF and net improve raw/stress;
- episode WR > parent WR by >=3 percentage points.
Supports R360/16 and R300/15:
- >=3/4 positive recovery net raw;
- >=3/4 positive recovery net stress;
- >=3/4 positive overlay-net improvement raw/stress.

No OOS retuning. Research only; live Baba Bot unchanged.