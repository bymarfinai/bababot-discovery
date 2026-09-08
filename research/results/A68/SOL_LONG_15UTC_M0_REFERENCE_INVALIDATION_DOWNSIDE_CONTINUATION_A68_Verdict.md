# SOL LONG 15:00 UTC M0 Reference-Invalidation Downside-Continuation Anatomy — A68 Scientific Verdict

## Verdict

**`SOL_LONG_15UTC_M0_REFERENCE_INVALIDATION_DOWNSIDE_CONTINUATION_A68_INCONCLUSIVE`**

A68 does **not** establish that a causally confirmed frozen M0 reference invalidation is followed by a robust immediate downside-continuation regime that should be translated into a reverse-short intervention.

This is a scientific failure of the preregistered mechanism, not a technical or support failure. The experiment reconciled exactly to the frozen parent, raw SOLUSDT 5m coverage remained **99.7671%**, all 76 frozen M0 cases had usable forward data at every preregistered horizon, and frozen parent exit timing matched the causal next-bar directional origin in **100%** of M0 cases across all three partitions.

## Frozen lineage and reconciliation

The execution parent remained unchanged:

`R360 / 15UTC / E0_RESTING_H -> E40`

| Partition | Parent | CENTRAL losses | L0/M0 | Winners |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 244 |
| External Validation | 281 | 166 | 13 | 115 |
| Reference Validation | 337 | 187 | 26 | 150 |
| **Pooled** | **1,219** | **710** | **76** | **509** |

A68 did not alter the frozen long parent, redefine M0, reuse a same-candle short fill, reopen A64-A67 failed routes, optimize a short entry delay, or alter live Baba Bot.

## Why A68 existed

The A62-A67 lineage repeatedly established that severe adverse excursion is informative about genuine L0/M0 deterioration but failed to find a robust winner-retention discriminator suitable for early intervention. A68 therefore changed the causal question completely.

Instead of asking whether M0 can be predicted earlier, A68 asked what happens **after structural invalidation is already known**. The fixed directional origin was the open of the next 5m bar after `invalidation_close_ts`. This deliberately tested the user's reverse-short idea without hindsight execution on the invalidating candle itself.

## Preregistered directional families

Primary horizons were fixed at **30m and 60m**. The **120m** horizon was frozen in advance as a persistence diagnostic and was not allowed to rescue primary failure.

The two core directional families were:

- `short_close_return_R` — whether price is lower at the horizon close than at the causal next-bar origin;
- `short_excursion_dominance_R` — whether favorable short excursion exceeds adverse short excursion.

`short_capture_fraction` was corroborative only.

A core family had to pass Development first and then replicate in both External Validation and Reference Validation at **both 30m and 60m**. No family passed even the Development gate at either primary horizon.

## Primary results

| Horizon | Feature | Development median / effect | Dev blocks | External median / effect | Reference median / effect | Full replication |
|---:|---|---:|---:|---:|---:|---|
| 30m | `short_close_return_R` | **-0.078R / 0.174** | 1/5 | **-0.057R / 0.387** | **-0.032R / 0.095** | NO |
| 30m | `short_excursion_dominance_R` | +0.012R / 0.020 | 2/5 | **-0.057R / 0.258** | **-0.036R / 0.095** | NO |
| 60m | `short_close_return_R` | **-0.087R / 0.192** | 2/5 | **-0.051R / 0.423** | +0.041R / 0.119 | NO |
| 60m | `short_excursion_dominance_R` | **-0.074R / 0.108** | 2/5 | **-0.154R / 0.558** | **-0.041R / 0.092** | NO |

The sign convention is positive for short continuation. Therefore the dominant primary result is not merely “too weak.” For `short_close_return_R`, Development and External medians are **negative at both 30m and 60m**, meaning the median path ends *above* the causal short origin rather than below it. At 60m, `short_excursion_dominance_R` is also negative in Development, External, and Reference.

The Development block requirement fails badly: only `1/5` adequate blocks point in the short direction for 30m close return, `2/5` for 30m excursion dominance, and `2/5` for both core features at 60m. This is inconsistent with a stable pair-native immediate short regime.

## 120m persistence diagnostic

The preregistered 120m diagnostic also does not rescue the mechanism:

- Development `short_close_return_R`: **-0.051R**;
- External `short_close_return_R`: **-0.195R**;
- Reference `short_close_return_R`: **+0.222R**;
- Development `short_excursion_dominance_R`: +0.066R but only `2/5` adequate blocks in direction;
- External `short_excursion_dominance_R`: **-0.252R**;
- Reference `short_excursion_dominance_R`: +0.031R.

The partitions disagree materially. Reference eventually shows some lower-close tendency by 120m, while Development and External remain opposite. That is not a replicable directional transition and cannot be promoted.

## Scientific interpretation

The narrow supported conclusion after A68 is:

> **For this frozen SOL long parent, M0 reference invalidation is a reliable statement that the long thesis has failed, but it is not evidence that the market has immediately transitioned into a robust short-continuation regime.**

This matters. “Long invalidated” and “short edge activated” are not equivalent states.

A68 therefore argues against the simple transformation:

`losing long -> confirmed M0 -> immediate reverse short`

under the exact causal next-bar origin and fixed 30m/60m horizons tested here.

The result does **not** say SOL can never be shorted after a failed long. It says the failure event itself is insufficient directional evidence to justify that transition. Any future short lineage would need an independent pair-native short setup or a genuinely new post-failure confirmation mechanism rather than treating M0 alone as the short signal.

## Interpretation boundary

A68 does not authorize:

- reverse-short entry immediately after M0 invalidation;
- optimization of short TP, SL, trailing stop, leverage, sizing, or holding period from A68;
- moving the short entry to the invalidation candle or searching neighboring entry delays;
- selecting Reference 120m while ignoring Development and External disagreement;
- relaxing the Development block gate;
- using the 120m diagnostic to rescue failed 30m/60m primary horizons;
- reopening A64-A67 failed winner-retention routes;
- modifying live Baba Bot.

Because the prerequisite directional mechanism failed, a direct A69 reverse-short economic translation is **not scientifically justified** from A68.

## Lineage consequence

- Preserve A62 early deterioration as supported.
- Preserve A63 `running_mae_R` mechanism specificity as supported.
- Preserve A64 static MAE exit translation as rejected at Development.
- Preserve A65-A67 tested winner-retention anatomy families as inconclusive/closed.
- Close A68 exact **M0 -> causal next-bar immediate downside-continuation** mechanism as **inconclusive**.
- Treat M0 as a long-thesis invalidation state, not as an automatic opposite-direction signal.
- Any subsequent short research must establish an independent post-failure confirmation or standalone SOL-short structure before economic translation.

Research only. Live Baba Bot remains unchanged.
