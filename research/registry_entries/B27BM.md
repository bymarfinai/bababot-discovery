# B27BM — 24H SIDEWAYS Age-Hazard Audit

**Source:** `BTC_24H_SIDEWAYS_AGE_HAZARD_B27BM_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BM_PHASED_SIDEWAYS_HAZARD_SUPPORTED`.**

**Purpose:** test whether SIDEWAYS has a reproducible age-dependent cause-specific exit structure, conditional on the episode still being SIDEWAYS. No trading direction or economics were used.

**Exact parent identity:** 1,023 B27BH bracketed SIDEWAYS episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.

### Pooled-OOS primary hazard readout

- BULL age1 / 4h: RESUME **28.8%**, TRANSITION **13.7%**, survive **57.5%**; T-R **-15.0pp**.
- BULL age2 / 8h: RESUME **20.0%**, TRANSITION **25.0%**, survive **55.0%**; T-R **+5.0pp**.
- BULL age3 / 12h: RESUME **13.1%**, TRANSITION **22.2%**, survive **64.6%**; T-R **+9.1pp**.
- BEAR age1 / 4h: RESUME **25.2%**, TRANSITION **20.7%**, survive **54.1%**; T-R **-4.5pp**.
- BEAR age2 / 8h: RESUME **19.1%**, TRANSITION **40.5%**, survive **40.5%**; T-R **+21.4pp**.
- BEAR age3 / 12h: RESUME **20.8%**, TRANSITION **30.2%**, survive **49.1%**; T-R **+9.4pp**.

### OOS stability

The transition-minus-resume margin shifted upward from age1 to age2 in every preregistered OOS cell:

- external BULL: **-17.8pp -> -0.9pp**;
- external BEAR: **-7.4pp -> +10.6pp**;
- reference_validation BULL: **-12.0pp -> +13.5pp**;
- reference_validation BEAR: **-2.2pp -> +32.3pp**.

All frozen gates passed: age1 continuation-heavy for both origins, age2/3 transition-heavy for both origins, age1->age2 margin shift stable in external and validation, and OOS risk sets >=30 through age3.

**Interpretation:** SIDEWAYS is not temporally homogeneous. The first 4h SIDEWAYS bar is continuation-heavy, while the 8h-12h phase becomes transition-heavy. Ages 4-6 are descriptive only and do not support a monotonic 'older SIDEWAYS = more reversal' rule. This supports an age-dependent regime-state concept, not a production state machine or trading rule.

Observable CI: run `32619094283`, job `97144386776`, success. Exact hazard CSV is preserved in artifact `9487827397`; manifest: `BTC_24H_SIDEWAYS_AGE_HAZARD_B27BM_ArtifactManifest.md`.

Research only. Live BBC unchanged.
