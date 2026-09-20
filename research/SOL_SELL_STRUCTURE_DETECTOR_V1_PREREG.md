# SOL SELL Structure Detector V1 — Preregistration

## Objective

Build and audit a causal SOLUSDT H1 bearish structure detector matching the reference structure discussed in chat:

1. **Buy-side liquidity event** — an already-confirmed H1 swing high is swept and the sweep candle closes back below that liquidity level.
2. **Bearish displacement + structural break** — after the sweep, price displaces down and closes below the latest confirmed significant H1 swing low that formed after the liquidity high.
3. **Corrective return to bearish origin / break block** — the bearish leg's last bullish H1 candle before BOS defines the supply / break-block zone; after BOS, price later retraces into that zone from below.
4. **Rejection + SHORT activation** — during the first return lifecycle, a 5m bearish rejection closes back below the zone's proximal edge without first accepting above the distal edge.

This experiment is about **structure-detector fidelity**, not TP/SL optimization and not live readiness.

## Frozen data discipline

- Symbol: SOLUSDT.
- Parent structure timeframe: H1, built causally from complete 5m bars.
- Activation timeframe: 5m.
- Development evaluation window: 2020-01-01 through 2024-12-31 UTC.
- 2025+ remains CLOSED.
- Required 5m data coverage: >= 99.5%.
- No hour filter.
- No EMA/RSI/Fibonacci/volume/regime gate.
- No TP/SL optimization.
- No post-result threshold rescue on 2020-2024.

## H1 pivots

Use the repository's frozen causal pivot semantics from `sol_structure_library_v1.py`:

- pivot order = 2;
- a pivot becomes usable only after its confirmation bar.

## Stage A — Buy-side liquidity sweep

For the latest unconsumed confirmed H1 swing high `H0`:

- find the latest confirmed H1 swing low `L0` whose pivot occurs after `H0`;
- require the sweep bar to occur after both pivots are confirmed;
- sweep condition:
  - H1 high > H0 price;
  - H1 close < H0 price.

Each H0 is consumed by its first qualifying sweep.

## Stage B — Bearish displacement + BOS

After the sweep:

- inspect at most 12 completed H1 bars;
- require the first completed H1 close below L0;
- BOS must occur strictly after the sweep bar;
- compute median H1 range over the 20 completed H1 bars preceding the sweep;
- require displacement from sweep high to BOS close >= 1.50x that median range;
- require bearish close-path efficiency from sweep close to BOS close >= 0.55.

The **break block / bearish origin** is the last bullish H1 candle in [sweep, BOS).

Frozen zone geometry:

- proximal edge = origin candle low;
- distal edge = origin candle high;
- full origin-candle range is the detector zone.

## Stage C — Corrective return

Starting only after the BOS H1 candle has fully closed:

- search the next 7 days of completed 5m bars;
- the first 5m candle intersecting [zone_low, zone_high] is the first return;
- if no return occurs within 7 days, the structure stops at Stage B.

## Stage D — Rejection + SHORT activation

Beginning at the first return:

- observe at most 12 completed 5m candles (60 minutes);
- invalidation: any completed 5m close > zone_high before activation;
- valid rejection candle:
  - candle is bearish: close < open;
  - candle high reaches at least zone_low;
  - candle close < zone_low.

Signal time = close of that rejection candle.
Diagnostic entry = next 5m open.

## Diagnostic continuation only

To understand whether the detector is pointing in the intended direction, record a fixed +60m SHORT diagnostic:

- entry = next 5m open after activation;
- exit = close after 60 minutes;
- round-trip cost = 0.15%;
- notional = $500.

This is **not** execution optimization and cannot promote the detector to live trading.

## Required outputs

Persist:

- Stage A sweep events;
- Stage B BOS/origin events;
- Stage C first-return events;
- Stage D full matches / activations;
- full-match trade diagnostic rows;
- pooled and yearly +60m short diagnostics;
- stage-to-stage conversion rates;
- delay distributions:
  - sweep -> BOS;
  - BOS -> first return;
  - return -> activation.

## Interpretation

The primary result is the **structural funnel A -> B -> C -> D**.

A full Stage D match means the complete reference grammar was found causally:

**liquidity sweep -> bearish displacement/BOS -> new low context -> corrective return to break block -> rejection -> SHORT activation**.

No nearby thresholds may be tested as a rescue on the same Development sample after this result is seen.

2025_PLUS=CLOSED
