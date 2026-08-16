# BTC Temporal Friday16 — A6.34 Independent Discovery Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** REJECT AS STANDALONE SLOT FOR NOW  
**Symbol:** BTCUSDT  
**Entry:** every Friday exact 16:00 WIB 5m open  
**Sample:** 138 Fridays; first82 discovery / last56 validation  
**Live BBC:** untouched

## Purpose

Test Friday16 independently, without copying Friday15 entry or management. Phase 1 measured raw BUY vs SELL direction at 30/60/120/240/360m. Phase 2 swept the same executable BUY money geometry used in Friday15 A6.0: $500 notional, 0.15% roundtrip fee, adverse-first same-5m TP/SL, TP 0.3–2.0%, SL 0.3–1.4%, hold 120–720m.

## Raw direction

Friday16 BUY shows an attractive full-sample headline but severe chronological decay.

| Horizon | Full WR | Full avg signed | Discovery WR | Discovery avg | Validation WR | Validation avg |
|---|---:|---:|---:|---:|---:|---:|
| 30m | 55.80% | +0.0670% | 59.76% | +0.0975% | 50.00% | +0.0223% |
| 60m | 57.25% | +0.0667% | 62.20% | +0.1435% | 50.00% | -0.0458% |
| 120m | **64.49%** | +0.0899% | **73.17%** | +0.2057% | **51.79%** | **-0.0796%** |
| 240m | 60.14% | +0.1383% | 68.29% | +0.2976% | 48.21% | -0.0950% |
| 360m | 55.07% | +0.1033% | 62.20% | +0.3058% | 44.64% | -0.1931% |

Validation MFE/MAE also loses the directional asymmetry: at 60m ratio ~0.98, 120m ~1.04, 240m ~1.05, 360m ~0.99. SELL becomes roughly neutral/slightly favorable in later validation horizons, which indicates regime change rather than a stable fixed BUY edge.

## Executable money geometry

Tested **1,152 BUY configurations**.

Key result:

- **0 configurations** have positive PnL in both discovery and validation.
- **0 stable cross-period configurations**.

Best full-sample net config:
- TP 1.2%
- SL 0.8%
- max hold 720m
- N138
- WR 50.00%
- full net **+$31.338**
- PF 1.103
- max DD $67.184
- 4/8 positive blocks
- discovery **+$79.914**, WR57.32%, PF1.534
- validation **-$48.576**, WR39.29%, PF0.686

High-WR example:
- TP0.6 / SL0.9 / 720m
- WR70.29%
- full net only **+$4.913**
- discovery +$30.713
- validation **-$25.800**

Thus the high headline WR is not economically robust after fees and chronology.

## Verdict

Friday16 should **not** be promoted as an additional standalone weekly slot on this sample.

The full-sample raw 120m BUY WR of 64.49% is misleading because discovery was 73.17% while validation fell to 51.79% with negative average signed return. The executable sweep confirms the deterioration: no configuration survives both chronological halves.

Do **not** transfer Friday15 EMA45 damage-control or other management onto Friday16 yet. Management should not be used to rescue a temporal prior that fails cross-period robustness.

Next legitimate exploration, if continuing the Friday cluster, is Friday17 as an independent slot. Another useful later question is whether 16:00/17:00 can act as a conditional re-entry or continuation window **after observing the outcome/state of Friday15**, rather than as unconditional standalone entries.
