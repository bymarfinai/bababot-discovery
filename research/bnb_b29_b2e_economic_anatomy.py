#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import bnb_b29_b1j_journey_sweep_character as b1j

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B29_B2E_ECONOMIC_ANATOMY"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_HORIZON = ROOT / f"{PFX}_HorizonMetrics.csv"
OUT_THRESHOLD = ROOT / f"{PFX}_ThresholdMetrics.csv"
OUT_ERA_THRESHOLD = ROOT / f"{PFX}_EraThresholdMetrics.csv"
OUT_WINLOSS = ROOT / f"{PFX}_WinLossMetrics.csv"
OUT_EVENTS = ROOT / f"{PFX}_EventPaths.csv.gz"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"
OUT_CHECK = ROOT / f"{PFX}_Integrity.json"

SYMBOL = "BNBUSDT"
BAR = pd.Timedelta(minutes=5)
STEP15 = pd.Timedelta(minutes=15)
HORIZONS = [15, 30, 60, 120, 360]
PRIMARY_H = 60
THRESHOLDS = [0.0025, 0.0050, 0.0075, 0.0100]
EXPECTED_COUNTS = {2022: 97, 2023: 82, 2024: 114, 2025: 93, 2026: 65}
EXPECTED_TOTAL = 451
BASE = "https://data.binance.vision/data/futures/um/monthly/klines"


def wilson_lcb(hits: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return np.nan
    p = hits / n
    den = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return (center - margin) / den


def month_urls(start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    m = pd.Timestamp(start.year, start.month, 1, tz="UTC")
    em = pd.Timestamp(end.year, end.month, 1, tz="UTC")
    out = []
    while m <= em:
        ym = m.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        m += pd.offsets.MonthBegin(1)
    return out


def fetch_month(url: str) -> pd.DataFrame:
    last_exc = None
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=90, headers={"User-Agent": "bababot-b29-b2e/1.0"})
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not names:
                    raise RuntimeError(f"no csv in {url}")
                with zf.open(names[0]) as fh:
                    q = pd.read_csv(
                        fh, header=None, usecols=[0, 1, 2, 3, 4],
                        names=["ts", "open", "high", "low", "close"],
                    )
            return q
        except Exception as exc:
            last_exc = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed Binance Vision month after retries: {url}: {last_exc}")


def load_raw_path(start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    urls = month_urls(start, end)
    frames: list[pd.DataFrame] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_month, u): u for u in urls}
        for fut in as_completed(futs):
            q = fut.result()
            if len(q):
                frames.append(q)
    if not frames:
        raise RuntimeError("no Binance Vision raw path data")

    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x["ts"], errors="coerce")
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x["ts"] = pd.to_datetime(t, unit="ms", utc=True, errors="coerce")
    for c in ["open", "high", "low", "close"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna().drop_duplicates("ts", keep="last").sort_values("ts")
    x = x[(x["ts"] >= start.floor("D")) & (x["ts"] <= end.ceil("D"))]
    x = x.set_index("ts")[["open", "high", "low", "close"]].astype(float)
    if x.empty or x.index.has_duplicates or not x.index.is_monotonic_increasing:
        raise RuntimeError("raw path index invalid")
    diag = {
        "monthly_files": len(urls),
        "rows": int(len(x)),
        "first_open": x.index[0].isoformat(),
        "last_open": x.index[-1].isoformat(),
    }
    return x, diag


def frozen_character_events(fp: pd.DataFrame) -> pd.DataFrame:
    beh = b1j.build_forward(fp)
    events = b1j.build_events(fp, beh)
    char = events[
        events["pre_path_state"].astype(str).eq("CONT_DOWN")
        & events["reclaim_strength"].astype(str).eq("HIGH")
        & events["reclaim_body"].astype(str).eq("LOW")
    ].copy().sort_index()
    counts = {int(y): int((char["year"] == y).sum()) for y in EXPECTED_COUNTS}
    if len(char) != EXPECTED_TOTAL or counts != EXPECTED_COUNTS:
        raise RuntimeError(f"frozen B1J event-universe mismatch: total={len(char)} counts={counts}")
    if char.index.has_duplicates:
        raise RuntimeError("duplicate frozen event timestamps")
    return char


def immutable_forward(fp: pd.DataFrame, t: pd.Timestamp, h: int) -> float | None:
    growth = 1.0
    for j in range(1, h // 15 + 1):
        z = t + j * STEP15
        if z not in fp.index:
            return None
        r = fp.at[z, "ret_15"]
        if not np.isfinite(float(r)):
            return None
        growth *= 1.0 + float(r)
    return growth - 1.0


def exact_path(raw: pd.DataFrame, t: pd.Timestamp, h: int):
    entry_open = t - BAR
    expected = pd.date_range(entry_open, t + pd.Timedelta(minutes=h) - BAR, freq=BAR, tz="UTC")
    if not expected.isin(raw.index).all():
        return None
    q = raw.loc[expected]
    if len(q) != len(expected):
        return None
    entry = float(q.iloc[0]["close"])
    post = q.iloc[1:]
    if len(post) != h // 5:
        return None
    terminal = float(post.iloc[-1]["close"]) / entry - 1.0
    highs = post["high"].to_numpy(float)
    lows = post["low"].to_numpy(float)
    mfe = float(np.max(highs) / entry - 1.0)
    mae = float(np.min(lows) / entry - 1.0)
    adverse = max(0.0, -mae)
    max_i = int(np.flatnonzero(highs == np.max(highs))[0])
    min_i = int(np.flatnonzero(lows == np.min(lows))[0])
    t_mfe = float((max_i + 1) * 5)
    t_mae = float((min_i + 1) * 5)
    return {
        "entry_close": entry,
        "terminal_return": terminal,
        "mfe": mfe,
        "mae": mae,
        "adverse": adverse,
        "time_mfe_min": t_mfe,
        "time_mae_min": t_mae,
        "post": post,
    }


def first_touch(post: pd.DataFrame, entry: float, thr: float) -> str:
    pos = np.flatnonzero(post["high"].to_numpy(float) >= entry * (1.0 + thr))
    neg = np.flatnonzero(post["low"].to_numpy(float) <= entry * (1.0 - thr))
    pi = int(pos[0]) if len(pos) else None
    ni = int(neg[0]) if len(neg) else None
    if pi is None and ni is None:
        return "NEITHER"
    if pi is not None and ni is None:
        return "POS_FIRST"
    if ni is not None and pi is None:
        return "NEG_FIRST"
    if pi < ni:
        return "POS_FIRST"
    if ni < pi:
        return "NEG_FIRST"
    return "AMBIGUOUS_SAME_BAR"


def threshold_metrics(df: pd.DataFrame, thr: float, year: int | None = None) -> dict:
    q = df if year is None else df[df["year"] == year]
    col = f"touch_{int(round(thr * 10000))}bp"
    valid = q[q["valid_60"]].copy()
    n = len(valid)
    vc = valid[col].value_counts()
    pos = int(vc.get("POS_FIRST", 0))
    neg = int(vc.get("NEG_FIRST", 0))
    amb = int(vc.get("AMBIGUOUS_SAME_BAR", 0))
    neither = int(vc.get("NEITHER", 0))
    unamb = pos + neg
    pos_reach = pos + amb + int(((valid[col] == "NEG_FIRST") & (valid[f"pos_reach_{int(round(thr*10000))}bp"])).sum())
    neg_reach = neg + amb + int(((valid[col] == "POS_FIRST") & (valid[f"neg_reach_{int(round(thr*10000))}bp"])).sum())
    return {
        "threshold": thr,
        "year": "POOLED" if year is None else year,
        "n": n,
        "positive_reach": int(pos_reach),
        "positive_reach_rate": pos_reach / n if n else np.nan,
        "adverse_reach": int(neg_reach),
        "adverse_reach_rate": neg_reach / n if n else np.nan,
        "pos_first": pos,
        "neg_first": neg,
        "ambiguous_same_bar": amb,
        "neither": neither,
        "pos_first_rate_all": pos / n if n else np.nan,
        "neg_first_rate_all": neg / n if n else np.nan,
        "ambiguous_rate": amb / n if n else np.nan,
        "neither_rate": neither / n if n else np.nan,
        "unambiguous_n": unamb,
        "positive_first_share": pos / unamb if unamb else np.nan,
        "wilson_lcb": wilson_lcb(pos, unamb),
    }


def fmt_pct(v) -> str:
    return "n/a" if not np.isfinite(v) else f"{100.0 * float(v):.2f}%"


def main():
    fp, a1diag = b1j.load_frozen_a1()
    char = frozen_character_events(fp)

    raw_start = char.index.min() - BAR
    raw_end = char.index.max() + pd.Timedelta(minutes=max(HORIZONS))
    raw, rawdiag = load_raw_path(raw_start, raw_end)

    rows = []
    max_anchor_diff = 0.0
    anchor_mismatches = 0
    continuity_failures = 0

    for t, erow in char.iterrows():
        rec = {"event_ts": t, "year": int(erow["year"])}
        for h in HORIZONS:
            p = exact_path(raw, t, h)
            imm = immutable_forward(fp, t, h)
            valid = p is not None and imm is not None
            rec[f"valid_{h}"] = bool(valid)
            if not valid:
                continuity_failures += 1
                continue
            diff = abs(float(p["terminal_return"]) - float(imm))
            rec[f"anchor_diff_{h}"] = diff
            rec[f"terminal_{h}"] = p["terminal_return"]
            rec[f"mfe_{h}"] = p["mfe"]
            rec[f"mae_{h}"] = p["mae"]
            rec[f"adverse_{h}"] = p["adverse"]
            rec[f"time_mfe_{h}"] = p["time_mfe_min"]
            rec[f"time_mae_{h}"] = p["time_mae_min"]
            max_anchor_diff = max(max_anchor_diff, diff)
            if diff > 5e-6:
                anchor_mismatches += 1
            if h == PRIMARY_H:
                for thr in THRESHOLDS:
                    bp = int(round(thr * 10000))
                    post = p["post"]
                    entry = p["entry_close"]
                    rec[f"touch_{bp}bp"] = first_touch(post, entry, thr)
                    rec[f"pos_reach_{bp}bp"] = bool((post["high"] >= entry * (1.0 + thr)).any())
                    rec[f"neg_reach_{bp}bp"] = bool((post["low"] <= entry * (1.0 - thr)).any())
        rows.append(rec)

    D = pd.DataFrame(rows).sort_values("event_ts").reset_index(drop=True)
    D.to_csv(OUT_EVENTS, index=False, compression="gzip")

    # Integrity coverage at primary horizon.
    primary_valid = D["valid_60"].fillna(False).astype(bool)
    overall_cov = float(primary_valid.mean())
    era_cov = {int(y): float(D.loc[D["year"] == y, "valid_60"].fillna(False).astype(bool).mean()) for y in EXPECTED_COUNTS}
    integrity_errors = []
    if overall_cov < 0.995:
        integrity_errors.append(f"primary path coverage {overall_cov:.6f} < 0.995")
    for y, c in era_cov.items():
        if c < 0.99:
            integrity_errors.append(f"{y} primary path coverage {c:.6f} < 0.99")
    if anchor_mismatches:
        integrity_errors.append(f"{anchor_mismatches} endpoint anchor mismatches >5e-6")
    if len(D) != EXPECTED_TOTAL or D["event_ts"].duplicated().any():
        integrity_errors.append("event universe total/uniqueness failure")

    horizon_rows = []
    for h in HORIZONS:
        q = D[D[f"valid_{h}"].fillna(False).astype(bool)].copy()
        horizon_rows.append({
            "horizon_min": h,
            "n": len(q),
            "terminal_hit": float((q[f"terminal_{h}"] > 0).mean()) if len(q) else np.nan,
            "mean_terminal": float(q[f"terminal_{h}"].mean()) if len(q) else np.nan,
            "median_terminal": float(q[f"terminal_{h}"].median()) if len(q) else np.nan,
            "mean_mfe": float(q[f"mfe_{h}"].mean()) if len(q) else np.nan,
            "median_mfe": float(q[f"mfe_{h}"].median()) if len(q) else np.nan,
            "mean_adverse": float(q[f"adverse_{h}"].mean()) if len(q) else np.nan,
            "median_adverse": float(q[f"adverse_{h}"].median()) if len(q) else np.nan,
            "p_mfe_gt_adverse": float((q[f"mfe_{h}"] > q[f"adverse_{h}"]).mean()) if len(q) else np.nan,
            "median_time_mfe_min": float(q[f"time_mfe_{h}"].median()) if len(q) else np.nan,
            "median_time_mae_min": float(q[f"time_mae_{h}"].median()) if len(q) else np.nan,
        })
    H = pd.DataFrame(horizon_rows)
    H.to_csv(OUT_HORIZON, index=False)

    pooled_t = pd.DataFrame([threshold_metrics(D, thr) for thr in THRESHOLDS])
    era_t = pd.DataFrame([threshold_metrics(D, thr, y) for thr in THRESHOLDS for y in EXPECTED_COUNTS])
    pooled_t.to_csv(OUT_THRESHOLD, index=False)
    era_t.to_csv(OUT_ERA_THRESHOLD, index=False)

    q60 = D[D["valid_60"].fillna(False).astype(bool)].copy()
    q60["endpoint_group"] = np.where(q60["terminal_60"] > 0.0, "WIN", "LOSS")
    wl_rows = []
    for g, q in q60.groupby("endpoint_group", sort=True):
        wl_rows.append({
            "group": g,
            "n": len(q),
            "median_mfe_60": float(q["mfe_60"].median()),
            "median_adverse_60": float(q["adverse_60"].median()),
            "median_time_mfe_60": float(q["time_mfe_60"].median()),
            "median_time_mae_60": float(q["time_mae_60"].median()),
        })
    WL = pd.DataFrame(wl_rows)
    WL.to_csv(OUT_WINLOSS, index=False)

    primary = H.loc[H["horizon_min"] == 60].iloc[0]
    sample_gate = int(primary["n"]) >= 400
    excursion_gate = float(primary["median_mfe"]) > float(primary["median_adverse"])
    direction_gate = float(primary["terminal_hit"]) >= 0.57

    threshold_pass = {}
    for thr in THRESHOLDS:
        pr = pooled_t.loc[np.isclose(pooled_t["threshold"], thr)].iloc[0]
        et = era_t[np.isclose(era_t["threshold"], thr)].copy()
        era_pass_count = int(((et["unambiguous_n"] >= 15) & (et["positive_first_share"] > 0.50)).sum())
        recent = D[(D["year"].isin([2025, 2026])) & D["valid_60"].fillna(False).astype(bool)].copy()
        bp = int(round(thr * 10000))
        rv = recent[f"touch_{bp}bp"].value_counts()
        rpos = int(rv.get("POS_FIRST", 0)); rneg = int(rv.get("NEG_FIRST", 0))
        recent_share = rpos / (rpos + rneg) if (rpos + rneg) else np.nan
        threshold_pass[thr] = bool(
            int(pr["unambiguous_n"]) >= 120
            and float(pr["positive_first_share"]) >= 0.55
            and float(pr["wilson_lcb"]) > 0.50
            and era_pass_count >= 4
            and np.isfinite(recent_share) and recent_share >= 0.52
        )
        pooled_t.loc[np.isclose(pooled_t["threshold"], thr), "era_pass_count"] = era_pass_count
        pooled_t.loc[np.isclose(pooled_t["threshold"], thr), "recent_2025_2026_positive_first_share"] = recent_share
        pooled_t.loc[np.isclose(pooled_t["threshold"], thr), "frozen_threshold_gate"] = threshold_pass[thr]
    pooled_t.to_csv(OUT_THRESHOLD, index=False)

    adjacent = [(0.0025, 0.0050), (0.0050, 0.0075), (0.0075, 0.0100)]
    plateau_pairs = [(a, b) for a, b in adjacent if threshold_pass[a] and threshold_pass[b]]
    plateau_gate = len(plateau_pairs) > 0

    integrity_pass = len(integrity_errors) == 0
    if not integrity_pass:
        status = "BNB_B29_B2E_DATA_TOOLING_FAILURE"
    elif sample_gate and excursion_gate and plateau_gate and direction_gate:
        status = "BNB_B29_B2E_ECONOMIC_GEOMETRY_PROMISING"
    else:
        status = "BNB_B29_B2E_ECONOMIC_GEOMETRY_WEAK"

    integ = {
        "a1": {k: (v.isoformat() if isinstance(v, pd.Timestamp) else v) for k, v in a1diag.items()},
        "raw": rawdiag,
        "event_total": int(len(D)),
        "event_counts": {str(y): int((D["year"] == y).sum()) for y in EXPECTED_COUNTS},
        "primary_coverage": overall_cov,
        "era_primary_coverage": {str(k): v for k, v in era_cov.items()},
        "continuity_failures_all_horizons": int(continuity_failures),
        "anchor_mismatches": int(anchor_mismatches),
        "max_anchor_abs_diff": float(max_anchor_diff),
        "integrity_errors": integrity_errors,
        "integrity_pass": integrity_pass,
    }
    OUT_CHECK.write_text(json.dumps(integ, indent=2, sort_keys=True), encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# BNB B29-B2E — Frozen Character Economic Anatomy Result",
        "",
        f"**Status: {status}**",
        "",
        "B2E measures post-entry path geometry for the exact frozen B1J character + E0 event-close universe. It does not select TP/SL and does not authorize trading.",
        "",
        "## Frozen universe / integrity",
        f"- Frozen events: **{len(D)}** (2022 {EXPECTED_COUNTS[2022]}, 2023 {EXPECTED_COUNTS[2023]}, 2024 {EXPECTED_COUNTS[2024]}, 2025 {EXPECTED_COUNTS[2025]}, 2026 {EXPECTED_COUNTS[2026]}).",
        f"- Primary +60m raw-path coverage: **{fmt_pct(overall_cov)}**.",
        f"- Max raw-vs-immutable endpoint difference: **{max_anchor_diff:.10f}**.",
        f"- Endpoint anchor mismatches >5e-6: **{anchor_mismatches}**.",
        f"- Integrity gate: **{'PASS' if integrity_pass else 'FAIL'}**.",
        "",
        "## Horizon anatomy",
        "| Horizon | N | Terminal hit | Median terminal | Median MFE | Median adverse | P(MFE>adverse) | Med t-MFE | Med t-MAE |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in H.iterrows():
        lines.append(
            f"| +{int(r.horizon_min)}m | {int(r.n)} | {fmt_pct(r.terminal_hit)} | {fmt_pct(r.median_terminal)} | {fmt_pct(r.median_mfe)} | {fmt_pct(r.median_adverse)} | {fmt_pct(r.p_mfe_gt_adverse)} | {r.median_time_mfe_min:.0f}m | {r.median_time_mae_min:.0f}m |"
        )
    lines += [
        "",
        "## +60m symmetric first-touch anatomy",
        "| Threshold | Unamb N | Positive first | Wilson LCB | Recent 2025+26 | Era pass | Frozen gate |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in pooled_t.iterrows():
        lines.append(
            f"| {100*r.threshold:.2f}% | {int(r.unambiguous_n)} | {fmt_pct(r.positive_first_share)} | {fmt_pct(r.wilson_lcb)} | {fmt_pct(r.recent_2025_2026_positive_first_share)} | {int(r.era_pass_count)}/5 | {'PASS' if bool(r.frozen_threshold_gate) else 'FAIL'} |"
        )
    pair_txt = ", ".join(f"{100*a:.2f}%+{100*b:.2f}%" for a, b in plateau_pairs) if plateau_pairs else "none"
    lines += [
        "",
        "## Frozen geometry gates",
        f"- Primary valid N >=400: **{'PASS' if sample_gate else 'FAIL'}** ({int(primary['n'])}).",
        f"- Median MFE60 > median adverse60: **{'PASS' if excursion_gate else 'FAIL'}** ({fmt_pct(primary['median_mfe'])} vs {fmt_pct(primary['median_adverse'])}).",
        f"- Adjacent-threshold plateau: **{'PASS' if plateau_gate else 'FAIL'}** ({pair_txt}).",
        f"- Pooled +60m directional sanity >=57%: **{'PASS' if direction_gate else 'FAIL'}** ({fmt_pct(primary['terminal_hit'])}).",
        "",
        "## Endpoint WIN vs LOSS diagnostic",
    ]
    for _, r in WL.iterrows():
        lines.append(
            f"- {r['group']}: N={int(r['n'])}; median MFE60={fmt_pct(r['median_mfe_60'])}; median adverse60={fmt_pct(r['median_adverse_60'])}; median t-MFE={r['median_time_mfe_60']:.0f}m; median t-MAE={r['median_time_mae_60']:.0f}m."
        )
    lines += [
        "",
        "## Decision",
        f"**{status}**",
        "",
        "A PROMISING verdict only permits a separately preregistered B3 TP/SL discovery. B2S prospective shadow remains a separate unchanged checkpoint. No live orders are authorized.",
    ]
    if integrity_errors:
        lines += ["", "Integrity errors:"] + [f"- {x}" for x in integrity_errors]
    OUT_RESULT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status, flush=True)
    print("primary", primary.to_dict(), flush=True)
    print("thresholds", pooled_t.to_dict(orient="records"), flush=True)
    print("plateau_pairs", plateau_pairs, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        OUT_STATUS.write_text("BNB_B29_B2E_DATA_TOOLING_FAILURE\n", encoding="utf-8")
        OUT_RESULT.write_text(
            "# BNB B29-B2E — Frozen Character Economic Anatomy Result\n\n"
            "**Status: BNB_B29_B2E_DATA_TOOLING_FAILURE**\n\n"
            f"Tooling/integrity exception: `{type(exc).__name__}: {exc}`\n",
            encoding="utf-8",
        )
        raise
