# BTC Temporal Friday F6.19 — Remaining Giveback Forensic

**Status:** COMPLETE — FORENSIC ONLY; NO NEW RULE TUNED/PROMOTED  
**Live BBC untouched. Frozen F6.12/F6.9/F6.5 and F6.18 D3 unchanged.**

## Exact cohort correction
The F6.14 untouched giveback cohort is exactly 25:
- 12 reached +0.5R but <+1R.
- 13 reached +1R but <+2R.

F6.18 D3 has **4**, not 5, exact overlaps with this F6.14 cohort. One of F6.18's five loss→positive conversions belongs to a parent loss that had a later existing 3-layer action, so it was not part of F6.14's untouched-25 cohort.

Therefore the exact F6.14 giveback remainder after D3 is:
- **21 total = 12 low (+0.5R–<1R) + 9 high (+1R–<2R).**

## 12 low givebacks: main mechanism
These trades reach +0.5R but never +1R. Their strongest stable separator is **failure to continue making progress**, not a special D3 candle.

At +35m after first +0.5R:
- median progress: **0.296R loss vs 0.516R winner controls**
- below EMA7 is materially more common in losses (AUC toward loss 0.719; Discovery 0.671, Validation 0.857)
- median last-bar taker: **-0.192 loss vs +0.030 controls**

At +65m:
- median progress: **0.086R loss vs 0.623R controls**
- retained fraction of best progress: **0.122 vs 0.613**
- median EMA7>EMA20 state: **0 for losses vs 1 for controls**
- below EMA20: loss-directed AUC **0.714 in full, Discovery, and Validation**
- median drawdown from best: **0.607R loss vs 0.356R controls**

Interpretation:
> +0.5R is achieved, but the move then fails to accelerate; progress decays, buyer flow weakens, EMA7 acceptance is lost, and by ~60m the deeper EMA20/EMA7 structure is often deteriorating.

The later rolling D3-like pattern is **not selective** for this cohort:
- low losses: 12/12 eventually show it
- comparable winner controls: 58/65 also eventually show it.
Thus merely waiting for a later D3-like candle after +0.5R is not a useful discriminator.

## 9 +1R D3 misses
Why frozen D3 misses them at its fixed decision time:
- **8/9:** no F6.16 P1 alert yet (`median taker<0 + below EMA7` is not present at the frozen +20m decision)
- **1/9:** P1 alert exists but strong-body confirmation is absent
- **0/9:** strong body exists but prior-low break alone is missing

So the dominant reason is **timing**: momentum death has not developed yet at the frozen post-+1R observation point.

A diagnostic rolling scan finds the same D3-like state later in **8/9** of these losses, median **47.5 minutes after +1R**. Seven of those eight hypothetical later exits are still positive, median cut PnL **+$1.381**.

However this later state is not rare among winners either:
- 42/54 comparable +1R winner controls eventually show the same rolling state
- 40/42 hypothetical winner-control cuts are still positive
- median winner-control cut PnL **+$2.310**.

Therefore the mechanism is real, but a naive `scan continuously and exit on first D3-like state` would likely truncate many eventual winners. This later rolling scan remains diagnostic only.

## F6.19 verdict
The remaining 21 givebacks are two different problems:

1. **12 partial-progress failures (+0.5R–<1R):** a slow failure-to-accelerate state, best visible by progress decay + flow weakening + EMA structure deterioration around 35–65m.
2. **9 +1R D3 misses:** mainly delayed momentum death; the D3-like pattern often appears later, but it is also common in winners, so later D3 alone is insufficient.

### Best next experiments
- For the 12 low cohort: predeclare a causal **failure-to-accelerate** state around the +0.5R milestone using progress retention + EMA7/EMA20 structure, without threshold sweeping.
- For the 9 high misses: study what distinguishes **later D3 that recovers** from **later D3 that continues failing**, rather than simply extending D3 monitoring indefinitely.

## Guardrail
F6.19 is forensic only. No later rolling scan or 35/65-minute observation is promoted as a trading rule. Any F6.20 action test must freeze its timing and conditions before observing management PnL.
