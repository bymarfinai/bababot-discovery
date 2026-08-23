#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
REG=ROOT/'BABA_BOT_RESEARCH_RESULTS_REGISTRY.md'
MARK='## B27BJ — 24H Magnitude-Aware SIDEWAYS Redesign Audit'
BLOCK=r'''## B27BJ — 24H Magnitude-Aware SIDEWAYS Redesign Audit

**Source:** `BTC_24H_MAGNITUDE_AWARE_SIDEWAYS_REDESIGN_B27BJ_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BJ_MAGNITUDE_AWARE_REDESIGN_NOT_SUPPORTED`.**

**Purpose:** test a minimal magnitude-aware redesign of first-SIDEWAYS handling without hand-picking ATR thresholds. Separate BULL-origin and BEAR-origin logistic regressions were trained on `development` only using six preregistered causal B27BI features; external and reference_validation were strictly out-of-sample. The state-machine candidate inherited the prior directional state for exactly one 4H interval only when `P(RESUME)>=0.50`.

### Out-of-sample classifier performance

| Origin | Partition | N | AUC | Balanced accuracy | RESUME recall | TRANSITION recall |
|---|---|---:|---:|---:|---:|---:|
| BULL | external | 163 | 0.652 | 0.612 | 59.6% | 62.7% |
| BULL | reference_validation | 150 | 0.763 | 0.685 | 80.6% | 56.4% |
| BULL | pooled OOS | 313 | 0.690 | 0.637 | 68.2% | 59.1% |
| BEAR | external | 108 | 0.664 | 0.587 | 75.0% | 42.3% |
| BEAR | reference_validation | 134 | 0.637 | 0.558 | 67.3% | 44.3% |
| BEAR | pooled OOS | 242 | 0.654 | 0.573 | 71.2% | **43.5%** |

### Detector effect

- Raw pooled-major one-interval flip-back: **459/2,202 = 20.8%**.
- B27BJ one-interval flip-back: **177/1,640 = 10.8%**.
- `INHERITED_PAUSE` first-SIDEWAYS intervals: **604**.
- Pooled BULL persistence: **90.9% -> 93.2%**.
- Pooled BEAR persistence: **89.3% -> 91.9%**.
- Maximum major-partition occupancy drift: **20.5pp -> 21.2pp** (worse).
- Direct BULL<->BEAR change share: **7.0% -> 13.5%**.

**Why promotion failed:** the candidate dramatically reduced SIDEWAYS flip-back noise and improved directional persistence, but the BEAR-origin model hid too many genuine transitions: pooled-OOS TRANSITION recall was only **43.5%**, below the frozen 55% gate. It also worsened occupancy drift from 20.5pp to 21.2pp. Therefore the exact B27BJ threshold/model/state semantics are not promoted and must not be post-hoc tuned.

**Key interpretation:** magnitude-aware first-SIDEWAYS information is real out of sample (all origin/partition AUCs exceed 0.60), especially for BULL-origin, but a symmetric one-bar inherited-pause rule is too aggressive for BEAR-origin. Any next redesign must use a new preregistered experiment ID; no trading direction or entry research is authorized from B27BJ.

---

'''
text=REG.read_text()
if MARK not in text:
    anchor='# REGIME DETECTOR FOUNDATION\n\n'
    if anchor not in text: raise SystemExit('registry anchor missing')
    text=text.replace(anchor,anchor+BLOCK,1)
    REG.write_text(text)
    print('inserted B27BJ registry block')
else:
    print('B27BJ registry block already present')
