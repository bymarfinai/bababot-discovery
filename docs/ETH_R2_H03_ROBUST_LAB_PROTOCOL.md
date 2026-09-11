# ETH R2 H03 Robust Lab — Preregistered Protocol

## Scope

- Pair: ETHUSDT 5m.
- Direction: LONG only.
- Target habitat: 03:00–04:00 WIB, four 15-minute anchors.
- Development evidence available to the lab: 2022–2023 only unless a later stage is explicitly unlocked by this protocol.
- 2024 is HARD LOCKED during diagnosis/discovery/confirmation rounds.
- 2025+ OOS/reference validation remains CLOSED.
- Legacy E12–E16/H03 results are research history only and may not select a candidate in this lab.

## Fixed timing topology and economics

Unless a later hypothesis is preregistered before execution, use the frozen R1 coarse timing topology:
- lookbacks: 60, 120, 180, 240, 360 minutes;
- holds: 120, 240, 360, 480 minutes;
- fee/notional and causal feature construction exactly as inherited from the R1/E12 engine.

No fine LB/Hold search may be introduced to rescue a failed result.

## Bounded lab rule

Maximum five hypothesis rounds. A failed round does not authorize gate relaxation, threshold shopping, alternate-candidate rescue after a holdout is opened, or opening 2024. The lab may stop before Round 5 when falsification is sufficient.

## Round 1 — structural diagnosis

Diagnose only the plateau-supportive families already present in the frozen `ETH_R1_H03_ROBUST_TrainGrid.csv`.

Ranking is fixed before execution:
1. strict+temporal cell count;
2. largest connected component;
3. supportive cell count;
4. temporal breadth;
5. anchor breadth;
6. family median expectancy;
7. family median PF;
8. lexical rule name.

Round 1 does NOT freeze a trading candidate. It may nominate exactly one family hypothesis only when that family has either:
- at least one strict+temporal cell; or
- at least two connected/supportive cells with at least three positive half-years.

Otherwise H03 stops with `NO_FAMILY_HYPOTHESIS` and 2024 remains locked.

## Later rounds

Any Round 2+ test must be preregistered before its first execution and must be a structural hypothesis derived from the preceding failure mode, not a search for the best observed parameter.

Permitted architecture, when justified:
- definition/threshold perturbation with a small fixed grid while coarse timing stays frozen;
- nested discovery using 2022 only, followed by one-shot confirmation of the exact frozen region on 2023;
- cross-year invariance falsification using 2022 and 2023 independently.

If a 2022-only discovery opens 2023, no alternate 2022 region/rule/timing may be selected after seeing 2023.

## 2024 unlock rule

2024 may be opened only if a candidate/region is frozen without using 2024 and has already demonstrated broad parameter robustness plus independent temporal confirmation on 2022–2023. If unlocked, only the exact frozen candidate is evaluated once. Failure is final for that generation; no rescue candidate is allowed.

## Scientific stop rule

A clean FAIL is a valid result. If bounded rounds show no parameter- and time-invariant H03 LONG habitat, record `H03_LAB_NO_ROBUST_EDGE`, leave 2024 unopened, and stop rather than consume another round to force a PASS.
