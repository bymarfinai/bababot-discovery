# B27CH — BTC 24H F05 Reclaim SHORT Controlled-Loss Economics — Preregistration

## Purpose
Test the B27CF best observed post-reclaim entry geometry as an actual SHORT trade while explicitly controlling loss. This is a separately preregistered economic test. It does not alter B27CF/B27CG anatomy.

User constraint: nominal reward:risk must be at least 1:1.

## Frozen source cohort
Source: persisted `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`.

Include only major partitions and `eligible == True`.
Identity must reproduce exactly:
- external 202
- development 333
- reference_validation 194
- pooled OOS 396
- pooled major 729.

No regime, weekday, session, or clock exclusion may alter the cohort.

## Frozen post-reclaim entry
For each row:
- `L` = previous completed 4H Low.
- `H` = previous completed 4H High.
- `R4 = H-L`.
- F05 sell-limit = `L + 0.05*R4`.
- hard invalidation F25 = `L + 0.25*R4`.
- evaluation starts at the first raw 5m bar after reclaim confirmation (`reclaim_complete_ts`) and ends at the same 4H block end.

Before fill:
1. if a completed 5m close `< L` occurs before fill, cancel the order (`REBREAK_BEFORE_FILL`);
2. if a completed 5m close `> H` occurs before fill, cancel the order (`HIGH_BREAK_BEFORE_FILL`);
3. if a bar opens at or above F25 before entry, cancel (`INVALIDATED_BEFORE_FILL`);
4. otherwise a sell-limit fills on the first bar with `high >= F05`.

Execution price for a filled sell-limit is causal/marketable:
- if that bar opens below F05, fill at F05;
- if it opens at/above F05 but below F25, fill at that bar open.
No extra favorable price improvement beyond the observed bar open is assumed.

Initial hard stop is always F25. Actual initial risk is `F25 - fill_price`, which must be positive.

## Frozen loss control
After fill, while no completed 5m close `< L` has yet confirmed a Low rebreak:
- count consecutive completed post-entry bars with `close > L`;
- after two consecutive such closes, exit at the second bar close (`EARLY_HOLD_EXIT`) if neither stop nor target executed earlier in that bar.

This is the frozen 10-minute persistence defense derived from the preregistered B27CG candidate set. No +25% R4 discriminator is used as a separate discretionary filter because F25 is already the hard invalidation/stop.

A completed close `< L` confirms rebreak and permanently ends the early-hold rule for that trade.

## Frozen six variants
All variants share the exact same entry and initial F25 hard stop.

Targets use actual entry risk, preserving true nominal RR even when the marketable sell-limit fills above F05:
- `target = fill_price - TP_MULTIPLE * (F25 - fill_price)`.

Variants:
- `A_R1`: TP 1.0R; hard stop stays F25.
- `A_R1_5`: TP 1.5R; hard stop stays F25.
- `A_R2`: TP 2.0R; hard stop stays F25.
- `B_R1_BE`: TP 1.0R; after confirmed Low rebreak, move stop to entry beginning on the next 5m bar.
- `B_R1_5_BE`: TP 1.5R; same break-even rule.
- `B_R2_BE`: TP 2.0R; same break-even rule.

Break-even is never active on the rebreak-confirmation bar itself.

## Intrabar chronology / conservative ambiguity
On the fill bar:
- if the bar reaches F25 after/around fill, record STOP conservatively;
- same-fill-bar target is not credited because OHLC cannot establish target-after-fill ordering;
- the fill-bar close may establish the first `close > L` hold count or confirm Low rebreak.

On later bars:
1. if bar open is beyond the active stop, exit at open;
2. if bar open is beyond the target in the favorable direction, exit at open unless the active stop is also violated at open;
3. if both stop and target are touched within the same 5m bar, STOP wins conservatively;
4. otherwise execute STOP or TP at the frozen price;
5. only if neither executes, evaluate the completed close for Low-rebreak confirmation or the two-close early-hold exit.

If still open at block end, exit at the final raw 5m close (`TIME`).

## Economics
Illustrative fixed notional: **$500 per trade**.
Round-trip fee: **$0.40 per trade**.
No additional slippage assumption.

SHORT gross return = `(entry_price - exit_price) / entry_price`.
Net PnL USD = `gross_return*500 - 0.40`.
Trading win iff net PnL > 0.

## Required metrics
For every variant report separately:
- external / development / reference_validation;
- pooled OOS = external + reference_validation;
- pooled major;
- every one of the six UTC 4H clock blocks for pooled OOS and pooled major.

Metrics:
- source N, fills/trades N, fill rate;
- WR;
- PF;
- expectancy/trade;
- total net PnL;
- average win and average loss;
- maximum drawdown in chronological trade order;
- maximum consecutive losing trades;
- TP / hard-stop / early-hold / break-even / TIME counts;
- median initial risk % and median hold minutes.

No clock may be removed to rescue a result.

## Frozen development-only optimization
Optimization is done only on development after all six variants are frozen.

A variant is development-eligible only if:
- development trades >=150;
- development net expectancy >0;
- development PF >=1.10;
- development total net PnL >0.

If no variant is eligible, no candidate is selected.

If one or more are eligible:
1. find the highest development total net PnL among eligible variants;
2. retain variants with development total net PnL >=80% of that maximum (profit floor);
3. among that retained set, select the highest `total_net_pnl / max_drawdown` ratio;
4. tie-break by higher development PF, then lower maximum consecutive losses, then higher nominal target RR.

This deliberately seeks near-top development profit while controlling drawdown rather than maximizing WR alone.

## Frozen robustness gate for selected candidate
A selected candidate is `ROBUST_PASS` only if all:
- exact source and raw-data audit passes;
- external trades >=80, development >=150, validation >=80;
- expectancy >0 in each major partition;
- PF >=1.20 in each major partition;
- pooled-OOS expectancy >0 and PF >=1.20;
- no post-hoc clock/regime/weekday exclusion.

`HIGH_QUALITY_70` is reported separately and requires trading WR >=70% in external, development, and validation for the same selected variant.

Frozen verdict labels:
- `B27CH_CONTROLLED_LOSS_ECON_SUPPORTED`
- `B27CH_CONTROLLED_LOSS_ECON_NOT_SUPPORTED`
- `B27CH_NO_DEVELOPMENT_CANDIDATE`

Research only. No live BBC change follows automatically.