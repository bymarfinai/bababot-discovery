# SOL LONG 15:00 UTC Dynamic Episode Rescue — A32 Preregistration

## Frozen baseline
- Habitat R360/15 and A20 parent unchanged.
- Exact A27 RC30_C2 signal and next-open re-entry unchanged.
- A23/A27/A29/A31 remain rejected and are not combined.

## Motivation from A30/A31
A30 showed the amount required to recover the original parent loss is observable and known at re-entry (`required_exit_R_to_episode_be`). A31 showed fixed E10/E20 can raise WR strongly but fixed targets leave too little expectancy after costs. A32 therefore targets the actual economic objective: make the combined parent+recovery episode positive after stress, rather than forcing every episode to the same H-relative target.

## Single preregistered mechanism: `DYN_EP_RESCUE_5BPS`
Let:
- parent raw PnL = P < 0;
- notional = N;
- frozen one-trade stress = c = 5bps * N.

The recovery raw-profit target is:
`required_recovery_profit = -P + 3c`.

Rationale:
- parent + recovery together incur 2c under the frozen 5bps-per-entry stress convention;
- recovering `-P + 2c` is stress break-even;
- the additional +c creates a positive stressed episode margin equal to one frozen cost unit.

At the RC30_C2 next-open entry E:
`dynamic_target_price = E * (1 + required_recovery_profit/N)`.

Guardrails:
- if dynamic target <= entry, skip;
- if dynamic target > frozen E40 (H+0.40R), skip rather than expanding payoff coordinates;
- target is not credited on signal/re-entry bar; checking starts next 5m bar;
- completed close <=H -> next-open FAILED_RECLAIM exit;
- otherwise same 720m post-parent-exit time boundary;
- one recovery maximum per parent loss.

## Development gate
- recovery N >=60;
- recovery WR >=50%;
- recovery PF >1.20 raw and >1.05 stress;
- recovery expectancy/net >0 raw/stress;
- parent overlay PF and net improve raw/stress;
- episode WR improves >=7 percentage points raw and >=5pp stress;
- raw rescue rate >=45% and stress rescue rate >=40%;
- >=4/6 adequate Development blocks positive raw and >=4/6 positive stress.

## Frozen OOS gate
Exact R360/15 External and RefVal:
- recovery net >0 raw/stress;
- overlay PF/net improve raw/stress;
- episode WR improves >=4pp raw and >=3pp stress.
Supports R360/16 and R300/15: >=3/4 positive recovery net raw/stress and >=3/4 positive overlay-net improvement raw/stress.

No alternative multiplier/margin and no OOS retuning are authorized in A32. Research only; live Baba Bot unchanged.