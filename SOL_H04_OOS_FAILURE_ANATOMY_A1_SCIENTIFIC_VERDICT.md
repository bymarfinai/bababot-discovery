# SOL H04 OOS Failure Anatomy A1 — Scientific Verdict

## Status

**SOL_H04_A1_PRE_ENTRY_REGIME_SHIFT_DOMINANT**

Preregistered interpretation label: **`PRE_ENTRY_REGIME_SHIFT_DOMINANT`**.

Research/shadow only. This is a failure-anatomy result, not a rescue filter, live promotion, or profit guarantee.

## Audit trail

- Branch: `sol-h04-oos-failure-anatomy-a1`.
- Result-bearing workflow run: **34694081271**.
- Job: **103554424449**.
- Result-bearing head SHA: **cb646ef748dc14275ec3f3e76434a421ad3b70d7**.
- Artifact ID: **10297703400**.
- Artifact digest: **sha256:504364446828a03a497ac321476d0c44c0d08deb98eef19e35009dd71205ae4f**.
- Persisted output commit: **16063ce0db9b6d890b1671b46e3864d1e1b9ef07**.
- Raw SOLUSDT 5m coverage: **99.7698%**.

The first workflow attempt failed only because Binance Vision reset a network connection during raw-data download. No research rule was changed. The identical preregistered engine was rerun successfully.

## Frozen setup under diagnosis

H04 / 11:00–12:00 WIB LONG only:

- Character: `EFF_LOW__RANGE_HIGH`.
- Lookback: 360 minutes.
- Hold: 240 minutes.
- Anchors: 11:00 / 11:15 / 11:30 / 11:45 WIB.
- Exact-open entry and exact-open time exit.
- $500 fixed notional and $0.75 round-trip fee.

No candidate, threshold, hold, anchor, TP, or SL was optimized in A1.

## Core finding

The dominant failure mechanism is **absolute-volatility / absolute-range compression before entry**, not excessive giveback from the frozen 240-minute exit.

The original H04 character uses a **causally normalized relative range percentile**. That percentile remained broadly stable in 2026, while the underlying absolute range collapsed. Therefore `RANGE_HIGH` in 2026 still meant “high versus the recent 60-observation local history,” but the whole recent market regime had become much quieter than the Development regime.

This creates a scale-regime failure: the relative character remains syntactically true while the absolute movement available to monetize the four-hour LONG hold is materially smaller.

## Evidence 1 — Relative range stayed stable while absolute range collapsed

| Diagnostic | Development | 2025 | 2026 | 2026 PSI vs Dev |
|---|---:|---:|---:|---:|
| Relative `range_pct` median | 0.8000 | 0.7833 | 0.7667 | 0.038 |
| Raw 360m range median | 5.14% | 4.21% | **3.53%** | **4.800** |
| Trailing 24h range median | 9.89% | 7.30% | **6.57%** | **0.929** |
| Trailing 72h range median | 18.27% | 12.85% | **11.04%** | **1.002** |

The relative percentile itself barely shifts, but the absolute 360m/24h/72h movement contracts strongly.

The Development-frozen raw 360m range terciles were approximately:

- LOW: <= **4.43%**
- MID: **4.43%–5.72%**
- HIGH: > **5.72%**

In 2026, **34 / 41 = 82.93%** of frozen H04 trades fell into the Development-defined LOW absolute-range tercile. For trailing 24h range, **32 / 41 = 78.05%** fell into the Development-defined LOW tercile. For trailing 72h range, **26 / 41 = 63.41%** were in the LOW tercile and only **1 / 41 = 2.44%** reached the Development-defined HIGH tercile.

This is a large composition shift, not a one-anchor anomaly.

## Evidence 2 — OOS failure concentrates in the compressed absolute-range states

### Raw 360m range — Reference Validation

| Dev-defined tercile | N | WR | Net | Exp | PF | DD |
|---|---:|---:|---:|---:|---:|---:|
| LOW | 59 | 47.46% | **-$128.32** | **-$2.17** | 0.492 | $152.20 |
| MID | 11 | 45.45% | -$2.06 | -$0.19 | 0.960 | $48.78 |
| HIGH | 14 | **71.43%** | **+$43.65** | **+$3.12** | **1.704** | $56.67 |

### Trailing 24h range — Reference Validation

| Dev-defined tercile | N | WR | Net | Exp | PF | DD |
|---|---:|---:|---:|---:|---:|---:|
| LOW | 56 | 46.43% | **-$136.94** | **-$2.45** | 0.459 | $160.82 |
| MID | 15 | 53.33% | -$1.24 | -$0.08 | 0.981 | $27.07 |
| HIGH | 13 | **69.23%** | **+$51.45** | **+$3.96** | **2.058** | $40.71 |

The same frozen H04 entry character remains economically strong in the relatively small number of Reference Validation observations that still resemble Development-scale absolute-range conditions. The economic collapse is concentrated where the local-relative `RANGE_HIGH` signal occurs inside an absolutely compressed market.

These tables are diagnostic evidence only. A1 does **not** authorize using the HIGH bins as a trading filter.

## Evidence 3 — Broader market context also shifted lower

The H04 cohort moved into a materially weaker broader context:

- 7-day return median: Development **+6.89%** -> Reference Validation **-4.86%** -> 2026 **-4.18%**.
- 7-day location median: Development **0.618** -> Reference Validation **0.295** -> 2026 **0.287**.
- PSI versus Development: 7-day return **0.258** for Reference Validation / **0.366** for 2026; 7-day location **0.390** / **0.310**.

This supports the interpretation that H04's locally choppy/high-relative-range condition was increasingly occurring within a quieter and lower-positioned broader market environment.

## Evidence 4 — The 240m exit is not the primary failure mechanism

| Cohort | N | WR | Net | PF | Median MFE | Median MAE | Median giveback |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development | 201 | 62.19% | +$580.75 | 1.861 | **1.91%** | -1.07% | **1.23%** |
| Reference Validation | 84 | 51.19% | -$86.72 | 0.763 | **1.24%** | -1.04% | **1.11%** |
| 2025 | 43 | 55.81% | +$28.83 | 1.184 | 1.58% | -0.75% | 1.25% |
| 2026 | 41 | 46.34% | -$115.56 | 0.448 | **1.02%** | -1.22% | **0.92%** |

The key deterioration is that trades receive **less favorable excursion at all**. Median giveback does not increase; it actually falls from 1.23% in Development to 0.92% in 2026. Median MAE is only moderately worse in 2026.

Therefore the evidence does **not** support “the four-hour hold is simply giving back too much profit” as the primary explanation. The available favorable movement itself shrinks under the compressed pre-entry regime.

## Evidence 5 — Not one broken quarter-hour anchor

Reference Validation is negative at every H04 quarter-hour anchor:

| WIB anchor | N | WR | Net | Exp | PF |
|---|---:|---:|---:|---:|---:|
| 11:00 | 23 | 56.52% | -$10.60 | -$0.46 | 0.856 |
| 11:15 | 15 | 46.67% | -$50.12 | -$3.34 | 0.462 |
| 11:30 | 20 | 50.00% | -$20.44 | -$1.02 | 0.782 |
| 11:45 | 26 | 50.00% | -$5.56 | -$0.21 | 0.947 |

The degradation is broad across the one-hour habitat, reinforcing a regime-level explanation rather than an isolated bad anchor.

## Scientific interpretation

**`PRE_ENTRY_REGIME_SHIFT_DOMINANT`** is the best-fitting preregistered label.

There is some post-entry deterioration, especially the fall in median MFE, but it is consistent with and downstream of the absolute-range compression already visible before entry. The giveback evidence specifically argues against an exit-timing/giveback mechanism being dominant.

The important discovery is therefore not “H04 was a false character.” A more precise statement is:

> H04's `EFF_LOW__RANGE_HIGH` character appears scale-sensitive. Its relative percentile normalization can continue labeling a state as high-range after the absolute SOL volatility regime has compressed enough that the original economic edge is no longer reliably available.

## Stop-rule outcome

A1 stops here.

- No absolute-range threshold is promoted.
- No Development tercile is converted into a live gate.
- No H04 threshold, lookback, hold, or anchor is changed.
- No second H04 Development passer is substituted.
- No TP/SL or early exit is tested.

The strongest next research question is a separately preregistered **secondary-confirmation experiment** asking whether an absolute-scale state variable can explain H04 validity without simply fitting the already exposed OOS failures. Such a test must be clearly labeled post-hoc/secondary confirmation and must not be reported as untouched OOS validation.
