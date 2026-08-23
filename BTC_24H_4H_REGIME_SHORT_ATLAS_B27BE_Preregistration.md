# B27BE — BTC 24H Causal 4H Regime SHORT Compatibility Atlas — Preregistration

## Question
Does a causal regime detector applied across the full 24-hour BTC day identify recurring periods/states that are structurally more compatible with SHORT, without restricting research to Asia/London/New-York session labels?

## Frozen data
- Existing BTCUSDT 5m source and existing partitions.
- Weekdays only for primary comparability with B27Q/B27AG lineage.
- No live BBC changes.

## Causal regime
Reuse the exact B27AG / existing `v4h_regime_endpoint.py` semantics:
- complete UTC 4H bars only;
- EMA7 / EMA20;
- ATR14;
- SwingRegime slb=5, sa=0.5;
- BULL: hh>=2, hl>=2, EMA7>EMA20, completed 4H close>EMA20;
- BEAR: lh>=2, ll>=2, EMA7<EMA20, completed 4H close<EMA20;
- otherwise SIDEWAYS;
- a 4H state becomes available only after that 4H bar has fully completed.

## Full-day geometry
The day is covered by six sequential 4H UTC blocks: 00-04, 04-08, 08-12, 12-16, 16-20, 20-24.

For each observation block, freeze H/L from the immediately previous completed 4H block. Thus each observation block has a causal previous-range liquidity reference and a causal regime state available at its start.

No London/NY/Asia labels are used in selection.

## SHORT structural census
Within each observation block, chronologically scan frozen previous-4H Low/High using B27Q-style distinct-visit semantics:
- strict completed close below Low or above High ends the structural path;
- breakout bar is not counted as a touch;
- Low touch: low <= L and close >= L;
- consecutive touching bars collapse into one distinct Low visit;
- High touch is the opposite visit;
- bars touching both boundaries before a strict break are chronologically ambiguous and excluded.

For SHORT compatibility, focus on Low-side pressure. Record K1, K2, K3 Low visits and opposite-visit count at each event.

Primary structural metrics by regime and 4H clock block:
- number of K1 OPP0 Low events;
- P(strict Low break first | K1 OPP0);
- P(second distinct Low visit before opposite break | K1 OPP0);
- P(strict Low break after second visit | second visit occurs);
- no-break and opposite-break rates.

## Daily regime map
Also record for every complete weekday which of the six observation blocks are BULL/BEAR/SIDEWAYS at block start. This provides a full-day causal regime map rather than a session-restricted attribution.

## No economics in B27BE
B27BE is structural discovery only. It does not select F05/F10/F15, D30/D40/D50, E20, runner logic, confirmation, or a live gate.

## Frozen interpretation gate
A regime may be called `SHORT_STRUCTURALLY_FAVORED` only if, in EACH major partition (external, development, reference_validation):
1. K1 OPP0 N >= 30; and
2. strict Low-break-first probability >= 60%; and
3. second-Low-visit probability >= 50%.

This gate is descriptive/structural and does not authorize trading. If no regime passes, selected regime = NONE.

Clock-block diagnostics may be shown but no individual clock block will be promoted unless it independently satisfies the same three-partition gate.

## Anti-fitting rules
- No regime parameter changes.
- No intraday clock subdivisions beyond the six preregistered 4H blocks.
- No session labels used as filters.
- No post-hoc threshold changes.
- No entry/stop/TP/runner search.
- Research only; live BBC unchanged.
