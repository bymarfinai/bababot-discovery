# SOL LONG Mirror Structural Character V6 — Directional Symmetry Validation

## Objective

Test whether the structural character discovered on the SHORT side generalizes when direction is mirrored.

This is **not** a new LONG optimization exercise.

The SHORT V5 rule is frozen and mirrored exactly:

- SHORT V5: `largest_bull_body_share >= 0.141955835962`
  AND `rise_per_bar_range_units <= 0.310541310541`

Mirror LONG test:

- `largest_bear_body_share >= 0.141955835962`
  AND `fall_per_bar_range_units <= 0.310541310541`

No LONG-side threshold search, quantile selection, or rescue is permitted.

## Mirrored parent grammar

The LONG family is the directional mirror of frozen SHORT V2:

**sell-side liquidity raid/reclaim -> bullish H1 BOS/new-high state -> first return to H1 bullish origin area -> structural continuation vs H1-origin invalidation**

## Data discipline

- Symbol: SOLUSDT.
- Parent structure: H1 built from complete 5m bars.
- Retracement anatomy: 5m.
- Validation window: 2020-01-01 through 2024-12-31 UTC.
- 2025+ CLOSED.
- Minimum 5m coverage >= 99.5%.
- No session/hour filter.
- No EMA/RSI/Fibonacci/volume/regime feature.
- No entry, TP, SL, or fixed trade horizon.

Because the mirror rule was selected entirely on the opposite directional family, **all 2020-2024 LONG cases are out-of-direction validation cases**.

## Causal H1 pivots

Use the same frozen order-2 causal pivot semantics as the SOL structure library.

A pivot becomes usable only after its confirmation bar.

## Stage A — sell-side liquidity raid/reclaim

For the latest unconsumed confirmed H1 swing low L0:

- the raid bar trades below L0;
- reclaim may occur on the same H1 bar or within the next 2 completed H1 bars;
- reclaim = completed H1 close > L0;
- H0 is the latest confirmed H1 swing high whose pivot occurs after L0 and whose confirmation was already known before the raid;
- each L0 is consumed by its first raid/reclaim family event.

## Stage B — bullish structural shift

After reclaim:

- inspect at most 16 completed H1 bars;
- first completed H1 close > H0 = bullish BOS;
- before BOS, no completed H1 close may fall below the raid extreme;
- no displacement threshold is imposed;
- record displacement, path efficiency, BOS extension, and timing descriptively.

Bullish origin / break block:
- last bearish H1 candle from raid through the bar before BOS;
- zone = full origin candle range [low, high].

## Stage C — first corrective return

Starting after the bullish BOS H1 candle closes:

- search up to 14 calendar days of completed 5m bars;
- first 5m range overlapping the bullish origin zone = first return;
- highest 5m high reached from BOS close until immediately before return becomes the **pre-return structural high**.

## Stage D — structural response

Starting at first return, inspect the next 24 hours of completed 5m bars.

### CONTINUATION
Price trades above the pre-return structural high before bullish-origin invalidation.

### INVALIDATED
A completed 5m candle closes below the bullish-origin zone low before a fresh structural high.

If both become true on the same 5m bar, label AMBIGUOUS.
If neither occurs within 24h, label UNRESOLVED.

This is a structural outcome label, not a trade exit.

## Structural-path deduplication

Collapse rows sharing the same:
- H1 BOS index;
- H1 origin-block index;
- first-return 5m index.

Keep one canonical row:
- earliest raid index;
- then lexicographically smallest structure_id.

All validation metrics use this deduplicated path set.

## Mirrored retracement path

For every deduplicated LONG case:

1. Start after bullish BOS close.
2. Before first return, locate the **last occurrence of the maximum 5m high**.
3. This is the retracement anchor high.
4. Path = anchor-high bar through first-return bar, inclusive.
5. Path must contain >= 4 bars to be usable for compression-character validation.

## Mirrored path features

Directional mirrors of SHORT V5:

1. descent_bars
2. down_path_efficiency
3. median_adjacent_overlap
4. overlap_gt50_share
5. range_contraction_ratio
6. body_contraction_ratio
7. largest_bear_body_share
8. sign_flip_rate
9. lower_high_share
10. fall_per_bar_range_units
11. max_bear_body_range_units
12. pre_return_drawdown_fraction

Primary frozen selector uses **only**:
- largest_bear_body_share >= 0.141955835962
- fall_per_bar_range_units <= 0.310541310541

No other LONG feature may be substituted after results are observed.

## Frozen mirror-validation gates

Promote to **DIRECTIONALLY_SYMMETRIC_STRUCTURAL_CHARACTER** only if all are true on usable resolved LONG paths from 2020-2024:

1. selected resolved N >= 30;
2. selected continuation rate >= 45%;
3. lift vs all usable LONG baseline >= 10 percentage points;
4. selected continuation rate > yearly baseline in at least 4 of 5 years;
5. selected continuation rate > era baseline in both:
   - 2020-2022;
   - 2023-2024.

If any gate fails:
**MIRROR_NOT_CONFIRMED_AS_DEFINED**.

No LONG-side threshold tuning is permitted after this result.

## Required outputs

Persist:
- raw LONG Stage A-D rows;
- deduplicated structural paths;
- path features;
- usable resolved mirror-validation rows;
- selected cohort;
- overall comparison;
- yearly comparison;
- early/late era comparison;
- winner/failure feature summary;
- explicit verdict.

## Research boundary

This experiment validates structural character only.

Even if promoted, next phase is still separate:

**adaptive entry discovery -> adaptive SL discovery -> adaptive TP discovery**

2025_PLUS=CLOSED
