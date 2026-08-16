# BTC Temporal Friday15 — A6.10–A6.12 Dynamic Wrong-Way Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** PROMISING FULL-COVERAGE DYNAMIC LAYER — NOT FROZEN CHAMPION / NOT LIVE  
**Symbol:** BTCUSDT  
**Parent:** every Friday exact 15:00 WIB BUY, TP 2.0%, SL 0.7%, max hold 6h, fee 0.15% roundtrip, $500 fixed notional  
**Sample:** 138 Friday occurrences; first 82 discovery / last 56 validation  
**Live BBC:** untouched

## Parent
- N138
- 66 winners / 72 losers
- WR 47.83%
- PnL +$64.630
- PF 1.266
- DD $56.530
- loss streak 8
- discovery +$99.194, WR54.88%
- validation -$34.563, WR37.50%

## A6.10 — 60m dynamic thesis-state

Candidate rules were based on the A6.9b taxonomy boundary +0.30% and evaluated at 15/30/60m. Candidate selection used discovery only.

Selected discovery rule at 60m, using only completed information before the decision open:
- cumulative MFE still < +0.30%
- current progress < 0
- taker-flow < 0
- current price below completed EMA20
- completed EMA20 15m slope < 0

Signals:
- full 33
- discovery 17
- validation 16

Eventual-loss precision:
- full 28/33 = 84.85%
- discovery 14/17 = 82.35%
- validation 14/16 = 87.50%

Signal labels full:
- eventual winners 5
- A wrong-way 17
- B weak-pop 4
- C giveback 3
- D deep-giveback 4

Direct CUT or immediate FLIP at 60m was rejected because the five false-positive eventual winners were economically important.

## A6.11 — recovery confirmation

Instead of acting at 60m, keep the BUY alive and require persistent failure later.

Selected confirmation at 120m:
- initial A6.10 60m failure state occurred
- cumulative MFE still < +0.30%
- current progress still < 0

Confirmed signals:
- full 27: 25 eventual losses / 2 eventual winners => 92.59% loss precision
- discovery 11: 11/11 eventual losses => 100% precision
- validation 16: 14/16 eventual losses => 87.50% precision

This demonstrates that many false 60m failures recover within the following hour, while persistent no-impulse/negative state is much cleaner.

### Predeclared action family
After confirmation, close the original BUY at actual 120m open and optionally flip SHORT for the remaining original 6h horizon. Both legs pay their roundtrip fee. Same-bar ambiguity is adverse-first.

Results:
- FLIP short TP0.7/SL0.7: full WR50.72%, +$26.522 (rejected)
- FLIP short TP1.0/SL0.7: full WR52.17%, +$77.878; discovery delta +$8.812; validation delta +$4.435
- FLIP short TP1.0/SL1.0: full WR52.17%, +$77.845; discovery delta +$12.441; validation delta +$0.773

A6.10 discovery-only economic selector preferred TP1.0/SL1.0 because it had the largest discovery PnL. However TP1.0/SL0.7 gave the cleaner cross-period improvement and lower short-side risk. Because that preference uses cross-period inspection, TP1.0/SL0.7 is treated only as a **provisional balanced candidate**, not untouched OOS evidence.

## A6.12 — fixed robustness of balanced TP1.0 / SL0.7 flip

Fixed dynamic rule:
1. all 138 Friday trades still enter BUY at 15:00 WIB;
2. at 60m mark warning if MFE<0.30%, progress<0, taker<0, price<EMA20 and EMA20 slope<0;
3. do not act yet;
4. at 120m, if MFE is still <0.30% and progress is still negative, close BUY at actual open and flip SHORT;
5. SHORT TP1.0%, SL0.7%, expiry remains the original 6h horizon.

### Full
- N138 unchanged
- WR 47.83% -> **52.17%**
- PnL +$64.630 -> **+$77.878**
- expectancy $0.4683 -> **$0.5643/trade**
- PF 1.266 -> **1.325**
- loss streak 8 -> **4**
- DD $56.530 -> $57.192
- delta +$13.248

27 actions:
- 8 original loss -> positive
- 17 loss -> still loss
- 2 original winner -> loss
- 0 winner -> winner among intervention set

Thus net +6 wins, explaining WR 47.83% -> 52.17%.

### Chronological blocks — intervention delta
- B1 +$10.809
- B2 +$1.722
- B3 +$4.826
- B4 -$7.655
- B5 -$0.890
- B6 +$8.276
- B7 -$3.199
- B8 -$0.641

Only **4/8 blocks** improve, so this is not yet a uniformly robust management layer.

### Calendar years
- 2024: base +$69.736 -> new +$79.439, delta **+$9.702**
- 2025: base -$14.185 -> new -$6.799, delta **+$7.386**
- 2026 through July: base +$2.898 -> new -$0.943, delta **-$3.841**

The layer helps 2024–2025 but slightly hurts 2026, another reason not to freeze it as final.

### Leave-one-intervention-out
If any one of the 27 interventions is disabled, total strategy PnL ranges from **+$70.261 to +$88.689**, always remaining above zero. The aggregate result is not explained by one single intervention.

### Extra execution-cost stress on intervention only
Baseline already includes the normal fees on both BUY and SHORT legs.
- +0.02% extra cost per intervention: +$75.178
- +0.05%: +$71.128
- +0.10%: +$64.378
- +0.15%: +$57.628

The intervention remains aggregate-profitable under these stress costs, although at +0.10% the total PnL is essentially back to the original parent level.

## Verdict

The **state detector is substantially stronger than the action rule**.

Strong evidence:
- a 60m failed-rebound warning state exists and is stable across discovery/validation;
- waiting for persistence until 120m raises eventual-loss precision to 92.59%;
- direct 60m action is too early;
- a 120m conditional reverse can raise full-coverage WR and PnL without skipping any Friday occurrence.

Weaknesses:
- only 4/8 chronological blocks get positive intervention delta;
- 2026 delta is negative;
- two eventual winners are damaged by the 120m flip;
- TP1.0/SL0.7 balanced preference is not pristine OOS because it was compared after seeing both halves.

**Current status:** keep as a provisional dynamic wrong-way layer. Do not deploy/freeze as final Friday champion yet. The next separate improvement family should analyze the 32 C+D losses that first reached >=+0.50% and later gave back, while keeping all 138 parent entries.
