# SOL LONG 15:00 UTC L0 Early MAE Economic Translation — A64 Scientific Verdict

## Verdict

**`SOL_LONG_15UTC_L0_EARLY_MAE_ECONOMIC_TRANSLATION_A64_REJECTED_DEVELOPMENT`**

A64 rejects the preregistered static `running_mae_R` full-exit translation at the Development promotion stage. No candidate passed every frozen Development gate, so External Validation and Reference Validation intervention economics were correctly left unopened.

This rejection does **not** invalidate the A62 anatomy or A63 mechanism-specificity findings. It means that the exact A64 translation architecture — fixed 60m/120m decision age, Development-only nearest-rank Q25/Q50/Q75 MAE threshold family, and 100% exit at the decision open — is not promoted under the preregistered economic gate.

## Frozen reconciliation

The execution parent remained:

`R360 / 15UTC / E0_RESTING_H -> E40`

The parent and mature loss universe reconciled exactly:

| Partition | Parent | CENTRAL losses | L0/M0 | Raw winners |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 244 |
| External Validation | 281 | 166 | 13 | 115 |
| Reference Validation | 337 | 187 | 26 | 150 |
| **Pooled** | **1,219** | **710** | **76** | **509** |

Raw SOLUSDT 5m coverage was **99.7671%**.

## Preregistered threshold family

Thresholds were learned from eligible frozen Development L0/M0 cases only, before any OOS intervention result could be opened.

| Age | Eligible Development L0 | Q25 | Q50 | Q75 |
|---:|---:|---:|---:|---:|
| 60m | 33 | 0.336679R | 0.513333R | 0.737518R |
| 120m | 29 | 0.588785R | 0.664723R | 0.803653R |

No neighboring threshold, alternate age, additional feature, composite, partial position response, or OOS tuning was permitted.

## Development result

All six preregistered candidates increased raw and 5bps net PnL relative to the frozen Development baseline, and all six increased raw and stressed PF. Nevertheless, every candidate failed at least one frozen promotion clause.

| Candidate | Raw ΔNet | 5bps ΔNet | L0 ΔPnL | Winner ΔPnL | Positive blocks raw/stress | Development gate |
|---|---:|---:|---:|---:|---:|---|
| A60_Q25 | +$29.02 | +$29.02 | +$205.48 | -$215.01 | 3/6 / 3/6 | FAIL |
| A60_Q50 | +$49.99 | +$49.99 | +$117.52 | -$77.42 | 3/6 / 3/6 | FAIL |
| A60_Q75 | +$42.32 | +$42.32 | +$58.05 | -$23.17 | 3/6 / 3/6 | FAIL |
| A120_Q25 | +$86.29 | +$86.29 | +$165.54 | -$76.38 | 5/6 / 5/6 | FAIL |
| A120_Q50 | +$46.00 | +$46.00 | +$96.32 | -$49.92 | 4/6 / 4/6 | FAIL |
| A120_Q75 | +$22.57 | +$22.57 | +$45.28 | -$15.44 | 5/6 / 5/6 | FAIL |

### Common decisive failure: stressed WR preservation

Every candidate failed the preregistered requirement:

`5bps WR >= frozen baseline 5bps WR`

The frozen Development baseline stressed WR was approximately **40.27%**. Candidate stressed WRs were:

- A60_Q25: **36.11%**
- A60_Q50: **38.60%**
- A60_Q75: **39.93%**
- A120_Q25: **38.77%**
- A120_Q50: **39.27%**
- A120_Q75: **39.77%**

Therefore no candidate could pass the full gate even when its PnL, PF, drawdown, L0 loss saving, and block behavior were otherwise favorable.

### Additional failures at 60m

The 60m candidates also had insufficient Development block consistency: all three produced only `3/6` positive raw and stressed blocks.

`A60_Q25` additionally failed the explicit A56-derived winner-damage safeguard because L0 saved (`+$205.48`) did not exceed eventual-winner damage (`$215.01`).

## Strongest non-promotional diagnostic

`A120_Q25` was the strongest Development economic near-miss under the frozen family:

- threshold: `running_mae_R >= 0.5887850467` at 120m;
- 40 triggers;
- 22 L0/M0 triggers;
- 9 other-loss triggers;
- 9 eventual-winner triggers;
- raw net: **$425.21** versus baseline **$338.91**;
- raw ΔNet: **+$86.29**;
- stressed net: **$274.96** versus baseline **$188.66**;
- stressed ΔNet: **+$86.29**;
- raw PF: **1.388** versus baseline about **1.28**;
- stressed PF: **1.232** versus baseline about **1.14**;
- raw max DD: **$114.01** versus baseline **$148.06**;
- L0/M0 ΔPnL: **+$165.54**;
- eventual-winner ΔPnL: **-$76.38**;
- positive Development blocks: **5/6 raw and 5/6 stress**.

However its stressed WR was **38.77%**, below the frozen baseline, so it remains a rejected diagnostic rather than a selected rule. The preregistered gate cannot be relaxed after seeing this near-miss.

## OOS boundary

Because Development produced zero fully passing candidates:

- no candidate was selected;
- no exact age/threshold was frozen for validation;
- External Validation intervention economics were not computed;
- Reference Validation intervention economics were not computed;
- OOS cannot be used post hoc to rescue A64.

This is a protocol success, not missing analysis: Development-first rejection is the preregistered stopping rule.

## Scientific interpretation

The A62 -> A63 -> A64 chain now says three different things:

1. **A62:** deeper early adverse excursion separates L0/M0 from future winners by roughly 60–120 minutes.
2. **A63:** adverse-excursion depth remains specifically associated with L0/M0 relative to another never-break loss mechanism.
3. **A64:** converting static MAE depth into the tested full-exit threshold family produces meaningful Development PnL/PF/DD improvement, but cannot satisfy the full preregistered promotion gate because it sacrifices eventual winners and lowers stressed win rate; therefore the exact translation is rejected before OOS.

The correct conclusion is not “MAE has no economic information.” The correct conclusion is:

> **Mechanism-specific MAE depth contains Development economic information, but static full exit at the tested fixed-age Development-quantile thresholds is too blunt to satisfy the complete promotion objective.**

## Interpretation boundary

A64 does not authorize:

- relaxing or deleting the stressed-WR gate retroactively;
- promoting A120_Q25 because its PnL/PF/DD look attractive;
- testing neighboring MAE thresholds inside A64;
- moving the decision age;
- opening OOS for a failed Development candidate;
- adding partial derisk or re-arm as an A64 rescue;
- combining `running_mae_R` with A63-rejected `close_H_R` or `drawdown_from_best_R`;
- modifying live Baba Bot.

Any future experiment must use a new identifier and a genuinely new preregistered scientific question rather than a post-hoc rescue of A64.

## Lineage consequence

- Preserve A62 and A63 as valid descriptive/mechanistic results.
- Close the exact A64 static full-exit translation family under its frozen gate.
- Preserve `running_mae_R` as a mechanism-specific research axis, but not as an authorized executable threshold.
- Treat `A120_Q25` only as a non-promotional diagnostic showing the key tension: loss savings and portfolio economics can improve while winner retention / stressed WR deteriorates.
- The next lineage decision should investigate that tension mechanistically before any new economic intervention is attempted; it must not simply remove the gate that A64 failed.

Research only. Live Baba Bot remains unchanged.
