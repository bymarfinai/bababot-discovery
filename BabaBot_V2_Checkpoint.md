# BabaBot V2 Checkpoint — Frozen Results

## Status: CHECKPOINT (not final SSOT)

## Architecture
- V2 Continuation Detector: 3-layer (REGIME → PHASE → EVENT)
- BULL: 2 HH + 2 HL, ATR-scaled swings, EMA slope/alignment
- BEAR: 2 LH + 2 LL, symmetric
- SIDEWAYS: default (~85% of time)
- Full Switcher: state machine execution engine
- Integration: Mode B = V2 regime gate on Full Switcher entries

## Key Findings

### V2 Regime Detector — VALID
- EMA hold lift: +12.7pp mean (range +9.1 to +15.0) across all 8 pair×side combos
- Protected swing survival: +5.3pp mean lift after reclaim
- BULL/BEAR HH/LL base rate: 99%+ in regime (regime = directional permission)
- Event reclaim adds quality timing, not HH/LL prediction

### Coverage vs Profitability — CONFLICTING CONSTRAINTS
| Max Hold | Coverage | Best Net | Status |
|---|---|---|---|
| 4×15m (60min) | 1.45/d/p ✅ | -$4,024 | ❌ |
| 8×15m (120min) | 1.04/d/p ✅ | -$2,379 | ❌ |
| 200×15m (unlimited) | 0.27/d/p | -$14 | ≈ breakeven |

**No configuration achieves BOTH coverage ≥1.0/day/pair AND net PnL > 0.**

### 15m Execution Layer
- MFE > MAE at 15m entry: SOL 1.34/1.12 (1.20), ETH 1.34/1.10 (1.22)
- Fixes the MFE≈MAE problem from 1H entry
- Coverage: 2.01/day/pair with symmetric TP/SL
- Gross positive: +$2,590 aggregate, but fee drain -$5,847

### Per-Pair Best (wide TP, long hold)
| Pair | Config | Trades | Net | WF |
|---|---|---|---|---|
| SOL | TP3.0/SL2.5 | 345 | +$137 | 2/3 |
| ETH | TP3.0/SL1.3 | 415 | +$116 | 2/3 |
| BTC | TP2.5/SL2.5 | 214 | +$156 | 3/3 ✅ |
| BNB | ALL configs | ALL | NEGATIVE | 0/3 ❌ |

### BNB
Structurally incompatible. ALL configs, ALL folds, BOTH sides negative.
Documented as pair not suitable for this strategy architecture.

## Files
| File | Purpose |
|---|---|
| continuation_detector_endpoint.py | V2 three-layer detector |
| v2_audit_endpoint.py | Matched control audit |
| v2_gated_endpoint.py | V2 regime gate integration |
| v2_excursion_endpoint.py | 15m execution + entry matrix |
| v2_m15_sweep_endpoint.py | Frozen TP/SL sweep |
| v2_m15_hold_endpoint.py | Coverage-preserving exit study |

## Rules
- DO NOT modify mode3_bbc/config.py or mode3_bbc/switcher.py
- DO NOT deploy to live
- V2 detector FROZEN — no parameter changes
- This is discovery, not validated strategy
