#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import RobustScaler

import sol_structural_motif_discovery_v3 as v3

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_RESET_WINNER_FIRST_V1"
MODEL_START = pd.Timestamp("2020-01-01", tz="UTC")
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
BAR = pd.Timedelta(minutes=5)
SEQ_BARS = 24
TRAIL_BARS = 288
DECISION_MINUTES = (0, 15, 30, 45)
FUTURE_BARS = 12
ROUNDTRIP_COST_PCT = 0.15
NOTIONAL = 500.0
TEST_YEARS = (2022, 2023, 2024)
TRAIN_WINDOW_YEARS = 2
N_FAMILIES = 12
RADIUS_Q = 0.75
MIN_FAMILY_SUPPORT = 80
MIN_PRECISION_LIFT = 1.50
MIN_TRAIN_PF = 1.10
UP_FLOOR_PCT = 0.75
UP_SIGMA_MULT = 1.5
DOWN_FRAC = 0.50
VECTOR_COLS = v3.VECTOR_COLS


def profit_factor(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def max_drawdown(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    if a.empty:
        return np.nan
    eq = a.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def max_loss_streak(pnls) -> int:
    best = cur = 0
    for x in pd.Series(pnls, dtype=float).dropna():
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def econ(g: pd.DataFrame) -> dict:
    if g.empty:
        return {
            "n": 0, "wr": np.nan, "expectancy_pct": np.nan,
            "pnl_usd": 0.0, "pf": np.nan, "max_dd_usd": np.nan,
            "max_ls": 0,
        }
    r = g.net60_pct.astype(float)
    p = r / 100.0 * NOTIONAL
    return {
        "n": int(len(g)),
        "wr": float((r > 0).mean()),
        "expectancy_pct": float(r.mean()),
        "pnl_usd": float(p.sum()),
        "pf": float(profit_factor(p)),
        "max_dd_usd": float(max_drawdown(p)),
        "max_ls": int(max_loss_streak(p)),
    }


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
        vec = v3.sequence_vector(q)
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
        denom = abs(mae)
        ratio = float(mfe / denom) if denom > 1e-9 else np.nan
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
        raise RuntimeError("no winner-first opportunities")
    return out.sort_values("entry_time").reset_index(drop=True)


def training_bounds(test_year: int):
    end = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
    start = pd.Timestamp(f"{test_year - TRAIN_WINDOW_YEARS}-01-01", tz="UTC")
    return max(start, MODEL_START), end


def assign_nearest(X: np.ndarray, centers: np.ndarray):
    d2 = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    fam = np.argmin(d2, axis=1)
    dist = np.sqrt(d2[np.arange(len(X)), fam])
    return fam.astype(int), dist.astype(float)


def fit_fold(ev: pd.DataFrame, test_year: int):
    train_start, train_end = training_bounds(test_year)
    test_end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
    tr = ev[(ev.entry_time >= train_start) & (ev.exit_known_time <= train_end)].copy()
    te = ev[(ev.entry_time >= train_end) & (ev.entry_time < test_end)].copy()
    if tr.empty or te.empty:
        raise RuntimeError(f"missing fold data {test_year}")

    winners = tr[tr.clean_long_winner == 1].copy()
    if len(winners) < N_FAMILIES * 20:
        raise RuntimeError(f"insufficient clean winners for {test_year}: {len(winners)}")

    scaler = RobustScaler(quantile_range=(25.0, 75.0))
    Xtr = np.clip(scaler.fit_transform(tr[VECTOR_COLS].astype(float).to_numpy()), -8.0, 8.0)
    Xte = np.clip(scaler.transform(te[VECTOR_COLS].astype(float).to_numpy()), -8.0, 8.0)
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
        e = econ(g)
        precision = float(g.clean_long_winner.mean()) if len(g) else np.nan
        lift = float(precision / baseline) if baseline > 0 and np.isfinite(precision) else np.nan
        year_ok = True
        represented = 0
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
        e = econ(g)
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
        e = econ(s)
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
    # Reuse only the repository's SOL 5m loader; no V4 detector semantics are used.
    v3.v1.base.fetch_one = v3.v1.fetch_one_with_volume
    x5, coverage = v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    ev = build_opportunities(x5)
    scored_parts = []; fam_parts = []
    for y in TEST_YEARS:
        s, f = fit_fold(ev, y)
        scored_parts.append(s); fam_parts.append(f)
    scored = pd.concat(scored_parts, ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    famstats = pd.concat(fam_parts, ignore_index=True)
    selected = scored[scored.selected].copy().reset_index(drop=True)
    transfer = family_transfer(scored, famstats)
    years = yearly_summary(scored)

    all_e = econ(scored)
    sel_e = econ(selected)
    baseline = float(scored.clean_long_winner.mean())
    precision = float(selected.clean_long_winner.mean()) if len(selected) else np.nan
    lift = float(precision / baseline) if len(selected) and baseline > 0 else np.nan
    finite_ratio = selected.mfe_mae_ratio.replace([np.inf, -np.inf], np.nan) if len(selected) else pd.Series(dtype=float)
    med_ratio = float(finite_ratio.median()) if len(finite_ratio) else np.nan
    positive_years = int((years.selected_pnl_usd > 0).sum())
    family_keys = int(selected.assign(family_key=selected.test_year.astype(str)+":"+selected.family_id.astype(str)).family_key.nunique()) if len(selected) else 0

    gates = {
        "selected_oos_n_ge_100": len(selected) >= 100,
        "clean_winner_precision_lift_ge_1_50x": bool(np.isfinite(lift) and lift >= 1.50),
        "fixed60_expectancy_positive": bool(np.isfinite(sel_e["expectancy_pct"]) and sel_e["expectancy_pct"] > 0),
        "fixed60_pf_ge_1_15": bool(np.isfinite(sel_e["pf"]) and sel_e["pf"] >= 1.15),
        "positive_pnl_years_ge_2_of_3": positive_years >= 2,
        "median_mfe_mae_ratio_ge_1_25": bool(np.isfinite(med_ratio) and med_ratio >= 1.25),
        "distinct_selected_family_keys_ge_2": family_keys >= 2,
    }
    passed = bool(all(gates.values()))
    verdict = "WINNER_PRECURSOR_FAMILIES_FOUND" if passed else "WINNER_FIRST_V1_NOT_READY"

    ev.to_csv(ROOT / f"{PFX}_Opportunities.csv", index=False)
    scored.to_csv(ROOT / f"{PFX}_OOSAssignments.csv", index=False)
    selected.to_csv(ROOT / f"{PFX}_SelectedTrades.csv", index=False)
    famstats.to_csv(ROOT / f"{PFX}_TrainingFamilyStats.csv", index=False)
    transfer.to_csv(ROOT / f"{PFX}_FamilyTransfer.csv", index=False)
    years.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    lines = [
        "# SOL Reset — Winner-First Discovery V1 Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- Research opportunities: **{len(ev)}**",
        f"- OOS opportunities 2022-2024: **{len(scored)}**",
        f"- OOS selected LONG entries: **{len(selected)}**",
        f"- OOS baseline clean-winner rate: **{baseline*100:.2f}%**",
        f"- Selected clean-winner precision: **{precision*100:.2f}%**" if np.isfinite(precision) else "- Selected clean-winner precision: **n/a**",
        f"- Precision lift: **{lift:.3f}x**" if np.isfinite(lift) else "- Precision lift: **n/a**",
        f"- Selected family keys: **{family_keys}**",
        "- 2025+ reference_validation remained CLOSED.", "",
        "## Fixed +60m diagnostic", "",
        f"- ALL OOS expectancy: **{all_e['expectancy_pct']:.4f}%**, PF **{pfmt(all_e['pf'])}**",
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
    for _, r in years.iterrows():
        lines.append(
            f"| {int(r.test_year)} | {int(r.all_n)} | {float(r.baseline_clean_rate)*100:.2f}% | {int(r.selected_n)} | "
            + (f"{float(r.selected_clean_precision)*100:.2f}% | {float(r.precision_lift):.3f}x | {float(r.selected_wr60)*100:.2f}% | {float(r.selected_expectancy60_pct):.4f}% | {pfmt(r.selected_pf60)} | ${float(r.selected_pnl_usd):.2f} | {float(r.median_mfe_mae_ratio):.3f} | {int(r.selected_family_count)} |" if int(r.selected_n) else "n/a | n/a | n/a | n/a | n/a | $0.00 | n/a | 0 |")
        )
    lines += ["", "## Gate audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "", f"# VERDICT: {verdict}", "",
        "WINNER_PRECURSOR_FAMILIES_FOUND means winner-derived precursor families transfer OOS with positive pre-exit-optimization economics and can advance to a causal detector/execution characterization stage.",
        "WINNER_FIRST_V1_NOT_READY means do not rescue this exact architecture by sweeping clusters, winner barriers, precursor length, radius, support, hour filters, horizon, TP, or SL on 2022-2024.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
