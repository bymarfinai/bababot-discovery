# BTC Temporal Friday F6.20 — Failure-to-Accelerate Management Checkpoint

**Status:** COMPLETE — NO CANDIDATE PROMOTED  
**Research only; live BBC untouched. Frozen F6.12/F6.9/F6.5 and F6.18 D3 unchanged.**

## Baseline parity
Frozen four-layer stack (FIB5 → EARLY10 → F6.5, plus chronological D3):
- N 138
- WR **51.45%**
- PnL **+$123.232**
- PF **1.680**
- DD **$28.699**

## Predeclared causal candidates
No threshold sweep.

### A35_MILESTONE_LOST
35 minutes after first +0.5R, exit at actual decision open iff:
- current progress has fallen back below +0.5R;
- latest close < EMA7;
- latest 5m taker imbalance < 0.

Result:
- 22 actions (D15 / V7)
- 8 low givebacks caught
- 10 eventual winners acted
- 5 loss→positive conversions
- **4 winner→nonpositive conversions**
- incremental **-$20.107** (D -$15.661 / V -$4.446)
- managed PnL **+$103.124**
- WR **50.72%**
- PF **1.645**
- DD **$30.383**
- **FAIL**

### A65_STRUCTURE_FAIL
65 minutes after first +0.5R, exit iff:
- progress remains below +0.5R;
- close < EMA20;
- EMA7 <= EMA20.

Result:
- 16 actions (D10 / V6)
- 7 low givebacks caught
- 8 eventual winners acted
- 0 loss→positive
- **6 winner→nonpositive**
- incremental **-$2.519** (D -$1.657 / V -$0.861)
- managed PnL **+$120.713**
- WR **47.10%**
- PF **1.721**
- DD **$28.115**
- **FAIL**

### A65_STRUCTURE_FLOW
A65_STRUCTURE_FAIL plus latest 5m taker imbalance < 0.

Result:
- 7 actions (D5 / V2)
- 4 low givebacks caught
- 3 eventual winners acted
- 0 loss→positive
- 2 winner→nonpositive
- incremental **+$0.803**, but D/V **+$1.331 / -$0.528**
- managed PnL **+$124.035**
- WR **50.00%**
- PF **1.707**
- DD **$31.583**
- **FAIL** because Validation is negative, WR deteriorates, DD worsens, and winners are converted nonpositive.

## Interpretation
F6.19 correctly identified a real failure-to-accelerate phenotype, but a single fixed snapshot at +35m or +65m is not selective enough for management. Healthy eventual winners can temporarily lose the +0.5R milestone, EMA7, EMA20, and even buyer flow before recovering.

The +35m rule proves timing is too early/noisy. The +65m rules prove deeper EMA deterioration alone is also insufficient; waiting longer reduces false alarms but can make the exit too late to convert low-giveback losses into positive outcomes.

Therefore the useful next question is not “which fixed checkpoint should cut?” but:
> what distinguishes a temporary structural pullback that re-accelerates from a persistent failure-to-accelerate trajectory?

A next forensic should compare **trajectory persistence / recovery attempts** between the low givebacks and the false-positive winners: number of EMA7 reclaims, duration below EMA7/EMA20, slope/recovery of progress, higher-low formation, taker recovery after negative flow, and whether price can rebuild the +0.5R milestone after losing it.

## Guardrail
Do not retune the 35/65m timing or thresholds on this sample. F6.20 is a valid negative management result, not evidence that the underlying failure-to-accelerate mechanism is absent.
