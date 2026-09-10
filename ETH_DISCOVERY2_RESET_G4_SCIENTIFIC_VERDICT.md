# ETH Discovery 2 Reset — G4 Scientific Verdict

**Verdict: SUPPORTED.**

G4 performed preregistered ETH-native entry discovery on the frozen G2+G3 lineage and selected **NEXT_OPEN**. Both independent historical holdouts passed unchanged.

## Frozen parent
- ETHUSDT Binance Futures raw 5m.
- LONG.
- Reference start: **01:30 UTC (08:30 WIB)**.
- Reference duration: **180m**.
- Execution horizon: **720m**.
- Reference: **01:30–04:30 UTC / 08:30–11:30 WIB**.
- Execution: **04:30–16:30 UTC / 11:30–23:30 WIB**.
- G2 parent: first valid HIGH-side pressure.
- G3 structure: **DIRECT B00**, first strict completed close above H after the pressure event.

## G4 candidate family
G4 compared:
- NEXT_OPEN;
- resting buy limits `H + qR` with q = 0.00/0.02/0.04/0.06/0.08/0.10/0.12;
- order lives 5/15/30/60 minutes;
- total = **29 candidates**.

`L06_W30` was the exact historical Z5 price/patience control, but had no inherited status.

Selection used Development only. External and Reference Validation stayed closed until one entry was frozen.

## Development result
Frozen DIRECT B00 cases: **184**.

### Winner: NEXT_OPEN
- Fills: **184/184 = 100.0%**.
- Median entry excess above H: **0.057R**.
- Conditional E10: **52.7%**.
- Conditional E20: **44.0%**.
- Effective E10: **52.7%**.
- Effective E20: **44.0%**.
- Wilson 95% lower bound for effective E10: **45.5%**.
- Positive chronological blocks: **4/4**.
- Block effective E10: **56.5%, 58.7%, 50.0%, 45.7%**.
- Block effective E20: **50.0%, 45.7%, 43.5%, 37.0%**.

NEXT_OPEN was the only Development candidate passing the complete preregistered gate + applicable stability rule.

## What happened to resting limits
The resting-limit family showed a clear trade-off:
- deeper pullbacks improved purchase price but destroyed conditional continuation and effective opportunity capture;
- higher limits recovered participation and continuation, but their median price improvement versus NEXT_OPEN collapsed to approximately zero.

Selected examples:

| Candidate | Fill | Median improvement | E10 | E20 | Eff E10 | Eff E20 | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| NEXT_OPEN | 100.0% | +0.000R | 52.7% | 44.0% | 52.7% | 44.0% | **PASS** |
| L00_W30 | 77.2% | +0.046R | 31.0% | 24.6% | 23.9% | 19.0% | FAIL |
| L02_W30 | 82.1% | +0.026R | 34.4% | 29.8% | 28.3% | 24.5% | FAIL |
| L04_W15 | 84.2% | +0.006R | 44.5% | 35.5% | 37.5% | 29.9% | FAIL |
| **L06_W30 historical control** | **89.7%** | **+0.000R** | **44.2%** | **37.6%** | **39.7%** | **33.7%** | **FAIL** |
| L08_W30 | 94.0% | +0.000R | 48.0% | 39.9% | 45.1% | 37.5% | FAIL |
| L10_W30 | 95.1% | +0.000R | 50.9% | 40.6% | 48.4% | 38.6% | FAIL |
| L12_W30 | 96.2% | +0.000R | 52.0% | 41.8% | 50.0% | 40.2% | FAIL |

The old L06_W30 rule therefore **does not re-earn promotion** on the reset lineage.

This is consistent with G3's structural observation that successful post-B00 movement happens quickly. Waiting for meaningful price improvement preferentially misses or enters after the strongest immediate continuation paths.

## Historical replication of frozen NEXT_OPEN
### External
- B00: **88**.
- Fills: **88/88 = 100.0%**.
- E10: **55.7%**.
- E20: **44.3%**.
- Effective E10: **55.7%**.
- Effective E20: **44.3%**.
- Wilson effective E10: **45.3%**.
- **PASS**.

### Reference Validation
- B00: **91**.
- Fills: **91/91 = 100.0%**.
- E10: **50.5%**.
- E20: **41.8%**.
- Effective E10: **50.5%**.
- Effective E20: **41.8%**.
- Wilson effective E10: **40.5%**.
- **PASS**.

Both independent historical replication gates passed unchanged.

## Scientific interpretation
The current ETH-native reset lineage is now:

**LONG → 01:30 UTC reference start → R180 → E720 → first HIGH-side pressure → DIRECT B00 → NEXT_OPEN**

The reset has now independently rediscovered:
1. geometry/clock-duration behavior;
2. downstream structure;
3. executable entry timing.

The result specifically rejects the assumption that waiting for the old shallow L06 pullback is beneficial after the newly calibrated ETH structure. Under this geometry, the best structural entry is immediate execution at the next 5m open after completed B00.

## Technical correction record
The first G4 CI attempt completed Development calculations but crashed while reading the pandas Series column named `mode` through attribute syntax (`sel.mode`), which collided with the built-in `Series.mode()` method.

A technical-only corrected wrapper replaced those accesses with bracket syntax (`sel["mode"]`) and fixed the same accessor in holdout specification construction. No preregistered candidate, threshold, ranking rule, data partition, or experiment outcome was changed. The corrected CI run completed successfully.

## What G4 does NOT validate
G4 does not validate:
- TP or SL;
- maximum holding period / exit management;
- leverage;
- fees/slippage;
- dollar PnL;
- expectancy/PF/drawdown;
- live execution viability.

## Next valid experiment
The strongest next experiment is **G5 economic translation** on the fully frozen G2+G3+G4 lineage:

**LONG / 01:30 UTC / R180 / E720 / HIGH-side pressure → DIRECT B00 → NEXT_OPEN**.

G5 should rediscover TP/SL/hold geometry from scratch on this reset lineage. Old Z6 money geometry may appear only as historical comparison; its TP0.60R / SL0.30R / 120m configuration must not be inherited automatically.

Research/shadow only. No live promotion.
