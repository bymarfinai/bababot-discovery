#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import RobustScaler

import sol_reset_winner_first_v1 as v1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_RESET_WINNER_FIRST_V2_EVENT_STRUCTURE"

MODEL_START = v1.MODEL_START
MODEL_END = v1.MODEL_END
BAR = v1.BAR
SEQ_BARS = v1.SEQ_BARS
TRAIL_BARS = v1.TRAIL_BARS
DECISION_MINUTES = v1.DECISION_MINUTES
FUTURE_BARS = v1.FUTURE_BARS
ROUNDTRIP_COST_PCT = v1.ROUNDTRIP_COST_PCT
NOTIONAL = v1.NOTIONAL
TEST_YEARS = v1.TEST_YEARS
TRAIN_WINDOW_YEARS = v1.TRAIN_WINDOW_YEARS
N_FAMILIES = v1.N_FAMILIES
RADIUS_Q = v1.RADIUS_Q
MIN_FAMILY_SUPPORT = v1.MIN_FAMILY_SUPPORT
MIN_PRECISION_LIFT = v1.MIN_PRECISION_LIFT
MIN_TRAIN_PF = v1.MIN_TRAIN_PF
UP_FLOOR_PCT = v1.UP_FLOOR_PCT
UP_SIGMA_MULT = v1.UP_SIGMA_MULT
DOWN_FRAC = v1.DOWN_FRAC

PIVOT_ORDER = 2
SWEEP_LOOKBACK = 6
DISP_MULT = 1.50
BULL_CLOSE_LOC = 0.65
BEAR_CLOSE_LOC = 0.35
EVENT_SLOTS = 12
EVENT_TYPES = (
    "HH", "LH", "HL", "LL",
    "SWEEP_LOW_RECLAIM", "SWEEP_HIGH_REJECT",
    "BULL_DISP", "BEAR_DISP",
)
TOKEN_TYPES = ("NONE",) + EVENT_TYPES
EVENT_ORDER = {
    "SWEEP_LOW_RECLAIM": 0,
    "SWEEP_HIGH_REJECT": 1,
    "HH": 2,
    "LH": 2,
    "HL": 3,
    "LL": 3,
    "BULL_DISP": 4,
    "BEAR_DISP": 5,
}

EVENT_VECTOR_COLS = []
for s in range(EVENT_SLOTS):
    EVENT_VECTOR_COLS.extend([f"slot{s:02d}_{t}" for t in TOKEN_TYPES])
    EVENT_VECTOR_COLS.extend([f"slot{s:02d}_recency", f"slot{s:02d}_strength"])
EVENT_VECTOR_COLS.extend([f"count_{t}" for t in EVENT_TYPES])


def _safe_close_loc(h: float, l: float, c: float) -> float:
    span = h - l
    if not np.isfinite(span) or span <= 0:
        return 0.5
    return float(np.clip((c - l) / span, 0.0, 1.0))


def event_sequence_vector(q: pd.DataFrame) -> dict | None:
    if len(q) != SEQ_BARS:
        return None
    op = q.open.astype(float).to_numpy()
    hi = q.high.astype(float).to_numpy()
    lo = q.low.astype(float).to_numpy()
    cl = q.close.astype(float).to_numpy()
    if not all(np.isfinite(x).all() for x in (op, hi, lo, cl)):
        return None
    if np.any(op <= 0) or np.any(hi <= 0) or np.any(lo <= 0) or np.any(cl <= 0):
        return None

    range_pct = np.maximum((hi - lo) / np.maximum(cl, 1e-12) * 100.0, 1e-9)
    body_pct = (cl - op) / np.maximum(op, 1e-12) * 100.0
    abs_body_pct = np.abs(body_pct)
    seq_med_range = float(np.median(range_pct))
    if not np.isfinite(seq_med_range) or seq_med_range <= 1e-9:
        seq_med_range = 1e-6

    pivot_high_kind: dict[int, tuple[str, float]] = {}
    pivot_low_kind: dict[int, tuple[str, float]] = {}
    prev_ph = None
    prev_pl = None
    for i in range(PIVOT_ORDER, SEQ_BARS - PIVOT_ORDER):
        left_h = hi[i - PIVOT_ORDER:i]
        right_h = hi[i + 1:i + PIVOT_ORDER + 1]
        is_ph = bool(hi[i] > np.max(left_h) and hi[i] >= np.max(right_h))
        if is_ph:
            if prev_ph is not None:
                token = "HH" if hi[i] > prev_ph else "LH"
                strength = abs(float(hi[i] - prev_ph)) / max(float(cl[i]) * seq_med_range / 100.0, 1e-12)
                pivot_high_kind[i] = (token, float(np.clip(strength, 0.0, 8.0)))
            prev_ph = float(hi[i])

        left_l = lo[i - PIVOT_ORDER:i]
        right_l = lo[i + 1:i + PIVOT_ORDER + 1]
        is_pl = bool(lo[i] < np.min(left_l) and lo[i] <= np.min(right_l))
        if is_pl:
            if prev_pl is not None:
                token = "HL" if lo[i] > prev_pl else "LL"
                strength = abs(float(lo[i] - prev_pl)) / max(float(cl[i]) * seq_med_range / 100.0, 1e-12)
                pivot_low_kind[i] = (token, float(np.clip(strength, 0.0, 8.0)))
            prev_pl = float(lo[i])

    events: list[tuple[int, str, float]] = []
    for i in range(SEQ_BARS):
        same_bar: list[tuple[int, str, float]] = []

        if i >= SWEEP_LOOKBACK:
            prior_low = float(np.min(lo[i - SWEEP_LOOKBACK:i]))
            prior_high = float(np.max(hi[i - SWEEP_LOOKBACK:i]))
            if lo[i] < prior_low and cl[i] > prior_low:
                penetration_pct = (prior_low - lo[i]) / max(float(cl[i]), 1e-12) * 100.0
                strength = penetration_pct / seq_med_range
                same_bar.append((EVENT_ORDER["SWEEP_LOW_RECLAIM"], "SWEEP_LOW_RECLAIM", float(np.clip(strength, 0.0, 8.0))))
            if hi[i] > prior_high and cl[i] < prior_high:
                penetration_pct = (hi[i] - prior_high) / max(float(cl[i]), 1e-12) * 100.0
                strength = penetration_pct / seq_med_range
                same_bar.append((EVENT_ORDER["SWEEP_HIGH_REJECT"], "SWEEP_HIGH_REJECT", float(np.clip(strength, 0.0, 8.0))))

        if i in pivot_high_kind:
            token, strength = pivot_high_kind[i]
            same_bar.append((EVENT_ORDER[token], token, strength))
        if i in pivot_low_kind:
            token, strength = pivot_low_kind[i]
            same_bar.append((EVENT_ORDER[token], token, strength))

        if i >= 3:
            start = max(0, i - 12)
            prior_bodies = abs_body_pct[start:i]
            med_body = float(np.median(prior_bodies)) if len(prior_bodies) else np.nan
            if np.isfinite(med_body) and med_body > 1e-9:
                loc = _safe_close_loc(float(hi[i]), float(lo[i]), float(cl[i]))
                ratio = abs_body_pct[i] / med_body
                if body_pct[i] > 0 and ratio >= DISP_MULT and loc >= BULL_CLOSE_LOC:
                    same_bar.append((EVENT_ORDER["BULL_DISP"], "BULL_DISP", float(np.clip(ratio, 0.0, 8.0))))
                if body_pct[i] < 0 and ratio >= DISP_MULT and loc <= BEAR_CLOSE_LOC:
                    same_bar.append((EVENT_ORDER["BEAR_DISP"], "BEAR_DISP", float(np.clip(ratio, 0.0, 8.0))))

        same_bar.sort(key=lambda z: (z[0], z[1]))
        for _, token, strength in same_bar:
            events.append((i, token, strength))

    recent = events[-EVENT_SLOTS:]
    pad = EVENT_SLOTS - len(recent)
    slots: list[tuple[int, str, float] | None] = [None] * pad + recent
    out: dict[str, float] = {}
    for s, ev in enumerate(slots):
        token = "NONE" if ev is None else ev[1]
        for t in TOKEN_TYPES:
            out[f"slot{s:02d}_{t}"] = 1.0 if token == t else 0.0
        if ev is None:
            out[f"slot{s:02d}_recency"] = 1.0
            out[f"slot{s:02d}_strength"] = 0.0
        else:
            bar_i, _, strength = ev
            out[f"slot{s:02d}_recency"] = float(np.clip((SEQ_BARS - 1 - bar_i) / SEQ_BARS, 0.0, 1.0))
            out[f"slot{s:02d}_strength"] = float(np.clip(strength, 0.0, 8.0))

    counts = {t: 0 for t in EVENT_TYPES}
    for _, token, _ in events:
        counts[token] += 1
    for t in EVENT_TYPES:
        out[f"count_{t}"] = float(counts[t])

    a = np.asarray([out[c] for c in EVENT_VECTOR_COLS], dtype=float)
    if not np.isfinite(a).all():
        return None
    return out


def build_opportunities(x5: pd.DataFrame) -> pd.DataFrame:
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()
    rows = []

    start_i = max(SEQ_BARS - 1, TRAIL_BARS - 1)
    for i in range(start_i, len(x5) - FUTURE_BARS - 1):
        ts = idx[i]
        if ts < MODEL_START or ts >= MODEL_END or ts.minute not in DECISION_MINUTES:
            continue

        q = x5.iloc[i - SEQ_BARS + 1:i + 1]
        if len(q) != SEQ_BARS or q.index[-1] - q.index[0] != BAR * (SEQ_BARS - 1):
            continue
        vec = event_sequence_vector(q)
        if vec is None:
            continue

        trailing = x5.iloc[i - TRAIL_BARS + 1:i + 1]
        if len(trailing) != TRAIL_BARS or trailing.index[-1] - trailing.index[0] != BAR * (TRAIL_BARS - 1):
            continue
        lr = np.diff(np.log(trailing.close.astype(float).to_numpy()))
        if len(lr) < 250:
            continue
        sigma60 = float(np.std(lr, ddof=1) * np.sqrt(12.0) * 100.0)
        if not np.isfinite(sigma60) or sigma60 <= 0:
            continue

        entry_i = i + 1
        last_i = entry_i + FUTURE_BARS - 1
        if last_i >= len(x5):
            continue
        entry_time = idx[entry_i]
        last_time = idx[last_i]
        if entry_time != ts + BAR or last_time != entry_time + BAR * (FUTURE_BARS - 1):
            continue
        if entry_time >= MODEL_END or last_time >= MODEL_END:
            continue

        entry = float(op[entry_i])
        if not np.isfinite(entry) or entry <= 0:
            continue
        fhi = hi[entry_i:last_i + 1]
        flo = lo[entry_i:last_i + 1]
        exitp = float(cl[last_i])
        if not (np.isfinite(fhi).all() and np.isfinite(flo).all() and np.isfinite(exitp)):
            continue

        thr = max(UP_FLOOR_PCT, UP_SIGMA_MULT * sigma60)
        up_barrier = entry * (1.0 + thr / 100.0)
        dn_barrier = entry * (1.0 - DOWN_FRAC * thr / 100.0)
        up_touch = fhi >= up_barrier
        dn_touch = flo <= dn_barrier
        up_any = bool(up_touch.any())
        dn_any = bool(dn_touch.any())
        up_idx = int(np.argmax(up_touch)) if up_any else 999
        dn_idx = int(np.argmax(dn_touch)) if dn_any else 999
        clean_winner = int(up_any and (not dn_any or up_idx < dn_idx))
        if up_any and dn_any and up_idx == dn_idx:
            clean_winner = 0

        mfe = float((np.max(fhi) / entry - 1.0) * 100.0)
        mae = float((np.min(flo) / entry - 1.0) * 100.0)
        ratio = float(mfe / abs(mae)) if abs(mae) > 1e-9 else np.nan
        net60 = float((exitp / entry - 1.0) * 100.0 - ROUNDTRIP_COST_PCT)
        pre_up_mae = np.nan
        if up_any:
            pre_up_mae = float((np.min(flo[:up_idx + 1]) / entry - 1.0) * 100.0)

        rows.append({
            "signal_time": ts,
            "entry_time": entry_time,
            "exit_known_time": last_time + BAR,
            "year": int(ts.year),
            "entry_price": entry,
            "sigma60_pct": sigma60,
            "impulse_threshold_pct": thr,
            "clean_long_winner": clean_winner,
            "time_to_up_barrier_min": (up_idx + 1) * 5 if up_any else np.nan,
            "pre_up_mae_pct": pre_up_mae,
            "mfe60_pct": mfe,
            "mae60_pct": mae,
            "mfe_mae_ratio": ratio,
            "net60_pct": net60,
            **vec,
        })

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("no V2 event-structure opportunities")
    return out.sort_values("entry_time").reset_index(drop=True)


def assign_nearest(X: np.ndarray, centers: np.ndarray):
    d2 = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    fam = np.argmin(d2, axis=1)
    dist = np.sqrt(d2[np.arange(len(X)), fam])
    return fam.astype(int), dist.astype(float)


def fit_fold(ev: pd.DataFrame, test_year: int):
    train_start, train_end = v1.training_bounds(test_year)
    test_end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
    tr = ev[(ev.entry_time >= train_start) & (ev.exit_known_time <= train_end)].copy()
    te = ev[(ev.entry_time >= train_end) & (ev.entry_time < test_end)].copy()
    if tr.empty or te.empty:
        raise RuntimeError(f"missing fold data {test_year}")

    winners = tr[tr.clean_long_winner == 1].copy()
    if len(winners) < N_FAMILIES * 20:
        raise RuntimeError(f"insufficient clean winners for {test_year}: {len(winners)}")

    scaler = RobustScaler(quantile_range=(25.0, 75.0))
    Xtr = np.clip(scaler.fit_transform(tr[EVENT_VECTOR_COLS].astype(float).to_numpy()), -8.0, 8.0)
    Xte = np.clip(scaler.transform(te[EVENT_VECTOR_COLS].astype(float).to_numpy()), -8.0, 8.0)
    win_mask = tr.clean_long_winner.astype(int).to_numpy() == 1
    Xwin = Xtr[win_mask]

    km = MiniBatchKMeans(
        n_clusters=N_FAMILIES,
        random_state=42,
        batch_size=4096,
        n_init=10,
        reassignment_ratio=0.01,
    )
    win_family = km.fit_predict(Xwin)
    win_dist = np.linalg.norm(Xwin - km.cluster_centers_[win_family], axis=1)
    radii = {}
    for f in range(N_FAMILIES):
        z = win_dist[win_family == f]
        radii[f] = float(np.quantile(z, RADIUS_Q)) if len(z) else 0.0

    tr_fam, tr_dist = assign_nearest(Xtr, km.cluster_centers_)
    te_fam, te_dist = assign_nearest(Xte, km.cluster_centers_)
    tr = tr.copy(); te = te.copy()
    tr["family_id"] = tr_fam; tr["family_distance"] = tr_dist
    te["family_id"] = te_fam; te["family_distance"] = te_dist
    tr["within_radius"] = [d <= radii[int(f)] for f, d in zip(tr_fam, tr_dist)]
    te["within_radius"] = [d <= radii[int(f)] for f, d in zip(te_fam, te_dist)]

    baseline = float(tr.clean_long_winner.mean())
    family_rows = []
    eligible = {}
    for f in range(N_FAMILIES):
        g = tr[(tr.family_id == f) & tr.within_radius].copy()
        e = v1.econ(g)
        precision = float(g.clean_long_winner.mean()) if len(g) else np.nan
        lift = float(precision / baseline) if baseline > 0 and np.isfinite(precision) else np.nan
        represented = 0
        year_ok = True
        for _, gy in g.groupby("year"):
            if len(gy) >= 20:
                represented += 1
                if float(gy.net60_pct.mean()) < 0:
                    year_ok = False
        ok = bool(
            len(g) >= MIN_FAMILY_SUPPORT
            and np.isfinite(lift) and lift >= MIN_PRECISION_LIFT
            and np.isfinite(e["expectancy_pct"]) and e["expectancy_pct"] > 0
            and np.isfinite(e["pf"]) and e["pf"] >= MIN_TRAIN_PF
            and represented >= 1
            and year_ok
        )
        eligible[f] = ok
        family_rows.append({
            "test_year": test_year,
            "family_id": f,
            "radius": radii[f],
            "train_baseline_clean_rate": baseline,
            "train_match_n": int(len(g)),
            "train_clean_precision": precision,
            "train_precision_lift": lift,
            "train_wr60": e["wr"],
            "train_expectancy60_pct": e["expectancy_pct"],
            "train_pf60": e["pf"],
            "represented_train_years_ge20": represented,
            "train_year_stability_ok": year_ok,
            "eligible_family": ok,
        })

    te["test_year"] = test_year
    te["eligible_family"] = te.family_id.map(eligible).fillna(False).astype(bool)
    te["selected"] = te.within_radius.astype(bool) & te.eligible_family.astype(bool)
    return te, pd.DataFrame(family_rows)


def family_transfer(scored: pd.DataFrame, famstats: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in famstats[famstats.eligible_family].iterrows():
        y = int(r.test_year); f = int(r.family_id)
        g = scored[(scored.test_year == y) & (scored.family_id == f) & scored.within_radius].copy()
        e = v1.econ(g)
        rows.append({
            **r.to_dict(),
            "test_match_n": int(len(g)),
            "test_clean_precision": float(g.clean_long_winner.mean()) if len(g) else np.nan,
            "test_wr60": e["wr"],
            "test_expectancy60_pct": e["expectancy_pct"],
            "test_pf60": e["pf"],
            "test_pnl_usd": e["pnl_usd"],
        })
    return pd.DataFrame(rows)


def yearly_summary(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in TEST_YEARS:
        a = scored[scored.test_year == y].copy()
        s = a[a.selected].copy()
        e = v1.econ(s)
        base = float(a.clean_long_winner.mean()) if len(a) else np.nan
        prec = float(s.clean_long_winner.mean()) if len(s) else np.nan
        rows.append({
            "test_year": y,
            "all_n": int(len(a)),
            "baseline_clean_rate": base,
            "selected_n": int(len(s)),
            "selected_clean_precision": prec,
            "precision_lift": float(prec / base) if len(s) and base > 0 else np.nan,
            "selected_wr60": e["wr"],
            "selected_expectancy60_pct": e["expectancy_pct"],
            "selected_pf60": e["pf"],
            "selected_pnl_usd": e["pnl_usd"],
            "selected_max_dd_usd": e["max_dd_usd"],
            "selected_max_ls": e["max_ls"],
            "median_mfe60_pct": float(s.mfe60_pct.median()) if len(s) else np.nan,
            "median_mae60_pct": float(s.mae60_pct.median()) if len(s) else np.nan,
            "median_mfe_mae_ratio": float(s.mfe_mae_ratio.replace([np.inf, -np.inf], np.nan).median()) if len(s) else np.nan,
            "selected_family_count": int(s.family_id.nunique()) if len(s) else 0,
        })
    return pd.DataFrame(rows)


def pfmt(v):
    if pd.isna(v): return "n/a"
    if np.isinf(v): return "inf"
    return f"{float(v):.3f}"


def main():
    # Data loader only. No V4/V5 detector semantics are reused.
    v1.v3.v1.base.fetch_one = v1.v3.v1.fetch_one_with_volume
    x5, coverage = v1.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    ev = build_opportunities(x5)
    scored_parts = []
    fam_parts = []
    for y in TEST_YEARS:
        s, f = fit_fold(ev, y)
        scored_parts.append(s)
        fam_parts.append(f)
    scored = pd.concat(scored_parts, ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    famstats = pd.concat(fam_parts, ignore_index=True)
    selected = scored[scored.selected].copy().reset_index(drop=True)
    transfer = family_transfer(scored, famstats)
    yr = yearly_summary(scored)

    all_oos_e = v1.econ(scored)
    sel_e = v1.econ(selected)
    base_clean = float(scored.clean_long_winner.mean())
    sel_clean = float(selected.clean_long_winner.mean()) if len(selected) else np.nan
    lift = float(sel_clean / base_clean) if len(selected) and base_clean > 0 else np.nan
    med_ratio = float(selected.mfe_mae_ratio.replace([np.inf, -np.inf], np.nan).median()) if len(selected) else np.nan
    pos_years = int((yr.selected_pnl_usd > 0).sum())
    family_keys = int(selected.groupby(["test_year", "family_id"]).ngroups) if len(selected) else 0

    gates = {
        "selected_oos_n_ge_100": len(selected) >= 100,
        "clean_winner_precision_lift_ge_1_50x": bool(np.isfinite(lift) and lift >= 1.50),
        "fixed60_expectancy_positive": bool(np.isfinite(sel_e["expectancy_pct"]) and sel_e["expectancy_pct"] > 0),
        "fixed60_pf_ge_1_15": bool(np.isfinite(sel_e["pf"]) and sel_e["pf"] >= 1.15),
        "positive_pnl_years_ge_2_of_3": pos_years >= 2,
        "median_mfe_mae_ratio_ge_1_25": bool(np.isfinite(med_ratio) and med_ratio >= 1.25),
        "distinct_selected_family_keys_ge_2": family_keys >= 2,
    }
    passed = bool(all(gates.values()))
    verdict = "WINNER_EVENT_FAMILIES_FOUND" if passed else "WINNER_FIRST_V2_NOT_READY"

    ev.to_csv(ROOT / f"{PFX}_Opportunities.csv", index=False)
    scored.to_csv(ROOT / f"{PFX}_OOSAssignments.csv", index=False)
    selected.to_csv(ROOT / f"{PFX}_SelectedTrades.csv", index=False)
    famstats.to_csv(ROOT / f"{PFX}_TrainingFamilyStats.csv", index=False)
    transfer.to_csv(ROOT / f"{PFX}_FamilyTransfer.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    lines = [
        "# SOL Reset — Winner-First V2 Event-Relative Structure Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- Research opportunities: **{len(ev)}**",
        f"- OOS opportunities 2022-2024: **{len(scored)}**",
        f"- OOS selected LONG entries: **{len(selected)}**",
        f"- OOS baseline clean-winner rate: **{base_clean*100:.2f}%**",
        f"- Selected clean-winner precision: **{sel_clean*100:.2f}%**" if np.isfinite(sel_clean) else "- Selected clean-winner precision: **n/a**",
        f"- Precision lift: **{lift:.3f}x**" if np.isfinite(lift) else "- Precision lift: **n/a**",
        f"- Selected family keys: **{family_keys}**",
        "- Representation: ordered pivot/sweep/displacement event stream; no raw candle-position path matching.",
        "- 2025+ reference_validation remained CLOSED.", "",
        "## Fixed +60m diagnostic", "",
        f"- ALL OOS expectancy: **{all_oos_e['expectancy_pct']:.4f}%**, PF **{pfmt(all_oos_e['pf'])}**",
        f"- Selected WR: **{sel_e['wr']*100:.2f}%**" if np.isfinite(sel_e['wr']) else "- Selected WR: **n/a**",
        f"- Selected expectancy: **{sel_e['expectancy_pct']:.4f}%**" if np.isfinite(sel_e['expectancy_pct']) else "- Selected expectancy: **n/a**",
        f"- Selected PF: **{pfmt(sel_e['pf'])}**",
        f"- Selected PnL: **${sel_e['pnl_usd']:.2f}**",
        f"- Selected max DD: **${sel_e['max_dd_usd']:.2f}**" if np.isfinite(sel_e['max_dd_usd']) else "- Selected max DD: **n/a**",
        f"- Selected max loss streak: **{sel_e['max_ls']}**", "",
        "## Future-path geometry", "",
        f"- Median MFE60: **{float(selected.mfe60_pct.median()):.4f}%**" if len(selected) else "- Median MFE60: **n/a**",
        f"- Median MAE60: **{float(selected.mae60_pct.median()):.4f}%**" if len(selected) else "- Median MAE60: **n/a**",
        f"- Median MFE/|MAE|: **{med_ratio:.3f}**" if np.isfinite(med_ratio) else "- Median MFE/|MAE|: **n/a**", "",
        "## Year stability", "",
        "| Year | All N | Baseline clean | Selected | Precision | Lift | WR60 | Exp60 | PF | PnL | Ratio | Families |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in yr.iterrows():
        lines.append(
            f"| {int(r.test_year)} | {int(r.all_n)} | {float(r.baseline_clean_rate)*100:.2f}% | {int(r.selected_n)} | "
            + (f"{float(r.selected_clean_precision)*100:.2f}% | {float(r.precision_lift):.3f}x | {float(r.selected_wr60)*100:.2f}% | {float(r.selected_expectancy60_pct):.4f}% | {pfmt(r.selected_pf60)} | ${float(r.selected_pnl_usd):.2f} | {float(r.median_mfe_mae_ratio):.3f} | {int(r.selected_family_count)} |" if int(r.selected_n) else "n/a | n/a | n/a | n/a | n/a | $0.00 | n/a | 0 |")
        )

    lines += ["", "## Training-eligible family transfer", ""]
    if transfer.empty:
        lines.append("- No training family passed the frozen eligibility gate.")
    else:
        for _, r in transfer.sort_values(["test_year", "family_id"]).iterrows():
            lines.append(
                f"- {int(r.test_year)} family {int(r.family_id)} — train N{int(r.train_match_n)} precision {float(r.train_clean_precision)*100:.2f}% lift {float(r.train_precision_lift):.2f}x exp {float(r.train_expectancy60_pct):.4f}% PF {pfmt(r.train_pf60)} → test N{int(r.test_match_n)} precision {float(r.test_clean_precision)*100:.2f}% exp {float(r.test_expectancy60_pct):.4f}% PF {pfmt(r.test_pf60)}"
            )

    lines += ["", "## Gate audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "", f"# VERDICT: {verdict}", "",
        "WINNER_EVENT_FAMILIES_FOUND means winner-derived event-relative structural families transfer OOS with positive pre-exit-optimization economics and can advance to causal detector/execution characterization.",
        "WINNER_FIRST_V2_NOT_READY means do not rescue this exact event representation by sweeping pivot order, sweep lookback, displacement thresholds, event slots, family count/radius/support, winner barriers, precursor length, hours, horizon, TP or SL on 2022-2024.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
