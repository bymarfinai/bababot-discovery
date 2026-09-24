# BNB B41 — Video HOD/LOD IV Forensic

## Status

**BNB_B41_VIDEO_FORENSIC_INFORMATION_SET_MISMATCH_IDENTIFIED**

This artifact reverse-engineers the user-supplied 28.1s video before proposing another B41 threshold/filter.

## Source evidence

Video reviewed frame-by-frame:
`SaveClip.App_AQMKUSG27EptJ0y0qBihs3K1x-ntlOFTiP78s9C7z3VFXnMRx6dmI3rlh6yyiukHzQjGECZMRNSxojraqL44LylEurpBeByl2oXUvpY.mp4`

Duration: ~28.1s, 720x1280, 30fps.

## What the video actually shows

The chart is not a plain support/demand/reclaim system.

Visible pre-plotted labels include:

- `HL Avg Ask IV`
- `WD Avg Ask IV`
- `Ask IV`
- `Weekly Normal Range HL`
- `Weekly RG Intersect HL`
- `Weekly Short Median HL`
- `Weekly Floor`
- `Weekly Wall Short HL`
- additional weekly long/short/range high-low zones

A separate screen in the video shows a dense option/volatility curve display across strikes/expirations with fields including OTM, VOLUME, OI and CRUSH-like diagnostics.

The marked HOD/LOD examples occur near intersections/confluences of these projected volatility/range levels, not merely at a generic price-action demand zone.

## Performance screenshot shown in the video

A screenshot in the video displays:

- Total P&L: approximately $9,598.50
- Average winning trade: approximately $620.34
- Trade win percentage: 100%
- 9 winning trades
- 0 losing trades

Important boundary: this is a displayed sample of 9 trades. The video alone does not establish sample selection, live timestamp availability, costs, full historical coverage, or pristine out-of-sample performance.

## Annotation timing finding

The red circles highlighting tops/bottoms appear on static historical chart cuts and change/disappear across edits.

Therefore the red circles themselves cannot be treated as evidence that the software emitted a real-time entry signal at those exact pixels.

What appears genuinely software-generated are the horizontal/rectangular IV/range levels that are already drawn across price.

## Core forensic conclusion

The video's information set is materially different from current B41.

Current B41 has mainly used:

`OHLCV -> causal Q80 wall -> interaction/reclaim -> timing -> entry -> post-entry path`

The video appears to use something closer to:

`OPTIONS IMPLIED VOLATILITY / ASK IV + HISTORICAL HOD/LOD/RANGE DISTRIBUTIONS + WEEKLY RANGE LEVELS -> PROJECTED PRICE LEVEL CONFLUENCE -> HOD/LOD reaction`

This explains why repeatedly tuning B41 demand/reclaim/SL logic cannot be expected to reproduce all highlighted video turning points.

## Live Binance feasibility checked 2026-09-24

Binance Options exchange information currently exposes both:

- `BNBUSDT` option contracts
- `SOLUSDT` option contracts

At the time of the audit:

- BNBUSDT had 140 trading option symbols.
- SOLUSDT had 74 trading option symbols.

Current underlying index observations:

- BNBUSDT ~767.55
- SOLUSDT ~114.84

Nearest-expiry ATM examples:

### BNB

`BNB-260924-770-C`

- bidIV ~0.2792
- askIV ~0.3641
- markIV ~0.3216
- delta ~0.3396

### SOL

`SOL-260924-114-C`

- bidIV ~0.5001
- askIV ~0.6189
- markIV ~0.5595
- delta ~0.6956

Therefore the raw live `Ask IV` ingredient visible in the video is technically obtainable for BNB/SOL now.

## Historical-data constraint

The existing BabaBot repository does not contain a historical BNB/SOL option-IV surface archive.

The Binance current mark endpoint exposes bidIV/askIV/markIV and Greeks, but this does not itself provide a multi-year historical IV surface.

BNBUSDT and SOLUSDT monthly options were introduced only in late 2024, so the current B41 2022-2026 development window cannot be reconstructed with native BNB/SOL options data across its full history.

Do not backfill current IV into old candles.

Do not infer historical askIV from future-known surfaces.

Do not call an OHLCV proxy an equivalent replication of the video.

## Correct next research question

Not:

> Which extra candle filter makes Q80 reach 70%?

Instead:

> Can a causal options-IV-derived expected-range / HOD-LOD level map be defined for BNB/SOL, and does price react at those levels out-of-sample?

This is a new information-set family and must be researched separately from B41 Q80.

## Recommended architecture for exact-family replication

1. Snapshot every listed BNB/SOL option contract at fixed intervals.
2. Store strike, expiry, call/put, bidIV, askIV, markIV, delta, gamma, vega, OI and underlying index.
3. Build causal IV surfaces by expiry and moneyness.
4. Convert frozen IV observations into projected daily/weekly expected high-low bands.
5. Combine those projections with historical HOD/LOD and weekly-range distributions.
6. Freeze confluence definitions before testing reactions.
7. Evaluate HOD/LOD capture rate, distance error, false levels, and trading economics on future/unseen data.

## Verdict

**The current B41 OHLCV/Q80 family has not replicated the video's information set.**

**The missing family is options-IV / expected-range / HOD-LOD level construction.**

Live BNB/SOL IV collection is feasible now; multi-year historical equivalence is not currently present in the repo.

## Execution / infrastructure note

A GitHub Actions live snapshot attempt was executed:

- run: `35947419374`
- job: `107468372169`
- direct request to `https://eapi.binance.com/eapi/v1/exchangeInfo` returned HTTP 451 from the GitHub-hosted runner.

This is an infrastructure/access limitation, not evidence that Binance Options data is unavailable.

The Binance public-data connector successfully returned live BNB/SOL option exchange information and current bidIV/askIV/markIV in the same session.

Therefore a future IV collector should run through an allowed data-access path or a self-hosted/non-blocked collector rather than relying on the current GitHub-hosted runner for Binance Options REST.
