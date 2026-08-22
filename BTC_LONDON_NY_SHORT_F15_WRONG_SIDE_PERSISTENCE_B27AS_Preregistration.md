# B27AS — BTC London->NY SHORT F15 Wrong-Side Persistence Exit — Preregistration

## Purpose
Test the specific failure-state hypothesis identified by B27AF/B27AL:

**The main SHORT problem is not lack of downside continuation among healthy paths; it is the minority of F15 entries that remain persistently on the wrong side and then produce very large adverse losses. A causal persistence exit immediately after F15 may cut those failure tails before the frozen F65 invalidation.**

This is a risk-state audit, not a new liquidity detector, entry search, TP search, regime filter, or runner search.

## Frozen cohort and geometry
Use exactly the independently discovered B27AK/B27AN BLIND_F15 filled cohort:
- external: 50
- development: 79
- reference_validation: 34
- august: 1

Frozen levels for each completed previous London session:
- L = London Low
- H = London High
- R = H-L
- entry = F15 = L + 0.15R
- frozen baseline invalidation = F65 = L + 0.65R
- frozen target = E20_DOWN = L - 0.20R

No confirmation filter and no 4H regime gate.

## Wrong-side persistence definition
Starting from the completed raw 5m bar that first fills F15, count consecutive completed raw 5m closes strictly ABOVE F15 while H2 has not yet occurred.

Preregister exactly three candidate rules:
- P1: exit after 1 consecutive completed close > F15
- P2: exit after 2 consecutive completed closes > F15
- P3: exit after 3 consecutive completed closes > F15

Rules:
1. The F15 fill bar close may count because it becomes observable after the intrabar fill.
2. A completed close <= F15 resets the consecutive counter to zero.
3. H2 is the first later bar whose intrabar low <= L. Once H2 occurs, the persistence detector is permanently disabled for that trade.
4. On a bar that reaches H2 intrabar and later closes >F15, H2 wins chronology for this detector; that close does NOT trigger a pre-H2 persistence exit.
5. A persistence exit executes at the actual completed 5m close that first reaches the required run length. No next-bar delay is added because the close itself is the first observable execution price.
6. No price-distance threshold above F15 is introduced; only the consecutive-close count is searched.

## Frozen economics after persistence logic
For trades not exited by persistence:
- TP remains exact E20_DOWN resting limit;
- baseline F65 invalidation remains completed raw 5m close strictly above F65, exiting at the actual completed close;
- wick-only penetration of F65 does not invalidate;
- if E20_DOWN is touched intrabar on a bar that later closes above F65, TP has precedence because the resting target can execute before the close becomes observable;
- if neither exit occurs, exit at the exact NY session-end open.

If a trade reaches H2 before persistence triggers, persistence stays disabled even if price later closes above F15. This isolates the hypothesized **pre-H2 failure-state** only.

Economics:
- illustrative notional $500
- one round-trip fee $0.40
- no leverage assumption needed.

## Required outputs
For each P1/P2/P3 and partition report:
- N trades
- persistence exit count/rate
- among persistence exits: fraction that would have failed to reach H2 in the frozen structural cohort
- among persistence exits: fraction that actually would have been baseline E20/D50 losers
- H2-before-exit rate
- E20 TP rate
- WR
- PF
- expectancy/trade
- total PnL
- median persistence-exit loss/profit
- baseline total and delta versus B27AN E20/D50

Also report pooled-major external+development+reference_validation.

## Frozen readout gates
Mechanism is considered **directionally supported** only if at least one preregistered P rule:
- improves pooled-major total PnL versus B27AN E20/D50 (-$11.666), AND
- has expectancy >= 0 and PF >= 1.0 in EACH external/development/reference_validation partition.

A rule is considered **promotion-pass** only under the stricter existing B27AN economic gate in EACH major partition:
- N >= 30
- WR >= 70%
- PF >= 1.20
- expectancy > 0.

If no rule satisfies the relevant gate, report NONE. Do not add P4/P5, a price buffer, candle body/wick thresholds, regime filters, alternate stops, alternate targets, or alternate entries after viewing results.

## Mandatory assertions
1. B27AK F15 identities reproduce exactly 50/79/34/1.
2. Frozen B27AN E20/D50 baseline reproduces before interpreting P1/P2/P3.
3. Persistence closes are strictly > F15.
4. Counter resets on close <= F15.
5. No persistence exit can occur on or after the first H2 bar.
6. Persistence exit price equals that completed bar close.
7. E20 target and F65 baseline geometry remain unchanged.
8. E20 intrabar precedence over same-bar completed-close F65 invalidation remains unchanged.
9. All chronology uses raw 5m bars.
10. Synthetic tests cover P1/P2/P3, counter reset, H2 disabling persistence, and baseline continuation after H2.

Research only. Live BBC unchanged.
