# SOL SELL Structural Character V4 — H4 Confluence Preregistration

## Objective

Test whether the broad SOL bearish structural family becomes materially stronger when the H1 bearish origin / break-block return occurs inside an **independently created H4 bearish structural supply area**.

This is a structural-character experiment only.

No entry trigger, TP, SL, session, indicator, or execution optimization is allowed.

## Parent family

Reuse the frozen V2 adaptive grammar unchanged:

**buy-side liquidity raid/reclaim -> bearish H1 BOS/new-low state -> corrective return to H1 bearish origin area -> structural continuation vs H1-origin invalidation**

The V3 separation rule is NOT used because it failed frozen confirmation.

## Data

- SOLUSDT.
- Parent structural layer: H1.
- Higher-timeframe context: H4 built causally from complete H1 bars.
- Child path layer: 5m.
- 2020-2022 = development description.
- 2023-2024 = frozen confirmation.
- 2025+ CLOSED.
- Minimum 5m coverage >= 99.5%.

## Frozen H4 bearish structural zone

H4 candles are UTC-aligned 4-hour bars built only from four complete H1 candles.

Use the same causal order-2 pivot semantics as the SOL structure library.

An H4 bearish BOS occurs when:
- a confirmed H4 swing low exists;
- previous completed H4 close is >= that swing-low price;
- current completed H4 close is < that swing-low price;
- each confirmed swing low is consumed only by its first qualifying close-break.

The H4 bearish origin / supply block is:
- the **last bullish H4 candle** among the eight completed H4 bars immediately preceding the BOS bar;
- bullish = close > open;
- zone geometry = full H4 candle range [low, high].

A zone becomes valid only after the BOS H4 candle closes.

A zone remains active until the first later completed H4 candle closes strictly above the zone high.

No displacement threshold is added in V4. H4 displacement and zone geometry are descriptive features only.

## H1/H4 confluence at the return

For each frozen V2 Stage-C first return:

- consider only H4 bearish zones whose BOS was already completed before that 5m return;
- discard any H4 zone already invalidated by a completed H4 close above its zone high before that return;
- H4_CONFLUENT = TRUE when the frozen H1 origin zone [H1 zone_low, H1 zone_high] has positive price overlap with at least one active H4 bearish zone.

If multiple active H4 zones overlap, use the most recently created H4 zone.

Record:
- H1/H4 overlap width;
- overlap as fraction of H1 zone width;
- overlap as fraction of H4 zone width;
- H4 zone age at the H1 return;
- H4 BOS extension below its broken swing low.

## Structural response

Do not alter V2 response semantics:

- CONTINUATION = fresh pre-return structural low is broken before H1-origin invalidation.
- INVALIDATED = completed 5m close above H1 origin-zone high occurs first.
- AMBIGUOUS / UNRESOLVED retain their V2 definitions.

Only CONTINUATION and INVALIDATED are used in binary rate comparisons.

## Frozen confirmation test

Primary comparison:
- H4-confluent resolved cases vs all resolved V2 cases.

Promotion to H4_STRUCTURAL_CHARACTER requires on 2023-2024:
1. H4-confluent resolved N >= 25;
2. continuation rate >= 45%;
3. lift vs 2023-2024 V2 baseline >= 10 percentage points;
4. H4-confluent continuation rate > baseline in 2023;
5. H4-confluent continuation rate > baseline in 2024.

No threshold rescue or alternative H4 zone geometry may be tested on 2023-2024 after seeing the result.

## Required outputs

Persist:
- H4 bearish zones;
- V2 return cases annotated with H4 confluence;
- resolved confluence comparison;
- yearly 2020-2024 rates;
- H4 overlap diagnostics;
- explicit frozen verdict.

## Next phase

Only if the H4 structural character is promoted do we move to:
**adaptive entry discovery -> adaptive SL discovery -> adaptive TP discovery**.

2025_PLUS=CLOSED
