# ETH B27DX — S9 Evidence Consolidation / Research Freeze

## Purpose
Consolidate the ETH B27DX calibration evidence through S8B without introducing another parameter, filter, conjunction, or post-hoc gate relaxation.

This document is a research freeze, not a new backtest.

## Frozen causal architecture that survived
The transferable B27DX grammar remains intact:
- completed 5m chronology only;
- frozen reference H/L before execution;
- K1 OPP0 event identity;
- completed causal leave;
- first legal post-leave retrace chronology;
- terminal precedence and ambiguity handling;
- no future-dependent veto;
- global chronological one-position lock for executable portfolio scoring.

For the mature ETH branch evaluated in S4-S8B, the frozen operating coordinates were:
- LONG;
- R300 / X360;
- clocks 05:00, 09:00, 10:00, 16:00 UTC;
- F75 entry;
- E25 target;
- F20 completed-close invalidation.

## Broad executable baseline
S4 global one-position lock established a real but below-BTC edge:
- pooled-major accepted: 478;
- frequency: 1.393 trades/week;
- WR: 62.8%;
- PF: 1.42;
- expectancy: +$0.81/trade;
- net: +$385.75;
- max loss streak: 5;
- 5 bps stress: WR 60.0%, PF 1.21, expectancy +$0.43/trade, net +$206.90.

Conclusion: the frozen ETH architecture has positive economic expectancy and survives modest execution stress, but it is not BTC B27DX quality.

BTC B27DX LONG reference benchmark:
- WR 71.9%;
- PF 2.22;
- expectancy approximately +$1.26/trade;
- max loss streak 3.

## Mechanisms rejected as broad solutions

### Global runner management
S5A arm scan E10-E40 did not produce a supported arm family. Earlier arm levels improved WR but reduced payoff; later arms improved payoff while reducing WR. No arm solved both dimensions simultaneously.

### Runner breathing gap
S5B G05-G25 barely changed WR and did not create a supported gap family. Breathing distance is not the primary missing edge.

### Per-habitat static geometry
S6A found no Development topology that could be frozen and then validated under the stricter habitat-specific quality gate.

### Post-leave retrace compression
S7B retained approximately 98-100% of events. Almost every filled event already retraced within the first half of its remaining legal execution opportunity, so this feature is non-discriminative.

### Simple volatility regime
S8A HIGH_VOL / LOW_VOL split using a causal trailing-20 same-clock reference-range median produced no Development-promotable state.

## Event-quality features with signal but no frozen promotion

### Single-bar K1 rejection — S7C
Improved PF in some clocks but failed the frozen WR gate.
- 05:00: N35, retention 67.3%, WR 65.7%, PF 2.00, expectancy +$1.15.
- 09:00: N64, retention 71.9%, WR 65.6%, PF 1.74, expectancy +$0.98.

### Minimal conjunction — S7D
The strongest broad-ish conjunction was:
- 05:00 A__B = single-bar K1 rejection + fill first-half;
- N26, retention 50.0%, WR 73.1%, PF 2.13, expectancy +$1.34.

It failed the frozen Development WR >=75% gate. The gate must not be relaxed after seeing the result.

### Bearish leave bar — S7E
The most important broad near-miss:
- 09:00 BEARISH_LEAVE_BAR;
- N70;
- retention 78.7%;
- WR 71.4%;
- PF 2.10;
- expectancy +$1.34/trade;
- net +$93.81.

This is close to BTC-quality on WR/PF/expectancy while retaining most of the clock's trades, but it still failed the preregistered WR >=75% Development promotion gate. External and Reference Validation therefore were correctly not opened for selection/replication.

### Bearish K1 touch bar — S7F
The strongest high-quality sparse island:
- 10:00 BEARISH_K1_BAR;
- N35;
- retention 36.1%;
- WR 77.1%;
- PF 2.56;
- expectancy +$1.64/trade;
- net +$57.39.

Quality exceeded the BTC benchmark on Development, but frozen retention >=50% failed. This is evidence of a potentially real event subclass, not evidence of a deployable strategy.

## Direction-regime evidence — S8B
A simple sign-only reference-direction split produced no Development-promotable state.

Two notable but non-promotable islands:
- 09:00 DOWN_REF: N22, retention 24.7%, WR 86.4%, PF 4.08, expectancy +$1.76/trade.
- 10:00 UP_REF: N65, retention 67.0%, WR 70.8%, PF 1.59, expectancy +$0.85/trade.

The 09:00 DOWN_REF result is exceptionally strong but too sparse under the frozen retention gate. It must not be combined post-hoc with S7E/S7F filters on the same inspected history.

## Evidence classification

### A. Robust broad edge
**S4 frozen portfolio.** Positive across the pooled historical sample and positive after 5 bps stress, but below BTC-quality.

### B. Broad near-BTC candidate — shadow only
**09:00 + BEARISH_LEAVE_BAR.**
Reason: high retention (78.7%) and Development quality close to BTC benchmark without a numeric threshold.

### C. Sparse BTC-quality candidate — shadow only
**10:00 + BEARISH_K1_BAR.**
Reason: Development WR 77.1%, PF 2.56, expectancy +$1.64, but only 36.1% retention.

### D. Quarantined extreme sparse island
**09:00 + DOWN_REF.**
Reason: WR 86.4%, PF 4.08, but only N22 / 24.7% retention. Do not promote and do not combine with inspected event filters.

### E. Rejected broad mechanisms
- global runner arm;
- breathing-gap calibration;
- post-leave retrace compression;
- simple HIGH/LOW volatility split;
- simple UP/DOWN reference direction as a broad standalone solution.

## Research decision

**Status: ETH_B27DX_HISTORICAL_EDGE_POSITIVE_NO_ROBUST_BTC_QUALITY_PROMOTION**

The correct conclusion is not that ETH has no edge. The correct conclusion is:
1. the frozen B27DX architecture on ETH has a broad positive executable edge;
2. BTC-like quality appears inside several ETH event subclasses;
3. every BTC-quality or near-BTC-quality subclass discovered so far either failed the preregistered WR gate or became too sparse under the preregistered retention gate;
4. continuing to combine the observed winners on the same historical sample would materially increase data-mining risk.

## Frozen next evidence step
Do **not** add another historical candle/regime conjunction to the inspected sample.

Freeze the following for pristine forward/shadow evaluation only:
1. **BROAD_SHADOW_09_BEARISH_LEAVE** — 09:00 UTC, R300/X360, F75/E25/F20, bearish completed leave bar.
2. **SPARSE_SHADOW_10_BEARISH_K1** — 10:00 UTC, R300/X360, F75/E25/F20, bearish first K1 touch bar.

Keep the original S4 portfolio as the broad positive benchmark. Do not change live BBC from this research freeze.

A future forward comparison must evaluate these frozen candidates without changing their filters after observing forward outcomes.