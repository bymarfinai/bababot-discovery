#!/usr/bin/env python3
"""Technical dtype fix runner for S5.7E; research design is unchanged."""
from __future__ import annotations

import numpy as np
import s57e_post_rejection_expansion_stall_atlas as m


def binary_row(g, signal, period, minutes):
    mask = g[signal].astype(bool)
    yes = g[mask]
    no = g[~mask]
    yr = float(yes.future_expand08.mean()) if len(yes) else np.nan
    nr = float(no.future_expand08.mean()) if len(no) else np.nan
    exp = m.BINARY_EXPECTED[signal]
    effect = yr - nr if np.isfinite(yr) and np.isfinite(nr) else np.nan
    expected_ok = bool(np.isfinite(effect) and ((exp == "HIGH" and effect > 0) or (exp == "LOW" and effect < 0)))
    return {
        "snapshot_min": minutes, "period": period, "signal": signal,
        "expected": exp, "n": int(len(g)), "yes_n": int(len(yes)),
        "no_n": int(len(no)), "yes_expand_rate": yr, "no_expand_rate": nr,
        "effect_yes_minus_no": effect, "expected_direction_ok": expected_ok,
    }


m.binary_row = binary_row

if __name__ == "__main__":
    m.main()
