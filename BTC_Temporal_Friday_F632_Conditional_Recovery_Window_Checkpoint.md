# Friday F6.32 — Conditional Recovery Window

**Diagnostic screen: FAIL**
**Same-sample diagnostic only; live BBC untouched; no automatic promotion.**

## Exact sequential architecture
F6.29 would cut at +20m. If F6.31 lower-low + improving-flow divergence is absent, keep the +20m cut. If divergence exists, defer for max 10m: recovery-chain confirmation at +25m releases to frozen HOLD; otherwise check once more at +30m; if still unconfirmed, cut at actual +30m open.

## Routing
- F6.29 actions **12**; guarded into grace **6**; immediate +20m cuts **6**
- +25 confirmations **2**; +30 confirmations **1**; +30 cuts **3**; frozen exits during grace **0**
- +25 confirm winner/loser **0/2**
- +30 confirm winner/loser **0/1**
- +30 cut winner/loser **2/1**

## Economics
- PnL frozen **+138.329** → F6.29 **+147.540** → F6.31 **+146.379** → F6.32 **+139.884**
- incremental vs frozen **+1.555**; vs F6.29 **-7.656**; vs F6.31 **-6.495**
- D/V vs frozen **-4.886 / +6.440**
- WR **52.90% → 50.72%**; PF **1.827 → 1.868**; DD **24.259 → 20.154**
- baseline positive→nonpositive **3**; parent winners preserved positive **0/3**
- failure-to-develop defensively cut **5/24**

## Guardrail
This is still same-sample architecture research. Do not retune +25/+30, EMA7, higher-close/higher-low definition, or add flow-magnitude thresholds based on this result.
