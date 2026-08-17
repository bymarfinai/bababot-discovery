# BTC Temporal Friday15 — A6.39 DD Causal Attribution

**Date:** 2026-08-17 WIB  
**Status:** DIAGNOSTIC ONLY — NO STRATEGY CHANGE  
**Live BBC:** untouched  
**Reference:** A6.33 Friday15 provisional champion

## Max-DD episode

- Peak: 2025-05-02
- DD start: 2025-05-09
- Trough: 2026-01-30
- 39 Friday occurrences
- A6.33 max DD: **$46.318**

## Core finding: management is not the primary cause

Within the exact max-DD descent:
- A6.33 managed PnL: **-$46.318**
- Parent-only counterfactual: **-$56.530**
- Management delta: **+$10.211**

Therefore the main drawdown is caused by a prolonged weakening of the Friday15 BUY temporal edge, not by EMA45/damage-control management as a whole.

## Regime deterioration

Before DD (74 Fridays):
- managed WR 68.92%
- PnL +$144.073
- avg +$1.9469
- PF 2.791
- median MFE 0.922%
- median MAE 0.467%

During DD (39 Fridays):
- managed WR **41.03%**
- PnL **-$46.318**
- avg **-$1.1876**
- PF **0.427**
- median MFE **0.495%**
- median MAE **0.628%**

Interpretation: Friday15 trades stopped producing enough upside excursion while adverse excursion increased. The direction prior itself became much weaker.

## Failure-type mix shift

Before DD:
- WIN 56.76%
- A wrong-way 10.81%
- B weak-pop 9.46%
- C giveback 16.22%
- D deep-giveback 6.76%

During DD:
- WIN **30.77%**
- A wrong-way **28.21%**
- B weak-pop **17.95%**
- C giveback 17.95%
- D deep-giveback 5.13%

The dominant structural change is the surge in **wrong-way + weak-pop** cases and collapse in true winners.

## Management attribution during DD

- A wrong-way parent PnL: -$33.856; managed: -$16.489; delta **+$17.367**
- C giveback parent: -$21.265; managed: -$19.512; delta **+$1.753**
- B weak-pop parent: -$22.528; managed: -$24.778; delta **-$2.250**
- D deep-giveback parent: -$8.500; managed: -$14.000; delta **-$5.500**

Thus management materially helps wrong-way failures, but current wrong-way rescue logic can worsen some **deep-giveback / already-moved** cases.

## First half vs second half of DD

First 19 occurrences:
- managed -$22.153 vs parent -$32.614
- management delta **+$10.461**

Second 20 occurrences:
- managed -$24.166 vs parent -$23.916
- management delta **-$0.250**

The second half is where management loses its protective advantage. It includes more post-stop/damage-control double-loss behavior.

## Post-trough behavior

After 2026-01-30 (25 Fridays available):
- managed WR 68.0%
- managed +$43.270
- PF 2.251
- parent +$15.522
- management delta **+$27.749**

So the Friday15 temporal edge appears to recover after the trough in the available sample. This supports a regime-dependent interpretation rather than permanent strategy failure.

## Causal interpretation

Most likely hierarchy of DD causes:
1. **Primary:** prolonged Friday15 BUY temporal regime deterioration — fewer genuine winners, lower MFE, higher MAE.
2. **Secondary:** wrong-way and weak-pop frequency rises sharply.
3. **Tertiary:** sequential SHORT rescue occasionally creates double-losses when the failed BUY had already experienced a meaningful upside excursion / deep giveback rather than clean wrong-way continuation.
4. EMA45/damage-control is **not** the main culprit; it is net protective over the full DD episode.

## Next research direction

Do not primarily attack DD with blanket size reduction. The cleaner research target is to identify a **causal regime-health state before/early after Friday15 entry** that distinguishes the healthy pre/post regimes from the May-2025–Jan-2026 weak regime, while preserving all Friday entries if possible and changing management/risk dynamically rather than filtering coverage.
