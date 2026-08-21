#!/usr/bin/env python3
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

import btc_h1_low_reject_structure_lr1 as dataio

ROOT = Path(__file__).resolve().parent.parent
OUTJ = ROOT / "BTC_WEEKLY_DIRECTION_B10_Result.json"
OUTM = ROOT / "BTC_WEEKLY_DIRECTION_B10_Result.md"
OUTS = ROOT / "BTC_WEEKLY_DIRECTION_B10_Selected.csv"
OUTT = ROOT / "BTC_WEEKLY_DIRECTION_B10_Thresholds.csv"
OUTF = ROOT / "BTC_WEEKLY_DIRECTION_B10_FeatureImportance.csv"

REVISION = "B10_V1"
FEE = 0.0015
FAVORABLE = 0.0115
ADVERSE = 0.0085
SAT_CUTOFF_HOURS = 5 * 24 + 12
RANDOM_STATE = 20260821
QGRID = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.925, 0.95, 0.975, 0.99]

EXT0 = pd.Timestamp("2020-01-01", tz="UTC")
EXT1 = pd.Timestamp("2022-01-01", tz="UTC")
DEV0 = pd.Timestamp("2022-01-01", tz="UTC")
DEV1 = pd.Timestamp("2025-01-01", tz="UTC")
VAL0 = pd.Timestamp("2025-01-01", tz="UTC")
VAL1 = pd.Timestamp("2026-07-30", tz="UTC")
AUG0 = pd.Timestamp("2026-08-01", tz="UTC")

FEATURES = [
    "r1", "r2", "r4", "r8", "r12", "r24", "r48",
    "atr_pct", "tr_atr",
    "ema8_dist", "ema21_dist", "ema55_dist",
    "ema8_slope3", "ema21_slope3", "ema55_slope3",
    "pos12", "pos24", "pos48", "d24_hi_atr", "d24_lo_atr",
    "body_frac", "upper_wick_frac", "lower_wick_frac",
    "week_pos", "week_range_pct", "week_ret",
    "day_pos", "day_range_pct", "day_ret",
    "pw_hi_atr", "pw_lo_atr", "pw_range_pct",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
]


def week_start(ts):
    t = pd.Timestamp(ts)
    d = t.floor("D")
    return d - pd.Timedelta(days=int(t.weekday()))


def week_key(w):
    iso = pd.Timestamp(w).isocalendar()
    return f"{int(iso.year)}-W{int(iso.week):02d}"


def complete_weeks(a, b, data_end):
    a = pd.Timestamp(a)
    b = min(pd.Timestamp(b), pd.Timestamp(data_end))
    d = a.floor("D")
    w = d - pd.Timedelta(days=int(d.weekday()))
    if w < a:
        w += pd.Timedelta(days=7)
    out = []
    while w + pd.Timedelta(days=7) <= b:
        out.append(w)
        w += pd.Timedelta(days=7)
    return out


def safe_pos(close, lo, hi):
    den = hi - lo
    return (close - lo) / den.replace(0.0, np.nan)


def prepare_features(k):
    x = k.copy().astype(float)
    prev = x.close.shift(1)
    tr = pd.concat([
        x.high - x.low,
        (x.high - prev).abs(),
        (x.low - prev).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=14).mean()
    x["tr"] = tr
    x["atr"] = atr

    for n in (1, 2, 4, 8, 12, 24, 48):
        x[f"r{n}"] = x.close.pct_change(n)

    x["atr_pct"] = atr / x.close
    x["tr_atr"] = tr / atr

    for span in (8, 21, 55):
        e = x.close.ewm(span=span, adjust=False).mean()
        x[f"ema{span}"] = e
        x[f"ema{span}_dist"] = (x.close - e) / atr
        x[f"ema{span}_slope3"] = e.pct_change(3)

    for n in (12, 24, 48):
        hi = x.high.rolling(n, min_periods=n).max()
        lo = x.low.rolling(n, min_periods=n).min()
        x[f"pos{n}"] = safe_pos(x.close, lo, hi)
        if n == 24:
            x["d24_hi_atr"] = (hi - x.close) / atr
            x["d24_lo_atr"] = (x.close - lo) / atr

    candle_range = (x.high - x.low).replace(0.0, np.nan)
    x["body_frac"] = (x.close - x.open) / candle_range
    x["upper_wick_frac"] = (x.high - x[["open", "close"]].max(axis=1)) / candle_range
    x["lower_wick_frac"] = (x[["open", "close"]].min(axis=1) - x.low) / candle_range

    wk_keys = pd.Series([week_start(t) for t in x.index], index=x.index)
    x["week_start"] = wk_keys
    g = x.groupby(wk_keys, sort=False)
    x["week_hi_run"] = g.high.cummax()
    x["week_lo_run"] = g.low.cummin()
    x["week_open"] = g.open.transform("first")
    x["week_pos"] = safe_pos(x.close, x.week_lo_run, x.week_hi_run)
    x["week_range_pct"] = (x.week_hi_run - x.week_lo_run) / x.week_open
    x["week_ret"] = x.close / x.week_open - 1.0

    day_keys = pd.Series(x.index.floor("D"), index=x.index)
    dg = x.groupby(day_keys, sort=False)
    x["day_hi_run"] = dg.high.cummax()
    x["day_lo_run"] = dg.low.cummin()
    x["day_open"] = dg.open.transform("first")
    x["day_pos"] = safe_pos(x.close, x.day_lo_run, x.day_hi_run)
    x["day_range_pct"] = (x.day_hi_run - x.day_lo_run) / x.day_open
    x["day_ret"] = x.close / x.day_open - 1.0

    wk = x.groupby(wk_keys).agg(high=("high", "max"), low=("low", "min"), open=("open", "first")).sort_index()
    prevwk = pd.DataFrame({
        "pw_hi": wk.high.shift(1),
        "pw_lo": wk.low.shift(1),
        "pw_open": wk.open.shift(1),
    })
    x["pw_hi"] = x.week_start.map(prevwk.pw_hi)
    x["pw_lo"] = x.week_start.map(prevwk.pw_lo)
    x["pw_open"] = x.week_start.map(prevwk.pw_open)
    mapped = float(x.pw_hi.notna().mean())
    if mapped < 0.90:
        raise RuntimeError(f"previous-week mapping coverage too low: {mapped:.3f}")
    x["pw_hi_atr"] = (x.pw_hi - x.close) / atr
    x["pw_lo_atr"] = (x.close - x.pw_lo) / atr
    x["pw_range_pct"] = (x.pw_hi - x.pw_lo) / x.pw_open

    hour = x.index.hour.to_numpy(float)
    dow = x.index.weekday.to_numpy(float)
    x["hour_sin"] = np.sin(2.0 * np.pi * hour / 24.0)
    x["hour_cos"] = np.cos(2.0 * np.pi * hour / 24.0)
    x["dow_sin"] = np.sin(2.0 * np.pi * dow / 7.0)
    x["dow_cos"] = np.cos(2.0 * np.pi * dow / 7.0)

    for c in FEATURES:
        x[c] = x[c].replace([np.inf, -np.inf], np.nan)
    return x


def side_outcome(x, signal_i, side, w):
    entry_i = signal_i + 1
    if entry_i >= len(x):
        return None
    entry_ts = x.index[entry_i]
    week_end = w + pd.Timedelta(days=7)
    if entry_ts >= week_end:
        return None
    end_i = int(x.index.searchsorted(week_end, side="left") - 1)
    if end_i < entry_i:
        return None
    entry = float(x.open.iloc[entry_i])
    if side == "LONG":
        tp = entry * (1.0 + FAVORABLE)
        sl = entry * (1.0 - ADVERSE)
    else:
        tp = entry * (1.0 - FAVORABLE)
        sl = entry * (1.0 + ADVERSE)

    for j in range(entry_i, end_i + 1):
        hi = float(x.high.iloc[j])
        lo = float(x.low.iloc[j])
        if side == "LONG":
            hit_sl = lo <= sl
            hit_tp = hi >= tp
        else:
            hit_sl = hi >= sl
            hit_tp = lo <= tp
        if hit_sl and hit_tp:
            return {"reason": "SL", "net_ret": -0.01, "exit_ts": x.index[j], "entry_ts": entry_ts, "entry": entry}
        if hit_sl:
            return {"reason": "SL", "net_ret": -0.01, "exit_ts": x.index[j], "entry_ts": entry_ts, "entry": entry}
        if hit_tp:
            return {"reason": "TP", "net_ret": 0.01, "exit_ts": x.index[j], "entry_ts": entry_ts, "entry": entry}

    last_close = float(x.close.iloc[end_i])
    gross = (last_close - entry) / entry if side == "LONG" else (entry - last_close) / entry
    net = gross - FEE
    return {"reason": "TIME", "net_ret": float(net), "exit_ts": x.index[end_i], "entry_ts": entry_ts, "entry": entry}


def build_rows(x, weeks, partition):
    rows = []
    for w in weeks:
        cut = w + pd.Timedelta(hours=SAT_CUTOFF_HOURS)
        a = int(x.index.searchsorted(w, side="left"))
        z = int(x.index.searchsorted(cut, side="right"))
        for i in range(a, z):
            if i + 1 >= len(x):
                continue
            f = x.iloc[i][FEATURES]
            if f.isna().any():
                continue
            lo = side_outcome(x, i, "LONG", w)
            so = side_outcome(x, i, "SHORT", w)
            if lo is None or so is None:
                continue
            long_tp = lo["reason"] == "TP"
            short_tp = so["reason"] == "TP"
            if long_tp and not short_tp:
                label = "LONG"
            elif short_tp and not long_tp:
                label = "SHORT"
            else:
                label = "NONE"
            r = {
                "partition": partition,
                "week": week_key(w),
                "week_start": w,
                "signal_ts": x.index[i],
                "signal_i": i,
                "label": label,
                "long_reason": lo["reason"],
                "long_net": float(lo["net_ret"]),
                "long_exit_ts": lo["exit_ts"],
                "short_reason": so["reason"],
                "short_net": float(so["net_ret"]),
                "short_exit_ts": so["exit_ts"],
                "entry_ts": lo["entry_ts"],
                "entry": float(lo["entry"]),
            }
            r.update({c: float(f[c]) for c in FEATURES})
            rows.append(r)
    return pd.DataFrame(rows)


def make_rf():
    return RandomForestClassifier(
        n_estimators=400,
        max_depth=8,
        min_samples_leaf=50,
        max_features="sqrt",
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )


def fit_models(dev):
    X = dev[FEATURES].to_numpy(float)
    yopp = (dev.label != "NONE").astype(int).to_numpy()
    if len(np.unique(yopp)) < 2:
        raise RuntimeError("opportunity target has fewer than two classes")
    opp = make_rf()
    opp.fit(X, yopp)

    dec = dev[dev.label != "NONE"].copy()
    ydir = (dec.label == "LONG").astype(int).to_numpy()
    if len(np.unique(ydir)) < 2:
        raise RuntimeError("direction target has fewer than two classes")
    direc = make_rf()
    direc.fit(dec[FEATURES].to_numpy(float), ydir)
    return opp, direc


def score(opp, direc, z):
    q = z.copy()
    if q.empty:
        for c in ("p_opp", "p_long", "confidence", "pred_side"):
            q[c] = []
        return q
    X = q[FEATURES].to_numpy(float)
    q["p_opp"] = opp.predict_proba(X)[:, 1]
    q["p_long"] = direc.predict_proba(X)[:, 1]
    q["pred_side"] = np.where(q.p_long.to_numpy() >= 0.5, "LONG", "SHORT")
    q["confidence"] = q.p_opp * np.maximum(q.p_long, 1.0 - q.p_long)
    return q


def select_weekly(scored, threshold, weeks):
    out = []
    for w in weeks:
        wk = scored[scored.week == week_key(w)].sort_values("signal_ts")
        if wk.empty:
            continue
        hit = wk[wk.confidence >= threshold]
        if len(hit):
            c = hit.iloc[0].copy()
            route = "MODEL_TRIGGER"
        else:
            c = wk.iloc[-1].copy()
            route = "FORCED_SAT12"
        side = str(c.pred_side)
        if side == "LONG":
            reason = str(c.long_reason)
            net = float(c.long_net)
            exit_ts = c.long_exit_ts
        else:
            reason = str(c.short_reason)
            net = float(c.short_net)
            exit_ts = c.short_exit_ts
        r = c.to_dict()
        r.update({
            "route": route,
            "threshold": float(threshold),
            "side": side,
            "reason": reason,
            "net_ret": net,
            "exit_ts": exit_ts,
        })
        out.append(r)
    return pd.DataFrame(out)


def pf_of(a):
    a = np.asarray(a, float)
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    if gl > 0:
        return gp / gl
    return 999.0 if gp > 0 else 0.0


def selected_stat(z, weeks_total):
    if z.empty:
        return {
            "weeks_total": int(weeks_total), "n": 0, "coverage": 0.0,
            "tp": 0, "sl": 0, "time": 0, "tp_wr": None, "positive_wr": None,
            "exp": None, "pf": None, "max_losing_streak": 0,
            "trigger": 0, "fallback": 0,
        }
    a = z.net_ret.to_numpy(float)
    tp = int((z.reason == "TP").sum())
    sl = int((z.reason == "SL").sum())
    tm = int((z.reason == "TIME").sum())
    streak = mx = 0
    for reason in z.reason:
        if reason != "TP":
            streak += 1
            mx = max(mx, streak)
        else:
            streak = 0
    return {
        "weeks_total": int(weeks_total),
        "n": int(len(z)),
        "coverage": float(z.week.nunique() / weeks_total) if weeks_total else 0.0,
        "tp": tp, "sl": sl, "time": tm,
        "tp_wr": float(tp / len(z)),
        "positive_wr": float((a > 0).mean()),
        "exp": float(a.mean()),
        "pf": float(pf_of(a)),
        "max_losing_streak": int(mx),
        "trigger": int((z.route == "MODEL_TRIGGER").sum()),
        "fallback": int((z.route == "FORCED_SAT12").sum()),
    }


def block_stats(z):
    if z.empty:
        return []
    q = z.sort_values("entry_ts").reset_index(drop=True)
    chunks = np.array_split(np.arange(len(q)), 4)
    out = []
    for bi, inds in enumerate(chunks, 1):
        s = q.iloc[inds]
        a = s.net_ret.to_numpy(float)
        out.append({
            "block": bi,
            "n": int(len(s)),
            "tp_wr": float((s.reason == "TP").mean()),
            "exp": float(a.mean()),
            "pf": float(pf_of(a)),
        })
    return out


def row_diag(z):
    if z.empty:
        return {"n": 0, "decisive_rate": None, "direction_accuracy_decisive": None, "predicted_side_tp_rate": None}
    decisive = z.label != "NONE"
    diracc = None
    if decisive.any():
        diracc = float((z.loc[decisive, "pred_side"] == z.loc[decisive, "label"]).mean())
    pred_tp = np.where(z.pred_side == "LONG", z.long_reason == "TP", z.short_reason == "TP")
    return {
        "n": int(len(z)),
        "decisive_rate": float(decisive.mean()),
        "direction_accuracy_decisive": diracc,
        "predicted_side_tp_rate": float(np.mean(pred_tp)),
    }


def threshold_table(dev_scored, dev_weeks):
    rows = []
    vals = dev_scored.confidence.to_numpy(float)
    for q in QGRID:
        th = float(np.quantile(vals, q))
        sel = select_weekly(dev_scored, th, dev_weeks)
        st = selected_stat(sel, len(dev_weeks))
        rows.append({"quantile": q, "threshold": th, **st})
    t = pd.DataFrame(rows)
    ranked = t.sort_values(
        ["tp_wr", "exp", "pf", "fallback", "quantile"],
        ascending=[False, False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    best = ranked.iloc[0]
    return t, float(best.threshold), float(best["quantile"])


def gate_100(stats, blocks):
    return (
        stats["coverage"] == 1.0
        and stats["n"] == stats["weeks_total"]
        and stats["tp_wr"] == 1.0
        and stats["exp"] > 0
        and stats["pf"] > 1
        and len(blocks) == 4
        and all(b["exp"] > 0 for b in blocks)
    )


def gate_80(stats, blocks):
    return (
        stats["coverage"] == 1.0
        and stats["n"] == stats["weeks_total"]
        and stats["tp_wr"] >= 0.80
        and stats["exp"] > 0
        and stats["pf"] > 1
        and stats["max_losing_streak"] <= 2
        and len(blocks) == 4
        and sum(b["exp"] > 0 for b in blocks) >= 3
    )


def pct(v):
    return "-" if v is None else f"{100.0*float(v):.2f}%"


def num(v, n=3):
    return "-" if v is None else f"{float(v):.{n}f}"


def main():
    raw = dataio.load_1h().copy()
    raw["ts"] = pd.to_datetime(raw.ts, utc=True)
    raw = raw.sort_values("ts").drop_duplicates("ts")
    k = raw.set_index("ts")[["open", "high", "low", "close"]].astype(float)
    data_end = raw.ts.max() + pd.Timedelta(hours=1)
    x = prepare_features(k)

    parts = {
        "external": (EXT0, EXT1),
        "development": (DEV0, DEV1),
        "reference_validation": (VAL0, VAL1),
        "august": (AUG0, data_end),
    }
    weeks_by_part = {name: complete_weeks(a, b, data_end) for name, (a, b) in parts.items()}
    rows_by_part = {name: build_rows(x, weeks, name) for name, weeks in weeks_by_part.items()}

    dev = rows_by_part["development"]
    if dev.empty:
        raise RuntimeError("empty development rows")
    opp, direc = fit_models(dev)
    scored = {name: score(opp, direc, z) for name, z in rows_by_part.items()}

    thtab, threshold, chosen_q = threshold_table(scored["development"], weeks_by_part["development"])
    thtab.to_csv(OUTT, index=False)

    result = {
        "experiment": "BTC_WEEKLY_DIRECTION_B10",
        "revision": REVISION,
        "coverage": {"first": str(raw.ts.min()), "last": str(raw.ts.max()), "h1_rows": int(len(raw))},
        "fee": FEE,
        "favorable_price_move": FAVORABLE,
        "adverse_price_move": ADVERSE,
        "chosen_quantile": chosen_q,
        "threshold": threshold,
        "partitions": {},
        "gates": {},
        "live_bbc_untouched": True,
    }
    selected_all = []
    for name in ("development", "reference_validation", "external", "august"):
        z = scored[name]
        weeks = weeks_by_part[name]
        sel = select_weekly(z, threshold, weeks)
        st = selected_stat(sel, len(weeks))
        bl = block_stats(sel)
        result["partitions"][name] = {
            "selected": st,
            "blocks": bl,
            "row_diagnostic": row_diag(z),
        }
        if len(sel):
            selected_all.append(sel)

    ext = result["partitions"]["external"]
    val = result["partitions"]["reference_validation"]
    robust = gate_100(ext["selected"], ext["blocks"]) and gate_100(val["selected"], val["blocks"])
    high = gate_80(ext["selected"], ext["blocks"]) and gate_80(val["selected"], val["blocks"])
    result["gates"] = {
        "B10_ROBUST_WEEKLY_100": bool(robust),
        "B10_HIGH_PRECISION_WEEKLY": bool(high),
    }
    result["verdict"] = "B10_ROBUST_WEEKLY_100" if robust else ("B10_HIGH_PRECISION_WEEKLY" if high else "B10_NO_ROBUST_WEEKLY_EDGE")

    fimps = []
    for model_name, model in (("opportunity", opp), ("direction", direc)):
        for f, imp in zip(FEATURES, model.feature_importances_):
            fimps.append({"model": model_name, "feature": f, "importance": float(imp)})
    pd.DataFrame(fimps).to_csv(OUTF, index=False)

    if selected_all:
        cols = [
            "partition", "week", "signal_ts", "entry_ts", "exit_ts", "route", "side", "reason",
            "net_ret", "confidence", "p_opp", "p_long", "threshold", "label",
        ]
        pd.concat(selected_all, ignore_index=True)[cols].to_csv(OUTS, index=False)

    with open(OUTJ, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    md = [
        "# BTC Weekly 1% Direction Detector B10 — Result",
        "",
        f"**Verdict: {result['verdict']}**",
        "",
        f"Implementation revision **{REVISION}**.",
        "",
        f"Coverage **{result['coverage']['first']} -> {result['coverage']['last']}**, official H1 rows **{result['coverage']['h1_rows']:,}**.",
        "",
        f"Frozen development-selected quantile **{chosen_q:.3f}**, confidence threshold **{threshold:.6f}**. Net +1.00% / -1.00% geometry after 0.15% round-trip fee; next-open; adverse-first; one trade per complete week; forced Saturday 12 UTC fallback.",
        "",
        "## Weekly selector",
        "",
        "| Partition | Weeks/N/Coverage | Trigger/Fallback | TP/SL/TIME | TP WR | Positive WR | Exp | PF | Max LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("development", "reference_validation", "external", "august"):
        s = result["partitions"][name]["selected"]
        md.append(
            f"| {name} | {s['weeks_total']}/{s['n']}/{pct(s['coverage'])} | {s['trigger']}/{s['fallback']} | "
            f"{s['tp']}/{s['sl']}/{s['time']} | {pct(s['tp_wr'])} | {pct(s['positive_wr'])} | "
            f"{pct(s['exp'])} | {num(s['pf'])} | {s['max_losing_streak']} |"
        )

    md += [
        "",
        "## Per-bar diagnostics",
        "",
        "| Partition | Rows | Decisive rate | Direction accuracy on decisive | Predicted-side TP rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ("development", "reference_validation", "external", "august"):
        d = result["partitions"][name]["row_diagnostic"]
        md.append(f"| {name} | {d['n']:,} | {pct(d['decisive_rate'])} | {pct(d['direction_accuracy_decisive'])} | {pct(d['predicted_side_tp_rate'])} |")

    md += [
        "",
        "## Four chronological blocks",
        "",
        "| Partition | Block | N | TP WR | Exp | PF |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("reference_validation", "external"):
        for b in result["partitions"][name]["blocks"]:
            md.append(f"| {name} | {b['block']} | {b['n']} | {pct(b['tp_wr'])} | {pct(b['exp'])} | {num(b['pf'])} |")

    md += [
        "",
        "## Gates",
        "",
        f"- `B10_ROBUST_WEEKLY_100`: **{'PASS' if robust else 'FAIL'}**",
        f"- `B10_HIGH_PRECISION_WEEKLY`: **{'PASS' if high else 'FAIL'}**",
        "- Live BBC untouched: **YES**",
        "",
        "This result must not be rescued by post-result feature/model/threshold/clock/TP/SL changes; any change requires a new preregistered experiment.",
    ]
    OUTM.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
