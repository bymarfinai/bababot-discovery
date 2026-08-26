# ETH London -> New York Liquidity Pressure — M1 Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Why this experiment exists
This is the correct first transfer milestone of the BTC F85 LONG lineage to ETHUSDT.

It deliberately mirrors the original **B27Q discovery stage**, not the later four-zone F85 operating portfolio.

The question is only:

> After the completed London range is frozen, does the **first distinct visit to the London High with zero prior Low visits (LONG K1 OPP0)** create a repeatable causal same-side pressure pattern during New York on ETHUSDT?

The earlier repo experiment `ETH_F85_F15_TRANSFER_M1_K1_OPP0` is **superseded for transfer research** because it incorrectly bundled multiple later operating clocks and SHORT into the first milestone. It must not be used as evidence for this lineage.

## Scope — one habitat, one side, one milestone
- Instrument: Binance USD-M **ETHUSDT perpetual**.
- Raw event clock: **5m**.
- Transition only: **London -> New York**.
- Direction only: **LONG**.
- Previous session: London **08:00-13:30 UTC**.
- Active session: New York **13:30-20:00 UTC**.
- Weekdays only.

No other clock is tested.
No SHORT is tested.
No F85/F90/F80/F75 is calculated for selection.
No entry, stop, target, runner, leverage, fee, PF, PnL, or portfolio lock is tested.

## Historical partitions
Keep the same frozen research boundaries used by the BTC lineage:
- external: 2020-01-01 <= date < 2022-01-01
- development: 2022-01-01 <= date < 2025-01-01
- reference_validation: 2025-01-01 <= date < 2026-07-30
- august telemetry: 2026-08-01 through available data

## Frozen London range
For every complete weekday London session:
- `H = max(high)` from 08:00 <= bar start < 13:30 UTC.
- `L = min(low)` over the same 66 raw 5m bars.
- Require `H > L`.
- At 13:30 UTC H/L are frozen and may never be modified by New York candles.

## Exact visit definition — copied from B27Q semantics
Before the first confirmed strict breakout of either boundary during New York:

### High visit
A raw 5m bar qualifies when:
- `high >= H`, and
- `close <= H`.

### Low visit
A raw 5m bar qualifies when:
- `low <= L`, and
- `close >= L`.

### Distinct visits
- Consecutive qualifying bars at the same boundary are **one visit episode**.
- Another visit is counted only after at least one intervening bar that does not qualify for that boundary.

### Strict breakouts
- Bull breakout: first completed raw 5m `close > H`.
- Bear breakout: first completed raw 5m `close < L`.
- A strict breakout bar is evaluated before touch counting and is not counted as a prior visit.
- A pre-breakout bar that simultaneously qualifies as both High and Low visit is `AMBIGUOUS_BOTH_LEVELS` and excluded because intrabar ordering is unknowable.

## M1 signal
Only the exact BTC-discovered pressure identity is tested:

**ETH LONG K1 OPP0** = the completed 5m bar that creates **High visit #1**, provided the number of distinct Low visits already known at that completed-bar close is **zero**.

Signal time is the end of the K1 signal bar.
There is no entry order.

## Structural outcome after K1 OPP0
Starting strictly after K1 signal completion and ending at New York session end, classify the first strict close breakout:
- `TARGET_BREAK`: first strict close breakout is `close > H`.
- `OPPOSITE_BREAK`: first strict close breakout is `close < L`.
- `NO_BREAK`: neither strict breakout occurs before New York end.

Additionally, for anatomy only, count subsequent distinct High visits known before breakout/end so K1 -> K2/K3 pressure persistence can be inspected. These counts cannot alter signal eligibility.

## BTC control
Run the exact same M1 engine on BTCUSDT over the same London/New York windows and partitions.

BTC is a control only. No ETH threshold may be changed based on the BTC result during execution.

## Required reporting
For ETH and BTC, per partition and pooled-major:
- complete London->NY sessions;
- LONG K1 OPP0 signals;
- K1 OPP0 rate per complete session;
- TARGET_BREAK count/rate;
- OPPOSITE_BREAK count/rate;
- NO_BREAK count/rate;
- resolved same-side win rate = TARGET_BREAK / (TARGET_BREAK + OPPOSITE_BREAK);
- median minutes signal -> target break;
- fraction reaching a second distinct High visit before terminal outcome;
- fraction reaching a third distinct High visit before terminal outcome.

No trading WR is to be claimed because there is no trade in M1.

## Frozen M1 interpretation gate
ETH M1 is `SUPPORTED` only if pooled-major satisfies all:
1. K1 OPP0 signals >= 100.
2. TARGET_BREAK rate among all K1 OPP0 signals >= 50%.
3. Resolved same-side win rate >= 65%.
4. TARGET_BREAK rate is no more than 10 percentage points below the exact BTC control.
5. External, development, and reference_validation each have positive directional edge: TARGET_BREAK count > OPPOSITE_BREAK count.

This is intentionally only a structural gate. Passing M1 authorizes **discussion of M2 only**.

## If M1 passes
Do **not** automatically execute M2.

The next experiment would mirror **B27W**:
`K1 OPP0 -> first-touch episode -> causal leave -> pre-H2 entry availability grid F95/F90/F85/F80/F75`.

That later experiment is where ETH is allowed to discover whether F85 is still the best location. M1 must not assume the answer.

## Mandatory assertions
Abort before result persistence if any fail:
1. Every valid London reference has exactly 66 raw 5m bars.
2. Every valid New York active session has exactly 78 raw 5m bars.
3. H/L are computed exclusively from London and remain immutable in New York.
4. Consecutive same-level qualifying bars collapse to one visit.
5. Leaving a level and later returning increments the visit ordinal.
6. Strict breakout bars are excluded from visit counts.
7. K1 OPP0 uses only opposite visits already observable at K1 signal completion.
8. No future terminal outcome affects K1 eligibility.
9. No F-level, indicator, entry, stop, target, or economics is consulted.
10. ETH and BTC raw 5m coverage must each be >=99.5% over their usable scoring span.

**Research only. Stop after M1.**
