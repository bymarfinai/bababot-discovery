#!/usr/bin/env python3
from __future__ import annotations

import time
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import bnb_b29_a1_structure_fingerprint as a1
import bnb_b29_a2_character_memory as a2

# Tooling-only identity guard. These values are taken from the accepted A1 run.
EXPECTED_START = pd.Timestamp("2020-02-10T08:00:00Z")
EXPECTED_LAST = pd.Timestamp("2026-08-25T23:55:00Z")
EXPECTED_ROWS = 687_936
EXPECTED_FP_HASH = "2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6"
MAX_ATTEMPTS = 5

_ORIGINAL_LOAD5 = base.load5


def load5_frozen_identity(symbol: str):
    """Retry Binance Vision reads until the exact accepted A1 raw identity is recovered.

    The legacy loader's coverage ratio is relative to the last successfully downloaded bar,
    so a missing contiguous tail can still report 100% coverage. A2 must never run on such
    a partial snapshot. This wrapper changes no A2 scientific parameter; it only enforces
    the already-frozen A1 data identity before A2 starts.
    """
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
            "attempt": attempt,
            "rows": len(raw),
            "start": start,
            "last": last,
            "coverage": coverage,
            "row_ok": row_ok,
            "boundary_ok": boundary_ok,
            "contiguous_ok": contiguous_ok,
            "fp_hash": fp_hash,
            "fp_ok": fp_ok,
        }
        print("A2 frozen-loader diagnostic:", last_diag, flush=True)
        if row_ok and boundary_ok and contiguous_ok and fp_ok:
            print(f"A2 frozen-loader identity PASS on attempt {attempt}", flush=True)
            return raw, coverage
        if attempt < MAX_ATTEMPTS:
            time.sleep(2)

    raise RuntimeError(f"could not recover exact frozen A1 raw/fingerprint identity after {MAX_ATTEMPTS} attempts; last={last_diag}")


def main():
    # a2.base and base refer to the same imported module object.
    a2.base.load5 = load5_frozen_identity
    a2.main()


if __name__ == "__main__":
    main()
