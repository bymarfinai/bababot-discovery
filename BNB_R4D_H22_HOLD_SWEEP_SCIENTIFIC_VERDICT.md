# BNB R4d — H22 Hold-Duration Sweep Scientific Verdict

## Frozen setup
- Target: BNBUSDT H22 WIB `RV_HIGH__RANGE_MID`
- Entry policy unchanged from R4c: 2-of-3 consensus across LB180/LB240/LB360, earliest qualifying H22 anchor, LONG, one position/day, no pyramiding
- Only variable tested: Hold 360 / 480 / 720 / 960 minutes
- 2022-2025 execution-synthesis diagnostic
- 2026 remained closed

## Formal result
No hold duration achieved full formal support under the preregistered requirement of 4/4 annual gates + pooled gate + 2-bps stress gate.

Preregistered ranking selected **H720 (12 hours)** as the best execution candidate.

### Ranked pooled 0-bps results
1. **H720** — N113, WR59.29%, Net +$297.77, Exp +$2.64/trade, PF2.041, DD$33.64, LS6, annual gates 3/4, pooled PASS, 2bps stress PASS.
2. **H960** — N113, WR61.06%, Net +$316.42, Exp +$2.80/trade, PF1.906, DD$72.46, LS5, annual gates 3/4, pooled PASS, 2bps stress PASS.
3. **H480** — N113, WR57.52%, Net +$105.61, Exp +$0.93/trade, PF1.331, DD$54.15, LS6, annual gates 2/4, pooled PASS, 2bps stress FAIL.
4. **H360** — N113, WR53.98%, Net +$48.42, Exp +$0.43/trade, PF1.169, DD$60.47, LS6, annual gates 2/4, pooled FAIL, 2bps stress FAIL.

## Why H720 ranks above H960
H960 has slightly higher pooled WR, Net, and expectancy, but the preregistered ranking prioritizes robustness floor before pooled headline economics. H720 has a higher minimum annual expectancy (+$1.27 vs +$1.11), materially lower pooled drawdown ($33.64 vs $72.46), and stronger pooled PF (2.041 vs 1.906). Therefore H720 remains the more robust deployment candidate despite H960's larger headline Net.

## Duration conclusion
- 6h is too short: 2023 and 2025 are negative; cost stress collapses.
- 8h improves materially but 2025 remains negative and 2bps stress gate fails.
- 12h is the best robustness/economics balance and survives 10bps/side with positive pooled expectancy and PF.
- 16h is economically strong but carries materially larger drawdown and a weaker worst-year expectancy floor.

## Deployment interpretation
Freeze **H720 / 12h** as the preferred H22 execution duration for shadow/live-candidate use. This is **BEST_EXECUTION_CANDIDATE_NOT_FORMALLY_SUPPORTED**, not a formal historical pass, because the 2023 annual WR remains 51.61% versus the frozen 52% annual threshold.

No post-result rescue or threshold relaxation is permitted. 2026 remains reserved for forward/shadow observation rather than re-optimization.

Research/shadow only.