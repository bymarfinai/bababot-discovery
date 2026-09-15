#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import bnb_b29_b1_event_transition as b1

BAR = pd.Timedelta(minutes=15)


def load_frozen_a1_gap_safe():
    """Tooling-only immutable A1 loader.

    The accepted A1 artifact contains a tiny number of historical gaps but every
    decision timestamp remains aligned to the 15-minute clock. Exact file SHA256
    is the primary identity guard. Continuity is enforced separately wherever a
    B1 event or forward horizon requires an adjacent 15-minute observation.
    """
    if not b1.FROZEN_FP.exists():
        raise FileNotFoundError(f"missing accepted A1 artifact fingerprint: {b1.FROZEN_FP}")
    digest = b1.file_sha256(b1.FROZEN_FP)
    q = pd.read_csv(b1.FROZEN_FP, compression="gzip", low_memory=False)
    if "decision_ts" not in q.columns:
        raise RuntimeError("accepted A1 fingerprint missing decision_ts")
    q["decision_ts"] = pd.to_datetime(q["decision_ts"], utc=True, errors="raise")
    q = q.set_index("decision_ts")
    q.index = pd.DatetimeIndex(q.index)

    diffs = q.index.to_series().diff().dropna()
    aligned = bool(((q.index.minute % 15) == 0).all() and (q.index.second == 0).all())
    gap_count = int((diffs != BAR).sum())
    max_gap = diffs.max() if len(diffs) else pd.NaT
    diag = {
        "sha256": digest,
        "sha_ok": digest == b1.FROZEN_FP_SHA256,
        "rows": len(q),
        "rows_ok": len(q) == b1.FROZEN_ROWS,
        "first": q.index.min() if len(q) else pd.NaT,
        "last": q.index.max() if len(q) else pd.NaT,
        "boundary_ok": bool(len(q) and q.index.min() == b1.FROZEN_FIRST and q.index.max() == b1.FROZEN_LAST),
        "grid_ok": aligned,
        "gap_count": gap_count,
        "max_gap": max_gap,
        "unique_ok": bool(not q.index.has_duplicates and q.index.is_monotonic_increasing),
        "schema_ok": all(c in q.columns for c in b1.REQUIRED_COLUMNS),
    }
    print("B1 immutable A1 gap-safe diagnostic:", diag, flush=True)
    if not all([diag["sha_ok"], diag["rows_ok"], diag["boundary_ok"], diag["grid_ok"], diag["unique_ok"], diag["schema_ok"]]):
        raise RuntimeError(f"accepted A1 artifact identity failure: {diag}")
    return q, diag


def build_behaviour_gap_safe(fp: pd.DataFrame) -> pd.DataFrame:
    """Exact-clock forward returns from frozen A1 ret_15; never cross a data gap."""
    r = pd.to_numeric(fp["ret_15"], errors="coerce").astype(float)
    full_index = pd.date_range(fp.index.min(), fp.index.max(), freq="15min", tz="UTC")
    r_full = r.reindex(full_index)
    out_full = pd.DataFrame(index=full_index)
    for h in b1.HORIZONS:
        steps = h // 15
        growth = pd.Series(1.0, index=full_index, dtype=float)
        valid = pd.Series(True, index=full_index, dtype=bool)
        for i in range(1, steps + 1):
            ri = r_full.shift(-i)
            growth = growth * (1.0 + ri)
            valid &= ri.notna()
        out_full[f"fwd_{h}"] = (growth - 1.0).where(valid)
    return out_full.reindex(fp.index)


def build_event_masks_gap_safe(fp: pd.DataFrame) -> dict[str, pd.Series]:
    """Frozen B1 event clauses, with 'previous 15m decision' interpreted literally."""
    prev = fp.shift(1)
    prev_exact = fp.index.to_series().diff().eq(BAR)
    return {
        "SWEEP_LOW_RECLAIM": fp["sweep_low_60"].eq(1.0),
        "SWEEP_HIGH_REJECT": fp["sweep_high_60"].eq(1.0),
        "BREAK_HIGH_HOLD": prev_exact & prev["break_high_60"].eq(1.0) & fp["break_high_60"].eq(1.0),
        "BREAK_LOW_HOLD": prev_exact & prev["break_low_60"].eq(1.0) & fp["break_low_60"].eq(1.0),
        "BREAK_HIGH_FAIL": prev_exact & prev["break_high_60"].eq(1.0) & fp["break_high_60"].eq(0.0) & fp["close_location"].lt(0.0),
        "BREAK_LOW_FAIL": prev_exact & prev["break_low_60"].eq(1.0) & fp["break_low_60"].eq(0.0) & fp["close_location"].gt(0.0),
        "COMPRESSION_EXPAND_UP": prev_exact & prev["vol_state"].eq("COMPRESS") & fp["vol_state"].eq("EXPAND") & fp["disp_atr_15"].ge(0.25),
        "COMPRESSION_EXPAND_DOWN": prev_exact & prev["vol_state"].eq("COMPRESS") & fp["vol_state"].eq("EXPAND") & fp["disp_atr_15"].le(-0.25),
        "PULLBACK_UP_RESUME": prev_exact & prev["path_state"].eq("PULLBACK_FROM_UP") & fp["ret_15"].gt(0.0) & fp["trend_state"].isin(["UP", "STRONG_UP"]),
        "PULLBACK_DOWN_RESUME": prev_exact & prev["path_state"].eq("PULLBACK_FROM_DOWN") & fp["ret_15"].lt(0.0) & fp["trend_state"].isin(["DOWN", "STRONG_DOWN"]),
    }


def main():
    # Tooling/causality fixes only; frozen B1 event definitions, directions,
    # cooldown, horizons and promotion gates remain unchanged.
    b1.load_frozen_a1 = load_frozen_a1_gap_safe
    b1.build_behaviour_from_frozen_a1 = build_behaviour_gap_safe
    b1.build_raw_event_masks = build_event_masks_gap_safe
    b1.main()


if __name__ == "__main__":
    main()
