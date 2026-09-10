# ETH Discovery 2 Reset — G6 Scientific Verdict

**Status: `ETH_DISCOVERY2_RESET_G6_ATLAS_COMPLETE`.**

G6 completed the preregistered fee-adjusted payoff / excursion atlas on the fully frozen ETH-native lineage:

**LONG / 01:30 UTC / R180 / E720 / first HIGH-side pressure → DIRECT B00 → NEXT_OPEN**.

G6 did not select or promote any TP, SL, hold, or live strategy.

## Frozen sample
- Development: **184** entries.
- External: **88** entries.
- Reference Validation: **91** entries.
- ETHUSDT raw 5m coverage: **100%**.
- Fixed notional: **$500**.
- Fixed round-trip cost: **$0.75**.
- No compounding and no extra slippage model.

All frozen entry-count invariants matched G4 exactly.

## Core finding
The G5 failure is **not** explained by an absence of favorable post-entry movement.

Across the full remaining frozen execution window:

| Partition | Median fee BE | Median MFE | Median MAE | MFE clears fee | Terminal net-positive | Terminal net sum |
|---|---:|---:|---:|---:|---:|---:|
| Development | **0.112R** | **0.943R** | **0.906R** | **89.7%** | **45.1%** | **-$164.73** |
| External | **0.066R** | **1.156R** | **0.476R** | **93.2%** | **62.5%** | **+$479.30** |
| Reference Validation | **0.094R** | **0.854R** | **0.837R** | **98.9%** | **40.7%** | **-$48.30** |

Therefore the signal very frequently develops enough favorable excursion to pay transaction cost, but much of that favorable excursion is subsequently given back if the position is simply marked at the end of the remaining session.

This is a materially different diagnosis from “the signal has no movement.”

## Stable favorable-excursion region
The preregistered target-shape rule identified the following major levels as cross-partition stable:

- **0.30R**
- **0.60R**
- **1.00R**

Reach rates:

| Target | Development | External | Reference Validation |
|---|---:|---:|---:|
| **0.30R** | **78.8%** | **83.0%** | **83.5%** |
| **0.60R** | **65.8%** | **65.9%** | **63.7%** |
| **1.00R** | **45.7%** | **54.5%** | **39.6%** |

The 0.30R–0.60R area is especially important because it is both frequently reached and, for nearly all sessions at those levels, already beyond the trade-specific fee break-even barrier.

Fee-profitable target-reach rates were:

| Target | Development | External | Reference Validation |
|---|---:|---:|---:|
| 0.20R | 71.7% | 87.5% | 92.3% |
| **0.30R** | **75.5%** | **83.0%** | **83.5%** |
| **0.40R** | **71.7%** | **76.1%** | **75.8%** |
| **0.60R** | **65.8%** | **65.9%** | **63.7%** |

This provides a stable **cost-clearing harvest zone**, not yet a validated exit rule.

## Time-to-target and adverse path
Development median time-to-target:
- 0.15R: **15m**
- 0.20R: **25m**
- 0.30R: **45m**
- 0.40R: **105m**
- 0.60R: **160m**
- 0.80R: **185m**
- 1.00R: **222.5m**
- 1.50R: **305m**
- 2.00R: **405m**

For successful Development reaches, p75 MAE before target was approximately:
- 0.30R target: **0.427R**
- 0.40R: **0.502R**
- 0.60R: **0.571R**
- 0.80R: **0.650R**
- 1.00R: **0.653R**

This explains why the G5 bracket family struggled: successful ETH paths can travel materially adverse before ultimately reaching a favorable target, so a tight static stop destroys many eventual winners. But simply widening the stop is not sufficient evidence of a profitable solution because the reward/risk deteriorates and fee remains material.

## First-hit structure
G6 found **27** target/adverse cells where favorable-first exceeded adverse-first in all three historical partitions.

Examples:

| Target | Adverse | Development F/A | External F/A | Ref-Val F/A |
|---|---:|---:|---:|---:|
| 0.30R | 0.60R | **66.8% / 29.3%** | **75.0% / 20.5%** | **71.4% / 25.3%** |
| 0.40R | 0.80R | **62.0% / 29.9%** | **69.3% / 19.3%** | **70.3% / 17.6%** |
| 0.60R | 0.80R | **54.3% / 34.8%** | **61.4% / 21.6%** | **56.0% / 27.5%** |
| 0.60R | 1.00R | **57.1% / 31.0%** | **63.6% / 17.0%** | **60.4% / 18.7%** |

However, this must **not** be misread as proof that a wider static SL works. A conservative probability-weighted first-hit R proxy remained too small in Development relative to the median **0.112R** fee burden. G5 already established that the tested static-bracket family did not survive cost.

## Chronological stability
Development was split into four near-equal chronological blocks of 46 trades each.

Full-window MFE medians were:
- Block 1: **0.861R**
- Block 2: **0.827R**
- Block 3: **1.354R**
- Block 4: **0.905R**

MFE >= 0.60R rates were:
- **63.0% / 65.2% / 67.4% / 67.4%**

MFE >= 0.30R rates were:
- **82.6% / 82.6% / 78.3% / 71.7%**

Thus the 0.30R–0.60R favorable excursion zone is present across all four Development blocks rather than being driven by one period.

The fee-clear rate by block was also high and stable:
- **93.5% / 89.1% / 87.0% / 89.1%**.

## Important time-horizon detail
The preregistered path ends at the earlier of execution end or entry + 720m. Because B00/NEXT_OPEN occurs after the E720 execution window has already begun, no trade has a complete **720 minutes after entry** remaining. Therefore the 720m time-slice has zero fully available observations by construction; the full-window MFE/MAE statistics use each trade's actual remaining frozen execution window and remain valid.

## Scientific interpretation
G6 supports **option 1, with an important qualification**:

> There is a stable fee-adjusted payoff region worth preregistering in a next experiment, but the evidence points toward **harvesting / give-back control**, not toward another plain static TP×SL grid.

The strongest repeated facts are:
1. 89.7%–98.9% of entries develop MFE beyond their own transaction-cost break-even;
2. only 40.7%–62.5% remain net-positive if simply held to the remaining execution end;
3. 0.30R and 0.60R target reach is stable across Development, External, and Reference Validation;
4. successful paths often experience substantial adverse excursion before target;
5. G5's static bracket family was net-negative everywhere.

Together these imply that the next scientific question should be **how to monetize early cost-clearing excursion without giving up all participation in the larger 0.60R–1.00R continuation tail**.

## Strongest next experiment — G7 staged harvest / cost recovery
G7 should remain on the frozen G2+G3+G4 entry and test a finite, preregistered **staged management** family derived from the broad G6 plateaus.

A scientifically justified family would compare:
- first harvest around the stable cost-clearing zone: **0.30R / 0.40R / 0.60R**;
- partial sizes such as **33% / 50% / 67%**;
- remaining runner targets around **0.60R / 0.80R / 1.00R / 1.50R** where applicable;
- post-harvest protection rules that are causal and finite, e.g. retain original stop versus move protection toward entry / fee-covered level;
- a finite adverse allowance informed by G6, not copied from G5 or another pair.

G7 must explicitly charge the full fixed transaction-cost model and must use Development for selection with External and Reference Validation closed until one management rule is frozen.

Do **not** simply widen G5's stop or rerun a denser static grid. That would ignore the primary G6 discovery: the ETH-native signal commonly creates monetizable favorable excursion but then gives it back.

Research/shadow only. No live promotion or profit guarantee.
