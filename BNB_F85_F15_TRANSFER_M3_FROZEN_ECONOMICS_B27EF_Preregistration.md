# B27EF — BNB Frozen BTC-Rule Economics Transfer — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Test whether the exact BTC signal and exit rules produce a robust economic BNB portfolio after B27EE identified three independently surviving habitats.

B27EF is an economics milestone only. It MUST NOT discover or tune clocks, F-levels, confirmation rules, stops, targets, runner steps, sizing, fees, or arbitration.

## Frozen prerequisite and habitat set
B27ED M1 must be supported and B27EE must already exist.

Only these B27EE-passing habitats are eligible:
- `ALT_0330` LONG;
- `RAW_0530` LONG;
- `SHORT_2000` SHORT.

`LONDON` and `RAW_2330` are excluded because they failed the preregistered B27EE exact-signal transfer gate. This exclusion was decided by B27EE before B27EF economics are observed.

## Frozen entry generation
Use the repository's unchanged `bbc_f85_f15_signals.py` causal raw-5m adapters.

LONG:
- same BTC K1 OPP0 semantics;
- causal leave;
- first pre-H2 F85 touch is decisive;
- same-bar close > F85;
- next raw 5m open entry only if `F35 < open < H`;
- ALT_0330 `TOUCH_FIRST_HALF <=195m` retained;
- RAW_0530 `RANGE_COMPLETED_SECOND_HALF >=165m` retained.

SHORT20:
- same BTC K1 OPP0 semantics;
- causal leave;
- first pre-H2 F15 touch is decisive;
- same-bar close < F15;
- next raw 5m open entry only if `L < open < F65`.

No BNB-specific entry rule is allowed.

## Frozen economics
Research sizing and fee are copied from BTC research:
- notional: **$500 per accepted trade**;
- roundtrip fee: **$0.40**.

### ALT_0330 LONG
Exact BTC fixed-E20 management:
- target `E20 = H + 0.20R`;
- completed-close invalidation `close < F35`;
- TP touch has priority on a bar over close invalidation;
- if unresolved, exit at execution-end next 5m open.

### RAW_0530 LONG
Exact BTC B27DQ live-executable N+2 E10 breathing runner:
- before E20 arm, completed-close `F35` invalidation remains active;
- E20 touch arms runner;
- initial E10 floor and later 0.10R ratchets are learned from completed bars and become active only at N+2;
- active floor gap-open/touch behavior is exactly B27DQ;
- placement-buffer F35 behavior and execution-end exit are exactly B27DQ.

Implementation must call the existing B27DQ runner function rather than reimplementing it.

### SHORT_2000
Exact BTC B27DR/B27DU fixed economics:
- target `E20_DOWN = L - 0.20R`;
- completed-close invalidation `close > F65`;
- target touch has priority over close invalidation on the same bar;
- unresolved trade exits at execution-end open.

Implementation must call the existing B27AD/B27DR fixed SHORT simulator rather than reimplementing it.

## One-BNB-position portfolio lock
Signals are sorted chronologically by entry timestamp. At most one BNB position may be active.
- candidate is accepted only if no earlier accepted BNB trade remains open at its entry timestamp;
- otherwise it is blocked;
- a position whose frozen exit timestamp is `<=` the next candidate entry is considered closed;
- deterministic same-timestamp priority: `ALT_0330`, then `RAW_0530`, then `SHORT_2000`.

No economic outcome may influence arbitration.

## Partitions
Use the same B27ED/B27EE historical partitions:
- external;
- development;
- reference_validation;
- august diagnostic.

Primary gate uses pooled major = external + development + reference_validation.

## Required outputs
Persist candidate-level detail and summary tables reporting:
- candidates / accepted / blocked;
- wins;
- WR;
- PF;
- expectancy;
- net PnL;
- max loss streak;
- source contribution;
- partition contribution;
- exit reasons.

## Conservative execution stress
Diagnostic repricing only; trade identity, exit reason, and timestamps remain frozen.
Apply symmetric adverse slippage to both entry and exit fills:
- LONG: entry `*(1+bps/10000)`, exit `*(1-bps/10000)`;
- SHORT: entry `*(1-bps/10000)`, exit `*(1+bps/10000)`.

Report 0, 2, 5, 10 bps per fill.

## Frozen decision gate
`B27EF_BNB_FROZEN_ECONOMICS_SUPPORTED` only if pooled-major primary portfolio satisfies ALL:
1. accepted N >= 60;
2. WR >= 70%;
3. PF >= 1.80;
4. net > 0;
5. max loss streak <= 4;
6. every major partition has net > 0;
7. each of ALT_0330, RAW_0530, SHORT_2000 has pooled-major net > 0;
8. at 5 bps adverse slippage per fill: WR >= 65%, PF >= 1.50, net > 0.

Otherwise status is `B27EF_BNB_FROZEN_ECONOMICS_NOT_SUPPORTED`.

## Mandatory assertions
- raw BNB 5m coverage >=99.5%;
- B27EE candidate identities for the three frozen habitats are reproduced exactly;
- existing BTC exit functions are reused where specified;
- $500 notional and $0.40 fee constants match BTC source modules;
- no signal from LONDON/RAW_2330 enters the economics portfolio;
- no overlapping accepted BNB positions;
- no entry/exit outcome used to create or rank signals;
- no post-result tuning in B27EF.

**Research only. Stop after B27EF result persistence. Do not run the next milestone automatically.**
