# BNB B38-S22 — Post-Cluster Far Expansion Character Preregistration

## Objective
Among frozen E2 trades that:
1. survive the frozen S20 Q4 early-failure layer, and
2. actually reach the causal TP2 cluster before the original structural SL,

discover which causal characteristics present by TP2 completion distinguish a local cluster winner from a true far-expansion move toward:
- Major nearest,
- H1 nearest,
- frozen Expansion high,
- +0.50R,
- +1.00R.

## Frozen upstream
- E2 signature:
  `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- E2 detector: reclaim -> hold -> local break
- Entry: frozen market break-close
- Initial structural SL: frozen touch-low
- S20 Q4 early-failure layer:
  - Q4 if baseline SL % > `0.017122292197580727`
  - first clean 5m close below frozen reclaim_close before TP1 => trade is cut and excluded from expansion eligibility.
- No S21 rescue layer is used.

## Expansion population
A trade is eligible only if:
- causal TP2 exists and TP2 > TP1,
- trade is not cut by S20 before TP1,
- TP2 is touched before the original structural SL.

The first 5m bar that touches TP2 is the cluster-completion bar.

## Decision point
The expansion decision is available only at the close of the TP2-touch 5m bar.

Therefore:
- all features may use information no later than that completed bar;
- if a farther objective is already touched on the TP2-touch bar, it is recorded as `FAR_BEFORE_DECISION`;
- such a move is not credited as a post-decision signal win.

This explicitly tests whether post-TP2 adaptation is fast enough. If too many far objectives occur before the decision point, the evidence will indicate that expansion must be decided earlier.

## Far objectives
Each objective is audited only when its level is strictly above TP2.

1. **MAJOR_NEAREST**
2. **H1_NEAREST**
3. **EXPANSION**
4. **R_0_50** = entry + 0.50 * original risk
5. **R_1_00** = entry + 1.00 * original risk

For each available objective:
- FAR_BEFORE_DECISION: first touch occurs on/before TP2 decision bar;
- EXPANDER: objective touches strictly after TP2 decision bar and before structural SL;
- STOPPER: structural SL occurs before objective after the decision;
- unresolved/ambiguous are kept explicit.

## Causal feature families

### A. Cluster geometry known before/at entry
- tp1_r
- tp2_r
- tp1_to_tp2_gap_r
- known_target_count
- objective_room_from_tp2_r

### B. Journey timing
- minutes_entry_to_tp1
- minutes_tp1_to_tp2
- minutes_entry_to_tp2
- cluster_gap_r_per_minute

### C. Journey cleanliness before TP2
Measured from TP1 touch through the completed bar immediately before TP2 touch:
- cluster_path_efficiency
- cluster_green_rate
- cluster_close_above_tp1_rate
- cluster_max_pullback_r
- cluster_mae_from_tp1_r

### D. Immediate approach to TP2
Using completed bars before the TP2-touch bar:
- last1_progress_r
- last3_progress_r
- last3_green_rate
- distance_remaining_tp2_r

### E. TP2 completion-bar state
Available only at decision-bar close:
- tp2_accept = close >= TP2
- tp2_close_above_r = (close - TP2) / original risk
- tp2_bar_body_r
- tp2_bar_range_r
- tp2_close_location

## Analysis discipline
- DEV and REF remain separate.
- Numeric cut points are derived from DEV quartiles only, target-by-target.
- The exact DEV cuts are then applied unchanged to REF.
- No combined rule is built in S22.
- Features are ranked by directional consistency between DEV and REF, not DEV peak.
- No threshold is promoted from this discovery stage.

## Required outputs
For each far objective and period:
- eligible target count
- far-before-decision count/rate
- post-decision EXPANDER / STOPPER counts and rate
- median objective room beyond TP2
- median time TP2 -> far target for expanders

Feature outputs:
- EXTENDER vs STOPPER medians
- robust effect size DEV and REF
- direction consistency
- DEV-quartile band success rates applied unchanged to REF
- ranked candidate expansion characters

## Stop rule
S22 is one expansion-character discovery stage.
Do not optimize an executable adaptive TP policy in the same stage.
A live runner/TP rule, if justified, must be preregistered separately.
