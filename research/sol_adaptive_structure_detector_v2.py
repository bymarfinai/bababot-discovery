#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import brier_score_loss, roc_auc_score

import sol_adaptive_structure_detector_v1 as v1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ADAPTIVE_STRUCTURE_DETECTOR_V2"

MODEL_START = pd.Timestamp("2020-01-01", tz="UTC")
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
BAR = pd.Timedelta(minutes=5)

ANALOG_WINDOW_DAYS = 730
MIN_ANALOG_POOL = 120
K_NEIGHBORS = 60
MIN_EFFECTIVE_N = 20.0
SEQ_POINTS = 18

PWIN_GATE = 0.60
EDGE_GATE_PCT = 0.15

ROUNDTRIP_COST_PCT = v1.ROUNDTRIP_COST_PCT
NOTIONAL = v1.NOTIONAL

BASE_CONTEXT = [
    "hour_sin",
    "hour_cos",
    "pre24_rv_pct",
    "pre7d_rv_pct",
    "pre24_trend_pct",
    "pre24_avg_bar_range_pct",
    "orb_volume_ratio",
    "orb_range_norm",
    "breakout_delay_min",
    "retest_delay_min",
    "bos_delay_min",
    "breakout_disp_orb_pct",
    "retest_depth_orb_frac",
    "retest_vwap_gap_pct",
    "bos_micro_break_pct",
    "bos_vs_orb_pct",
    "bos_vwap_gap_pct",
]

PHASE_COLS = [
    "breakout_phase",
    "retest_phase",
    "bars_to_bos",
]

PATH_COLS = (
    [f"path_close_{i:02d}" for i in range(SEQ_POINTS)]
    + [f"path_high_{i:02d}" for i in range(SEQ_POINTS)]
    + [f"path_low_{i:02d}" for i in range(SEQ_POINTS)]
    + [f"path_vwap_gap_{i:02d}" for i in range(SEQ_POINTS)]
)

VECTOR_COLS = PATH_COLS + PHASE_COLS + BASE_CONTEXT


def robust_scale(train: np.ndarray, current: np.ndarray):
    med = np.nanmedian(train, axis=0)
    q25 = np.nanpercentile(train, 25, axis=0)
    q75 = np.nanpercentile(train, 75, axis=0)
    scale = q75 - q25
    alt = np.nanstd(train, axis=0)
    scale = np.where(np.isfinite(scale) & (scale > 1e-9), scale, alt)
    scale = np.where(np.isfinite(scale) & (scale > 1e-9), scale, 1.0)
    zt = np.clip((train - med) / scale, -8.0, 8.0)
    zc = np.clip((current - med) / scale, -8.0, 8.0)
    return zt, zc


def path_features(x5: pd.DataFrame, r: pd.Series) -> dict | None:
    start = pd.Timestamp(r.session_start)
    bos_time = pd.Timestamp(r.bos_time)
    q = x5[(x5.index >= start) & (x5.index <= bos_time)].copy()
    if len(q) < 4:
        return None

    oh = float(r.orb_high)
    ol = float(r.orb_low)
    rng = oh - ol
    if not np.isfinite(rng) or rng <= 0:
        return None
    mid = (oh + ol) / 2.0

    vol = q.volume.astype(float).to_numpy()
    tp = ((q.high.astype(float) + q.low.astype(float) + q.close.astype(float)) / 3.0).to_numpy()
    den = np.cumsum(vol)
    num = np.cumsum(tp * vol)
    vw = np.divide(num, den, out=np.full_like(num, np.nan, dtype=float), where=den > 0)

    channels = {
        "close": (q.close.astype(float).to_numpy() - mid) / rng,
        "high": (q.high.astype(float).to_numpy() - mid) / rng,
        "low": (q.low.astype(float).to_numpy() - mid) / rng,
        "vwap_gap": (q.close.astype(float).to_numpy() - vw) / rng,
    }
    if not all(np.isfinite(v).all() for v in channels.values()):
        return None

    src = np.linspace(0.0, 1.0, len(q))
    dst = np.linspace(0.0, 1.0, SEQ_POINTS)
    out = {}
    for name, arr in channels.items():
        vals = np.interp(dst, src, arr)
        for i, val in enumerate(vals):
            out[f"path_{name}_{i:02d}"] = float(val)

    total = float((bos_time - start) / pd.Timedelta(minutes=1))
    if total <= 0:
        return None
    out["breakout_phase"] = float((pd.Timestamp(r.breakout_time) - start) / pd.Timedelta(minutes=1)) / total
    out["retest_phase"] = float((pd.Timestamp(r.retest_time) - start) / pd.Timedelta(minutes=1)) / total
    out["bars_to_bos"] = float(len(q))
    return out


def build_sequence_events(x5: pd.DataFrame) -> pd.DataFrame:
    base_ev = v1.collect_events(x5)
    rows = []
    for _, r in base_ev.iterrows():
        p = path_features(x5, r)
        if p is None:
            continue
        z = r.to_dict()
        z.update(p)
        z["outcome_known_time"] = pd.Timestamp(r.entry_time) + pd.Timedelta(minutes=60)
        rows.append(z)
    ev = pd.DataFrame(rows).sort_values("entry_time").reset_index(drop=True)
    if ev.empty:
        raise RuntimeError("no sequence events")
    bad = ~np.isfinite(ev[VECTOR_COLS].astype(float).to_numpy()).all(axis=1)
    if bad.any():
        ev = ev.loc[~bad].reset_index(drop=True)
    return ev


def effective_n(weights: np.ndarray) -> float:
    s = float(weights.sum())
    ss = float(np.square(weights).sum())
    return s * s / ss if ss > 0 else 0.0


def predict_online(ev: pd.DataFrame) -> pd.DataFrame:
    vec = ev[VECTOR_COLS].astype(float).to_numpy()
    entry = pd.to_datetime(ev.entry_time, utc=True)
    known = pd.to_datetime(ev.outcome_known_time, utc=True)
    outcome = ev.net_60m_pct.astype(float).to_numpy()
    win = ev.win_60m.astype(float).to_numpy()

    rows = []
    for i in range(len(ev)):
        now = entry.iloc[i]
        floor = now - pd.Timedelta(days=ANALOG_WINDOW_DAYS)
        mask = (entry < now) & (known <= now) & (entry >= floor)
        idx = np.flatnonzero(mask.to_numpy())
        if len(idx) < MIN_ANALOG_POOL:
            continue

        X = vec[idx]
        cur = vec[i]
        Xz, cz = robust_scale(X, cur)
        d = np.sqrt(np.mean(np.square(Xz - cz), axis=1))
        order = np.argsort(d)[: min(K_NEIGHBORS, len(d))]
        nn = idx[order]
        nd = d[order]

        bandwidth = float(np.median(nd))
        if not np.isfinite(bandwidth) or bandwidth <= 1e-9:
            bandwidth = float(np.mean(nd[nd > 0])) if np.any(nd > 0) else 1.0
        bandwidth = max(bandwidth, 1e-6)
        w = np.exp(-nd / bandwidth)
        if not np.isfinite(w).all() or float(w.sum()) <= 0:
            w = np.ones_like(nd)

        pwin = float(np.average(win[nn], weights=w))
        pred_edge = float(np.average(outcome[nn], weights=w))
        pool_edge = float(np.mean(outcome[idx]))
        eff = effective_n(w)
        trade = bool(pwin >= PWIN_GATE and pred_edge >= EDGE_GATE_PCT and eff >= MIN_EFFECTIVE_N)

        rows.append({
            "event_index": int(i),
            "session_start": ev.iloc[i].session_start,
            "entry_time": now,
            "year": int(ev.iloc[i].year),
            "hour_utc": int(ev.iloc[i].hour_utc),
            "hour_wib": int(ev.iloc[i].hour_wib),
            "analogs_available": int(len(idx)),
            "k_used": int(len(nn)),
            "effective_n": eff,
            "nearest_distance": float(nd[0]),
            "median_neighbor_distance": float(np.median(nd)),
            "pred_pwin": pwin,
            "pred_edge_pct": pred_edge,
            "recent_pool_edge_pct": pool_edge,
            "pred_edge_lift_pct": pred_edge - pool_edge,
            "trade_gate": trade,
            "actual_win": int(ev.iloc[i].win_60m),
            "actual_net_60m_pct": float(ev.iloc[i].net_60m_pct),
            "actual_pnl_60m_usd": float(ev.iloc[i].pnl_60m_usd),
        })
    return pd.DataFrame(rows)


def profit_factor(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def max_loss_streak(pnls) -> int:
    best = cur = 0
    for x in pd.Series(pnls, dtype=float).dropna():
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def max_drawdown(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    if a.empty:
        return np.nan
    eq = a.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def econ(g: pd.DataFrame) -> dict:
    if g.empty:
        return {
            "n": 0, "wr": np.nan, "expectancy_pct": np.nan,
            "net_pnl_usd": 0.0, "profit_factor": np.nan,
            "max_dd_usd": np.nan, "max_loss_streak": 0,
        }
    r = g.actual_net_60m_pct.astype(float)
    p = g.actual_pnl_60m_usd.astype(float)
    return {
        "n": int(len(g)),
        "wr": float((r > 0).mean()),
        "expectancy_pct": float(r.mean()),
        "net_pnl_usd": float(p.sum()),
        "profit_factor": float(profit_factor(p)),
        "max_dd_usd": float(max_drawdown(p)),
        "max_loss_streak": int(max_loss_streak(p)),
    }


def summarize_years(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, g in pred.groupby("year"):
        a = econ(g)
        a.update({"year": int(year), "selection": "ALL_ELIGIBLE"})
        rows.append(a)
        t = econ(g[g.trade_gate])
        t.update({"year": int(year), "selection": "TRADE_GATE"})
        rows.append(t)
    return pd.DataFrame(rows)


def edge_quartiles(pred: pd.DataFrame) -> pd.DataFrame:
    q = pred.copy()
    try:
        q["quartile"] = pd.qcut(q.pred_edge_pct, 4, labels=[1, 2, 3, 4], duplicates="drop")
    except ValueError:
        return pd.DataFrame()
    rows = []
    for quartile, g in q.groupby("quartile", observed=True):
        z = econ(g)
        z["quartile"] = int(quartile)
        z["pred_edge_mean_pct"] = float(g.pred_edge_pct.mean())
        z["pred_pwin_mean"] = float(g.pred_pwin.mean())
        rows.append(z)
    return pd.DataFrame(rows).sort_values("quartile")


def diagnostics(pred: pd.DataFrame):
    if pred.empty:
        return np.nan, np.nan, np.nan, np.nan
    y = pred.actual_win.astype(int)
    auc = roc_auc_score(y, pred.pred_pwin) if y.nunique() == 2 else np.nan
    brier = brier_score_loss(y, pred.pred_pwin)
    spr = float(spearmanr(pred.pred_edge_pct, pred.actual_net_60m_pct, nan_policy="omit").statistic)
    pear = float(pred.pred_edge_pct.corr(pred.actual_net_60m_pct))
    return float(auc), float(brier), spr, pear


def main():
    v1.base.fetch_one = v1.fetch_one_with_volume
    x5, coverage = v1.base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    ev = build_sequence_events(x5)
    pred = predict_online(ev)
    if pred.empty:
        raise RuntimeError("no online predictions after analog minimum")

    ys = summarize_years(pred)
    eq = edge_quartiles(pred)
    auc, brier, spr, pear = diagnostics(pred)

    allm = econ(pred)
    tradem = econ(pred[pred.trade_gate])
    positive_trade_years = int(
        ((ys.selection == "TRADE_GATE") & (ys.n >= 5) & (ys.expectancy_pct > 0)).sum()
    )

    q1 = eq[eq.quartile == 1].iloc[0] if 1 in set(eq.quartile) else None
    q4 = eq[eq.quartile == 4].iloc[0] if 4 in set(eq.quartile) else None
    rank_ok = bool(
        np.isfinite(spr) and spr > 0
        and q1 is not None and q4 is not None
        and float(q4.expectancy_pct) > float(q1.expectancy_pct)
    )
    econ_ok = bool(
        tradem["n"] >= 30
        and np.isfinite(tradem["wr"]) and tradem["wr"] >= 0.60
        and np.isfinite(tradem["expectancy_pct"]) and tradem["expectancy_pct"] > 0
        and np.isfinite(tradem["profit_factor"]) and tradem["profit_factor"] > 1
    )
    stability_ok = bool(positive_trade_years >= 2)
    verdict = "PROMISING_SEQUENCE_ANALOG" if (rank_ok and econ_ok and stability_ok) else "REJECT_V2_SEQUENCE_ANALOG"

    ev.to_csv(ROOT / f"{PFX}_Events.csv", index=False)
    pred.to_csv(ROOT / f"{PFX}_Predictions.csv", index=False)
    ys.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    eq.to_csv(ROOT / f"{PFX}_EdgeQuartiles.csv", index=False)

    audit = pd.DataFrame([{
        "coverage": coverage,
        "events": len(ev),
        "predictions": len(pred),
        "analog_window_days": ANALOG_WINDOW_DAYS,
        "min_analog_pool": MIN_ANALOG_POOL,
        "k_neighbors": K_NEIGHBORS,
        "min_effective_n": MIN_EFFECTIVE_N,
        "sequence_points": SEQ_POINTS,
        "pwin_gate": PWIN_GATE,
        "edge_gate_pct": EDGE_GATE_PCT,
        "auc": auc,
        "brier": brier,
        "spearman_edge_actual": spr,
        "pearson_edge_actual": pear,
        "positive_trade_years": positive_trade_years,
        "rank_ok": rank_ok,
        "econ_ok": econ_ok,
        "stability_ok": stability_ok,
        "verdict": verdict,
    }])
    audit.to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    lines = [
        "# SOL Adaptive Structure Detector v2 — Sequence/Path Analog Walk-Forward",
        "",
        f"- Data coverage: **{coverage*100:.4f}%**",
        f"- Structural events: **{len(ev)}**",
        f"- Online predictions: **{len(pred)}**",
        "- No event may use an analog whose 60m outcome was not already known at prediction time.",
        f"- Analog memory: trailing **{ANALOG_WINDOW_DAYS} days**, K={K_NEIGHBORS}, minimum pool={MIN_ANALOG_POOL}.",
        f"- Sequence: {SEQ_POINTS} time-normalized points from ORB anchor through BOS, using OHLC position vs ORB plus anchored-VWAP gap.",
        f"- Frozen trade gate: P(win) >= {PWIN_GATE:.0%}, predicted net 60m edge >= {EDGE_GATE_PCT:.2f}%, effective analog N >= {MIN_EFFECTIVE_N:.0f}.",
        "- 2025+ remains closed.",
        "",
        "## Ranking diagnostics",
        "",
        f"- ROC AUC P(win): **{auc:.4f}**",
        f"- Brier score: **{brier:.4f}**",
        f"- Spearman(predicted edge, actual return): **{spr:.4f}**",
        f"- Pearson(predicted edge, actual return): **{pear:.4f}**",
        "",
        "## Economics",
        "",
        "| Selection | N | WR | Expectancy | Net PnL | PF | Max DD | Max LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| All eligible | {allm['n']} | {allm['wr']*100:.2f}% | {allm['expectancy_pct']:.4f}% | ${allm['net_pnl_usd']:.2f} | {allm['profit_factor']:.3f} | ${allm['max_dd_usd']:.2f} | {allm['max_loss_streak']} |",
        f"| Predicted TRADE | {tradem['n']} | {tradem['wr']*100 if np.isfinite(tradem['wr']) else np.nan:.2f}% | {tradem['expectancy_pct'] if np.isfinite(tradem['expectancy_pct']) else np.nan:.4f}% | ${tradem['net_pnl_usd']:.2f} | {tradem['profit_factor'] if np.isfinite(tradem['profit_factor']) else np.nan:.3f} | ${tradem['max_dd_usd'] if np.isfinite(tradem['max_dd_usd']) else np.nan:.2f} | {tradem['max_loss_streak']} |",
        "",
        "## Edge quartiles",
        "",
        "| Q | N | Mean predicted edge | WR | Actual expectancy | PF |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in eq.iterrows():
        lines.append(
            f"| {int(r.quartile)} | {int(r.n)} | {r.pred_edge_mean_pct:.4f}% | "
            f"{r.wr*100:.2f}% | {r.expectancy_pct:.4f}% | {r.profit_factor:.3f} |"
        )
    lines += [
        "",
        "## Verdict",
        "",
        f"**{verdict}**",
        "",
        f"- Ranking gate: {'PASS' if rank_ok else 'FAIL'}",
        f"- Trade economics gate: {'PASS' if econ_ok else 'FAIL'}",
        f"- Multi-year stability gate: {'PASS' if stability_ok else 'FAIL'} ({positive_trade_years} positive trade years with N>=5)",
        "",
        "No threshold or K/window value may be changed after reading this result. Any redesign must be a new preregistered detector version.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
