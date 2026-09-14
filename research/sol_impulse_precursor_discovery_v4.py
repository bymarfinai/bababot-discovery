#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import roc_auc_score

import sol_structural_motif_discovery_v3 as v3

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_IMPULSE_PRECURSOR_DISCOVERY_V4"
MODEL_START = pd.Timestamp("2020-01-01", tz="UTC")
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
BAR = pd.Timedelta(minutes=5)
SEQ_BARS = 24
DECISION_MINUTES = (0, 15, 30, 45)
HOLD_MINUTES = 60
ROUNDTRIP_COST_PCT = 0.15
NOTIONAL = 500.0
TEST_YEARS = (2021, 2022, 2023, 2024)

IMPULSE_FLOOR_PCT = 0.75
IMPULSE_SIGMA_MULT = 1.5
CONTROL_RATIO = 3

BASE_VECTOR_COLS = v3.VECTOR_COLS
TRANSITION_COLS = [
    "ret_15", "ret_30", "ret_60", "ret_120",
    "rv_15", "rv_30", "rv_60", "rv_120",
    "range_15", "range_30", "range_60", "range_120",
    "eff_30", "eff_60", "eff_120",
    "compression_range_30_120", "compression_rv_30_120",
    "volume_30_vs_prior90", "volume_15_vs_prior105",
    "close_pos_120", "dist_from_high_120_pct", "dist_from_low_120_pct",
    "downside_sweep_reclaim", "downside_sweep_depth_pct",
    "upside_sweep_reject", "upside_sweep_depth_pct",
    "accel_15", "accel_30",
    "lower_wick_frac_30", "upper_wick_frac_30", "up_close_ratio_30",
]
FEATURES = BASE_VECTOR_COLS + TRANSITION_COLS


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


def pct_return(cl: np.ndarray, bars: int) -> float:
    if len(cl) < bars + 1:
        return np.nan
    return float((cl[-1] / cl[-bars - 1] - 1.0) * 100.0)


def rv_horizon(cl: np.ndarray, bars: int) -> float:
    if len(cl) < bars + 1:
        return np.nan
    z = np.diff(np.log(cl[-bars - 1:]))
    if len(z) < 2:
        return np.nan
    return float(np.std(z, ddof=1) * np.sqrt(bars) * 100.0)


def range_pct(q: pd.DataFrame, bars: int) -> float:
    z = q.iloc[-bars:]
    lo = float(z.low.min()); hi = float(z.high.max()); base = float(z.close.iloc[0])
    return float((hi / lo - 1.0) * 100.0) if lo > 0 and base > 0 else np.nan


def efficiency(cl: np.ndarray, bars: int) -> float:
    if len(cl) < bars + 1:
        return np.nan
    z = np.log(cl[-bars - 1:])
    gross = abs(float(z[-1] - z[0]))
    path = float(np.abs(np.diff(z)).sum())
    return gross / path if path > 1e-12 else 0.0


def transition_features(q: pd.DataFrame) -> dict | None:
    if len(q) != SEQ_BARS:
        return None
    op = q.open.astype(float).to_numpy(); hi = q.high.astype(float).to_numpy()
    lo = q.low.astype(float).to_numpy(); cl = q.close.astype(float).to_numpy(); vol = q.volume.astype(float).to_numpy()
    if not all(np.isfinite(a).all() for a in (op, hi, lo, cl, vol)):
        return None
    if np.any(cl <= 0) or np.any(op <= 0) or np.any(lo <= 0):
        return None

    ret15 = pct_return(cl, 3); ret30 = pct_return(cl, 6); ret60 = pct_return(cl, 12); ret120 = pct_return(cl, 23)
    rv15 = rv_horizon(cl, 3); rv30 = rv_horizon(cl, 6); rv60 = rv_horizon(cl, 12); rv120 = rv_horizon(cl, 23)
    r15 = range_pct(q, 3); r30 = range_pct(q, 6); r60 = range_pct(q, 12); r120 = range_pct(q, 24)

    prior90 = q.iloc[:-6]
    last30 = q.iloc[-6:]
    prior105 = q.iloc[:-3]
    last15 = q.iloc[-3:]
    prior90_low = float(prior90.low.min()); prior90_high = float(prior90.high.max())
    last_close = float(q.close.iloc[-1]); last30_low = float(last30.low.min()); last30_high = float(last30.high.max())

    sweep_dn = float(last30_low < prior90_low and last_close > prior90_low)
    sweep_up = float(last30_high > prior90_high and last_close < prior90_high)
    sweep_dn_depth = max(0.0, (prior90_low / last30_low - 1.0) * 100.0) if last30_low > 0 else 0.0
    sweep_up_depth = max(0.0, (last30_high / prior90_high - 1.0) * 100.0) if prior90_high > 0 else 0.0

    hi120 = float(q.high.max()); lo120 = float(q.low.min())
    span120 = hi120 - lo120
    close_pos = (last_close - lo120) / span120 if span120 > 0 else 0.5
    dist_hi = (last_close / hi120 - 1.0) * 100.0 if hi120 > 0 else np.nan
    dist_lo = (last_close / lo120 - 1.0) * 100.0 if lo120 > 0 else np.nan

    span = last30.high.astype(float).to_numpy() - last30.low.astype(float).to_numpy()
    lower = np.maximum(0.0, np.minimum(last30.open.astype(float).to_numpy(), last30.close.astype(float).to_numpy()) - last30.low.astype(float).to_numpy())
    upper = np.maximum(0.0, last30.high.astype(float).to_numpy() - np.maximum(last30.open.astype(float).to_numpy(), last30.close.astype(float).to_numpy()))
    lower_frac = float(np.mean(np.divide(lower, span, out=np.zeros_like(lower), where=span > 0)))
    upper_frac = float(np.mean(np.divide(upper, span, out=np.zeros_like(upper), where=span > 0)))
    up_ratio = float((last30.close.astype(float).to_numpy() > last30.open.astype(float).to_numpy()).mean())

    v_prior90 = float(prior90.volume.astype(float).median())
    v_prior105 = float(prior105.volume.astype(float).median())
    v30 = float(last30.volume.astype(float).mean())
    v15 = float(last15.volume.astype(float).mean())

    prev15 = float((cl[-4] / cl[-7] - 1.0) * 100.0) if len(cl) >= 7 else 0.0
    prev30 = float((cl[-7] / cl[-13] - 1.0) * 100.0) if len(cl) >= 13 else 0.0

    out = {
        "ret_15": ret15, "ret_30": ret30, "ret_60": ret60, "ret_120": ret120,
        "rv_15": rv15, "rv_30": rv30, "rv_60": rv60, "rv_120": rv120,
        "range_15": r15, "range_30": r30, "range_60": r60, "range_120": r120,
        "eff_30": efficiency(cl, 6), "eff_60": efficiency(cl, 12), "eff_120": efficiency(cl, 23),
        "compression_range_30_120": r30 / r120 if r120 and r120 > 1e-12 else np.nan,
        "compression_rv_30_120": rv30 / rv120 if rv120 and rv120 > 1e-12 else np.nan,
        "volume_30_vs_prior90": v30 / v_prior90 if v_prior90 > 0 else np.nan,
        "volume_15_vs_prior105": v15 / v_prior105 if v_prior105 > 0 else np.nan,
        "close_pos_120": close_pos,
        "dist_from_high_120_pct": dist_hi,
        "dist_from_low_120_pct": dist_lo,
        "downside_sweep_reclaim": sweep_dn,
        "downside_sweep_depth_pct": sweep_dn_depth,
        "upside_sweep_reject": sweep_up,
        "upside_sweep_depth_pct": sweep_up_depth,
        "accel_15": ret15 - prev15,
        "accel_30": ret30 - prev30,
        "lower_wick_frac_30": lower_frac,
        "upper_wick_frac_30": upper_frac,
        "up_close_ratio_30": up_ratio,
    }
    a = np.asarray(list(out.values()), dtype=float)
    return out if np.isfinite(a).all() else None


def build_opportunities(x5: pd.DataFrame) -> pd.DataFrame:
    idx = x5.index
    rows = []
    for i in range(max(SEQ_BARS - 1, 288), len(x5) - 13):
        ts = idx[i]
        if ts < MODEL_START or ts >= MODEL_END or ts.minute not in DECISION_MINUTES:
            continue
        q = x5.iloc[i - SEQ_BARS + 1:i + 1]
        if len(q) != SEQ_BARS or q.index[-1] - q.index[0] != BAR * (SEQ_BARS - 1):
            continue
        seq = v3.sequence_vector(q)
        trans = transition_features(q)
        if seq is None or trans is None:
            continue

        prev24 = x5.iloc[i - 288 + 1:i + 1]
        if len(prev24) != 288 or prev24.index[-1] - prev24.index[0] != BAR * 287:
            continue
        lr = np.diff(np.log(prev24.close.astype(float).to_numpy()))
        if len(lr) < 250:
            continue
        sigma60 = float(np.std(lr, ddof=1) * np.sqrt(12.0) * 100.0)
        if not np.isfinite(sigma60) or sigma60 <= 0:
            continue

        entry_i = i + 1
        exit_i = entry_i + HOLD_MINUTES // 5 - 1
        if exit_i >= len(x5):
            continue
        entry_ts = idx[entry_i]; exit_bar_ts = idx[exit_i]
        if entry_ts != ts + BAR or exit_bar_ts != entry_ts + pd.Timedelta(minutes=HOLD_MINUTES) - BAR:
            continue
        if entry_ts >= MODEL_END or exit_bar_ts >= MODEL_END:
            continue
        entry = float(x5.iloc[entry_i].open); exitp = float(x5.iloc[exit_i].close)
        if not (np.isfinite(entry) and np.isfinite(exitp) and entry > 0):
            continue
        gross = float((exitp / entry - 1.0) * 100.0)
        net = gross - ROUNDTRIP_COST_PCT
        impulse_thr = max(IMPULSE_FLOOR_PCT, IMPULSE_SIGMA_MULT * sigma60)
        impulse = int(gross >= impulse_thr)

        rows.append({
            "signal_time": ts, "entry_time": entry_ts, "exit_known_time": exit_bar_ts + BAR,
            "year": int(ts.year), "month": int(ts.month), "hour_utc": int(ts.hour), "minute_utc": int(ts.minute),
            "hour_wib": int((ts.hour + 7) % 24),
            "sigma60_pct": sigma60, "impulse_threshold_pct": impulse_thr, "impulse": impulse,
            "gross_60m_pct": gross, "net_60m_pct": net, "pnl_60m_usd": net / 100.0 * NOTIONAL,
            **seq, **trans,
        })
    ev = pd.DataFrame(rows)
    if ev.empty:
        raise RuntimeError("no precursor opportunities")
    return ev.sort_values("entry_time").reset_index(drop=True)


def training_bounds(test_year: int):
    end = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
    start = pd.Timestamp(f"{max(MODEL_START.year, test_year - 2)}-01-01", tz="UTC")
    return start, end


def matched_training(tr: pd.DataFrame, test_year: int) -> pd.DataFrame:
    z = tr.copy()
    try:
        z["vol_bin"] = pd.qcut(z.sigma60_pct.rank(method="first"), 5, labels=False)
    except ValueError:
        z["vol_bin"] = 0
    z["ym"] = z.entry_time.dt.strftime("%Y-%m")
    parts = []
    seed_base = 1000 + test_year
    for gi, (_, g) in enumerate(z.groupby(["ym", "hour_utc", "vol_bin"], sort=True)):
        pos = g[g.impulse == 1]
        neg = g[g.impulse == 0]
        if pos.empty or neg.empty:
            continue
        take = min(len(neg), CONTROL_RATIO * len(pos))
        parts.append(pos)
        parts.append(neg.sample(n=take, random_state=seed_base + gi, replace=False))
    if not parts:
        raise RuntimeError(f"no matched training rows for {test_year}")
    m = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["entry_time"])
    if m.impulse.nunique() < 2:
        raise RuntimeError(f"matched training has one class for {test_year}")
    return m.sort_values("entry_time").reset_index(drop=True)


def model():
    return ExtraTreesClassifier(
        n_estimators=240,
        max_depth=8,
        min_samples_leaf=30,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def fit_predict_year(ev: pd.DataFrame, test_year: int):
    a, b = training_bounds(test_year)
    te_end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
    tr = ev[(ev.entry_time >= a) & (ev.exit_known_time <= b)].copy()
    te = ev[(ev.entry_time >= b) & (ev.entry_time < te_end)].copy()
    if tr.empty or te.empty:
        raise RuntimeError(f"missing train/test {test_year}")
    mt = matched_training(tr, test_year)
    clf = model()
    clf.fit(mt[FEATURES].astype(float).to_numpy(), mt.impulse.astype(int).to_numpy())
    te = te.copy()
    te["test_year"] = test_year
    te["pred_impulse"] = clf.predict_proba(te[FEATURES].astype(float).to_numpy())[:, 1]
    imp = pd.DataFrame({"test_year": test_year, "feature": FEATURES, "importance": clf.feature_importances_})
    return te, mt, imp


def walk_forward(ev: pd.DataFrame):
    pp, mm, ii = [], [], []
    for y in TEST_YEARS:
        p, m, i = fit_predict_year(ev, y)
        pp.append(p); mm.append(m.assign(test_year=y)); ii.append(i)
    return pd.concat(pp, ignore_index=True), pd.concat(mm, ignore_index=True), pd.concat(ii, ignore_index=True)


def econ(g: pd.DataFrame) -> dict:
    if g.empty:
        return {"n": 0, "wr": np.nan, "expectancy_pct": np.nan, "net_pnl_usd": 0.0, "pf": np.nan, "max_dd_usd": np.nan, "max_ls": 0, "impulse_rate": np.nan}
    p = g.pnl_60m_usd.astype(float); r = g.net_60m_pct.astype(float)
    return {
        "n": int(len(g)), "wr": float((r > 0).mean()), "expectancy_pct": float(r.mean()),
        "net_pnl_usd": float(p.sum()), "pf": float(profit_factor(p)), "max_dd_usd": float(max_drawdown(p)),
        "max_ls": int(max_loss_streak(p)), "impulse_rate": float(g.impulse.mean()),
    }


def score_deciles(pred: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for y, g in pred.groupby("test_year"):
        q = g.copy()
        q["score_decile"] = pd.qcut(q.pred_impulse.rank(method="first"), 10, labels=range(1, 11)).astype(int)
        parts.append(q)
    return pd.concat(parts, ignore_index=True)


def main():
    v3.v1.base.fetch_one = v3.v1.fetch_one_with_volume
    x5, coverage = v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")
    ev = build_opportunities(x5)
    pred, matched, imp = walk_forward(ev)
    scored = score_deciles(pred)

    rows = []
    for d, g in scored.groupby("score_decile"):
        rows.append({"score_decile": int(d), "mean_score": float(g.pred_impulse.mean()), **econ(g)})
    dec = pd.DataFrame(rows).sort_values("score_decile")

    years = []
    for y, g in scored.groupby("test_year"):
        for scope, q in (("ALL", g), ("TOP_DECILE", g[g.score_decile == 10])):
            years.append({"test_year": int(y), "scope": scope, **econ(q)})
    yr = pd.DataFrame(years).sort_values(["test_year", "scope"])

    auc = float(roc_auc_score(pred.impulse.astype(int), pred.pred_impulse.astype(float))) if pred.impulse.nunique() > 1 else np.nan
    rho = float(spearmanr(pred.pred_impulse.astype(float), pred.net_60m_pct.astype(float)).statistic)
    allm = econ(scored)
    topm = econ(scored[scored.score_decile == 10])
    botm = econ(scored[scored.score_decile == 1])
    lift = topm["impulse_rate"] / allm["impulse_rate"] if allm["impulse_rate"] > 0 else np.nan
    pos_years = int(sum(float(r.net_pnl_usd) > 0 for _, r in yr[yr.scope == "TOP_DECILE"].iterrows()))

    fi = imp.groupby("feature", as_index=False).importance.mean().sort_values("importance", ascending=False)
    contrast = []
    for f in TRANSITION_COLS:
        a = matched[matched.impulse == 1][f].astype(float)
        b = matched[matched.impulse == 0][f].astype(float)
        pooled = float(np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0))
        effect = (float(a.mean()) - float(b.mean())) / pooled if np.isfinite(pooled) and pooled > 1e-12 else 0.0
        contrast.append({"feature": f, "impulse_mean": float(a.mean()), "control_mean": float(b.mean()), "std_effect": effect})
    contrast = pd.DataFrame(contrast).sort_values("std_effect", key=lambda s: s.abs(), ascending=False)

    gates = {
        "auc_ge_0_55": bool(np.isfinite(auc) and auc >= .55),
        "top_decile_impulse_lift_ge_1_50x": bool(np.isfinite(lift) and lift >= 1.50),
        "top_decile_expectancy_positive": bool(topm["expectancy_pct"] > 0),
        "top_decile_pf_ge_1_20": bool(np.isfinite(topm["pf"]) and topm["pf"] >= 1.20),
        "top_decile_positive_years_ge_3": pos_years >= 3,
        "top_beats_bottom_impulse_rate": bool(topm["impulse_rate"] > botm["impulse_rate"]),
        "top_beats_bottom_expectancy": bool(topm["expectancy_pct"] > botm["expectancy_pct"]),
    }
    passed = bool(all(gates.values()))

    ev.to_csv(ROOT / f"{PFX}_Opportunities.csv", index=False)
    pred.to_csv(ROOT / f"{PFX}_Predictions.csv", index=False)
    dec.to_csv(ROOT / f"{PFX}_ScoreDeciles.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    fi.to_csv(ROOT / f"{PFX}_FeatureImportance.csv", index=False)
    contrast.to_csv(ROOT / f"{PFX}_TransitionContrast.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    def pfmt(v):
        if pd.isna(v): return "n/a"
        if np.isinf(v): return "inf"
        return f"{float(v):.3f}"

    lines = [
        "# SOL Impulse Precursor Discovery v4 — Walk-Forward Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- Raw decision opportunities 2020-2024: **{len(ev)}**",
        f"- OOS predictions 2021-2024: **{len(pred)}**",
        f"- OOS strong-upside-impulse rate: **{allm['impulse_rate']*100:.2f}%**",
        f"- ROC AUC: **{auc:.4f}**",
        f"- Spearman(score, realized net 60m return): **{rho:.4f}**",
        f"- 2025+ reference_validation remained CLOSED.", "",
        "## OOS ranking economics", "",
        "| Scope | N | Impulse rate | WR | Exp % | Net PnL | PF | Max DD | Max LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| ALL | {allm['n']} | {allm['impulse_rate']*100:.2f}% | {allm['wr']*100:.2f}% | {allm['expectancy_pct']:.4f}% | ${allm['net_pnl_usd']:.2f} | {pfmt(allm['pf'])} | ${allm['max_dd_usd']:.2f} | {allm['max_ls']} |",
        f"| TOP score decile | {topm['n']} | {topm['impulse_rate']*100:.2f}% | {topm['wr']*100:.2f}% | {topm['expectancy_pct']:.4f}% | ${topm['net_pnl_usd']:.2f} | {pfmt(topm['pf'])} | ${topm['max_dd_usd']:.2f} | {topm['max_ls']} |",
        f"| BOTTOM score decile | {botm['n']} | {botm['impulse_rate']*100:.2f}% | {botm['wr']*100:.2f}% | {botm['expectancy_pct']:.4f}% | ${botm['net_pnl_usd']:.2f} | {pfmt(botm['pf'])} | ${botm['max_dd_usd']:.2f} | {botm['max_ls']} |",
        "", f"- Top-decile impulse-rate lift vs baseline: **{lift:.3f}x**", "",
        "## Top decile by OOS year", "", "| Year | N | Impulse rate | WR | Exp % | Net PnL | PF |", "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in yr[yr.scope == "TOP_DECILE"].iterrows():
        lines.append(f"| {int(r.test_year)} | {int(r.n)} | {float(r.impulse_rate)*100:.2f}% | {float(r.wr)*100:.2f}% | {float(r.expectancy_pct):.4f}% | ${float(r.net_pnl_usd):.2f} | {pfmt(r.pf)} |")
    lines += ["", "## Strongest transition contrasts in matched training", ""]
    for _, r in contrast.head(10).iterrows():
        direction = "higher" if float(r.std_effect) > 0 else "lower"
        lines.append(f"- `{r.feature}` — {direction} before impulses; standardized effect {float(r.std_effect):+.3f}")
    lines += ["", "## Top model features", ""]
    for _, r in fi.head(12).iterrows():
        lines.append(f"- `{r.feature}` — importance {float(r.importance):.4f}")
    lines += ["", "## Gate audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", f"# VERDICT: {'PASS' if passed else 'FAIL'}", "", "PASS means a repeatable precursor ranking survived the frozen 2021-2024 walk-forward diagnostics. It still does not authorize live trading or opening 2025+ reference_validation. FAIL means v4 must not be retuned against this same OOS sample."]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(("PASS" if passed else "FAIL") + "\n", encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
