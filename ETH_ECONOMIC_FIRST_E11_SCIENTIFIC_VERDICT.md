# ETH Economic-First E11 — Scientific Verdict

## Status
**ETH_ECONOMIC_FIRST_E11_NO_STATE_CANDIDATE**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- workflow run ID: **34475888995**
- job ID: **102866406686**
- head SHA: **ae7cd3b1bb49e82fdf4c6e9fefb0f99a27edb6dc**
- artifact ID: **10151620417**
- targeted workflow conclusion: **success**
- raw ETHUSDT 5m coverage: **100.0000%**

## Scientific question
E11 explicitly stopped treating clock as the primary coordinate. It tested whether a causal pre-entry market-state/path-shape grammar could produce high-WR positive economics across many different half-hour UTC clock contexts and consistently across 2022, 2023, and 2024.

External and Reference Validation remained closed.

## Frozen candidate universe
- 48 half-hour UTC clocks, used only as evaluation contexts
- lookbacks: 15, 30, 60, 120, 240, 360m
- holds: 60, 120, 240, 360, 720, 960m
- modes: MOMENTUM and REVERSAL
- causal feature families: directional efficiency (EFF), realized volatility (RV), realized range (RANGE), directional terminal location (EXT)
- each state feature normalized causally against its own previous same-clock/same-lookback observations
- single-feature terciles plus preregistered two-feature interactions
- **3,456 candidate identities**
- each candidate independently evaluated across all 48 clock contexts

## Result
**0 / 3,456 candidates passed the full preregistered market-state gate.**

No state achieved the required combination of:
- broad evaluability/support across clocks,
- median WR/economics,
- positive cross-era behavior in all of 2022, 2023, and 2024,
- and breadth across at least five of six UTC clock blocks.

No gate relaxation or raw-top substitution was used.

## Strongest broad candidate — descriptive only
The strongest candidate among the top results that remained evaluable across all 48 clocks was:

**MOMENTUM / EFF_HIGH__RV_MID / LB360 / hold960**

Development clock-panel summary:
- evaluable clocks: **48/48**
- supportive clocks: **4/48**
- median WR: **49.12%**
- median expectancy: **+$0.52/trade**
- median PF: **1.102**
- median DD: **$133.33**
- supportive UTC clock blocks: **0/6**
- 2022 median WR / expectancy: **51.72% / +$0.19**
- 2023: **44.64% / +$0.94**
- 2024: **47.21% / +$0.26**

Although median expectancy was positive, the win rate, drawdown, clock breadth, and 2023/2024 directional consistency were far below the preregistered requirements. It is not a candidate for promotion.

Another broad result, **MOMENTUM / EFF_HIGH__EXT_MID / LB360 / hold960**, had 48 evaluable clocks but only 10 supportive clocks, median WR 46.66%, median expectancy +$0.34, PF 1.066, DD $132.59, and only 1/6 supportive clock blocks. This likewise fails decisively.

The nominal top rows with stronger local numbers had only one evaluable clock and therefore fail the central E11 invariance question by construction.

## Scientific interpretation
E11 shows that the E9/E10 phenomenon is **not explained by simple marginal or pairwise pre-entry state variables** based on directional efficiency, realized volatility, realized range, or directional terminal location.

This strengthens the previous conclusion:

1. E9 found economically attractive coordinates.
2. E10A/E10B showed those coordinates were narrow ridges rather than stable clock/lookback/hold plateaus.
3. E11 shows that replacing clock with simple normalized state bins still does not recover a broad ETH character edge.

Therefore the next discovery should not return to clock tuning and should not endlessly combine more static scalar filters. The next family should move to **event/path sequence structure**: the order and shape of movement inside the pre-entry path, rather than summary statistics of that path.

A suitable next preregistered family is an economic-first path-shape/event grammar, for example testing causal sequences such as impulse → retrace → re-acceleration, compression → directional expansion, or directional excursion/recovery signatures. Candidate identity should be event grammar + horizon + execution/hold, while clock remains only a context. Cross-era and cross-clock breadth must again be required before OOS exposure.

## Integrity
- OOS unopened.
- No second-best substitution.
- No threshold relaxation.
- No claim that overlapping clock-panel economics are portfolio returns.
- E10 coordinate ridges remain descriptive findings only, not promoted strategies.
