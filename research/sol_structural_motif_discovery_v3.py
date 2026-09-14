#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import RobustScaler

import sol_adaptive_structure_detector_v1 as v1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_STRUCTURAL_MOTIF_DISCOVERY_V3"

MODEL_START = pd.Timestamp("2020-01-01", tz="UTC")
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
BAR = pd.Timedelta(minutes=5)
SEQ_BARS = 24
DECISION_MINUTES = (0, 30)
HOLD_MINUTES = 60
N_CLUSTERS = 32
TRAIN_WINDOW_YEARS = 2
PRIOR_STRENGTH = 100.0
MIN_MOTIF_N = 100
ROUNDTRIP_COST_PCT = 0.15
NOTIONAL = 500.0
TEST_YEARS = (2021, 2022, 2023, 2024)

CHANNELS = ("path", "body", "range", "close_loc", "volume")
VECTOR_COLS = [f"{ch}_{i:02d}" for ch in CHANNELS for i in range(SEQ_BARS)]


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


def sequence_vector(q: pd.DataFrame) -> dict | None:
    if len(q) != SEQ_BARS:
        return None
    op = q.open.astype(float).to_numpy()
    hi = q.high.astype(float).to_numpy()
    lo = q.low.astype(float).to_numpy()
    cl = q.close.astype(float).to_numpy()
    vol = q.volume.astype(float).to_numpy()
    if not all(np.isfinite(x).all() for x in (op, hi, lo, cl, vol)):
        return None
    if np.any(op <= 0) or np.any(cl <= 0) or np.any(vol < 0):
        return None

    lr = np.diff(np.log(cl))
    sigma = float(np.std(lr, ddof=1)) if len(lr) > 1 else np.nan
    if not np.isfinite(sigma) or sigma < 1e-6:
        return None

    path = np.log(cl / cl[0]) / sigma
    body = np.log(cl / op) / sigma
    rng = np.log(np.maximum(hi, 1e-12) / np.maximum(lo, 1e-12)) / sigma
    span = hi - lo
    close_loc = np.divide(cl - lo, span, out=np.full_like(cl, 0.5), where=span > 0) - 0.5
    med_vol = float(np.median(vol))
    if not np.isfinite(med_vol) or med_vol <= 0:
        return None
    volume = np.log1p(vol / med_vol)
    volume = volume - np.median(volume)

    chans = {
        "path": np.clip(path, -12.0, 12.0),
        "body": np.clip(body, -8.0, 8.0),
        "range": np.clip(rng, 0.0, 12.0),
        "close_loc": np.clip(close_loc, -0.5, 0.5),
        "volume": np.clip(volume, -4.0, 4.0),
    }
    out = {}
    for name, arr in chans.items():
        for i, val in enumerate(arr):
            out[f"{name}_{i:02d}"] = float(val)
    return out


def build_opportunities(x5: pd.DataFrame) -> pd.DataFrame:
    idx = x5.index
    rows = []
    for i in range(SEQ_BARS - 1, len(x5) - 13):
        ts = idx[i]
        if ts < MODEL_START or ts >= MODEL_END:
            continue
        if ts.minute not in DECISION_MINUTES:
            continue

        q = x5.iloc[i - SEQ_BARS + 1:i + 1]
        if len(q) != SEQ_BARS:
            continue
        if q.index[-1] - q.index[0] != BAR * (SEQ_BARS - 1):
            continue
        vec = sequence_vector(q)
        if vec is None:
            continue

        entry_i = i + 1
        exit_i = entry_i + HOLD_MINUTES // 5 - 1
        if exit_i >= len(x5):
            continue
        entry_ts = idx[entry_i]
        exit_bar_ts = idx[exit_i]
        if entry_ts >= MODEL_END or exit_bar_ts >= MODEL_END:
            continue
        if entry_ts != ts + BAR:
            continue
        if exit_bar_ts != entry_ts + pd.Timedelta(minutes=HOLD_MINUTES) - BAR:
            continue

        entry_price = float(x5.iloc[entry_i].open)
        exit_price = float(x5.iloc[exit_i].close)
        if not (np.isfinite(entry_price) and np.isfinite(exit_price) and entry_price > 0):
            continue
        net = (exit_price / entry_price - 1.0) * 100.0 - ROUNDTRIP_COST_PCT

        rows.append({
            "signal_time": ts,
            "entry_time": entry_ts,
            "exit_known_time": exit_bar_ts + BAR,
            "year": int(ts.year),
            "hour_utc": int(ts.hour),
            "minute_utc": int(ts.minute),
            "hour_wib": int((ts.hour + 7) % 24),
            "entry_price": entry_price,
            "exit_60m_price": exit_price,
            "net_60m_pct": float(net),
            "pnl_60m_usd": float(net / 100.0 * NOTIONAL),
            "win_60m": int(net > 0),
            **vec,
        })
    ev = pd.DataFrame(rows)
    if ev.empty:
        raise RuntimeError("no raw motif opportunities")
    return ev.sort_values("entry_time").reset_index(drop=True)


def training_bounds(test_year: int):
    end = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
    start_year = max(MODEL_START.year, test_year - TRAIN_WINDOW_YEARS)
    start = pd.Timestamp(f"{start_year}-01-01", tz="UTC")
    return start, end


def fit_predict_year(ev: pd.DataFrame, test_year: int):
    train_start, train_end = training_bounds(test_year)
    test_start = train_end
    test_end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")

    tr = ev[(ev.entry_time >= train_start) & (ev.exit_known_time <= train_end)].copy()
    te = ev[(ev.entry_time >= test_start) & (ev.entry_time < test_end)].copy()
    if len(tr) < N_CLUSTERS * MIN_MOTIF_N:
        raise RuntimeError(f"insufficient training opportunities for {test_year}: {len(tr)}")
    if te.empty:
        raise RuntimeError(f"no test opportunities for {test_year}")

    Xtr = tr[VECTOR_COLS].astype(float).to_numpy()
    Xte = te[VECTOR_COLS].astype(float).to_numpy()

    scaler = RobustScaler(quantile_range=(25.0, 75.0))
    Xtrz = np.clip(scaler.fit_transform(Xtr), -8.0, 8.0)
    Xtez = np.clip(scaler.transform(Xte), -8.0, 8.0)

    km = MiniBatchKMeans(
        n_clusters=N_CLUSTERS,
        random_state=42,
        batch_size=4096,
        n_init=10,
        reassignment_ratio=0.01,
    )
    tr_label = km.fit_predict(Xtrz)
    te_label = km.predict(Xtez)
    tr_dist = np.linalg.norm(Xtrz - km.cluster_centers_[tr_label], axis=1)
    te_dist = np.linalg.norm(Xtez - km.cluster_centers_[te_label], axis=1)

    tr = tr.copy()
    te = te.copy()
    tr["motif_id"] = tr_label
    tr["motif_distance"] = tr_dist
    te["motif_id"] = te_label
    te["motif_distance"] = te_dist

    global_edge = float(tr.net_60m_pct.mean())
    global_pwin = float(tr.win_60m.mean())

    motif_stats = []
    stat_map = {}
    for motif, g in tr.groupby("motif_id"):
        n = len(g)
        wins = float(g.win_60m.sum())
        mean_edge = float(g.net_60m_pct.mean())
        raw_pwin = float(g.win_60m.mean())
        shr_edge = (n * mean_edge + PRIOR_STRENGTH * global_edge) / (n + PRIOR_STRENGTH)
        shr_pwin = (wins + PRIOR_STRENGTH * global_pwin) / (n + PRIOR_STRENGTH)
        radius = float(np.median(g.motif_distance))
        radius = radius if np.isfinite(radius) and radius > 1e-9 else 1.0
        row = {
            "test_year": test_year,
            "train_start": train_start,
            "train_end": train_end,
            "motif_id": int(motif),
            "train_n": int(n),
            "train_wr": raw_pwin,
            "train_edge_pct": mean_edge,
            "train_pf": float(profit_factor(g.pnl_60m_usd)),
            "shrunk_pwin": float(shr_pwin),
            "shrunk_edge_pct": float(shr_edge),
            "motif_radius": radius,
            "global_train_wr": global_pwin,
            "global_train_edge_pct": global_edge,
        }
        motif_stats.append(row)
        stat_map[int(motif)] = row

    preds = []
    for _, r in te.iterrows():
        s = stat_map[int(r.motif_id)]
        similarity = float(np.exp(-float(r.motif_distance) / max(s["motif_radius"], 1e-6)))
        pred_edge = similarity * s["shrunk_edge_pct"] + (1.0 - similarity) * global_edge
        pred_pwin = similarity * s["shrunk_pwin"] + (1.0 - similarity) * global_pwin
        trade = bool(
            s["train_n"] >= MIN_MOTIF_N
            and pred_edge > 0.0
            and pred_pwin > global_pwin
        )
        preds.append({
            "test_year": test_year,
            "signal_time": r.signal_time,
            "entry_time": r.entry_time,
            "hour_utc": int(r.hour_utc),
            "minute_utc": int(r.minute_utc),
            "hour_wib": int(r.hour_wib),
            "motif_id": int(r.motif_id),
            "motif_distance": float(r.motif_distance),
            "motif_similarity": similarity,
            "motif_train_n": int(s["train_n"]),
            "motif_train_wr": float(s["train_wr"]),
            "motif_train_edge_pct": float(s["train_edge_pct"]),
            "pred_pwin": float(pred_pwin),
            "pred_edge_pct": float(pred_edge),
            "global_train_wr": global_pwin,
            "global_train_edge_pct": global_edge,
            "trade_gate": trade,
            "actual_win": int(r.win_60m),
            "actual_net_60m_pct": float(r.net_60m_pct),
            "actual_pnl_60m_usd": float(r.pnl_60m_usd),
        })

    centers_raw = scaler.inverse_transform(km.cluster_centers_)
    geom = []
    for motif in range(N_CLUSTERS):
        row = {"test_year": test_year, "motif_id": motif}
        for k, col in enumerate(VECTOR_COLS):
            row[col] = float(centers_raw[motif, k])
        geom.append(row)

    return pd.DataFrame(preds), pd.DataFrame(motif_stats), pd.DataFrame(geom)


def walk_forward(ev: pd.DataFrame):
    pp, ss, gg = [], [], []
    for y in TEST_YEARS:
        p, s, g = fit_predict_year(ev, y)
        pp.append(p)
        ss.append(s)
        gg.append(g)
    return (
        pd.concat(pp, ignore_index=True).sort_values("entry_time").reset_index(drop=True),
        pd.concat(ss, ignore_index=True),
        pd.concat(gg, ignore_index=True),
    )


def yearly_summary(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y, g in pred.groupby("test_year"):
        for scope, q in (("ALL", g), ("TRADE", g[g.trade_gate])):
            rows.append({"test_year": int(y), "scope": scope, **econ(q)})
    return pd.DataFrame(rows).sort_values(["test_year", "scope"])


def quartile_summary(pred: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for y, g in pred.groupby("test_year"):
        q = g.copy()
        q["edge_quartile"] = pd.qcut(
            q.pred_edge_pct.rank(method="first"),
            4,
            labels=[1, 2, 3, 4],
        ).astype(int)
        parts.append(q)
    z = pd.concat(parts, ignore_index=True)
    rows = []
    for qt, g in z.groupby("edge_quartile"):
        rows.append({
            "edge_quartile": int(qt),
            "mean_pred_edge_pct": float(g.pred_edge_pct.mean()),
            "mean_pred_pwin": float(g.pred_pwin.mean()),
            **econ(g),
        })
    return pd.DataFrame(rows).sort_values("edge_quartile")


def test_motif_summary(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (y, motif), g in pred.groupby(["test_year", "motif_id"]):
        m = econ(g)
        rows.append({
            "test_year": int(y),
            "motif_id": int(motif),
            "n": m["n"],
            "wr": m["wr"],
            "expectancy_pct": m["expectancy_pct"],
            "profit_factor": m["profit_factor"],
            "net_pnl_usd": m["net_pnl_usd"],
            "mean_pred_edge_pct": float(g.pred_edge_pct.mean()),
            "mean_pred_pwin": float(g.pred_pwin.mean()),
            "mean_similarity": float(g.motif_similarity.mean()),
            "trade_share": float(g.trade_gate.mean()),
        })
    return pd.DataFrame(rows)


def hour_audit(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    t = pred[pred.trade_gate]
    for (hour, minute), g in t.groupby(["hour_utc", "minute_utc"]):
        m = econ(g)
        rows.append({
            "hour_utc": int(hour),
            "minute_utc": int(minute),
            "hour_wib": int((hour + 7) % 24),
            **m,
        })
    return pd.DataFrame(rows).sort_values(["hour_utc", "minute_utc"]) if rows else pd.DataFrame()


def fmt_pf(v):
    if pd.isna(v):
        return "n/a"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.3f}"


def main():
    v1.base.fetch_one = v1.fetch_one_with_volume
    x5, coverage = v1.base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")
    if "volume" not in x5.columns:
        raise RuntimeError("volume column required")

    ev = build_opportunities(x5)
    pred, stats, geom = walk_forward(ev)
    yr = yearly_summary(pred)
    quart = quartile_summary(pred)
    mts = test_motif_summary(pred)
    ha = hour_audit(pred)

    all_m = econ(pred)
    trade = pred[pred.trade_gate].copy()
    trade_m = econ(trade)

    rho = float(spearmanr(pred.pred_edge_pct, pred.actual_net_60m_pct, nan_policy="omit").statistic)
    q1 = quart[quart.edge_quartile == 1].iloc[0]
    q4 = quart[quart.edge_quartile == 4].iloc[0]

    pos_years = 0
    for y in TEST_YEARS:
        q = trade[trade.test_year == y]
        if len(q) and float(q.actual_pnl_60m_usd.sum()) > 0:
            pos_years += 1

    gates = {
        "spearman_edge_positive": bool(np.isfinite(rho) and rho > 0),
        "q4_beats_q1_expectancy": bool(float(q4.expectancy_pct) > float(q1.expectancy_pct)),
        "q4_positive_expectancy": bool(float(q4.expectancy_pct) > 0),
        "q4_pf_gt_1": bool(float(q4.profit_factor) > 1),
        "trade_n_ge_100": bool(trade_m["n"] >= 100),
        "trade_expectancy_positive": bool(np.isfinite(trade_m["expectancy_pct"]) and trade_m["expectancy_pct"] > 0),
        "trade_pf_gt_1": bool(np.isfinite(trade_m["profit_factor"]) and trade_m["profit_factor"] > 1),
        "trade_positive_years_ge_3": bool(pos_years >= 3),
    }
    passed = bool(all(gates.values()))

    ev.to_csv(ROOT / f"{PFX}_Opportunities.csv", index=False)
    pred.to_csv(ROOT / f"{PFX}_Predictions.csv", index=False)
    stats.to_csv(ROOT / f"{PFX}_TrainMotifStats.csv", index=False)
    geom.to_csv(ROOT / f"{PFX}_MotifGeometry.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    quart.to_csv(ROOT / f"{PFX}_EdgeQuartiles.csv", index=False)
    mts.to_csv(ROOT / f"{PFX}_TestMotifSummary.csv", index=False)
    ha.to_csv(ROOT / f"{PFX}_HourAudit.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(
        ROOT / f"{PFX}_GateAudit.csv", index=False
    )

    lines = [
        "# SOL Structural Motif Discovery v3 — Raw 5m Walk-Forward",
        "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- Raw opportunities 2020-2024: **{len(ev)}**",
        f"- Walk-forward predictions 2021-2024: **{len(pred)}**",
        "- No ORB/VWAP/BOS/EMA/Fibonacci structure labels are inputs.",
        f"- Input motif = prior **{SEQ_BARS*5} minutes** of raw 5m candle path, sampled at :00 and :30.",
        f"- Unsupervised motifs per training fold: **{N_CLUSTERS}** MiniBatchKMeans clusters.",
        f"- Training window: rolling **{TRAIN_WINDOW_YEARS} years**; 2025+ remained CLOSED.",
        f"- Trade eligibility is causal: motif train N >= {MIN_MOTIF_N}, predicted edge > 0, and predicted P(win) > contemporaneous training baseline.",
        "",
        "## Overall walk-forward",
        "",
        "| Scope | N | WR | Net PnL | Exp % | PF | Max DD | Max LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| ALL | {all_m['n']} | {all_m['wr']*100:.2f}% | ${all_m['net_pnl_usd']:.2f} | {all_m['expectancy_pct']:.4f}% | {fmt_pf(all_m['profit_factor'])} | ${all_m['max_dd_usd']:.2f} | {all_m['max_loss_streak']} |",
        f"| MOTIF TRADE | {trade_m['n']} | {(trade_m['wr']*100 if np.isfinite(trade_m['wr']) else np.nan):.2f}% | ${trade_m['net_pnl_usd']:.2f} | {(trade_m['expectancy_pct'] if np.isfinite(trade_m['expectancy_pct']) else np.nan):.4f}% | {fmt_pf(trade_m['profit_factor'])} | ${(trade_m['max_dd_usd'] if np.isfinite(trade_m['max_dd_usd']) else np.nan):.2f} | {trade_m['max_loss_streak']} |",
        "",
        "## Ranking diagnostic",
        "",
        f"- Spearman(predicted motif edge, realized +60m net return): **{rho:.4f}**",
        "",
        "| Edge quartile | N | Mean predicted edge | Realized WR | Realized Exp % | PF |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in quart.iterrows():
        lines.append(
            f"| Q{int(r.edge_quartile)} | {int(r.n)} | {float(r.mean_pred_edge_pct):.4f}% | "
            f"{float(r.wr)*100:.2f}% | {float(r.expectancy_pct):.4f}% | {fmt_pf(r.profit_factor)} |"
        )

    lines += [
        "",
        "## MOTIF TRADE by test year",
        "",
        "| Year | N | WR | Net PnL | Exp % | PF |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for y in TEST_YEARS:
        r = yr[(yr.test_year == y) & (yr.scope == "TRADE")].iloc[0]
        wr = float(r.wr) * 100 if pd.notna(r.wr) else np.nan
        exp = float(r.expectancy_pct) if pd.notna(r.expectancy_pct) else np.nan
        lines.append(
            f"| {y} | {int(r.n)} | {wr:.2f}% | ${float(r.net_pnl_usd):.2f} | "
            f"{exp:.4f}% | {fmt_pf(r.profit_factor)} |"
        )

    lines += ["", "## Gate audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "",
        f"# VERDICT: {'MOTIF_SIGNAL_FOUND' if passed else 'NO_ROBUST_MOTIF_SIGNAL'}",
        "",
        "A pass means raw price-path motifs show causal out-of-time ranking and economics worth characterizing further. It does not authorize opening 2025+ or optimizing exits.",
        "A fail means this frozen raw-path motif representation should be rejected as a unit; K, lookback length, decision spacing, and gates must not be retuned on the same walk-forward sample.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(
        ("MOTIF_SIGNAL_FOUND" if passed else "NO_ROBUST_MOTIF_SIGNAL") + "\n",
        encoding="utf-8",
    )
    print(text)


if __name__ == "__main__":
    main()
