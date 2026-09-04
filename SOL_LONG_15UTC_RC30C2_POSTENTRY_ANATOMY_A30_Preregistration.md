# SOL LONG 15:00 UTC RC30_C2 Post-Entry Anatomy — A30 Preregistration

## Frozen subject
- Habitat R360/15.
- Parent A20 unchanged.
- Exact unguarded A27 `RC30_C2` trigger and next-open re-entry only.
- A27 and A29 remain rejected. A30 is forensic only.

## Objective
Explain why RC30_C2 raises episode WR materially but still dilutes overlay PF. Determine whether the next loss->win improvement should come from target geometry, re-entry geometry, or failure lifecycle.

## Future-defined outcome classes
- `REC_TARGET`: recovery exits at E40 target.
- `REC_POSITIVE_OTHER`: recovery PnL >0 without E40 target.
- `REC_FAIL`: recovery PnL <=0.
These labels are anatomy-only.

## Fixed entry geometry
At the causal next-open re-entry:
- entry_R = (entry-H)/R
- remaining reward to E40 = 0.40-entry_R
- distance to H = entry_R
- nominal E40 reward / H-risk ratio
- parent loss dollars and R-equivalent breakeven recovery requirement

## Fixed post-entry path anatomy
For each RC30_C2 recovery:
- final recovery PnL / exit reason / hold time
- path MFE and MAE from re-entry to frozen recovery exit
- max price_R and min price_R
- whether E10/E20/E30/E40 were touched before frozen recovery exit
- first-touch minutes for E10/E20/E30/E40
- whether a fixed E10/E20/E30 target, if filled causally before the frozen exit, would be sufficient to rescue the combined parent episode after accounting for the actual re-entry price
- failure-close overshoot below H and next-open slippage below H for `FAILED_RECLAIM`

Fixed completed snapshots after re-entry: +5/+10/+15/+30/+60m:
- close_R
- running MFE_R
- running MAE_R
- closes above H
- closes <=H

## Replication
- Central Development anatomy.
- Directional replication in Central External and Central RefVal.
- Secondary supports: R360/16 and R300/15, External + RefVal.

## Decision grammar
A30 may authorize A31 only if one intervention family is clearly indicated without threshold mining:
- **Target route:** a fixed E10/E20/E30 level is touched by a material share of RC30_C2 failures and would rescue a material share of their parent episodes.
- **Entry route:** entry_R/reward-risk separation is robustly different between winners and failures across central OOS.
- **Lifecycle route:** failure overshoot/giveback anatomy shows recoveries are lost mainly after a replicated path state rather than because E40 is unreachable.

No economics are modified in A30. No OOS tuning. Research only; live Baba Bot unchanged.