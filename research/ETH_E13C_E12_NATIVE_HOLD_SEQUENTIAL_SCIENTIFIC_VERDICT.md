# ETH E13C — E12 Native-Hold One-Position Sequential Audit — Scientific Verdict

## Status
**ETH_E13C_NATIVE_HOLD_SEQUENTIAL_AUDIT_COMPLETE**

Development/shadow research only. No live promotion. OOS remained closed.

## Result-bearing run
- workflow run: **34578495898**
- job: **103196364926**
- head SHA: **15ba564db8348c5c2d98c8f69af9befa625f2d44**
- artifact: **10190625980**
- artifact SHA256: **a289ebe19f3633eb3435db54aac6e32efa4413e0672581dcf151d47b1b5e37c3**
- raw ETHUSDT 5m coverage: **100.0000%**

## What E13C tested
E13C preserves each source hour's exact E12 representative rule, lookback, and fixed hold. It changes only execution accounting: at most one LONG position may be active. Every later signal is skipped until the active trade exits at its original E12 fixed-hold timestamp.

No TP, SL, first-positive-close, profit floor, or new exit was introduced.

## P1 — FORMAL_PASS_ONLY
Eligible hours: E12K 23–00, E12L 00–01, E12M 01–02, E12O 03–04 WIB only.

### Independent E12 opportunities versus sequential execution
- raw opportunities: **1,027**
- sequentially executed: **476**
- busy-skipped: **551 (53.65%)**
- raw WR: **58.71%**
- sequential WR: **55.25%**
- raw net: **+$2,218.58**
- sequential net: **+$622.52**
- sequential expectancy: **+$1.31/trade**
- sequential PF: **1.351**
- raw DD: **$149.69**
- sequential DD: **$131.02**
- raw max loss streak: **10**
- sequential max loss streak: **6**
- average native hold among executed trades: **12.01h**; median **12h**

### Sequential era readout
- 2022: N **147**, WR **55.78%**, net **+$82.65**, exp **+$0.56**, PF **1.102**
- 2023: N **165**, WR **55.15%**, net **+$242.40**, exp **+$1.47**, PF **1.521**
- 2024: N **164**, WR **54.88%**, net **+$297.47**, exp **+$1.81**, PF **1.598**

### Source-hour realization
- 23–00 E12K H720: raw 274; executed **203 (74.09%)**; sequential WR **55.17%**; net **+$373.84**.
- 00–01 E12L H720: raw 238; executed **131 (55.04%)**; WR **54.96%**; net **+$192.48**.
- 01–02 E12M H960: raw 265; executed **95 (35.85%)**; WR **53.68%**; net **-$24.76**.
- 03–04 E12O H240: raw 250; executed **47 (18.80%)**; WR **59.57%**; net **+$80.97**.

## P2 — ALL_HOURLY_REPRESENTATIVES
Diagnostic only; FAIL-hour clues are not promoted.

- raw opportunities: **7,720**
- executed: **1,149**
- busy-skipped: **6,571 (85.12%)**
- raw WR: **56.14%**
- sequential WR: **51.00%**
- raw net: **+$14,492.42**
- sequential net: **+$381.19**
- sequential expectancy: **+$0.33/trade**
- sequential PF: **1.075**
- raw DD: **$1,365.11**
- sequential DD: **$390.17**
- raw loss streak: **27**
- sequential loss streak: **11**

Era:
- 2022: N364, WR51.92%, net **-$47.61**, exp -$0.13, PF0.979.
- 2023: N388, WR47.42%, net +$118.75, exp +$0.31, PF1.103.
- 2024: N397, WR53.65%, net +$310.04, exp +$0.78, PF1.193.

P2 therefore demonstrates that sequential locking alone does not justify using all E12 FAIL-hour clues. The formal-pass subset is much cleaner.

## Scientific interpretation
1. The user's live constraint matters materially: more than half of formal-pass E12 opportunities disappear once only one position may be active.
2. The four formal E12 PASS characters still retain positive aggregate Development economics after sequentialization: +$622.52, +$1.31/trade, PF1.351, with positive net in all three Development years.
3. Risk path improves: max loss streak falls from 10 to 6 and DD falls modestly from $149.69 to $131.02.
4. Opportunity priority emerges naturally from chronology and hold duration. E12K 23–00 captures 74% of its raw opportunities, while E12O 03–04 captures only 18.8%, because earlier long-hold positions frequently block later signals.
5. E12M 01–02 changes from a strong independent character to a small negative realized contribution (-$24.76) under this deterministic first-available sequential policy. This does not invalidate E12M; it shows that overlap/priority is now an execution-design problem.
6. Running all 24 representative clues is inferior to restricting the executor to formal PASS characters. FAIL-hour clues remain diagnostic only.

## Next research boundary
The next experiment should investigate **execution priority / selection among simultaneous temporal characters while preserving the one-position constraint and native E12 holds**, before discovering a new TP/SL. In particular, E13C shows that taking the first available formal signal mechanically can suppress later high-quality hours and materially changes each character's realized contribution.

Any priority logic must be preregistered separately; do not retroactively drop losing E12M trades or reorder hours based on E13C results.
