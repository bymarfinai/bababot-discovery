# SOL LONG 15UTC Parent Pre-Range Anatomy — A45 Result

A45 keeps the A20 `R360/15` E0/E40 parent frozen and uses only the 72 completed 5m candles in the 09:00–15:00 UTC reference range.

Raw SOLUSDT 5m coverage: **99.7671%**.
A20 count reconciliation: **True**. H/L/R + 72-bar reference reconciliation: **True**. Enriched rows: **1219/1219**.

## Frozen parent economics

| Partition | N | WR | PF | Net | 5bps WR | 5bps PF | 5bps Net |
|---|---:|---:|---:|---:|---:|---:|---:|
| development | 601 | 40.6% | 1.28 | $338.91 | 40.3% | 1.14 | $188.66 |
| external | 281 | 40.9% | 1.55 | $419.82 | 40.6% | 1.43 | $349.57 |
| reference_validation | 337 | 44.5% | 1.57 | $263.33 | 43.9% | 1.35 | $179.08 |

## Replicated decision-time separators

| Feature | Dev gap | Dev effect | Dev block sign | External gap/effect | RefVal gap/effect |
|---|---:|---:|---:|---:|---:|
| none | - | - | - | - | - |

## Strongest Development effects (diagnostic)

These are not promoted unless `replicated_directional=True`.

| Feature | Dev effect | Dev block sign | External effect/sign | RefVal effect/sign | Replicated |
|---|---:|---:|---:|---:|---:|
| realized_close_path_R | 0.252 | 5/6 | 0.148/+1 | 0.078/+1 | NO |
| mean_bar_range_R | 0.234 | 5/6 | 0.240/+1 | 0.116/+1 | NO |
| first_half_range_fraction | 0.188 | 4/6 | 0.193/-1 | 0.047/-1 | NO |
| range_width_pct | 0.177 | 4/6 | 0.242/-1 | 0.042/-1 | NO |
| low_time_fraction | 0.161 | 4/6 | 0.103/+1 | 0.173/+1 | NO |
| open_location_R | 0.161 | 4/6 | 0.185/-1 | 0.158/-1 | NO |
| first_half_return_R | 0.127 | 5/6 | 0.010/+1 | 0.038/-1 | NO |
| signed_path_efficiency | 0.086 | 6/6 | 0.218/+1 | 0.094/-1 | NO |

## Decision

**Status: SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_INCONCLUSIVE**

No frozen pre-range feature met the preregistered Development stability + dual-OOS replication rule. Do not invent a 15UTC parent filter from weak or one-pool effects.

Research only. Live Baba Bot remains unchanged.
