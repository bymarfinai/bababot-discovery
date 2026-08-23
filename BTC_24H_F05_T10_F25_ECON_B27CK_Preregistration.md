# B27CK — BTC 24H F05 Entry / T10 TP / F25 SL Economics — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test exactly one user-requested SHORT configuration on the existing B27CE/B27CF reclaim lineage:
- entry candidate: `F05 = L + 0.05*R4`
- fixed TP: `T10 = L - 0.10*R4`
- fixed SL: `F25 = L + 0.25*R4`

This is an economic diagnostic only. It intentionally tests a nominal F05 geometry of reward 0.15*R4 versus risk 0.20*R4, i.e. **RR 0.75:1**, below the user's previously frozen >=1:1 requirement. Therefore B27CK cannot be promoted as a final production candidate even if profitable; the purpose is to learn the actual WR/economics of this exact SL hypothesis.

## Frozen source cohort
Source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`.
Use only major partitions with `eligible == True`.
Expected source identity:
- external 202
- development 333
- reference_validation 194
- pooled OOS 396
- pooled major 729.

No clock, regime, weekday, or partition exclusion.

## Frozen entry semantics
For each event:
- `R4 = H-L`
- sell-limit F05 = `L + 0.05*R4`
- SL F25 = `L + 0.25*R4`
- TP T10 = `L - 0.10*R4`
- evaluation starts at `reclaim_complete_ts` and ends at the same 4H `obs_end`.

Before fill, preserve B27CH causal execution semantics:
1. if bar open >= F25, cancel as `INVALIDATED_BEFORE_FILL`;
2. otherwise, if bar high >= F05, fill the SHORT;
3. fill price = F05 if bar open < F05, otherwise actual bar open, provided open < F25;
4. if no fill occurred, a completed close < L cancels as `REBREAK_BEFORE_FILL`;
5. if no fill occurred, a completed close > H cancels as `HIGH_BREAK_BEFORE_FILL`;
6. otherwise pending until block end.

No early-hold exit, no breakeven, no hybrid runner, no discretionary confirmation filter.

## Frozen post-fill execution
- TP is always the structural `T10 = L - 0.10*R4`, independent of actual marketable fill improvement.
- SL is always F25.
- On the fill bar, if F25 is touched, STOP wins conservatively; same-fill-bar TP is not credited because OHLC cannot prove target-after-fill ordering.
- On later bars:
  1. if open >= SL, exit at actual open;
  2. else if open <= TP, exit at actual open;
  3. if both SL and TP are touched intrabar, SL wins conservatively;
  4. otherwise execute whichever single boundary is touched;
- If unresolved at block end, exit at the final available raw 5m close before `obs_end`.

No additional slippage assumption.

## Economics
- fixed illustrative notional: $500/trade
- round-trip fee: $0.40/trade
- SHORT gross return = `(entry - exit) / entry`
- net PnL = `gross_return*500 - 0.40`
- trading win iff net PnL > 0.

Report actual reward/risk using actual fill price because marketable fills above F05 improve both reward and risk geometry.

## Required metrics
For external, development, validation, pooled OOS, pooled major, and each six UTC 4H clocks (clock rows first in user-facing interpretation):
- source N
- fills/trades N and fill rate
- TP / SL / TIME counts
- WR
- PF
- expectancy/trade
- total net PnL
- average win / average loss
- max drawdown
- max consecutive losses
- median hold minutes
- median actual reward:risk.

## Frozen diagnostic interpretation
`B27CK_DIAGNOSTIC_POSITIVE_ALL_MAJOR` only if expectancy >0 and PF >1.0 in external, development, and reference_validation, plus pooled OOS expectancy >0 and PF >1.0.
Otherwise: `B27CK_DIAGNOSTIC_MIXED_OR_NEGATIVE`.

This diagnostic label does not override the explicit RR<1 caveat and does not authorize live deployment.

Research only. Live BBC unchanged.
