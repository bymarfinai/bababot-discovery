# Market Hunter MH0 — Preregistered Cross-Sectional Opportunity Ranking

**Status: FROZEN BEFORE RESULT OBSERVATION. Research-only. Live BBC/Tuesdays untouched.**

## Why this is new
The repo already contains extensive fixed-pair and temporal research: BBC/EMA/MTF, structural/liquidity zones, Fibonacci, absorption, taker-flow forensics, derivatives-data feasibility, market breadth/regime, dynamic direction, Friday/Saturday/Sunday/Tuesday temporal families, causal execution audits, and true-OOS extensions.

MH0 tests a different question: **at the same decision timestamp, can causal information rank many USDT perpetual contracts cross-sectionally so the top opportunity has better forward economics than raw momentum or random selection?**

No prior repository search hit was found for a cross-sectional/scanner implementation that ranks a broad universe at each timestamp and trades top-N opportunities.

## Frozen data window
- End-exclusive: `2026-08-19T00:00:00Z`
- Primary history: 365 days, with 90d and 120d slices reported from the same frozen data.
- Source: official Binance USD-M public kline archives (`data.binance.vision`).
- Timeframe: 1h.
- Dynamic eligibility: a contract must have at least 168 completed 1h bars before it can be ranked.
- Universe is a broad preregistered list of USDT perpetual symbols. Missing/unlisted periods are simply ineligible.
- Limitation: the preregistered symbol list is survivorship-screened/current-knowledge and therefore MH0 is a feasibility study, not pristine historical-universe proof. A positive result must later survive an archived/delist-aware MH1.

## Causality
At decision bar `t`, only information from completed bars through `t` may be used.
Entry is always at the **next 1h bar open** (`t+1`).
No feature may use the next open, future high/low, future volume, future universe membership, or future derivatives observations.

## Causal features per eligible contract
Calculated from completed 1h bars:
1. `ret4h` — 4h return.
2. `ret24h` — 24h return.
3. `rel_quote_volume` — current quote volume relative to median of the prior 168 completed hours (excluding the current bar from the baseline).
4. `range_expansion` — current true-range percentage relative to the median prior 168h true-range percentage.
5. `breakout_position` — close location relative to the **prior** 24h high/low range.
6. `taker_imbalance` — `(2*taker_buy_quote_volume/quote_volume)-1` from the completed current bar.

## Liquidity universe at each timestamp
Among contracts with valid features and 168h warmup, compute trailing completed 24h quote-volume sum.
Keep the **top 50% by trailing 24h quote volume** at that timestamp, with a minimum of 10 contracts required for a decision.
This is causal and avoids using current-day liquidity to choose historical winners.

## Frozen ranking
All features are converted to percentile ranks **cross-sectionally at the same timestamp**.

LONG score = equal-weight mean percentile rank of:
- `ret4h`
- `ret24h`
- `rel_quote_volume`
- `range_expansion`
- `breakout_position`
- `taker_imbalance`

SHORT score = equal-weight mean percentile rank of:
- `-ret4h`
- `-ret24h`
- `rel_quote_volume`
- `range_expansion`
- `-breakout_position`
- `-taker_imbalance`

For each pair, keep its stronger direction. Rank pair-direction candidates by score.

Primary selection: **top 1** candidate per timestamp.
Secondary descriptive selection: **top 3** candidates per timestamp.
No K sweep is allowed.

## Controls
1. **Raw momentum control:** among the same liquid eligible universe, choose the contract with largest absolute `ret24h`; direction follows the sign of `ret24h`.
2. **Random control:** deterministic random eligible pair + random direction at the same timestamps, seed `20260819`; report the aggregate control, not cherry-picked seeds.

## Primary outcome
For the selected candidate entered at next 1h open:
- direction-adjusted 1h, 3h, and **6h forward close return**;
- primary economic metric = 6h signed return minus **0.15% round-trip modeled cost**.

A positive gross return that becomes negative after 15 bps is not an economic pass.

## Secondary executable control
One frozen management policy:
- TP 1.30%
- SL 1.30%
- maximum hold 6h
- 0.15% modeled round-trip cost
- entry next 1h open
- if TP and SL are both touched in the same hourly candle, assume **SL first** (conservative adverse-first rule).

No TP/SL sweep follows MH0.

## Portfolio realism
Report both:
1. independent hourly top-ranked opportunities (ranking quality diagnostic), and
2. **single-position sequential execution**: when a position is active, new hourly candidates are ignored until the frozen TP/SL/max-hold exit occurs.

The sequential result is the primary live-like execution result.

## Required robustness report
- 90d, 120d, and 365d results;
- long vs short attribution;
- pair contribution/concentration;
- four chronological blocks for the 365d period;
- number of eligible contracts over time;
- top-1 vs raw-momentum vs random controls;
- no live modification regardless of result.

## Frozen interpretation
**KEEP FOR MH1** only if the composite top-1 demonstrates positive after-cost 6h expectancy and positive sequential TP/SL economics over 365d, is not dependent on one pair, and is not solely a recent-window effect.

Otherwise: **REJECT MH0 composite as a live-candidate concept**.

A KEEP does not authorize live trading. It only justifies a stricter delist-aware/dynamic-universe MH1 validation.
