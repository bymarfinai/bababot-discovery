# ETH F85/F15 Transfer — M2 Causal Eligibility Correction

**Status: PREREGISTERED before corrected result-bearing execution.**

## Blocking defect found during M3 setup
The first M2 implementation encoded `eligible_start = leave_bar_start + 10 minutes`.

The frozen B27W chronology is instead:
- the causal leave bar completes;
- the immediately following raw 5m bar is the first entry-eligible bar.

Therefore if the leave bar starts at `t`, corrected eligibility is exactly:

`eligible_start = t + 5 minutes`.

The BTC B27W synthetic control explicitly fixes `leave_bar_start = idx[2]` and `eligible_start = idx[3]`.

## Allowed change
Exactly one research-semantic correction is authorized:
- replace M2 eligibility delay from `+2*BAR5` to `+BAR5`.

No other rule, habitat, level grid, partition, H2 definition, opposite-break definition, screen threshold, or metric may change.

## Frozen M2 screen
A habitat x level remains `SCREEN_PASS` only if in each major partition:
- >=30 pre-H2 fills; and
- >=70% H2 arrival among fills.

## Mandatory correction audit
Before persistence:
1. synthetic LONG K1 episode -> leave -> immediately following bar is first eligible bar;
2. same for SHORT mirror;
3. no fill on leave bar;
4. no fill on H2/opposite terminal bar;
5. all existing M2 rules are otherwise unchanged.

The original M2 result is superseded after the corrected result is persisted.

**Do not run M3 until corrected M2 output is observed.**
