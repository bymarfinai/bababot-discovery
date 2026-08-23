# B27BK — 24H BEAR False-Pause Anatomy Audit

**Source:** `BTC_24H_BEAR_FALSE_PAUSE_ANATOMY_B27BK_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BK_NO_ROBUST_BEAR_FALSE_PAUSE_DISCRIMINATOR`.**

**Purpose:** diagnose the B27BJ BEAR-origin failure mode without refitting or threshold tuning. Primary ambiguity cohort is the exact pooled-OOS rows where B27BJ predicted inherited BEAR: 79 genuine RESUME/TRUE_PAUSE versus 74 genuine TRANSITION/FALSE_PAUSE. External counts are 42/30; reference_validation counts are 37/44.

**Frozen gate:** a new causal first-SIDEWAYS/previous-4H feature had to show the same AUC direction in external and validation, `|AUC-0.50| >= 0.10` in both, pooled `|AUC-0.50| >= 0.15`, with >=20 observations per class in each OOS partition. No new feature passed.

### Key readout

- Strongest existing B27BJ diagnostic among inherited BEAR rows was `dir_ema_spread_atr`: TRUE_PAUSE median **0.362** vs FALSE_PAUSE **0.225**; pooled AUC **0.681**, external **0.610**, validation **0.750**. This feature was already part of B27BJ and therefore was diagnostic only in B27BK, not a new redesign justification.
- Frozen B27BJ `p_resume` still separated the inherited buckets only moderately: median **0.721** vs **0.660**; pooled AUC **0.642**, external **0.629**, validation **0.647**. It must not be used for post-hoc threshold selection.
- New price-path features were unstable across OOS partitions. Example: `dir_low_change_atr` AUC was **0.736 external** but **0.377 validation**; `dir_spread_change_atr` was **0.518 external** but **0.260 validation**; `prior_directional_age` was **0.495 external** but **0.710 validation**.
- Wick/location/structure-delta features were mostly near random discrimination.

**Interpretation:** the remaining BEAR ambiguity cannot be robustly resolved by one additional static causal feature from the first SIDEWAYS bar plus the immediately prior 4H bar. The most stable information remains surviving bearish EMA spread, but substantial overlap remains. This points toward a separately preregistered temporal/pending-transition audit rather than another first-bar threshold tweak.

**Artifact manifest:** `BTC_24H_BEAR_FALSE_PAUSE_ANATOMY_B27BK_ArtifactManifest.md` records workflow run `32617731278`, artifact ID `9487454890`, and ZIP SHA256 `1ee127ffa666641ce770af4bfacf426eb2552dbabebc2cfe1d16da03e936d654` for the exact cohort and full feature summary.

Research only. Live BBC unchanged.
