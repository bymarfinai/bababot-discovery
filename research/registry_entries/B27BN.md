# B27BN — 24H Swing-Boundary Invalidation Audit

**Source:** `BTC_24H_SWING_BOUNDARY_INVALIDATION_B27BN_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BN_SWING_BOUNDARY_INVALIDATION_SUPPORTED`.**

**Purpose:** test whether the prior causally confirmed swing boundary from the last directional 4H state carries regime-invalidation information during the subsequent SIDEWAYS episode. No trading direction or economics were used.

**Exact parent identity:** 1,023 B27BH bracketed SIDEWAYS episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.

**Frozen boundaries:** BULL uses the last directional state's latest confirmed swing low (`lsl`); BEAR uses the latest confirmed swing high (`lsh`). Boundary is frozen before SIDEWAYS begins. No ATR/percentage buffer or threshold fitting.

### Pooled-OOS first SIDEWAYS bar

- BULL: boundary break N **87**, eventual transition **49.4%**; boundary hold N **226**, transition **41.6%**; lift **+7.8pp**.
- BEAR: boundary break N **71**, eventual transition **59.2%**; boundary hold N **171**, transition **52.0%**; lift **+7.1pp**.

### Cumulative wick break by age 3 / 12h

- BULL: RESUME **33.0%** vs TRANSITION **47.4%** = **+14.5pp** transition separation.
- BEAR: RESUME **27.0%** vs TRANSITION **42.0%** = **+15.0pp** transition separation.

**OOS stability:** first-bar break lift and age-3 break separation were positive in external and reference_validation for both origins: external BULL +5.1pp/+15.5pp; external BEAR +9.6pp/+21.2pp; validation BULL +16.4pp/+18.8pp; validation BEAR +4.3pp/+10.1pp.

**Critical caveat:** swing-boundary break is informative but not a necessary or sufficient regime-change condition. In pooled OOS, **49.6%** of genuine BULL-origin transitions and **56.5%** of genuine BEAR-origin transitions reached the opposite detector state without ever wick-breaking the frozen boundary during SIDEWAYS. Conversely, **35.2%** of BULL resumes and **27.0%** of BEAR resumes did wick-break the boundary before returning to the origin regime. Therefore do not use swing break as a hard binary regime switch by itself.

Observable CI: run `32621440428`, job `97150076162`, success. Exact episode-level cohort is preserved in artifact `9488479830`, ZIP SHA256 `dd6bd11ab8be6e20c61c2516b51f2b1f8b9c4ec449879bdaccde4c29f7a97b95`.

Research only. Live BBC unchanged.
