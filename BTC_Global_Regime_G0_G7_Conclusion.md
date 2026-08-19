# BTC Global/Pooled Regime Research — G0 to G7 Conclusion

**Status: RESEARCH FAMILY CLOSED FOR TUESDAY MODIFICATION — keep telemetry, do not tune further on current sample.**

**Live BBC remains untouched.**

## Executive conclusion
The Global/Pooled Regime hypothesis produced one real positive result and one equally important negative result:

1. **YES — BTC market state is modestly predictable from pooled causal hourly data.**
   G1 passed every predeclared pooled pseudo-OOS gate.

2. **NO — on the current historical sample, that regime signal does not earn the right to modify the frozen Tuesday A5.11 strategy via entry gating or bounded risk sizing.**
   G1/G2/G3/G5/G6/G7 all failed their predeclared Tuesday economic/risk promotion gates, while G4 showed that frozen A5.11 outcome itself is not a learnable all-hours pooled target under the locked simple model.

The correct outcome is therefore **not** to tune thresholds, windows, sizing floors, or model complexity. Preserve the pooled regime model as diagnostic/shadow telemetry and return the Tuesday strategy to true forward/OOS observation.

---

## Frozen strategy anchor
Tuesday A5.11 remains unchanged:
- BTCUSDT
- Tuesday 06:00 WIB SELL
- TP 1.35%
- SL 0.80%
- max hold 6h
- A5.2 selective protection
- A5.9 FastMR
- A5.11 EMA7 runner recovery

Canonical historical anchor:
- 139 trades
- 89 wins / 50 losses
- WR 64.03%
- PnL +$130.33
- PF 1.692

G4 independently reproduced this with **zero trade-level PnL delta**, including A5.2=7, FastMR=12, recoveries=4.

August post-cutoff Tuesday observations remain:
- 2026-08-04: -$4.75
- 2026-08-11: -$0.82
- 2026-08-18: -$0.10
- total: -$5.68

---

## G0 — pooled market-state dataset
**Verdict: PASS**

Locked generic state label:
- 0.50% downside first in 6h => SELL_COMPATIBLE
- 0.50% upside first => BUY_COMPATIBLE
- neither / same-bar dual touch => NEUTRAL

Historical hourly states: **23,304**
- SELL_COMPATIBLE: 44.11%
- BUY_COMPATIBLE: 43.88%
- NEUTRAL: 12.01%

All dataset-integrity gates passed.

Historical Tuesday oracle-label distribution:
- SELL_COMPATIBLE: 62.59%
- BUY_COMPATIBLE: 33.81%
- NEUTRAL: 3.60%

August oracle labels:
- Aug 4: BUY_COMPATIBLE
- Aug 11: NEUTRAL
- Aug 18: NEUTRAL

Interpretation: pooled market-state construction is viable, and the August failures truly looked unlike a healthy Tuesday SELL development **after the fact**.

---

## G1 — embargoed pooled regime walk-forward
**Pooled verdict: PASS**  
**Tuesday hard-gate verdict: FAIL**

21,144 causal pseudo-OOS hourly predictions:
- accuracy: 46.17% vs causal prior 43.49%
- log loss: 0.907395 vs prior 0.985771
- Brier: 0.572877 vs prior 0.601950
- SELL-vs-rest AUC: 0.5690
- hard predicted SELL coverage: 34.14%
- actual SELL rate overall: 44.08%
- actual SELL rate when predicted SELL: 47.28%
- SELL enrichment: +3.21 pp
- model log loss beat causal prior in **4/4 chronological blocks**

Thus the pooled engine contains real but modest causal regime information.

Tuesday hard argmax-SELL gate on 126 causal opportunities:
- Always A5.11: WR 65.87%, +$150.89, PF 1.960, DD $20.91
- G1 gate: 40 trades, WR 77.50%, +$94.81, PF 4.287, DD $6.25
- PnL delta: -$56.08

August final frozen G1 model:
- Aug 4 => BUY_COMPATIBLE => WAIT
- Aug 11 => NEUTRAL => WAIT
- Aug 18 => NEUTRAL => WAIT

It correctly rejected all three August losses, but historical economics did not justify the hard gate.

---

## G2 — conflict-only veto
**Verdict: FAIL**

Policy:
- SELL => TRADE
- NEUTRAL => TRADE
- BUY => WAIT

Result:
- 43 trades
- WR 74.42%
- +$92.86
- PF 3.998

Crucial attribution:
- predicted SELL Tuesdays: +$94.81, $2.37/trade
- predicted NEUTRAL: -$1.96
- predicted BUY: **+$58.04, $0.70/trade**

Interpretation: global BUY conflict does not mean the Tuesday temporal SELL edge becomes negative. Hard veto remains too destructive.

---

## G3 — relative SELL-lift gate
**Verdict: FAIL**

Policy:
- SELL_LIFT = pSELL / causal training SELL prior
- TRADE iff SELL_LIFT >= 1.0

Result:
- 76 trades
- WR 65.79%
- +$91.96

Attribution:
- lift >=1: $1.2100/trade
- lift <1: $1.1787/trade

The point-in-time relative SELL probability barely discriminated Tuesday expectancy.

August: WAIT 3/3, but this did not rescue the weak historical discrimination.

---

## G4 — pooled A5.11 execution compatibility
**Verdict: FAIL; all-hours execution-aligned pooling hypothesis closed.**

The frozen A5.11 stack was hypothetically applied to all 23,304 hourly states.

Parity first:
- 139 Tuesday anchor reproduced exactly
- 89 wins
- +$130.328521
- A5.2=7 / FastMR=12 / recovery=4
- max trade-level delta vs canonical = 0

All-hours pooled A5.11 result:
- WIN rate: 40.59%
- aggregate hypothetical PnL: -$17,630.02

Embargoed pooled binary model:
- 21,144 pseudo-OOS predictions
- log loss 0.677453 vs prior 0.676520
- Brier 0.242167 vs prior 0.241727
- AUC 0.5117
- p>=0.50 coverage 0.73%

Interpretation: A5.11 is a **temporal strategy**, not a generic SELL engine. Its outcome is not usefully learnable by simply pooling every hour.

---

## G5 — point-in-time regime risk governor
**Verdict: FAIL**

Sizing:
`weight = min(1, pSELL / causal SELL prior)`

126 Tuesdays:
- baseline: +$150.89, $1.1976/exposure, DD $20.91, PnL/DD 7.216
- G5: +$146.33, $1.2064/exposure, DD $20.91, PnL/DD 6.997
- mean weight 0.963

Capital efficiency improved slightly, but full-sample drawdown did not improve and PnL/DD worsened.

---

## G6 — 168h weekly regime-health gate
**Verdict: FAIL as gate; useful diagnostic ranking.**

Weekly health:
`mean over prior 168h (pSELL - causal SELL prior)`

125 eligible Tuesdays:
- Always: WR 66.40%, +$155.64, $1.2452/opportunity, PF 2.021, DD $20.91
- Health>=0 gate: 55 trades, WR 69.09%, +$103.94, PF 2.483, DD $13.64

Outcome attribution:
- weekly health >=0: **$1.8899/trade**, WR 69.09%, PF 2.483
- weekly health <0: **$0.7386/trade**, WR 64.29%, PF 1.628

This is the clearest regime-quality ranking found in the family, but the hostile subset remains positive expectancy. A hard WAIT rule still throws away too much valid edge.

August weekly health:
- Aug 4: -0.04655 => WAIT
- Aug 11: -0.10538 => WAIT
- Aug 18: -0.12001 => WAIT

August was indeed deeply hostile under the slow regime measure.

---

## G7 — weekly-health risk governor
**Verdict: FAIL narrowly; do not retune.**

Sizing:
`weight = min(1, mean_pSELL_168h / mean causal SELL prior_168h)`

125 Tuesdays:
- Always: +$155.64, $1.2452/exposure, DD $20.91, PnL/DD 7.443
- G7: +$151.60, $1.2664/exposure, DD $20.44, PnL/DD 7.415
- mean weight: 0.958
- efficiency improved in 3/4 chronological blocks

G7 improved capital efficiency and slightly reduced DD, but failed the preregistered PnL/DD requirement. It is **not** promoted.

---

# What is now accepted

## KEEP
1. **Tuesday temporal prior** — historical edge remains strong.
2. **Frozen A5.11 management** — unchanged.
3. **G1 pooled regime model as diagnostic/shadow telemetry** — it demonstrated genuine causal pseudo-OOS state information.
4. **G6 weekly regime health as diagnostic/shadow telemetry** — it meaningfully ranks Tuesday quality and identified the August hostile state.

## REJECT as Tuesday production modifiers on current evidence
- Tuesday-only logistic TRADE/WAIT gate
- G1 hard pooled regime gate
- G2 conflict-only veto
- G3 relative SELL-lift gate
- G4 all-hours A5.11 pooled classifier
- G5 point risk governor
- G6 hard weekly-health gate
- G7 weekly-health sizing governor

## SHADOW ONLY
- August compression guard
- G1 current-state regime probabilities
- G6 168h weekly health

---

# Research guardrail from here
Do **not** run:
- G1 probability threshold sweeps
- alternative G3 SELL-lift thresholds
- G5/G7 sizing floors or nonlinear sizing
- G6 24h/72h/14d/30d lookback sweeps on this same sample
- XGBoost / Random Forest simply to force a pass
- A5.11 retuning to fit August

Those would convert the observed August anomaly into same-sample overfit.

---

# Recommended next step
## TRUE FORWARD SHADOW VALIDATION
The cleanest next milestone is no longer another historical filter.

Build a **separate Tuesday A5.11 shadow/telemetry runner** that does not touch BBC live orders and freezes all research rules. On each future Tuesday 06:00 WIB it should record before outcome is known:

1. frozen A5.11 paper/live-parity entry anchor,
2. G1 `pBUY / pNEUTRAL / pSELL`,
3. G6 prior-168h weekly SELL health,
4. G7 suggested diagnostic weight (telemetry only),
5. actual market/exchange-observable execution path,
6. A5.11 realized outcome after management closes.

No model or threshold should be refit between observations.

The purpose is to accumulate **pristine forward Tuesdays** and test whether the August hostile regime signal persists prospectively. Until then, the three August losses are an important warning, not enough evidence to overwrite a 139-trade frozen historical strategy.

A later decision to live-trade Tuesday A5.11 should be based on this forward evidence and live-parity execution, not further same-sample optimization.
