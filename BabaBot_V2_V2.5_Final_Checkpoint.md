# BabaBot V2/V2.5 — FINAL RESEARCH CHECKPOINT

**Status:** FINAL CHECKPOINT — current BBC architecture  
**Date:** 2026-08-07  
**Scope:** 1H regime detector + causal 15m execution + EMA reclaim entry family  
**Data:** BTC, ETH, SOL, BNB — ~971 days (~23,000 1H candles per pair)  
**Fee tiers tested:** 0.10% and 0.15% round-trip  
**Validation:** first-touch TP/SL sequencing, one-position-per-pair integrated runs  

---

## 1. REGIME DETECTOR

### V2 Strict — VALID as regime classifier
- Architecture: REGIME (BULL/BEAR/SIDEWAYS) → PHASE (TREND/PULLBACK) → EVENT (CONTINUATION)
- BULL: 2 confirmed HH + 2 confirmed HL, ATR-scaled swings, EMA slope/alignment
- BEAR: 2 confirmed LH + 2 confirmed LL, symmetric
- Active ~15% of time, SIDEWAYS ~85%

**Validated metrics:**
- EMA hold lift: +12.7pp mean (range +9.1 to +15.0) across all 8 pair×side combos
- Protected swing survival: +5.3pp mean lift after reclaim event
- HH/LL base rate: 99%+ within regime (regime = directional permission gate)
- Fast transitions: controlled by hysteresis and minimum duration

### V2.5 Tier C — expands regime coverage
- Adds early-transition detection: ATR impulse + EMA alignment + confirmed pullback
- Active regime expands from ~15% to ~26% of time
- EMA hold: 83–87% (higher than Tier A's 56–60%)
- Coverage at symmetric TP/SL: 1.42 trades/day/pair (exceeds 1.0 target)
- MFE/MAE ratio: neutral or slightly worse than Tier A (not an improvement in entry precision)

### Tier B — INACTIVE (separate bug)
- 0% activation across all pairs and all periods
- Likely cause: state-counter or condition conflict in developing-trend criteria
- Documented as separate implementation task
- Not part of the production conclusion

---

## 2. ENTRY TRIGGER AUDIT

Six triggers tested on frozen A+C regime stream, all causal (decided at 15m candle close):

| Trigger | Description | Signals | t/d/p | MFE/MAE | TP-b4-SL | Gross E/t |
|---|---|---|---|---|---|---|
| A | Baseline 15m EMA reclaim | 16,662 | 4.29 | 1.051 | 51.9% | +$0.26 |
| B | A + break previous 15m high/low | 10,988 | 2.83 | 1.040 | 51.7% | +$0.23 |
| C | A + close-location + body-strength | 10,136 | 2.61 | 1.058 | 52.3% | +$0.29 |
| D | A + ATR/range expansion | 5,337 | 1.37 | 1.077 | 51.5% | +$0.19 |
| E | A + volume confirmation (1.5× avg) | 2,726 | 0.70 | 1.018 | 51.5% | +$0.21 |
| F | Pullback retest + structural breakout | 4,798 | 1.24 | 1.025 | 51.3% | +$0.17 |

**Findings:**
- TP-before-SL remains approximately 51–52% regardless of trigger
- MFE/MAE remains approximately 1.02–1.08 across all triggers
- Filters reduce trade count but do not materially improve first-touch quality
- Gross expectancy ranges +$0.17 to +$0.29/trade — all positive but all below the ~$0.75 fee/trade threshold
- The surviving entries after filtering are not better; there are simply fewer of them

**Per-pair pattern (consistent across all triggers):**
- ETH: gross positive, strongest MFE/MAE (~1.12–1.17)
- SOL: gross positive, moderate MFE/MAE (~1.03–1.08)
- BTC: gross near-zero, moderate MFE/MAE (~1.06–1.19)
- BNB: gross negative, MFE/MAE < 1.0

---

## 3. PROFITABILITY

### Frozen sweep (no position blocking)
- ETH: 16/144 configs net positive (best +$725, TP3.0/SL2.0 at 0.10% fee)
- BTC: 1/144 configs net positive
- SOL: 0/144 net positive
- BNB: 0/144 net positive
- No config net positive on 2+ pairs simultaneously

### Integrated one-position-per-pair
- All configs turn net negative after position blocking
- ETH best frozen +$725 → integrated -$355
- Wide TP/SL holds positions 40–70 bars, blocking 60–70% of subsequent entries
- Walk-forward: 0/3 folds positive for all integrated configs

### Coverage-preserving exit study
- Max hold 4×15m (60 min): coverage 1.45/d/p, net -$4,024
- Max hold 8×15m (120 min): coverage 1.04/d/p, net -$2,379
- Max hold 200×15m (unlimited): coverage 0.27/d/p, net -$14
- Coverage and profitability are monotonically opposing constraints
- No configuration achieves both coverage ≥1.0/d/p AND net PnL > 0

### BNB
- Structurally negative across all configurations, all folds, both BULL and BEAR
- MFE/MAE < 1.0 (price moves adversely more than favorably after entry)
- Documented as pair incompatible with this strategy architecture

---

## 4. ACCEPTANCE CRITERIA — FINAL STATUS

| Criterion | Target | Result | Status |
|---|---|---|---|
| Coverage ≥ 1.0 trade/day/pair | 1.0/d/p | Achievable at 1.42/d/p with symmetric TP/SL | ✅ alone |
| Net PnL positive after fees | > $0 | All integrated configs negative | **FAIL** |
| Positive walk-forward expectancy | OOS positive | 0/3 folds positive on integrated | **FAIL** |
| Cross-pair robustness | 3+ pairs positive | Only ETH shows frozen promise; 0 in integrated | **FAIL** |
| WR 71% + PnL +$5,000 | Combined | Not achieved | **FAIL** |
| Coverage AND profitability simultaneously | Both met | Structurally conflicting | **FAIL** |

---

## 5. CONCLUSION

**The current 1H V2/V2.5 regime detector is valid as a regime classifier, but the 15m EMA reclaim/rejection entry family does not provide sufficient directional precision to overcome trading costs. Adding filters, changing fixed TP/SL, or expanding the same regime family does not solve the problem.**

The regime correctly identifies trending environments with +12.7pp EMA hold lift and 99%+ HH/LL accuracy. The entry timing (15m EMA reclaim) produces MFE slightly above MAE (ratio ~1.05), indicating a marginal directional edge exists. However, this edge is insufficient to overcome the 0.10–0.15% round-trip trading cost at any TP/SL configuration.

The fundamental bottleneck is not the regime detector, not the coverage, and not the exit method — it is the entry trigger's directional precision (MFE/MAE ≈ 1.05 across all tested variants).

---

## 6. WHAT THIS CONCLUSION DOES NOT CLAIM

- This does NOT claim that every possible strategy is impossible
- This does NOT claim the V2 regime detector is useless — it is a valid regime classifier
- This does NOT claim the data is insufficient — 971 days × 4 pairs is adequate for this analysis
- This conclusion applies specifically to:
  - The current 15m EMA reclaim/rejection entry family
  - Fixed TP/SL and trailing exit methods
  - The BBC architecture as currently designed

---

## 7. FUTURE RESEARCH — V3 HYPOTHESIS

A fundamentally different entry mechanism is required. The V2/V2.5 regime gate should be retained as a permission layer. Candidate V3 approaches (separate experiments, not tuning of V2):

- **Impulse/breakout model:** entry on confirmed structural break rather than EMA touch
- **Order-flow data:** liquidation cascades, funding rate shifts, open interest changes
- **Different timeframe:** 5m or tick-level entries for tighter MFE/MAE
- **Mean-reversion within regime:** fade the pullback rather than follow the reclaim
- **Machine learning directional classifier:** trained on regime-conditioned features
- **Cross-pair correlation:** entry triggered by leader-pair momentum

Each V3 candidate must be evaluated independently against the same acceptance criteria before any production integration.

---

## 8. FILES AND ENDPOINTS

| File | Purpose | Status |
|---|---|---|
| `continuation_detector_endpoint.py` | V2 three-layer detector | ✅ frozen |
| `v2_audit_endpoint.py` | Matched control audit | ✅ frozen |
| `v2_gated_endpoint.py` | V2 regime gate integration | ✅ frozen |
| `v2_excursion_endpoint.py` | 15m execution + entry matrix | ✅ frozen |
| `v2_m15_sweep_endpoint.py` | Frozen TP/SL sweep | ✅ frozen |
| `v2_m15_hold_endpoint.py` | Coverage-preserving exit study | ✅ frozen |
| `v25_detector_endpoint.py` | V2.5 tiered regime | ✅ frozen |
| `v25_sweep_endpoint.py` | V2.5 TP/SL sweep | ✅ frozen |
| `v25_triggers_endpoint.py` | Phase 3 entry trigger comparison | ✅ frozen |
| `BabaBot_V2_Checkpoint.md` | Earlier V2-only checkpoint | superseded by this document |

**Live code:** NOT modified. No strategy enabled in production.
