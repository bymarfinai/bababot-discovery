# BabaBot V2/V2.5 — FINAL RESEARCH CHECKPOINT

**Status:** CLOSED — EMA reclaim entry family exhausted  
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
- MFE/MAE ratio: neutral or slightly worse than Tier A

### Tier B — INACTIVE (separate bug)
- 0% activation across all pairs and all periods
- Likely cause: state-counter or condition conflict in developing-trend criteria
- Documented as separate implementation task; not part of the production conclusion

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
- Gross expectancy +$0.17 to +$0.29/trade — all below ~$0.75 fee/trade threshold

---

## 3. FORENSIC WINNER-VS-LOSER ANALYSIS (ADDENDUM)

### Feature Comparison
20 features measured at entry time across 12,902 entries (4 pairs × 971 days). Winner vs loser median comparison:

| Feature | Win Median | Loss Median | Lift | Verdict |
|---|---|---|---|---|
| fresh_cross (bool) | 37.4% | 36.8% | +0.58pp | noise |
| bars_regime | 4.0 | 3.5 | +0.50 | noise |
| dist_sl (ATR) | 2.35 | 2.28 | +0.07 | noise |
| cl_loc | 0.569 | 0.598 | -0.030 | noise |
| spread_atr | 0.053 | 0.053 | -0.000 | noise |
| e7_slope | 0.013 | 0.005 | +0.008 | noise |
| dist_e7 (ATR) | 0.404 | 0.409 | -0.005 | noise |
| vol_ratio | 0.734 | 0.750 | -0.017 | noise |

**No measured entry-time feature meaningfully separates winners from losers.** The largest lift (fresh_cross at +0.58pp) is statistically negligible. Winner and loser distributions are essentially identical across all 20 features.

### Quantile Analysis
Conditional WR by feature quartile (Q1→Q4): no monotonic relationship found for any feature across any pair. Q1-Q4 WR differences are ±5pp at best, inconsistent across pairs, and non-monotonic.

### EMA Hypotheses A–D (integrated one-position-per-pair)

| Hypothesis | Description | Trades | t/d/p | WR | Net | WF |
|---|---|---|---|---|---|---|
| A | EMA7 above EMA20 for BULL / below for BEAR | 4,713 | 1.21 | 51.3% | -$2,722 | 0/12 |
| B | Fresh EMA7/EMA20 cross within 12 bars | 1,743 | 0.45 | 52.6% | -$703 | 1/12 |
| C | EMA aligned + spread widening | 2,388 | 0.61 | 50.9% | -$1,466 | 1/12 |
| D | EMA aligned + spread > 0.3 ATR | 4,409 | 1.14 | 51.1% | -$2,650 | 0/12 |

**All four hypotheses are net negative out-of-sample.** EMA7/EMA20 alignment, fresh cross, spread widening, and combined filters do not separate winners from losers in walk-forward validation.

---

## 4. PROFITABILITY

### Frozen sweep (no position blocking)
- ETH: 16/144 configs net positive (best +$725, TP3.0/SL2.0 at 0.10% fee)
- BTC: 1/144 configs net positive
- SOL: 0/144 net positive
- BNB: 0/144 net positive
- No config net positive on 2+ pairs simultaneously

### Integrated one-position-per-pair
- All configs turn net negative after position blocking
- Wide TP/SL blocks 60–70% of subsequent entries
- Walk-forward: 0/3 folds positive for all integrated configs

### Coverage-preserving exit study
- Coverage and profitability are monotonically opposing constraints
- No configuration achieves both coverage ≥1.0/d/p AND net PnL > 0

### BNB
- Structurally negative: all configs, all folds, both BULL and BEAR
- MFE/MAE < 1.0 — incompatible with this strategy architecture

---

## 5. ACCEPTANCE CRITERIA — FINAL STATUS

| Criterion | Target | Result | Status |
|---|---|---|---|
| Coverage ≥ 1.0 trade/day/pair | 1.0/d/p | Achievable at 1.42/d/p with symmetric TP/SL | ✅ alone |
| Net PnL positive after fees | > $0 | All integrated configs negative | **FAIL** |
| Positive walk-forward expectancy | OOS positive | 0/12 folds positive on hypotheses | **FAIL** |
| Cross-pair robustness | 3+ pairs positive | No config positive on 2+ pairs | **FAIL** |
| No feature separates W/L | — | Confirmed: 0/20 features discriminative | **CONFIRMED** |
| WR 71% + PnL +$5,000 target | Combined | Not achieved | **FAIL** |

---

## 6. LOCKED CONCLUSIONS

1. **No measured entry-time feature meaningfully separates winners from losers.**
2. **EMA reclaim remains approximately 50–52% first-touch WR** regardless of filter or confirmation.
3. **EMA7/EMA20 alignment, fresh cross, spread widening, and combined filters are all net negative out-of-sample.**
4. **The EMA reclaim entry family is CLOSED for further tuning.** Do not run additional EMA, body-ratio, or TP/SL sweeps on this family.
5. **Live code is NOT modified.** No strategy enabled in production.

**V2/V2.5 regime detector is valid, but the EMA reclaim entry family is not tradable after fees and does not generalize out-of-sample.**

---

## 7. WHAT THIS CONCLUSION DOES NOT CLAIM

- Does NOT claim every possible strategy is impossible
- Does NOT claim the V2 regime detector is useless — it is a valid regime classifier
- Does NOT claim the data is insufficient — 971 days × 4 pairs is adequate
- Applies specifically to the 15m EMA reclaim/rejection entry family with fixed TP/SL and trailing exits within the BBC architecture

---

## 8. FUTURE RESEARCH — V3 HYPOTHESIS

The V2/V2.5 regime gate should be retained as a permission layer. A fundamentally different entry mechanism is required. Do not begin V3 implementation until the new hypothesis and causal rules are written explicitly.

**Candidate V3 approaches (each a separate experiment):**
- Market microstructure / order-flow: taker imbalance, open interest, liquidation cascades, funding rate
- Compression-breakout: price range compression followed by directional expansion
- Impulse / momentum ignition: large-volume bars initiating new directional moves
- Different timeframe: 5m or tick-level entries for tighter MFE/MAE
- Mean-reversion within regime: fade the pullback rather than follow the reclaim
- Cross-pair correlation: entry triggered by leader-pair momentum

Each V3 candidate must be evaluated against the same acceptance criteria (coverage, net PnL, walk-forward, cross-pair robustness) before any production integration.

---

## 9. FILES AND ENDPOINTS

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
| `v25_forensic_endpoint.py` | Forensic winner-vs-loser analysis | ✅ frozen |
| `BabaBot_V2_Checkpoint.md` | Earlier V2-only checkpoint | superseded |

**Live code:** NOT modified. No strategy enabled in production.
