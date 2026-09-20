#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s3_adaptive_execution as s3
import bnb_b38_s11_e2_economics as s11
import bnb_b38_s12_e2_target_selection as s12
import bnb_b38_s13_e2_path_room_audit as s13

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B38_S14_POST_TP1_CONTINUATION"
START = pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END = pd.Timestamp("2024-12-31T23:59:59Z")
EXPECTED_SIGNATURE = "d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"
STATES = ["ACCEPT", "ACCEPT_HOLD", "ACCEPT_HOLD_BREAK", "RECLAIM_HOLD_BREAK"]


def period(ts):
    return "DEV" if pd.Timestamp(ts) <= DEV_END else "REF"


def first_touch_idx(raw5, entry_ts, level, kind, end):
    if not np.isfinite(level):
        return None
    idx = raw5.index
    i0 = int(idx.searchsorted(entry_ts, side="right"))
    i1 = int(idx.searchsorted(end, side="right"))
    if i1 <= i0:
        return None
    arr = (raw5.high if kind == "HIGH" else raw5.low).to_numpy(float, copy=False)[i0:i1]
    z = np.flatnonzero(arr >= level) if kind == "HIGH" else np.flatnonzero(arr <= level)
    return i0 + int(z[0]) if len(z) else None


def touch_after_idx(raw5, start_idx, level, kind, end_idx):
    if not np.isfinite(level) or end_idx <= start_idx:
        return None
    arr = (raw5.high if kind == "HIGH" else raw5.low).to_numpy(float, copy=False)[start_idx:end_idx]
    z = np.flatnonzero(arr >= level) if kind == "HIGH" else np.flatnonzero(arr <= level)
    return start_idx + int(z[0]) if len(z) else None


def build_frozen(raw, end):
    s1.START = START
    s1.END = end
    s3.END = end

    h1 = s1.exact_exec(raw, "1h", 12)
    h1 = h1[h1.index <= end]
    m15 = s1.exact_exec(raw, "15min", 3)
    m15 = m15[m15.index <= end]
    raw5 = raw[["open", "high", "low", "close"]].astype(float)

    zones = s1.demand_zones(h1)
    fam = s1.visual_family(m15, zones)
    fam = fam[
        (pd.to_datetime(fam.first_touch_ts, utc=True) >= START) &
        (pd.to_datetime(fam.first_touch_ts, utc=True) <= end)
    ].copy()

    dev = fam[pd.to_datetime(fam.first_touch_ts, utc=True) <= DEV_END]
    ref = fam[pd.to_datetime(fam.first_touch_ts, utc=True) > DEV_END]
    if len(dev) != 788 or len(ref) != 463:
        raise RuntimeError(f"parent parity drift dev={len(dev)} ref={len(ref)}")

    P = s11.e2_plans(m15, h1, fam, end)
    K = s12.known_targets_at_entry(P, m15, h1, fam)
    P = P.merge(K, on="zone_id", how="left", validate="one_to_one")
    P["period"] = [period(x) for x in P.first_touch_ts]
    P = P[np.isfinite(P.tp1) & (P.entry_price > P.touch_low_sl)].copy()

    baseline = []
    for r in P.itertuples(index=False):
        out, rt, rr = s11.touch_resolve(
            raw5, r.entry_ts, float(r.entry_price), float(r.touch_low_sl), float(r.tp1), end
        )
        baseline.append({
            "zone_id": r.zone_id,
            "baseline_outcome": out,
            "baseline_resolution_ts": rt,
            "baseline_realized_r": rr,
        })
    B = pd.DataFrame(baseline)
    P = P.merge(B, on="zone_id", how="left", validate="one_to_one")

    parity = {
        "DEV": (
            int((P.period == "DEV").sum()),
            int(((P.period == "DEV") & (P.baseline_outcome == "WIN")).sum()),
            int(((P.period == "DEV") & (P.baseline_outcome == "LOSS")).sum()),
        ),
        "REF": (
            int((P.period == "REF").sum()),
            int(((P.period == "REF") & (P.baseline_outcome == "WIN")).sum()),
            int(((P.period == "REF") & (P.baseline_outcome == "LOSS")).sum()),
        ),
    }
    if parity != {"DEV": (440, 325, 115), "REF": (272, 201, 71)}:
        raise RuntimeError(f"frozen parity drift {parity}")

    sig = s13.plan_signature(P)
    if sig != EXPECTED_SIGNATURE:
        raise RuntimeError(f"frozen signature drift got={sig} expected={EXPECTED_SIGNATURE}")

    return raw5, m15, h1, P, sig


def accept_signal(raw5, t0, tp1, tp2_idx, sl_idx):
    # Decision is only available at completion of TP1 touch bar.
    if tp2_idx is not None and tp2_idx <= t0:
        return "TP2_BEFORE_SIGNAL", None
    if sl_idx is not None and sl_idx <= t0:
        return "SL_BEFORE_SIGNAL", None
    if float(raw5.close.iloc[t0]) >= tp1:
        return "SIGNAL", t0
    return "NO_SIGNAL", None


def accept_hold_signal(raw5, t0, tp1, tp2_idx, sl_idx):
    t1 = t0 + 1
    if t1 >= len(raw5):
        return "NO_SIGNAL", None
    if tp2_idx is not None and tp2_idx <= t1:
        return "TP2_BEFORE_SIGNAL", None
    if sl_idx is not None and sl_idx <= t1:
        return "SL_BEFORE_SIGNAL", None
    if float(raw5.close.iloc[t0]) >= tp1 and float(raw5.close.iloc[t1]) >= tp1:
        return "SIGNAL", t1
    return "NO_SIGNAL", None


def accept_hold_break_signal(raw5, t0, tp1, tp2_idx, sl_idx, end_idx):
    # ACCEPT
    if float(raw5.close.iloc[t0]) < tp1:
        return "NO_SIGNAL", None

    # HOLD = immediate next completed 5m bar.
    t1 = t0 + 1
    if t1 >= end_idx:
        return "NO_SIGNAL", None
    if tp2_idx is not None and tp2_idx <= t1:
        return "TP2_BEFORE_SIGNAL", None
    if sl_idx is not None and sl_idx <= t1:
        return "SL_BEFORE_SIGNAL", None
    if float(raw5.close.iloc[t1]) < tp1:
        return "NO_SIGNAL", None

    local_high = max(float(raw5.high.iloc[t0]), float(raw5.high.iloc[t1]))
    for j in range(t1 + 1, end_idx):
        if tp2_idx is not None and tp2_idx <= j:
            return "TP2_BEFORE_SIGNAL", None
        if sl_idx is not None and sl_idx <= j:
            return "SL_BEFORE_SIGNAL", None
        c = float(raw5.close.iloc[j])
        if c < tp1:
            return "NO_SIGNAL", None
        if c > local_high:
            return "SIGNAL", j
        local_high = max(local_high, float(raw5.high.iloc[j]))
    return "NO_SIGNAL", None


def reclaim_hold_break_signal(raw5, t0, tp1, tp2_idx, sl_idx, end_idx):
    # Structural state machine:
    # WAIT_RECLAIM -> WAIT_HOLD -> WAIT_BREAK.
    state = "WAIT_RECLAIM"
    reclaim_i = None
    hold_i = None
    local_high = np.nan

    for j in range(t0, end_idx):
        if tp2_idx is not None and tp2_idx <= j:
            return "TP2_BEFORE_SIGNAL", None
        if sl_idx is not None and sl_idx <= j:
            return "SL_BEFORE_SIGNAL", None

        c = float(raw5.close.iloc[j])
        h = float(raw5.high.iloc[j])

        if state == "WAIT_RECLAIM":
            if c >= tp1:
                reclaim_i = j
                local_high = h
                state = "WAIT_HOLD"
            continue

        if state == "WAIT_HOLD":
            if c < tp1:
                state = "WAIT_RECLAIM"
                reclaim_i = None
                local_high = np.nan
                continue
            if j > reclaim_i:
                hold_i = j
                local_high = max(local_high, h)
                state = "WAIT_BREAK"
            continue

        if state == "WAIT_BREAK":
            if c < tp1:
                state = "WAIT_RECLAIM"
                reclaim_i = None
                hold_i = None
                local_high = np.nan
                continue
            if c > local_high:
                return "SIGNAL", j
            local_high = max(local_high, h)

    return "NO_SIGNAL", None


def label_after_signal(raw5, signal_idx, tp2, entry, sl, end_idx):
    if signal_idx is None:
        return {
            "tp2_after_signal": False,
            "tp2_before_be_after_signal": False,
            "tp2_idx_after_signal": None,
            "sl_idx_after_signal": None,
            "be_idx_after_signal": None,
        }

    start = signal_idx + 1
    ti = touch_after_idx(raw5, start, tp2, "HIGH", end_idx)
    si = touch_after_idx(raw5, start, sl, "LOW", end_idx)
    bi = touch_after_idx(raw5, start, entry, "LOW", end_idx)

    tp2_after = ti is not None and (si is None or ti < si)
    tp2_before_be = ti is not None and (bi is None or ti < bi)
    return {
        "tp2_after_signal": bool(tp2_after),
        "tp2_before_be_after_signal": bool(tp2_before_be),
        "tp2_idx_after_signal": ti,
        "sl_idx_after_signal": si,
        "be_idx_after_signal": bi,
    }


def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"


def fmt_num(x, d=2):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"


def main():
    raw, diag = b31.load_raw()
    if diag["coverage"] < .995:
        raise RuntimeError(f"raw coverage low {diag}")
    a1 = b31.load_a1()
    ident = b31.identity(raw, a1)
    if ident["max_ret15_diff"] > 5e-8 or ident["max_close_location_diff"] > 5e-8:
        raise RuntimeError(f"identity fail {ident}")

    end = raw.index.max()
    raw5, m15, h1, P, sig = build_frozen(raw, end)
    idx = raw5.index
    end_idx = int(idx.searchsorted(end, side="right"))

    # Post-TP1 decision only exists for baseline winners with a causal TP2.
    Q = P[(P.baseline_outcome == "WIN") & np.isfinite(P.tp2) & (P.tp2 > P.tp1)].copy()

    rows = []
    for r in Q.itertuples(index=False):
        entry = float(r.entry_price)
        sl = float(r.touch_low_sl)
        tp1 = float(r.tp1)
        tp2 = float(r.tp2)

        t0 = first_touch_idx(raw5, r.entry_ts, tp1, "HIGH", end)
        if t0 is None:
            raise RuntimeError(f"baseline WIN missing TP1 touch {r.zone_id}")

        tp2_idx = touch_after_idx(raw5, t0, tp2, "HIGH", end_idx)
        sl_idx = touch_after_idx(raw5, t0, sl, "LOW", end_idx)
        be_idx = touch_after_idx(raw5, t0 + 1, entry, "LOW", end_idx)

        tp2_before_sl = tp2_idx is not None and (sl_idx is None or tp2_idx < sl_idx)
        tp2_before_be = tp2_idx is not None and (be_idx is None or tp2_idx < be_idx)

        funcs = {
            "ACCEPT": accept_signal,
            "ACCEPT_HOLD": accept_hold_signal,
            "ACCEPT_HOLD_BREAK": accept_hold_break_signal,
            "RECLAIM_HOLD_BREAK": reclaim_hold_break_signal,
        }

        for state, fn in funcs.items():
            if state in ("ACCEPT", "ACCEPT_HOLD"):
                status, signal_idx = fn(raw5, t0, tp1, tp2_idx, sl_idx)
            else:
                status, signal_idx = fn(raw5, t0, tp1, tp2_idx, sl_idx, end_idx)

            post = label_after_signal(raw5, signal_idx, tp2, entry, sl, end_idx)
            signal_ts = idx[signal_idx] if signal_idx is not None else pd.NaT
            delay_min = (
                float((signal_ts - idx[t0]) / pd.Timedelta(minutes=1))
                if pd.notna(signal_ts) else np.nan
            )

            rows.append({
                "zone_id": r.zone_id,
                "period": r.period,
                "year": r.year,
                "entry_ts": r.entry_ts,
                "tp1_touch_ts": idx[t0],
                "state": state,
                "status": status,
                "signal_ts": signal_ts,
                "signal_delay_min": delay_min,
                "entry_price": entry,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "tp1_r": (tp1 - entry) / (entry - sl),
                "tp2_r": (tp2 - entry) / (entry - sl),
                "extension_gap_r": (tp2 - tp1) / (entry - sl),
                "tp2_before_sl": bool(tp2_before_sl),
                "tp2_before_be": bool(tp2_before_be),
                **post,
            })

    L = pd.DataFrame(rows)

    base = []
    for per in ["DEV", "REF"]:
        q = L[(L.period == per) & (L.state == "ACCEPT")].copy()
        base.append({
            "period": per,
            "eligible": len(q),
            "tp2_before_sl": int(q.tp2_before_sl.sum()),
            "tp2_before_sl_rate": float(q.tp2_before_sl.mean()) if len(q) else np.nan,
            "tp2_before_be": int(q.tp2_before_be.sum()),
            "tp2_before_be_rate": float(q.tp2_before_be.mean()) if len(q) else np.nan,
            "median_tp1_r": float(q.tp1_r.median()) if len(q) else np.nan,
            "median_tp2_r": float(q.tp2_r.median()) if len(q) else np.nan,
            "median_extension_gap_r": float(q.extension_gap_r.median()) if len(q) else np.nan,
        })
    B = pd.DataFrame(base)

    summary = []
    for per in ["DEV", "REF"]:
        eligible = int((L[(L.period == per) & (L.state == "ACCEPT")]).shape[0])
        continuation_total = int(
            L[(L.period == per) & (L.state == "ACCEPT")].tp2_before_sl.sum()
        )

        for state in STATES:
            q = L[(L.period == per) & (L.state == state)].copy()
            sigq = q[q.status == "SIGNAL"].copy()
            preq = q[q.status == "TP2_BEFORE_SIGNAL"].copy()

            success = int(sigq.tp2_after_signal.sum()) if len(sigq) else 0
            strict = int(sigq.tp2_before_be_after_signal.sum()) if len(sigq) else 0
            false = int(len(sigq) - success)
            signaled_success_ids = set(sigq[sigq.tp2_after_signal].zone_id)
            pre_success_ids = set(preq[preq.tp2_before_sl].zone_id)
            all_cont_ids = set(q[q.tp2_before_sl].zone_id)
            captured = len(signaled_success_ids | pre_success_ids)
            missed = len(all_cont_ids - signaled_success_ids - pre_success_ids)

            summary.append({
                "period": per,
                "state": state,
                "eligible": eligible,
                "continuation_total": continuation_total,
                "signals": len(sigq),
                "signal_coverage": len(sigq) / eligible if eligible else np.nan,
                "tp2_before_signal": len(preq),
                "tp2_success_after_signal": success,
                "success_rate_after_signal": success / len(sigq) if len(sigq) else np.nan,
                "tp2_before_be_after_signal": strict,
                "strict_success_rate": strict / len(sigq) if len(sigq) else np.nan,
                "false_signals": false,
                "continuations_captured_including_pre_signal": captured,
                "continuation_capture_rate": captured / continuation_total if continuation_total else np.nan,
                "continuations_missed": missed,
                "median_signal_delay_min": float(sigq.signal_delay_min.median()) if len(sigq) else np.nan,
                "median_extension_gap_r_signaled": float(sigq.extension_gap_r.median()) if len(sigq) else np.nan,
            })
    S = pd.DataFrame(summary)

    by_year = []
    for y in [2022, 2023, 2024, 2025, 2026]:
        for state in STATES:
            q = L[(L.year == y) & (L.state == state)]
            sigq = q[q.status == "SIGNAL"]
            if not len(q):
                continue
            by_year.append({
                "year": y,
                "state": state,
                "eligible": len(q),
                "signals": len(sigq),
                "signal_coverage": len(sigq) / len(q),
                "success_rate_after_signal": float(sigq.tp2_after_signal.mean()) if len(sigq) else np.nan,
                "strict_success_rate": float(sigq.tp2_before_be_after_signal.mean()) if len(sigq) else np.nan,
                "tp2_before_signal": int((q.status == "TP2_BEFORE_SIGNAL").sum()),
            })
    Y = pd.DataFrame(by_year)

    status_counts = (
        L.groupby(["period", "state", "status"], dropna=False)
         .size().reset_index(name="n")
    )

    L.to_csv(ROOT / f"{PFX}_Ledger.csv.gz", index=False, compression="gzip")
    B.to_csv(ROOT / f"{PFX}_Baseline.csv", index=False)
    S.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    Y.to_csv(ROOT / f"{PFX}_ByYear.csv", index=False)
    status_counts.to_csv(ROOT / f"{PFX}_StatusCounts.csv", index=False)
    (ROOT / f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\n"
        "DEV_PLANS=440\nREF_PLANS=272\nDEV_WINS=325\nREF_WINS=201\n",
        encoding="utf-8",
    )

    lines = [
        "# BNB B38-S14 — Post-TP1 Continuation Character", "",
        f"Frozen E2 signature: `{sig}`", "",
        "## Eligible post-TP1 population", "",
        "Only baseline E2 WINs with a causal TP2 above TP1 are eligible.", "",
        "| Period | Eligible | TP2 before structural SL | TP2 before BE | Med TP1 | Med TP2 | Med extension gap |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in B.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.eligible} | {r.tp2_before_sl} ({fmt_pct(r.tp2_before_sl_rate)}) | "
            f"{r.tp2_before_be} ({fmt_pct(r.tp2_before_be_rate)}) | {r.median_tp1_r:.3f}R | "
            f"{r.median_tp2_r:.3f}R | {r.median_extension_gap_r:.3f}R |"
        )

    lines += ["", "## Structural state results", "",
        "A TP2 touch that happens before a state can complete is recorded separately rather than credited as a predictive signal.", "",
        "| Period | State | Signals | Coverage | TP2 before signal | TP2 success after signal | Strict TP2 before BE | False signals | Continuation capture* | Median delay |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.state} | {r.signals} | {fmt_pct(r.signal_coverage)} | "
            f"{r.tp2_before_signal} | {r.tp2_success_after_signal}/{r.signals} ({fmt_pct(r.success_rate_after_signal)}) | "
            f"{r.tp2_before_be_after_signal}/{r.signals} ({fmt_pct(r.strict_success_rate)}) | "
            f"{r.false_signals} | {r.continuations_captured_including_pre_signal}/{r.continuation_total} "
            f"({fmt_pct(r.continuation_capture_rate)}) | {fmt_num(r.median_signal_delay_min,1)}m |"
        )

    lines += ["", "\*Continuation capture includes TP2 moves that completed before a slower confirmation signal; those are not counted as signal wins.", "",
        "## Year stability", "",
        "| Year | State | Eligible | Signals | Coverage | Success after signal | Strict success | TP2 before signal |",
        "|---:|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.state} | {r.eligible} | {r.signals} | {fmt_pct(r.signal_coverage)} | "
            f"{fmt_pct(r.success_rate_after_signal)} | {fmt_pct(r.strict_success_rate)} | {r.tp2_before_signal} |"
        )

    lines += ["", "## Interpretation boundary",
        "S14 is a character-discovery stage only.",
        "No partial sizing, runner allocation, TP promotion, or stop modification is selected here.",
        "A useful continuation character should improve post-signal TP2 reliability without collapsing coverage or degrading sharply from DEV to REF."
    ]

    (ROOT / f"{PFX}_Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text("BNB_B38_S14_POST_TP1_CONTINUATION_COMPLETE\n", encoding="utf-8")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
