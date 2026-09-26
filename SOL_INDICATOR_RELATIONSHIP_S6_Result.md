# SOL Indicator Relationship Discovery — Stage 6 Result

**Regime + market-state mapping. Research only; no entry rule is selected here.**

- Decision rows: **130,848**
- Replicated directional states: **5**
- Replicated expansion states: **6**
- Stable regime × state cells: **6**

## Regime baseline

| Regime | Partition | N | LONG | SHORT | D | Expansion |
|---|---|---:|---:|---:|---:|---:|
| BULL | development | 5360 | 48.3% | 47.4% | 1.0% | 96.0% |
| BEAR | development | 3412 | 41.3% | 47.6% | -6.3% | 88.9% |
| SIDEWAYS | development | 11728 | 29.7% | 33.5% | -3.8% | 63.2% |
| TRANSITION | development | 47848 | 42.9% | 43.8% | -0.9% | 86.7% |
| BULL | validation_2025 | 2708 | 47.2% | 48.7% | -1.5% | 96.1% |
| BEAR | validation_2025 | 1920 | 42.4% | 39.7% | 2.7% | 82.2% |
| SIDEWAYS | validation_2025 | 6696 | 30.0% | 33.3% | -3.3% | 63.4% |
| TRANSITION | validation_2025 | 23716 | 41.1% | 42.7% | -1.6% | 83.9% |
| BULL | validation_2026 | 1932 | 39.5% | 40.7% | -1.2% | 80.4% |
| BEAR | validation_2026 | 736 | 36.1% | 40.1% | -3.9% | 76.2% |
| SIDEWAYS | validation_2026 | 11400 | 22.4% | 24.4% | -2.0% | 46.9% |
| TRANSITION | validation_2026 | 11549 | 35.0% | 36.9% | -1.9% | 72.0% |

## Replicated market states

| State | Class | DEV N | DEV D | 2025 D | 2026 D | DEV Exp lift | 2025 | 2026 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| POST_BREAKDOWN_UNWIND_30M | REPLICATED_DIRECTIONAL_STATE;REPLICATED_EXPANSION_STATE | 269 | -15.6% | -38.9% | -24.0% | 10.6% | 6.5% | 14.5% |
| UP_POSITION_BUILD | REPLICATED_EXPANSION_STATE | 2283 | 5.2% | 8.9% | 4.8% | 11.2% | 12.2% | 23.3% |
| UP_UNWIND_LIKE | REPLICATED_DIRECTIONAL_STATE;REPLICATED_EXPANSION_STATE | 429 | -11.9% | -37.8% | -28.2% | 12.2% | 9.3% | 22.9% |
| DOWN_POSITION_BUILD | REPLICATED_DIRECTIONAL_STATE;REPLICATED_EXPANSION_STATE | 312 | 18.6% | 24.6% | 11.0% | 13.6% | 10.8% | 22.0% |
| DOWN_UNWIND_LIKE | REPLICATED_EXPANSION_STATE | 1910 | -3.6% | -10.7% | -13.7% | 12.5% | 12.3% | 20.9% |
| HIGHLOC_BUY_EXHAUSTION_LIKE | REPLICATED_DIRECTIONAL_STATE | 854 | -13.0% | -22.8% | -10.8% | 1.3% | 1.0% | 4.2% |
| HIGHLOC_SELL_ABSORPTION_LIKE | REPLICATED_DIRECTIONAL_STATE | 945 | 14.7% | 15.2% | 27.8% | 3.5% | 3.7% | 14.0% |
| PRESSURE_BUILD | REPLICATED_EXPANSION_STATE | 5158 | -0.6% | 11.7% | 8.7% | 5.0% | 7.3% | 12.1% |

## Stable regime × state cells

| Regime | State | DEV N/D | 2025 N/D | 2026 N/D |
|---|---|---:|---:|---:|
| BULL | DELEVERAGING | 488/-15.0% | 257/-23.3% | 147/-24.5% |
| SIDEWAYS | HIGHLOC_BUY_BUILD | 603/11.4% | 287/8.0% | 440/10.9% |
| SIDEWAYS | HIGHLOC_BUY_EXHAUSTION_LIKE | 132/-17.4% | 100/-21.0% | 193/-8.8% |
| SIDEWAYS | DELEVERAGING | 896/-11.0% | 483/-13.7% | 683/-7.3% |
| TRANSITION | HIGHLOC_BUY_EXHAUSTION_LIKE | 623/-14.0% | 499/-21.0% | 280/-14.6% |
| TRANSITION | HIGHLOC_SELL_ABSORPTION_LIKE | 705/15.9% | 547/13.5% | 233/29.6% |

## Lifecycle self-persistence

| Partition | State | +15m same-state | +30m same-state |
|---|---|---:|---:|
| development | EVENT_CONFLICT | 1.6% | 1.6% |
| development | POST_BREAKDOWN_UNWIND_30M | 4.8% | 7.1% |
| development | UP_POSITION_BUILD | 16.2% | 10.5% |
| development | UP_UNWIND_LIKE | 3.3% | 2.3% |
| development | DOWN_POSITION_BUILD | 2.6% | 2.2% |
| development | DOWN_UNWIND_LIKE | 9.0% | 5.7% |
| development | HIGHLOC_BUY_BUILD | 16.3% | 14.3% |
| development | HIGHLOC_BUY_EXHAUSTION_LIKE | 3.2% | 5.0% |
| development | HIGHLOC_SELL_ABSORPTION_LIKE | 2.9% | 4.0% |
| development | HIGHLOC_SELL_UNWIND_LIKE | 16.4% | 13.8% |
| development | PRESSURE_BUILD | 17.1% | 15.1% |
| development | DELEVERAGING | 17.3% | 13.7% |
| validation_2025 | EVENT_CONFLICT | - | - |
| validation_2025 | POST_BREAKDOWN_UNWIND_30M | 12.1% | 11.1% |
| validation_2025 | UP_POSITION_BUILD | 15.1% | 9.2% |
| validation_2025 | UP_UNWIND_LIKE | 1.7% | 3.5% |
| validation_2025 | DOWN_POSITION_BUILD | 4.2% | 4.2% |
| validation_2025 | DOWN_UNWIND_LIKE | 9.3% | 4.8% |
| validation_2025 | HIGHLOC_BUY_BUILD | 15.5% | 12.3% |
| validation_2025 | HIGHLOC_BUY_EXHAUSTION_LIKE | 2.8% | 6.0% |
| validation_2025 | HIGHLOC_SELL_ABSORPTION_LIKE | 3.7% | 6.2% |
| validation_2025 | HIGHLOC_SELL_UNWIND_LIKE | 18.6% | 14.3% |
| validation_2025 | PRESSURE_BUILD | 15.1% | 13.3% |
| validation_2025 | DELEVERAGING | 18.5% | 15.1% |
| validation_2026 | EVENT_CONFLICT | - | - |
| validation_2026 | POST_BREAKDOWN_UNWIND_30M | 15.0% | 10.0% |
| validation_2026 | UP_POSITION_BUILD | 13.6% | 7.9% |
| validation_2026 | UP_UNWIND_LIKE | 4.9% | 3.9% |
| validation_2026 | DOWN_POSITION_BUILD | 4.4% | 2.2% |
| validation_2026 | DOWN_UNWIND_LIKE | 10.6% | 2.2% |
| validation_2026 | HIGHLOC_BUY_BUILD | 14.4% | 11.4% |
| validation_2026 | HIGHLOC_BUY_EXHAUSTION_LIKE | 6.0% | 6.7% |
| validation_2026 | HIGHLOC_SELL_ABSORPTION_LIKE | 4.1% | 3.6% |
| validation_2026 | HIGHLOC_SELL_UNWIND_LIKE | 15.2% | 10.8% |
| validation_2026 | PRESSURE_BUILD | 14.4% | 11.8% |
| validation_2026 | DELEVERAGING | 16.3% | 13.0% |

## Guardrail

State names ending in _LIKE are economic interpretations of observed configurations, not causal proof.
BTC.D / USDT.D are not state splitters because Stage 5B found no replicated incremental information.
Stage 7 may only consider states that survive the frozen Stage-6 replication gates; Stage 6 itself does not authorize LONG/SHORT trades.

**Status: SOL_INDICATOR_RELATIONSHIP_S6_COMPLETED_WITH_REPLICATED_STATES**
