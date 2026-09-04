# SOL LONG 15:00 UTC RC30_C2 Rescue Anatomy — A28 Preregistration

## Frozen subject
- Habitat R360/15.
- Parent A20 unchanged.
- Exact A27 `RC30_C2` trigger only: within 30m after a frozen parent loss exits, the second completed 5m close > H occurs before E40; re-entry would be next open.
- A27 itself is rejected; A28 is forensic only.

## Outcome labels (future-defined, anatomy only)
- `EPISODE_RESCUE`: parent PnL + RC30_C2 recovery PnL > 0.
- `RECOVERY_WIN_NOT_RESCUE`: recovery PnL >0 but combined episode <=0.
- `RECOVERY_FAIL`: recovery PnL <=0.
Primary comparison: `EPISODE_RESCUE` vs all `NON_RESCUE`.

## Fixed causal features observable by the RC30_C2 signal close
Parent path:
- parent loss magnitude / return
- parent MFE_R, MAE_R, hold minutes
- frozen loss class

Post-exit to signal:
- signal delay
- first reclaim delay
- gap first reclaim -> second reclaim signal
- whether the two closes >H are consecutive
- closes <=H before signal
- first reclaim close_R
- signal close_R
- max close_R to signal
- running MFE_R / MAE_R to signal
- giveback from post-exit max close to signal close
- signal bar body_R, upper/lower wick_R, close location in bar

## Replication
- Central Development describes the anatomy.
- Direction must replicate in Central External and Central RefVal.
- Secondary supports: R360/16 and R300/15, External + RefVal only.

## Support gate for A29
- Development rescue N >=40 and non-rescue N >=40.
- >=4 causal dimensions show non-zero rescue-vs-nonrescue Development separation and same direction in both Central External and RefVal.
- >=2 of those dimensions replicate in >=3/4 topology support cells.
- No profitability claim and no threshold optimization in A28.

If supported, A29 may preregister at most three small guards derived from robust A28 features. No OOS retuning.