# BTC Temporal Friday17 — A6.35 Independent Discovery Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** REJECT AS STANDALONE SLOT  
**Symbol:** BTCUSDT  
**Entry:** every Friday exact 17:00 WIB 5m open  
**Sample:** 138 Fridays; first82 discovery / last56 validation  
**Live BBC:** untouched

## Purpose

Test Friday17 independently, without reusing Friday15/16 entry or management. Phase 1 measured raw BUY vs SELL at 30/60/120/240/360m. Phase 2 swept the same executable BUY money geometry used in Friday15/16: $500 notional, 0.15% roundtrip fee, adverse-first same-5m TP/SL, TP0.3–2.0%, SL0.3–1.4%, hold120–720m.

## Raw BUY direction

| Horizon | Full WR | Full avg signed | Discovery WR | Discovery avg | Validation WR | Validation avg |
|---|---:|---:|---:|---:|---:|---:|
| 30m | 52.90% | -0.0136% | 56.10% | +0.0060% | 48.21% | -0.0424% |
| 60m | 60.14% | +0.0233% | 63.41% | +0.0623% | 55.36% | -0.0339% |
| 120m | **62.32%** | +0.0592% | 65.85% | +0.1089% | **57.14%** | **-0.0136%** |
| 240m | 56.52% | +0.1278% | 62.20% | +0.2793% | 48.21% | -0.0941% |
| 360m | 44.93% | -0.0031% | 47.56% | +0.1031% | 41.07% | -0.1586% |

The raw 120m headline remains directionally positive, but average signed return is already negative in validation. At 240/360m the validation edge clearly decays further.

## Executable money geometry

Tested **1,152 BUY configurations**.

Key result:

- **0 configurations** profitable in both discovery and validation.
- **0 stable cross-period configurations**.
- **0 full-sample profitable configurations**.

Best full-sample net config was still negative:
- TP1.6%
- SL0.7%
- max hold720m
- N138
- WR35.51%
- net **-$36.089**
- PF0.898
- max DD $84.487
- only2/8 positive blocks
- discovery +$27.155
- validation **-$63.244**

Thus Friday17 is weaker than Friday16 economically. Even though raw directional WR can exceed 60% around 60–120m, the magnitude is insufficient to overcome fees/losing tails with tested executable geometry.

## Verdict

Friday17 should **not** be promoted as an unconditional standalone weekly slot.

Do not transfer Friday15 EMA45 damage-control or other management onto Friday17. The appropriate next research direction for the Friday cluster is no longer unconditional 16:00/17:00 entries. If explored further, 16:00/17:00 should be treated only as **conditional continuation/re-entry windows after observing the realized state/path of the Friday15 trade**, while preserving one-position-per-pair execution constraints.
