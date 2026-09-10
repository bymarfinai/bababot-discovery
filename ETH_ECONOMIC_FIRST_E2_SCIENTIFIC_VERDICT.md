# ETH Economic-First Reset — E2 Scientific Verdict

**Verdict: NO DEVELOPMENT CANDIDATE.**

Official status: `ETH_ECONOMIC_FIRST_E2_NO_DEV_CANDIDATE`.

E2 tested whether ETH's pair-native economic character could be exposed by one causal conditioning variable only: the sign of the pre-entry return, followed by either momentum or reversal.

## Frozen search
- ETHUSDT Binance Futures raw 5m, 100% coverage.
- Weekday UTC anchors.
- 48 half-hour entry clocks.
- Pre-entry lookbacks: 15/30/60/120/240/360m.
- Response: MOMENTUM or REVERSAL.
- Holds: 15/30/60/120/240/360/720m.
- Exact 5m open entry/exit.
- $500 fixed notional.
- $0.75 round-trip cost.
- 4,032 Development candidates.
- No H/L/range/breakout/retest/EMA/Fibonacci.

## Result
- Healthy Development gate passers: **0 / 4,032**.
- Healthy + local-stability passers: **0 / 4,032**.
- Holdouts were not opened.

## Best raw Development economics — descriptive only
**17:00 UTC (00:00 WIB) / MOMENTUM / lookback 360m / hold 720m**
- WR: **47.63%**.
- Net PnL: **+$481.58**.
- Expectancy: **+$0.62/trade**.
- PF: **1.155**.
- Max DD: **$315.01**.
- Max loss streak: **13**.
- Positive chronological blocks: **3/4**.
- Supportive neighbors: **0/4**.

This is economically positive but is not the high-WR, low-drawdown character being sought and has no local support under the preregistered rule.

Other raw positive-net examples also generally used long 720m holds and had sub-52% WR. This indicates that sign-only momentum can capture occasional large moves, but not with sufficiently consistent hit rate or drawdown behavior.

## Highest-WR Development coordinate — descriptive only
**04:30 UTC (11:30 WIB) / MOMENTUM / lookback 30m / hold 720m**
- WR: **52.30%**.
- Net PnL: **-$88.70**.
- Expectancy: **-$0.11/trade**.
- PF: **0.976**.
- Max DD: **$564.18**.

Thus the raw WR leader is not economically healthy either.

## Scientific conclusion
E1 established that pure clock drift is insufficient. E2 establishes that **pre-entry return sign alone** is also insufficient.

However, unlike E1, E2 exposes a useful next hypothesis: some momentum coordinates have positive expectancy and PF after fee but poor WR / DD. This suggests the missing causal variable may be **drive quality or magnitude**, not another H boundary.

A next family, if run, should remain economic-first and test whether conditioning on the strength of the pre-entry drive converts the low-WR positive-expectancy tail into a smaller but higher-quality trade set. The threshold must be defined prospectively and causally, preferably by broad quantile bands rather than tuned fixed percentage cutoffs.

Do not rescue E2 by changing its gates or by selecting its best raw coordinate. The E2 family is closed as preregistered.

Research/shadow only. No live promotion or profit guarantee.
