#!/usr/bin/env python3
from __future__ import annotations

import time
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import bnb_b29_a1_structure_fingerprint as a1
import bnb_b29_a3_regime_aware_character_memory as a3

EXPECTED_START = pd.Timestamp("2020-02-10T08:00:00Z")
EXPECTED_LAST = pd.Timestamp("2026-08-25T23:55:00Z")
EXPECTED_ROWS = 687_936
EXPECTED_FP_HASH = "2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6"
MAX_ATTEMPTS = 5

_ORIGINAL_LOAD5 = base.load5


def load5_frozen_identity(symbol: str):
    last_diag = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw, coverage = _ORIGINAL_LOAD5(symbol)
        idx = pd.DatetimeIndex(raw.index)
        start = idx.min() if len(idx) else pd.NaT
        last = idx.max() if len(idx) else pd.NaT
        row_ok = len(raw) == EXPECTED_ROWS
        boundary_ok = start == EXPECTED_START and last == EXPECTED_LAST
        contiguous_ok = bool(len(idx) == EXPECTED_ROWS and not idx.has_duplicates and idx.is_monotonic_increasing)
        fp_hash = None
        fp_ok = False
        if row_ok and boundary_ok and contiguous_ok:
            fp = a1.build_fingerprint(raw)
            fp_hash = a1.fingerprint_hash(fp)
            fp_ok = fp_hash == EXPECTED_FP_HASH
        last_diag = {
            "attempt": attempt, "rows": len(raw), "start": start, "last": last,
            "coverage": coverage, "row_ok": row_ok, "boundary_ok": boundary_ok,
            "contiguous_ok": contiguous_ok, "fp_hash": fp_hash, "fp_ok": fp_ok,
        }
        print("A3 frozen-loader diagnostic:", last_diag, flush=True)
        if row_ok and boundary_ok and contiguous_ok and fp_ok:
            print(f"A3 frozen-loader identity PASS on attempt {attempt}", flush=True)
            return raw, coverage
        if attempt < MAX_ATTEMPTS:
            time.sleep(2)
    raise RuntimeError(f"could not recover exact frozen A1 identity after {MAX_ATTEMPTS} attempts; last={last_diag}")


def main():
    a3.base.load5 = load5_frozen_identity
    a3.main()


if __name__ == "__main__":
    main()
