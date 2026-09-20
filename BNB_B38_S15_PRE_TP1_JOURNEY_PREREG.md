# BNB B38-S15 — Pre-TP1 Journey Character Preregistration

## Objective
Explain, using only information available no later than the first TP1 touch, why some frozen E2 winners continue to causal TP2 while others stop after TP1.

## Frozen upstream
- Frozen B38-S13/S14 E2 signature:
  `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- Executable E2 population remains:
  - DEV 440 = 325 WIN / 115 LOSS
  - REF 272 = 201 WIN / 71 LOSS
- No change to E2 detector, entry, SL, TP1, TP2, or target ladder.

## Study population
Only baseline E2 WINs with a causal TP2 above TP1:
- Expected DEV: 288
- Expected REF: 178

Primary label:
- **EXTENDER** = TP2 touches before frozen structural SL after TP1.
- **STOPPER** = TP2 does not touch before frozen structural SL.

## Causal feature families
All journey features are measured strictly before the first 5m bar that touches TP1. TP1/TP2 geometry is already known at entry.

### A. Journey speed
- completed 5m bars before TP1 touch
- minutes from entry to TP1 touch
- progress per completed bar
- distance remaining to TP1 on the last completed pre-touch bar

### B. Journey cleanliness
- maximum adverse excursion before TP1 touch
- close-path efficiency = net close progress / total absolute close movement
- fraction of completed closes above entry
- fraction of green completed bars
- maximum close pullback from running high before TP1

### C. Immediate approach
- last 1-bar and last 3-bar net progress in R
- last 3-bar green fraction

### D. Known target geometry
- TP1 distance in R
- TP2 distance in R
- TP1→TP2 extension gap in R
- extension gap / TP1 distance
- number of causal objectives known at entry

## Discovery discipline
1. First compare EXTENDER vs STOPPER distributions independently in DEV and REF.
2. For each numeric feature, define DEV quartile cut points only.
3. Freeze those DEV cuts and apply the same bands to REF.
4. Report TP2 continuation rate and sample size by band.
5. Rank features by directional consistency across DEV and REF, not by DEV-only peak rate.
6. No multivariate rule, position sizing, or trade-policy promotion is allowed in S15.

## Boundary
S15 is diagnostic character discovery only. Any candidate continuation rule must be preregistered and tested separately after this stage.
