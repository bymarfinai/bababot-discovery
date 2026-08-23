# B27CV — BTC 24H F05 SHORT Full-Loser Separability Anatomy — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Determine whether the existing F05 SHORT clock-TP architecture contains causal information that can identify catastrophic `FULL_SL_HIGH_BREAK` trades early enough to skip or abort them without sacrificing too many trades that eventually reach the frozen clock target.

This is **classifier/anatomy research only**. No new SL, exit, entry price, target, runner, clock deletion, or live rule is authorized. Trading WR/PF/expectancy/PnL from a hypothetical detector are N/A in this experiment.

External and reference_validation have already been inspected in the lineage and are reused-data confirmation only, not untouched OOS.

## Frozen source identity and labels
Source: `BTC_24H_CLOCK_TP_SL_B27CS_SelectedTrades.csv`, candidate `BASE_H`, exact executable F05 trade identity.

Expected filled identity:
- external 183;
- development 297;
- reference_validation 172;
- pooled major 652.

Expected labels from the frozen B27CS clock-TP architecture:
- `BAD`: `exit_reason == FULL_SL_HIGH_BREAK`; expected pooled major 78;
- `GOOD`: `target_reached == True`; expected pooled major 348;
- `OTHER`: every other filled trade.

Primary separability training/evaluation uses BAD vs GOOD only. OTHER is reported separately and is never relabeled post hoc.

Raw 5m identity: exactly 698,112 rows and 100% coverage.

## Frozen causal checkpoints
Exactly five decision checkpoints:
1. `RECLAIM`: `reclaim_complete_ts`; no later fill price, fill timestamp, or reclaim-to-fill delay may be used;
2. `FILL`: `fill_ts`, using only information completed strictly before the fill bar plus the actual executable entry price that becomes known at fill;
3. `PLUS5`: `fill_ts + 5m`;
4. `PLUS10`: `fill_ts + 10m`;
5. `PLUS15`: `fill_ts + 15m`.

At PLUS5/10/15, a trade is model-eligible only if its frozen B27CS `exit_ts` is strictly later than the checkpoint. GOOD trades already exited at target are counted as safely resolved and cannot be falsely cut at that later checkpoint. BAD trades already exited via High break are counted as `too_late_bad` misses for that checkpoint.

No bar completing after the checkpoint may contribute features.

## Frozen feature family
No indicator/feature may be added after results are seen.

### Static / setup features available at RECLAIM
- `clock_block` one-hot;
- `regime` one-hot;
- reclaim completed 5m close position `(close-L)/R4`;
- reclaim candle body / range and upper/lower wick fractions;
- remaining minutes in original 4H block at reclaim;
- known F05 setup position `(F05-L)/R4` and distance F05-to-H / R4.

### Fill features available only from FILL onward
- actual executable entry position `(entry-L)/R4`;
- entry gap above F05 normalized by R4;
- distance entry-to-H normalized by R4;
- reclaim-to-fill minutes.

At RECLAIM these fill-specific values are structurally missing and are never backfilled with future values.

### Completed 1H context
At each decision timestamp, use the most recent fully completed UTC 1H candle only:
- `(decision_price-EMA20)/R4`;
- `(decision_price-EMA50)/R4`;
- `(EMA20-EMA50)/R4`;
- `(EMA50-EMA50_lag3)/R4`.

For RECLAIM, `decision_price` is the completed reclaim-bar close. For FILL it is the executable entry price. For PLUS5/10/15 it is the latest completed 5m close at the checkpoint.

EMA spans are fixed at 20 and 50, `adjust=False`; lag is exactly 3 completed 1H bars.

### Post-fill path features (PLUS5/10/15 only)
Using completed raw 5m bars from fill bar through the checkpoint:
- current close position `(close-L)/R4`;
- net close movement from entry / R4;
- maximum high adverse excursion above entry / R4;
- maximum close adverse excursion above entry / R4;
- maximum favorable low excursion below entry / R4;
- whether any completed close `< L` has occurred;
- number of consecutive higher closes ending at checkpoint, capped at 3;
- number of consecutive higher highs ending at checkpoint, capped at 3;
- fraction of completed bars bullish;
- fraction of completed closes above entry;
- maximum bullish real-body / R4;
- count of completed closes at or above F10 (`L+0.10R4`);
- count of completed closes at or above F15 (`L+0.15R4`).

At RECLAIM/FILL, post-fill features are structurally absent and are imputed only inside the model pipeline; no future values are substituted.

## Frozen model
For each checkpoint independently:
- development BAD+GOOD eligible rows only;
- preprocessing: median imputation for numeric features, standard scaling for numeric features, one-hot categorical features;
- classifier: sklearn `LogisticRegression(C=1.0, class_weight='balanced', max_iter=2000, solver='liblinear', random_state=27)`;
- target class BAD=1, GOOD=0.

No model family, regularization strength, feature set, interaction search, resampling, SMOTE, or hyperparameter sweep is allowed.

Report development ROC-AUC and BAD probability distributions descriptively. These are not promotion criteria by themselves.

## Frozen development-only cutoffs
For each checkpoint, compute predicted BAD probabilities on the same development eligible cohort and choose exactly two operating points from unique predicted probabilities plus endpoints:

### SAFE
Choose the threshold that maximizes BAD capture subject to GOOD sacrifice <=10.0%. Tie-break: lower GOOD sacrifice, then higher threshold.

### AGGRESSIVE
Choose the threshold that maximizes BAD capture subject to GOOD sacrifice <=20.0%. Tie-break: lower GOOD sacrifice, then higher threshold.

If no flagged trade exists under the constraint, threshold is `+inf` and capture is zero.

Thresholds are frozen after development and applied unchanged to external and reference_validation.

## Required metrics
For every checkpoint × operating point × partition:
- BAD total;
- BAD already too late before checkpoint;
- BAD eligible/alive;
- BAD flagged;
- cumulative BAD capture as % of all BAD in the partition;
- eligible BAD recall;
- GOOD total;
- GOOD safely resolved before checkpoint;
- GOOD eligible/alive;
- GOOD flagged;
- cumulative GOOD sacrifice as % of all GOOD;
- eligible GOOD false-positive rate;
- flagged BAD precision among BAD+GOOD flagged;
- number flagged.

Report all six 4H clocks independently for the frozen model/cutoff secondarily, and regime splits secondarily. No clock/regime deletion.

Also report top absolute logistic coefficients per checkpoint as descriptive diagnostics only.

## Reused-data support
A checkpoint/operating-point is `REUSED_SUPPORTED` only if both external and reference_validation satisfy:

SAFE:
- cumulative BAD capture >=25%;
- cumulative GOOD sacrifice <=15%;
- at least 5 BAD total in the partition.

AGGRESSIVE:
- cumulative BAD capture >=40%;
- cumulative GOOD sacrifice <=25%;
- at least 5 BAD total in the partition.

Because external/reference_validation are reused lineage data, support is candidate evidence only.

## Overall verdict
`B27CV_FULL_LOSER_DETECTOR_REUSED_CANDIDATE` requires audit PASS and at least one checkpoint/operating-point reused-supported in both external and reference_validation under the frozen criteria.

Otherwise: `B27CV_FULL_LOSER_SEPARABILITY_NOT_SUPPORTED`.

Even a candidate verdict does not authorize economic use. The next step would require a separate preregistered execution simulation where the detector actually skips/aborts trades causally and reports WR/PF/expectancy/PnL with nominal RR discipline.

Research only. Live BBC unchanged.
