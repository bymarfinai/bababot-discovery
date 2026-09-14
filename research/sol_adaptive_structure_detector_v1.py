#!/usr/bin/env python3
from __future__ import annotations

import io
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import brier_score_loss, roc_auc_score

import eth_london_ny_liquidity_pressure_m1 as base

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ADAPTIVE_STRUCTURE_DETECTOR_V1"
BAR = pd.Timedelta(minutes=5)
MODEL_START = pd.Timestamp("2020-01-01", tz="UTC")
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
ROUNDTRIP_COST_PCT = 0.15
NOTIONAL = 500.0
TEST_YEARS = (2021, 2022, 2023, 2024)

PWIN_GATE = 0.60
EDGE_GATE_PCT = 0.15

FEATURES = [
    "hour_sin",
    "hour_cos",
    "pre24_rv_pct",
    "pre7d_rv_pct",
    "pre24_trend_pct",
    "pre24_avg_bar_range_pct",
    "orb_volume_ratio",
    "orb_range_pct",
    "orb_range_norm",
    "breakout_delay_min",
    "breakout_disp_orb_pct",
    "breakout_vwap_gap_pct",
    "breakout_body_frac",
    "breakout_upper_wick_frac",
    "retest_delay_min",
    "retest_depth_orb_frac",
    "retest_close_vs_orb_pct",
    "retest_vwap_gap_pct",
    "retest_bullish_body",
    "retest_wick_rejection",
    "retest_bullish_reaction",
    "retest_body_frac",
    "retest_lower_wick_frac",
    "bos_delay_min",
    "bos_micro_break_pct",
    "bos_vs_orb_pct",
    "bos_vwap_gap_pct",
    "bos_body_frac",
    "anchor_to_bos_min",
]


def fetch_one_with_volume(url: str):
    r = requests.get(
        url,
        timeout=90,
        headers={"User-Agent": "bababot-sol-adaptive-structure-detector-v1/1.0"},
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh,
                header=None,
                usecols=[0, 1, 2, 3, 4, 5],
                names=["ts", "open", "high", "low", "close", "volume"],
            )


def row_at(x: pd.DataFrame, ts: pd.Timestamp):
    try:
        r = x.loc[ts]
    except KeyError:
        return None
    if isinstance(r, pd.DataFrame):
        r = r.iloc[0]
    return r


def anchored_vwap(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float:
    q = x[(x.index >= start) & (x.index <= end)]
    if q.empty:
        return np.nan
    vol = pd.to_numeric(q["volume"], errors="coerce").astype(float).to_numpy()
    tp = ((q["high"].astype(float) + q["low"].astype(float) + q["close"].astype(float)) / 3.0).to_numpy()
    m = np.isfinite(vol) & np.isfinite(tp)
    if not m.any():
        return np.nan
    vs = float(vol[m].sum())
    if vs <= 0:
        return np.nan
    return float((tp[m] * vol[m]).sum() / vs)


def frac_body(r) -> float:
    hi, lo, op, cl = map(float, (r.high, r.low, r.open, r.close))
    span = hi - lo
    return abs(cl - op) / span if span > 0 else 0.0


def upper_wick_frac(r) -> float:
    hi, lo, op, cl = map(float, (r.high, r.low, r.open, r.close))
    span = hi - lo
    return max(0.0, hi - max(op, cl)) / span if span > 0 else 0.0


def lower_wick_frac(r) -> float:
    hi, lo, op, cl = map(float, (r.high, r.low, r.open, r.close))
    span = hi - lo
    return max(0.0, min(op, cl) - lo) / span if span > 0 else 0.0


def context_features(x5: pd.DataFrame, start: pd.Timestamp, orb_rows: list) -> dict | None:
    q24 = x5[(x5.index >= start - pd.Timedelta(hours=24)) & (x5.index < start)]
    q7 = x5[(x5.index >= start - pd.Timedelta(days=7)) & (x5.index < start)]
    if len(q24) < 250 or len(q7) < 1500:
        return None

    c24 = q24.close.astype(float)
    c7 = q7.close.astype(float)
    lr24 = np.log(c24).diff().dropna()
    lr7 = np.log(c7).diff().dropna()
    if len(lr24) < 200 or len(lr7) < 1000:
        return None

    rv24 = float(lr24.std(ddof=1) * np.sqrt(288.0) * 100.0)
    rv7 = float(lr7.std(ddof=1) * np.sqrt(288.0) * 100.0)
    trend24 = float((c24.iloc[-1] / c24.iloc[0] - 1.0) * 100.0)
    bar_range_pct = ((q24.high.astype(float) - q24.low.astype(float)) / q24.close.astype(float) * 100.0)
    avg_bar_range = float(bar_range_pct.mean())
    vol_med = float(q24.volume.astype(float).median())
    orb_vol = float(sum(float(r.volume) for r in orb_rows))
    orb_vol_ratio = orb_vol / (3.0 * vol_med) if vol_med > 0 else np.nan

    h = int(start.hour)
    ang = 2.0 * np.pi * h / 24.0
    return {
        "hour_sin": float(np.sin(ang)),
        "hour_cos": float(np.cos(ang)),
        "pre24_rv_pct": rv24,
        "pre7d_rv_pct": rv7,
        "pre24_trend_pct": trend24,
        "pre24_avg_bar_range_pct": avg_bar_range,
        "orb_volume_ratio": orb_vol_ratio,
    }


def detect_event(x5: pd.DataFrame, start: pd.Timestamp) -> dict | None:
    if start < MODEL_START or start >= MODEL_END:
        return None
    orb_times = [start + i * BAR for i in range(3)]
    orb = [row_at(x5, t) for t in orb_times]
    if any(r is None for r in orb):
        return None

    oh = max(float(r.high) for r in orb)
    ol = min(float(r.low) for r in orb)
    o0 = float(orb[0].open)
    rng = oh - ol
    if not np.isfinite(rng) or rng <= 0 or o0 <= 0:
        return None

    ctx = context_features(x5, start, orb)
    if ctx is None:
        return None

    breakout_ts = None
    breakout = None
    for i in range(3, 12):
        ts = start + i * BAR
        if ts >= MODEL_END:
            break
        r = row_at(x5, ts)
        if r is not None and float(r.close) > oh:
            breakout_ts, breakout = ts, r
            break
    if breakout_ts is None:
        return None

    retest_ts = None
    retest = None
    for j in range(1, 7):
        ts = breakout_ts + j * BAR
        if ts >= MODEL_END:
            break
        r = row_at(x5, ts)
        if r is not None and float(r.low) <= oh:
            retest_ts, retest = ts, r
            break
    if retest_ts is None:
        return None

    prev = row_at(x5, retest_ts - BAR)
    if prev is None:
        return None
    micro = max(float(prev.high), float(retest.high))

    bos_ts = None
    bos = None
    bos_vwap = np.nan
    for k in range(1, 4):
        ts = retest_ts + k * BAR
        if ts >= MODEL_END:
            break
        r = row_at(x5, ts)
        if r is None:
            continue
        vw = anchored_vwap(x5, start, ts)
        if (
            float(r.close) > micro
            and float(r.close) > oh
            and np.isfinite(vw)
            and float(r.close) > vw
        ):
            bos_ts, bos, bos_vwap = ts, r, vw
            break
    if bos_ts is None:
        return None

    entry_ts = bos_ts + BAR
    if entry_ts >= MODEL_END:
        return None
    er = row_at(x5, entry_ts)
    if er is None:
        return None
    entry_price = float(er.open)

    exit_bar_ts = entry_ts + pd.Timedelta(minutes=60) - BAR
    if exit_bar_ts >= MODEL_END:
        return None
    xr = row_at(x5, exit_bar_ts)
    if xr is None:
        return None
    exit_price = float(xr.close)
    gross = (exit_price / entry_price - 1.0) * 100.0
    net = gross - ROUNDTRIP_COST_PCT

    breakout_vwap = anchored_vwap(x5, start, breakout_ts)
    retest_vwap = anchored_vwap(x5, start, retest_ts)
    if not all(np.isfinite(v) for v in (breakout_vwap, retest_vwap, bos_vwap)):
        return None

    rc = float(retest.close)
    ro = float(retest.open)
    rl = float(retest.low)
    rbody_abs = abs(rc - ro)
    lower_wick_abs = max(0.0, min(ro, rc) - rl)
    reclaim = rc >= oh
    bull_body = rc > ro
    wick_reject = lower_wick_abs >= rbody_abs
    bull_reaction = bool(reclaim and (bull_body or wick_reject))

    orb_range_pct = rng / o0 * 100.0
    avg_bar_range = float(ctx["pre24_avg_bar_range_pct"])

    row = {
        "session_start": start,
        "year": int(start.year),
        "hour_utc": int(start.hour),
        "hour_wib": int((start.hour + 7) % 24),
        "orb_high": oh,
        "orb_low": ol,
        "breakout_time": breakout_ts,
        "retest_time": retest_ts,
        "bos_time": bos_ts,
        "entry_time": entry_ts,
        "entry_price": entry_price,
        "exit_60m_price": exit_price,
        "net_60m_pct": net,
        "pnl_60m_usd": net / 100.0 * NOTIONAL,
        "win_60m": int(net > 0),
        **ctx,
        "orb_range_pct": orb_range_pct,
        "orb_range_norm": orb_range_pct / avg_bar_range if avg_bar_range > 0 else np.nan,
        "breakout_delay_min": float((breakout_ts - start) / pd.Timedelta(minutes=1)),
        "breakout_disp_orb_pct": (float(breakout.close) / oh - 1.0) * 100.0,
        "breakout_vwap_gap_pct": (float(breakout.close) / breakout_vwap - 1.0) * 100.0,
        "breakout_body_frac": frac_body(breakout),
        "breakout_upper_wick_frac": upper_wick_frac(breakout),
        "retest_delay_min": float((retest_ts - breakout_ts) / pd.Timedelta(minutes=1)),
        "retest_depth_orb_frac": (oh - float(retest.low)) / rng,
        "retest_close_vs_orb_pct": (rc / oh - 1.0) * 100.0,
        "retest_vwap_gap_pct": (rc / retest_vwap - 1.0) * 100.0,
        "retest_bullish_body": int(bull_body),
        "retest_wick_rejection": int(wick_reject),
        "retest_bullish_reaction": int(bull_reaction),
        "retest_body_frac": frac_body(retest),
        "retest_lower_wick_frac": lower_wick_frac(retest),
        "bos_delay_min": float((bos_ts - retest_ts) / pd.Timedelta(minutes=1)),
        "bos_micro_break_pct": (float(bos.close) / micro - 1.0) * 100.0,
        "bos_vs_orb_pct": (float(bos.close) / oh - 1.0) * 100.0,
        "bos_vwap_gap_pct": (float(bos.close) / bos_vwap - 1.0) * 100.0,
        "bos_body_frac": frac_body(bos),
        "anchor_to_bos_min": float((bos_ts - start) / pd.Timedelta(minutes=1)),
    }
    if not np.isfinite(pd.Series({k: row[k] for k in FEATURES}, dtype=float).to_numpy()).all():
        return None
    return row


def collect_events(x5: pd.DataFrame) -> pd.DataFrame:
    q = x5[(x5.index >= MODEL_START) & (x5.index < MODEL_END)]
    days = pd.Index(q.index.normalize().unique()).sort_values()
    rows = []
    for day in days:
        if day.weekday() >= 5:
            continue
        for hour in range(24):
            e = detect_event(x5, day + pd.Timedelta(hours=hour))
            if e is not None:
                rows.append(e)
    ev = pd.DataFrame(rows)
    if ev.empty:
        raise RuntimeError("no adaptive-structure events detected")
    return ev.sort_values("entry_time").reset_index(drop=True)


def profit_factor(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def max_loss_streak(pnls) -> int:
    best = cur = 0
    for v in pd.Series(pnls, dtype=float).dropna():
        if v < 0:
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


def metrics(g: pd.DataFrame) -> dict:
    if g.empty:
        return {
            "n": 0,
            "wr": np.nan,
            "net_pnl_usd": 0.0,
            "expectancy_pct": np.nan,
            "expectancy_usd": np.nan,
            "profit_factor": np.nan,
            "max_dd_usd": np.nan,
            "max_loss_streak": 0,
        }
    p = g.pnl_60m_usd.astype(float)
    r = g.net_60m_pct.astype(float)
    return {
        "n": int(len(g)),
        "wr": float((r > 0).mean()),
        "net_pnl_usd": float(p.sum()),
        "expectancy_pct": float(r.mean()),
        "expectancy_usd": float(p.mean()),
        "profit_factor": float(profit_factor(p)),
        "max_dd_usd": float(max_drawdown(p)),
        "max_loss_streak": int(max_loss_streak(p)),
    }


def make_models():
    clf = GradientBoostingClassifier(
        n_estimators=120,
        learning_rate=0.03,
        max_depth=2,
        min_samples_leaf=20,
        subsample=0.8,
        random_state=42,
    )
    reg = GradientBoostingRegressor(
        n_estimators=120,
        learning_rate=0.03,
        max_depth=2,
        min_samples_leaf=20,
        subsample=0.8,
        random_state=42,
        loss="huber",
    )
    return clf, reg


def walk_forward(ev: pd.DataFrame):
    pred_rows = []
    imp_rows = []
    for test_year in TEST_YEARS:
        tr = ev[ev.year < test_year].copy()
        te = ev[ev.year == test_year].copy()
        if len(tr) < 100:
            raise RuntimeError(f"insufficient training events before {test_year}: {len(tr)}")
        if len(te) == 0:
            raise RuntimeError(f"no test events in {test_year}")
        Xtr = tr[FEATURES].astype(float)
        Xte = te[FEATURES].astype(float)
        ycls = tr.win_60m.astype(int)
        yreg = tr.net_60m_pct.astype(float)
        if ycls.nunique() < 2:
            raise RuntimeError(f"training target has one class before {test_year}")

        clf, reg = make_models()
        clf.fit(Xtr, ycls)
        reg.fit(Xtr, yreg)

        te = te.copy()
        te["test_year"] = test_year
        te["train_start_year"] = int(tr.year.min())
        te["train_end_year"] = int(tr.year.max())
        te["pred_pwin"] = clf.predict_proba(Xte)[:, 1]
        te["pred_edge_pct"] = reg.predict(Xte)
        te["trade_gate"] = (te.pred_pwin >= PWIN_GATE) & (te.pred_edge_pct >= EDGE_GATE_PCT)
        pred_rows.append(te)

        ci = np.asarray(clf.feature_importances_, dtype=float)
        ri = np.asarray(reg.feature_importances_, dtype=float)
        for i, f in enumerate(FEATURES):
            imp_rows.append({
                "test_year": test_year,
                "feature": f,
                "classifier_importance": float(ci[i]),
                "regressor_importance": float(ri[i]),
            })

    pred = pd.concat(pred_rows, ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    imp = pd.DataFrame(imp_rows)
    return pred, imp


def yearly_summary(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y, g in pred.groupby("test_year"):
        for scope, q in (("ALL", g), ("TRADE", g[g.trade_gate])):
            m = metrics(q)
            rows.append({"test_year": int(y), "scope": scope, **m})
    return pd.DataFrame(rows).sort_values(["test_year", "scope"])


def quartile_summary(pred: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for y, g in pred.groupby("test_year"):
        q = g.copy()
        pct_rank = q.pred_edge_pct.rank(method="first", pct=True)
        q["edge_quartile"] = np.ceil(pct_rank * 4.0).clip(1, 4).astype(int)
        parts.append(q)
    z = pd.concat(parts, ignore_index=True)
    rows = []
    for qt, g in z.groupby("edge_quartile"):
        m = metrics(g)
        rows.append({
            "edge_quartile": int(qt),
            "mean_pred_edge_pct": float(g.pred_edge_pct.mean()),
            "mean_pred_pwin": float(g.pred_pwin.mean()),
            **m,
        })
    return pd.DataFrame(rows).sort_values("edge_quartile")


def feature_importance_summary(imp: pd.DataFrame) -> pd.DataFrame:
    s = imp.groupby("feature", as_index=False)[["classifier_importance", "regressor_importance"]].mean()
    s["mean_importance"] = (s.classifier_importance + s.regressor_importance) / 2.0
    return s.sort_values("mean_importance", ascending=False).reset_index(drop=True)


def fmt_pf(v):
    if pd.isna(v):
        return "n/a"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.3f}"


def main():
    base.fetch_one = fetch_one_with_volume
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")
    if "volume" not in x5.columns:
        raise RuntimeError("volume column required")

    ev = collect_events(x5)
    pred, imp = walk_forward(ev)
    yr = yearly_summary(pred)
    quart = quartile_summary(pred)
    fi = feature_importance_summary(imp)

    all_m = metrics(pred)
    trade = pred[pred.trade_gate].copy()
    trade_m = metrics(trade)

    auc = roc_auc_score(pred.win_60m.astype(int), pred.pred_pwin.astype(float)) if pred.win_60m.nunique() > 1 else np.nan
    brier = brier_score_loss(pred.win_60m.astype(int), pred.pred_pwin.astype(float))
    spearman = float(pred.pred_edge_pct.corr(pred.net_60m_pct, method="spearman"))

    pos_years = 0
    for y in TEST_YEARS:
        q = trade[trade.test_year == y]
        if len(q) and float(q.pnl_60m_usd.sum()) > 0:
            pos_years += 1

    q4 = quart[quart.edge_quartile == 4]
    q4_exp = float(q4.expectancy_pct.iloc[0]) if len(q4) else np.nan

    gates = {
        "gated_n_ge_30": trade_m["n"] >= 30,
        "gated_wr_ge_60pct": bool(np.isfinite(trade_m["wr"]) and trade_m["wr"] >= 0.60),
        "gated_expectancy_positive": bool(np.isfinite(trade_m["expectancy_pct"]) and trade_m["expectancy_pct"] > 0),
        "gated_pf_ge_1_25": bool(np.isfinite(trade_m["profit_factor"]) and trade_m["profit_factor"] >= 1.25),
        "gated_net_pnl_positive": trade_m["net_pnl_usd"] > 0,
        "positive_years_ge_3": pos_years >= 3,
        "top_quartile_beats_all": bool(np.isfinite(q4_exp) and q4_exp > all_m["expectancy_pct"]),
    }
    passed = bool(all(gates.values()))

    ev.to_csv(ROOT / f"{PFX}_Events.csv", index=False)
    pred.to_csv(ROOT / f"{PFX}_WalkForwardPredictions.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    quart.to_csv(ROOT / f"{PFX}_EdgeQuartiles.csv", index=False)
    fi.to_csv(ROOT / f"{PFX}_FeatureImportance.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    lines = [
        "# SOL Adaptive Structure Detector v1 — Walk-Forward Result",
        "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- Eligible fixed-skeleton events 2020-2024: **{len(ev)}**",
        f"- Walk-forward predicted events 2021-2024: **{len(pred)}**",
        "- Test protocol: expanding annual walk-forward; each test year trained only on prior years.",
        "- 2025+ reference_validation remained CLOSED.",
        f"- Frozen trade gate: P(win) >= {PWIN_GATE:.0%} AND predicted net 60m edge >= {EDGE_GATE_PCT:.2f}%.",
        "",
        "## Overall walk-forward",
        "",
        "| Scope | N | WR | Net PnL | Exp % | Exp $ | PF | Max DD | Max LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| ALL fixed-skeleton events | {all_m['n']} | {all_m['wr']*100:.2f}% | ${all_m['net_pnl_usd']:.2f} | {all_m['expectancy_pct']:.4f}% | ${all_m['expectancy_usd']:.3f} | {fmt_pf(all_m['profit_factor'])} | ${all_m['max_dd_usd']:.2f} | {all_m['max_loss_streak']} |",
        f"| TRADE gate | {trade_m['n']} | {(trade_m['wr']*100 if np.isfinite(trade_m['wr']) else np.nan):.2f}% | ${trade_m['net_pnl_usd']:.2f} | {(trade_m['expectancy_pct'] if np.isfinite(trade_m['expectancy_pct']) else np.nan):.4f}% | ${(trade_m['expectancy_usd'] if np.isfinite(trade_m['expectancy_usd']) else np.nan):.3f} | {fmt_pf(trade_m['profit_factor'])} | ${(trade_m['max_dd_usd'] if np.isfinite(trade_m['max_dd_usd']) else np.nan):.2f} | {trade_m['max_loss_streak']} |",
        "",
        "## Prediction quality",
        "",
        f"- ROC AUC for P(win): **{auc:.4f}**",
        f"- Brier score: **{brier:.4f}**",
        f"- Spearman(predicted edge, realized net return): **{spearman:.4f}**",
        "",
        "## Gated results by test year",
        "",
        "| Year | N | WR | Net PnL | Exp % | PF |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for y in TEST_YEARS:
        r = yr[(yr.test_year == y) & (yr.scope == "TRADE")].iloc[0]
        wr = float(r.wr) * 100 if pd.notna(r.wr) else np.nan
        lines.append(f"| {y} | {int(r.n)} | {wr:.2f}% | ${float(r.net_pnl_usd):.2f} | {float(r.expectancy_pct) if pd.notna(r.expectancy_pct) else np.nan:.4f}% | {fmt_pf(r.profit_factor)} |")

    lines += [
        "",
        "## Predicted-edge quartiles (ranking diagnostic only)",
        "",
        "| Q | N | Mean Pred Edge | Mean P(win) | Realized WR | Realized Exp % | PF |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in quart.iterrows():
        lines.append(f"| {int(r.edge_quartile)} | {int(r.n)} | {float(r.mean_pred_edge_pct):.4f}% | {float(r.mean_pred_pwin)*100:.2f}% | {float(r.wr)*100:.2f}% | {float(r.expectancy_pct):.4f}% | {fmt_pf(r.profit_factor)} |")

    lines += ["", "## Top adaptive features", ""]
    for _, r in fi.head(10).iterrows():
        lines.append(f"- `{r.feature}` — mean importance {float(r.mean_importance):.4f}")

    lines += ["", "## v1 gate audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "",
        f"# VERDICT: {'PASS' if passed else 'FAIL'}",
        "",
        "PASS means the frozen adaptive score survived its preregistered 2021-2024 walk-forward gates. It does NOT yet authorize opening 2025+ reference_validation or optimizing TP/SL.",
        "FAIL means v1 thresholds must not be retuned against this same walk-forward sample; any revision requires a separately preregistered v2 architecture/semantics change.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(("PASS" if passed else "FAIL") + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
