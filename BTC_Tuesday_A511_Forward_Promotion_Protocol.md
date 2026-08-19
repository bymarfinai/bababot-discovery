# BTC Tuesday A5.11 — Preregistered Forward Promotion Protocol

**Status: FROZEN BEFORE FIRST PRISTINE FORWARD OBSERVATION.**

**Research/shadow only. This protocol cannot promote or place a live order automatically. Live BBC remains untouched.**

## Purpose
Define, before the first pristine forward Tuesday on 2026-08-25, exactly how the accumulated Tuesday A5.11 forward ledger will be evaluated.

This prevents changing the standard after seeing favorable or unfavorable future outcomes.

The underlying shadow protocol remains `BTC_Tuesday_A511_Forward_Shadow_Protocol.md`.

## Frozen historical context — reference only
Canonical A5.11 historical anchor:
- 139 trades.
- 89 wins / 50 losses.
- WR 64.03%.
- PnL approximately +$130.33.
- Expectancy approximately +$0.9376/trade.
- PF 1.692.
- Max drawdown approximately $26.64 at the frozen $500 reference notional.

These values are context, not targets to optimize against.

## Evidence universe
Only rows in `BTC_Tuesday_A511_Forward_Shadow_Ledger.csv` that are:
- `evidence_class = TRUE_FORWARD`;
- `status = SETTLED`;
- unique by Tuesday WIB date;
- produced with the frozen model fingerprint;
- free of forward-ledger integrity violations.

August 4/11/18 are implementation fixtures and can never enter this universe.

## Primary forward metrics
For settled true-forward A5.11 outcomes compute, without threshold tuning:
- number of opportunities;
- wins / losses / WR;
- total PnL;
- expectancy per opportunity;
- gross-profit / gross-loss profit factor;
- max closed-trade drawdown;
- longest loss streak;
- deterministic bootstrap confidence interval for mean PnL/trade.

Bootstrap specification is frozen:
- ordinary resampling of settled Tuesday trade PnLs with replacement;
- 20,000 bootstrap samples;
- random seed `20260819`;
- report 80% and 95% percentile intervals.

WR confidence interval is descriptive only and is not a promotion gate.

## Telemetry diagnostics — never promotion gates inside this protocol
Report, but do not optimize or gate on:
- G1 predicted class attribution;
- G1 pSELL / point SELL lift;
- G6 weekly SELL health attribution;
- G7 diagnostic weight;
- G0 oracle label attribution after settlement.

The purpose is to learn whether the August hostile-regime warning persists prospectively without turning those diagnostics into same-sample rules.

# Frozen staged decision framework

## Stage F0 — fewer than 12 settled Tuesdays
Decision: `OBSERVE_ONLY`.

No strategy promotion, rejection, threshold change, retraining, or A5.11 modification is permitted from this sample size.

## Stage F1 — 12 to 25 settled Tuesdays
Decision: `EARLY_CHECKPOINT_ONLY`.

The evaluator may label the checkpoint:
- `EARLY_SUPPORTIVE` when total PnL > 0, expectancy > 0, and PF > 1;
- `EARLY_CAUTION` otherwise.

Neither label is eligible for production promotion or strategy rejection.

## Stage F2 — 26 to 51 settled Tuesdays
This is the first sample size eligible for a **candidate review**, not live deployment.

`CANDIDATE_REVIEW_ELIGIBLE` requires ALL:
1. total PnL > 0;
2. expectancy per trade > 0;
3. PF >= 1.20;
4. lower bound of the frozen 80% bootstrap CI for mean PnL/trade > 0;
5. max forward drawdown <= historical full-sample A5.11 max DD reference of $26.64;
6. zero ledger/model-integrity violations.

If any condition fails: `CONTINUE_FORWARD_OBSERVATION`.

A passing F2 result does not authorize live trading. It only permits a separate live-parity engineering review while forward observation continues unchanged.

## Stage F3 — 52 or more settled Tuesdays
This is the first **strong forward evidence** gate.

`LIVE_ENGINEERING_REVIEW_ELIGIBLE` requires ALL:
1. total PnL > 0;
2. expectancy per trade > 0;
3. PF >= 1.20;
4. lower bound of the frozen 95% bootstrap CI for mean PnL/trade > 0;
5. max forward drawdown <= $26.64 historical A5.11 DD reference;
6. zero ledger/model-integrity violations.

This result still does NOT authorize automatic live trading. It permits a separate explicit review of exchange execution parity, operational risk, capital sizing, and production safeguards.

### Strong negative evidence
At F3, if the **upper bound** of the frozen 95% bootstrap CI for mean PnL/trade is <= 0, classify `FORWARD_EDGE_REJECTED`.

Otherwise, if the positive gate is not met, classify `CONTINUE_FORWARD_OBSERVATION`.

## Why WR is not a hard gate
A5.11 has frozen dynamic management layers and non-uniform realized PnLs. Economic expectancy and PF therefore carry more information than forcing the future WR to equal the historical 64.03%.

WR and its interval remain visible diagnostics.

## Explicit anti-overfit prohibitions
Until a new named research protocol is explicitly created, do not:
- change the 12 / 26 / 52 stage boundaries;
- change PF 1.20;
- change the $26.64 drawdown reference;
- change bootstrap seed, resample count, or interval levels;
- change G1/G6/G7 thresholds based on forward outcomes;
- retrain G1 on forward outcomes;
- change A5.11 TP, SL, hold, A5.2, FastMR, or runner-recovery rules;
- exclude an unfavorable valid Tuesday;
- include August fixtures as forward evidence;
- reset the ledger after a losing period.

Any future protocol revision must receive a new version/name and cannot rewrite earlier forward evidence.

## Final principle
The forward system is designed to make rejection possible. The objective is not to prove A5.11 works; it is to determine whether the frozen historical edge survives genuinely unseen Tuesdays strongly enough to justify a later, separate live-engineering decision.
