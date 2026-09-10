# ETH Discovery 2 Reset — G5 Scientific Verdict

**Verdict: NO DEVELOPMENT CANDIDATE.**

Official status: `ETH_DISCOVERY2_RESET_G5_NO_DEV_CANDIDATE`.

G5 tested static TP × SL × maximum-hold economics on the fully frozen ETH-native G2+G3+G4 lineage:

**LONG / 01:30 UTC / R180 / E720 / first HIGH-side pressure → DIRECT B00 → NEXT_OPEN**.

No clock, reference duration, execution duration, downstream structure, entry timing, or entry price rule was changed.

## Fixed economics
- $500 notional per trade.
- $0.75 round-trip trading cost per trade.
- No compounding.
- No additional slippage model.
- Development frozen entries: **184**.
- External frozen entries: **88**.
- Reference Validation frozen entries: **91**.

## Preregistered search
- TP: 0.05/0.08/0.10/0.12/0.15/0.20/0.30/0.40/0.60/0.80R.
- SL: 0.05/0.08/0.10/0.12/0.15/0.20/0.30/0.40/0.60R.
- Max hold: 15/30/60/120/240/480/720m.
- Total: **630 Development configurations**.
- Same-bar TP+SL ambiguity was conservatively recorded as SL.

External and Reference Validation were not opened because no Development candidate passed.

## Stronger finding than the formal gate result
The result was not a near miss caused by one preregistered threshold:

- **0 / 630 configurations had positive net PnL.**
- **0 / 630 had PF >= 1.20.**
- **0 / 630 had max DD <= $40.**
- **0 / 630 had >=3/4 positive chronological blocks.**
- Only **5 / 630** produced even one positive Development block; 625/630 produced zero positive blocks.
- **286 / 630** were gross-PnL positive before fees, but none produced enough gross edge to pay the fixed round-trip cost.

Therefore no threshold relaxation is scientifically justified inside G5.

## Best Development configuration by net PnL — descriptive only
**TP0.10R / SL0.60R / hold240m**

- Trades: **184**.
- TP/SL/timeout: **164 / 17 / 3**.
- Gross PnL: **+$57.51**.
- Fees: **$138.00**.
- Net PnL: **-$80.49**.
- Expectancy: **-$0.437/trade**.
- Net/100 trades: **-$43.74**.
- Net win rate: **34.24%**.
- PF: **0.288**.
- Max DD: **$83.62**.
- Max loss streak: **29**.
- Positive chronological blocks: **0/4**.

The unusually large difference between 164 TP hits and only 34.24% fee-adjusted winning trades is economically meaningful: for many sessions, a 0.10R target is smaller in dollars than the fixed $0.75 round-trip cost.

## Post-run fee-scale diagnostic
Using the frozen G4 NEXT_OPEN Development audit, the session-range scale relative to entry was:
- median `R / entry`: **1.340%**;
- 25th percentile: **0.923%**;
- 75th percentile: **1.996%**.

At $500 notional with a $0.75 round-trip cost, the gross return required merely to pay the fee is **0.15%**. Expressed in each session's R units, the Development distribution of fee break-even distance was:
- median: **0.112R**;
- 25th percentile: **0.075R**;
- 75th percentile: **0.163R**;
- 90th percentile: **0.237R**.

This diagnostic was calculated only after the preregistered G5 result and did not participate in candidate selection.

It explains why very small TP coordinates can record many nominal TP touches while still losing after cost. It does **not** by itself prove that larger static targets will work.

## Historical Z6 coordinate on the reset lineage
The old Z6 coordinate was included as an ordinary grid point and did not recover:

**TP0.60R / SL0.30R / hold120m**
- Trades: **184**.
- Net WR: **31.52%**.
- Net PnL: **-$142.66**.
- Expectancy: **-$0.775/trade**.
- PF: **0.538**.
- Max DD: **$142.66**.
- Max loss streak: **18**.
- Positive blocks: **0/4**.

Thus the reset lineage also rejects simply transplanting the old money geometry.

## Scientific interpretation
G1–G4 remain structurally supported. G5 does **not** invalidate the pair-native clock, R180 reference, E720 horizon, DIRECT breakout grammar, or NEXT_OPEN entry. It establishes a narrower statement:

> The preregistered **static bracket family bounded by TP <=0.80R, SL <=0.60R, hold <=720m does not economically translate the frozen ETH-native signal under the fixed $500 / $0.75 cost model.**

The correct response is not to loosen G5's economic gates and not to copy BTC/SOL exits.

The failure suggests that the next discovery step must move one layer upstream within payoff geometry: measure how far and how fast post-entry paths actually travel relative to R and transaction-cost break-even before defining another money grid.

## Strongest next experiment
The next valid experiment should be a **G6 fee-adjusted payoff atlas / excursion discovery**, still freezing G2+G3+G4.

Development-only G6 should characterize, without selecting a live strategy:
- per-trade fee break-even distance in R units;
- MFE and MAE through the frozen execution horizon;
- target-reach probabilities beyond the G5 cap, with a broad diagnostic ladder such as 0.10R through multiple R;
- time-to-target distributions;
- adverse excursion before reaching each favorable target;
- first-hit relationships between favorable and adverse R levels;
- whether profitable paths form a stable payoff plateau or whether the structural edge is simply too small after cost.

Only after that atlas should a finite G7 economic family be preregistered. This follows the same discovery principle used in the reset: **copy the method of finding the pair's coordinates, not another pair's coordinates.**

Research/shadow only. No live promotion or profit guarantee.
