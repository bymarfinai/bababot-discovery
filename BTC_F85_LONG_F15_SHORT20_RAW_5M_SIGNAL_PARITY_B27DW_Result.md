# B27DW — Raw Closed-5m F85 LONG + F15 SHORT20 Signal Parity — Result

5m rows: **698,112**; coverage: **100.0000%**; causal sessions replayed: **8,646**.

Generated raw signals: **245 LONG + 57 SHORT20**.

## Parity gates

| Check | Actual | Expected | Result | Detail |
|---|---:|---:|---|---|
| LONG_count | 245 | 244 | FAIL |  |
| LONG_identity_order | 222 | 244 | FAIL |  |
| LONG_geometry_identity | 1 | 0 | FAIL | common=244 missing=0 extra=1 |
| SHORT20_count | 57 | 57 | PASS |  |
| SHORT20_identity_order | 57 | 57 | PASS |  |
| SHORT20_geometry_identity | 0 | 0 | PASS | common=57 missing=0 extra=0 |
| duplicate_raw_event_no_duplicate_signal | 1 | 1 | PASS | LONG/LONDON/2020-02-12T13:50:00+00:00 |
| confirmation_requires_next_open | on_bar_open only | on_bar_open only | PASS | on_bar_close cannot emit |
| reference_range_immutable | frozen | frozen | PASS | H/L set only at adapter construction |
| generated_exit_map_complete | 1 | 0 | FAIL |  |
| generated_entry_control_plane_n | 0 | 283 | FAIL |  |
| generated_entry_control_plane_order | 0 | 283 | FAIL |  |

Mismatch rows: **2**.

**Status: B27DW_RAW_5M_SIGNAL_PARITY_NOT_READY**

No exchange writes; legacy live BBC unchanged. Canonical exits are attached only after raw entry generation.
