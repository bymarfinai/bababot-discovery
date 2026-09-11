# ETH R2 H03 — Round 3 Nested Market-State Test Preregistration

Round 2 showed the pooled `RV_HIGH__RANGE_MID` definition is not robust to nested percentile perturbation. Round 3 therefore does not tune its boundary. It asks a different structural question: can H03 reveal any two-feature causal market-state habitat in 2022 that forms a broad timing region and then independently reappear in 2023?

## R3A discovery firewall

- Discovery period: 2022-01-01 through 2022-12-31 only.
- 2023 is an unopened internal confirmation holdout during R3A.
- 2024 remains HARD LOCKED.
- 2025+ OOS remains CLOSED.
- Grammar: the 36 existing E11 two-feature pair states only; no new thresholds and no DRIVE_UP/DOWN overlay.
- Timing: frozen 5 x 4 R1 coarse LB/Hold grid = 20 timings.
- Total R3A search: 36 x 20 = 720 cells.

## 2022 cell gates

A discovery-supportive cell requires:
- N >=45, WR >=52%, net >0, expectancy >0, PF >=1.05, DD <=125, loss streak <=10;
- both 2022 half-years N>=18, expectancy>0, PF>1.

A discovery-strict cell additionally requires:
- N>=60, WR>=55%, expectancy>=+$0.50/trade, PF>=1.20, DD<=110, loss streak<=8;
- at least 3 evaluable anchors (N>=12) and at least 3 anchors with expectancy>0 and PF>1.

## 2022 robust region

For the same pair-state rule, supportive cells must form an orthogonally connected region with:
- >=4 cells;
- >=2 distinct lookbacks;
- >=2 distinct holds;
- >=1 discovery-strict cell;
- region median expectancy >=+$0.25/trade;
- region median PF>=1.10;
- region median of each cell's minimum half-year expectancy >0.

Regions are ranked before 2023 is opened by: strict cells, region size, median minimum-half expectancy, median expectancy, median PF, lower median DD, lexical rule name. Representative is the strict-cell grid medoid, ties shorter hold then shorter lookback.

## R3B one-shot 2023 confirmation

If R3A finds a qualifying region, freeze its exact rule, exact set of timing cells, and representative before opening 2023. R3B may evaluate only that frozen region. No alternate 2022 region/rule/timing may be selected after 2023 is seen.

If R3A finds no qualifying region, 2023 remains unopened for this round. In either case 2024 remains locked.
