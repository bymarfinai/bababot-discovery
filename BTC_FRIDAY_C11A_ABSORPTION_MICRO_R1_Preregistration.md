# BTC Friday C11A True Absorption Microstructure R1 — Preregistration

**Protocol:** `C11A_MICRO_R1`  
**Status:** FROZEN BEFORE MICROSTRUCTURE RESULT  
**Historical C11A result:** preserved; not overwritten.  
**Live BBC:** untouched.

## Research question

Did the historical C11A aggregate-flow `absorption` events actually contain true passive-side L2 absorption, and can that true microstructure distinguish the winners from the many losers of the frozen C11A event set?

C11A historically inferred absorption when aggressive-flow direction failed to move price in the same direction over the final 5 minutes of a Friday 15m candle. That result remains a valid rejection of the frozen 1m/5m aggregate-flow identifier. R1 tests whether actual passive book replenishment/depletion adds information inside those same events.

## Frozen candidate universe

Reuse the historical C11A event rows from:

`BTC_Friday_C11A_1m_Absorption_Rows.csv`

No new Friday candle may enter R1. This is intentionally a confirmation study on the previously frozen 141 aggregate-proxy events, not a fresh search over all Friday candles.

Required frozen fields:
- `signal_ts`, `entry_ts`, `friday_wib`, `period`, `direction`;
- original event-side orientation;
- original outcome/economics.

Historical C11A candidate construction and labels are not changed.

## Frozen split

Reuse C11A:
- first 70% of unique Friday dates = discovery/development;
- last 30% = validation.

R1 does not repartition after CoinDesk outcomes are inspected.

## Data window

For every frozen event:
- feature end `T = entry_ts`;
- primary microstructure window = final 5m of the frozen signal 15m candle, matching C11A;
- context L2/tick window = `[T-15m,T)`;
- no message timestamp >=T may enter an entry feature.

L2 replay requested depth is fixed at 1000 levels.

## True absorption orientation

### Historical `SELLER_ABSORPTION_LONG`
The old event had net aggressive selling while price failed to move lower. R1 tests whether this is accompanied by passive **bid-side** persistence/replenishment.

Mechanism evidence includes:
- negative tick-level signed trade delta;
- bid quantity repeatedly replenished after execution/removal;
- bid-side depth does not collapse despite sell aggression;
- limited downside price progress per unit sell delta;
- optional OI change as context.

### Historical `BUYER_ABSORPTION_SHORT`
Mirrored:
- positive tick-level signed trade delta;
- ask quantity repeatedly replenished;
- ask-side depth does not collapse despite buy aggression;
- limited upside price progress per unit buy delta.

These are orientation rules only. No outcome-derived magnitude threshold is introduced.

## Frozen features

### Tick flow over final 5m, final 60s, and full 15m
- BUY/SELL aggressive base and quote volume;
- signed quote delta / delta ratio;
- trade count;
- price return;
- price-per-delta efficiency;
- top-5%-trade concentration;
- liquidation count/quote when supplied.

### L2
At 15m start, final-5m start, and entry-nearest state when reconstructable:
- spread;
- bid/ask depth at 5/10/25 bps;
- signed depth imbalance;
- cumulative bid/ask added and removed quantity;
- replenishment ratios;
- directional absorber-side replenishment ratio;
- directional aggressed-side depletion ratio;
- depth/imbalance change;
- replay integrity and sequence diagnostics.

### OI
- first/last settlement and quote OI;
- absolute/percentage changes.

OI is auxiliary; L2 + tick flow are mandatory.

## Coverage gates

Before winner/loser analysis:
- usable L2 on >=90% of frozen C11A events in discovery and validation separately;
- tick trades on >=90% in each split;
- OI >=75% in each split to admit OI features;
- zero feature timestamp leakage;
- no silent OHLC fallback.

Mandatory failure => `BLOCKED_DATA_ACCESS` or `BLOCKED_DATA_COVERAGE`.

## Frozen analysis

Report:
1. original C11A performance on the full frozen event set;
2. same performance on the CoinDesk-covered subset;
3. true-L2/tick feature medians for winners vs losers;
4. stable differentiators whose effect sign agrees between discovery and validation;
5. one development-frozen shallow selector.

Allowed selector:

`DecisionTreeClassifier(max_depth=2, min_samples_leaf=12, class_weight='balanced', random_state=20260821)`

Discovery chooses one positive leaf with N>=15 by Wilson lower bound, then WR, N, leaf id. Validation is untouched.

## Gates

`C11A_MICRO_ABSORPTION_SUPPORTED` requires:
- discovery N>=15 and validation N>=10 in selected leaf;
- validation WR>=65%;
- validation PF>1;
- selected-leaf WR exceeds same-covered frozen C11A baseline in both splits;
- at least one true-L2 absorption feature is a stable differentiator with the preregistered directional sign.

`C11A_MICRO_HIGH_PRECISION` requires:
- discovery and validation WR>=80%;
- validation N>=10;
- positive validation PnL/PF>1.

`C11A_MICRO_ROBUST_100` is diagnostic only and requires validation N>=10 with zero losses.

## Interpretation limit

A rejection of R1 means true L2 information does not rescue the **previously frozen C11A proxy-event universe**. It does not by itself falsify every possible true-absorption setup across all Friday candles. A fresh all-candle true-absorption search would require `C11A_MICRO_R2` with a new preregistration.

## Prohibited rescue

No change after result to:
- frozen C11A candidate set;
- final-5m primary window;
- 5/10/25-bps bands;
- replay depth;
- event direction;
- outcome economics;
- split;
- tree hyperparameters;
- data-source fallback.
