#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

import btc_h1_low_reject_structure_lr1 as dataio
import btc_weekly_structural_b8 as b8

ROOT = Path(__file__).resolve().parent.parent
OUTJ = ROOT / "BTC_WEEKLY_ENTRYMAP_B9_Result.json"
OUTM = ROOT / "BTC_WEEKLY_ENTRYMAP_B9_Result.md"
OUTC = ROOT / "BTC_WEEKLY_ENTRYMAP_B9_Selected.csv"
OUTCOEF = ROOT / "BTC_WEEKLY_ENTRYMAP_B9_Coefficients.csv"

IMPLEMENTATION_REVISION = "B9_TZFIX1"
FEE = 0.0015
EXT0 = pd.Timestamp("2020-01-01", tz="UTC")
EXT1 = pd.Timestamp("2022-01-01", tz="UTC")
DEV0 = pd.Timestamp("2022-01-01", tz="UTC")
DEV1 = pd.Timestamp("2025-01-01", tz="UTC")
VAL0 = pd.Timestamp("2025-01-01", tz="UTC")
VAL1 = pd.Timestamp("2026-07-30", tz="UTC")
AUG0 = pd.Timestamp("2026-08-01", tz="UTC")

FEATURES = [
    "sr_dist",
    "sr_sweep",
    "sr_room",
    "pw_dist",
    "pw_sweep",
    "pw_pos",
    "orb_near",
    "orb_state",
    "orb_reclaim",
    "fvg_dist",
    "fvg_touch",
    "fib_dist",
    "fib_touch",
    "body_align",
    "reject_wick",
]


def week_start(ts):
    t = pd.Timestamp(ts)
    d = t.floor("D")
    return d - pd.Timedelta(days=t.weekday())


def add_previous_week_levels(x):
    z = x.copy()
    keys = pd.Series([week_start(t) for t in z.index], index=z.index)
    wk = z.groupby(keys).agg({"high": "max", "low": "min"}).sort_index()
    prev = pd.DataFrame({
        "pw_hi": wk.high.shift(1),
        "pw_lo": wk.low.shift(1),
    })
    # Preserve timezone-aware Timestamp keys. `.values` would strip the tz and
    # silently break mapping against the tz-aware weekly index.
    z["week_start"] = keys
    z["pw_hi"] = z["week_start"].map(prev.pw_hi)
    z["pw_lo"] = z["week_start"].map(prev.pw_lo)
    mapped = float(z.pw_hi.notna().mean())
    if mapped < 0.90:
        raise RuntimeError(f"previous-week mapping coverage too low: {mapped:.3f}")
    return z


def latest_fvg_side(x, i, side):
    lo = max(2, i - 12)
    for j in range(i - 1, lo - 1, -1):
        a = x.iloc[j - 2]
        c = x.iloc[j]
        if side == "LONG" and float(c.low) > float(a.high):
            zlo, zhi = float(a.high), float(c.low)
            prior = x.iloc[j + 1:i]
            if len(prior) and float(prior.low.min()) <= zlo:
                continue
            return zlo, zhi
        if side == "SHORT" and float(c.high) < float(a.low):
            zlo, zhi = float(c.high), float(a.low)
            prior = x.iloc[j + 1:i]
            if len(prior) and float(prior.high.max()) >= zhi:
                continue
            return zlo, zhi
    return None


def fib_zone_side(x, i, side):
    if i < 12:
        return None
    w = x.iloc[i - 12:i]
    b = x.iloc[i]
    atr = float(b.atr)
    if not np.isfinite(atr) or atr <= 0:
        return None
    hi_pos = int(np.argmax(w.high.to_numpy(float)))
    lo_pos = int(np.argmin(w.low.to_numpy(float)))
    hi = float(w.high.iloc[hi_pos])
    lo = float(w.low.iloc[lo_pos])
    rng = hi - lo
    if rng < 2.0 * atr:
        return None
    if side == "LONG" and lo_pos < hi_pos:
        return hi - 0.618 * rng, hi - 0.500 * rng
    if side == "SHORT" and hi_pos < lo_pos:
        return lo + 0.500 * rng, lo + 0.618 * rng
    return None


def feature_row(x, i, tf, side):
    b = x.iloc[i]
    t = x.index[i]
    atr = float(b.atr)
    if not np.isfinite(atr) or atr <= 0:
        return None
    o, h, l, c = map(float, (b.open, b.high, b.low, b.close))
    sign = 1.0 if side == "LONG" else -1.0

    sup, res = float(b.lo20), float(b.hi20)
    relevant_sr = sup if side == "LONG" else res
    opposite_sr = res if side == "LONG" else sup
    sr_dist = (c - relevant_sr) / atr if side == "LONG" else (relevant_sr - c) / atr
    if side == "LONG":
        sr_sweep = float(l < sup and c >= sup)
        sr_room = (opposite_sr - c) / atr
    else:
        sr_sweep = float(h > res and c <= res)
        sr_room = (c - opposite_sr) / atr

    pw_hi = float(b.pw_hi) if np.isfinite(b.pw_hi) else np.nan
    pw_lo = float(b.pw_lo) if np.isfinite(b.pw_lo) else np.nan
    if np.isfinite(pw_hi) and np.isfinite(pw_lo) and pw_hi > pw_lo:
        relevant_pw = pw_lo if side == "LONG" else pw_hi
        pw_dist = (c - relevant_pw) / atr if side == "LONG" else (relevant_pw - c) / atr
        if side == "LONG":
            pw_sweep = float(l < pw_lo and c >= pw_lo)
            pw_pos = (c - pw_lo) / (pw_hi - pw_lo)
        else:
            pw_sweep = float(h > pw_hi and c <= pw_hi)
            pw_pos = (pw_hi - c) / (pw_hi - pw_lo)
    else:
        pw_dist, pw_sweep, pw_pos = 9.0, 0.0, 0.5

    orb_available = int(t.hour) >= 4
    oh = float(b.or_hi) if np.isfinite(b.or_hi) else np.nan
    ol = float(b.or_lo) if np.isfinite(b.or_lo) else np.nan
    if orb_available and np.isfinite(oh) and np.isfinite(ol) and oh > ol:
        orb_near = min(abs(c - oh), abs(c - ol)) / atr
        mid = (oh + ol) / 2.0
        orb_state = sign * (c - mid) / atr
        if side == "LONG":
            orb_reclaim = float(l <= oh and c > oh)
        else:
            orb_reclaim = float(h >= ol and c < ol)
    else:
        orb_near, orb_state, orb_reclaim = 9.0, 0.0, 0.0

    g = latest_fvg_side(x, i, side)
    if g is None:
        fvg_dist, fvg_touch = 9.0, 0.0
    else:
        zlo, zhi = g
        mid = (zlo + zhi) / 2.0
        fvg_dist = (c - mid) / atr if side == "LONG" else (mid - c) / atr
        fvg_touch = float(l <= zhi and h >= zlo)

    fz = fib_zone_side(x, i, side)
    if fz is None:
        fib_dist, fib_touch = 9.0, 0.0
    else:
        zlo, zhi = fz
        mid = (zlo + zhi) / 2.0
        fib_dist = (c - mid) / atr if side == "LONG" else (mid - c) / atr
        fib_touch = float(l <= zhi and h >= zlo)

    body_align = sign * (c - o) / atr
    if side == "LONG":
        reject_wick = max(0.0, min(o, c) - l) / atr
    else:
        reject_wick = max(0.0, h - max(o, c)) / atr

    vals = {
        "sr_dist": float(np.clip(sr_dist, -10, 10)),
        "sr_sweep": sr_sweep,
        "sr_room": float(np.clip(sr_room, -10, 10)),
        "pw_dist": float(np.clip(pw_dist, -10, 10)),
        "pw_sweep": pw_sweep,
        "pw_pos": float(np.clip(pw_pos, -3, 3)),
        "orb_near": float(np.clip(orb_near, 0, 10)),
        "orb_state": float(np.clip(orb_state, -10, 10)),
        "orb_reclaim": orb_reclaim,
        "fvg_dist": float(np.clip(fvg_dist, -10, 10)),
        "fvg_touch": fvg_touch,
        "fib_dist": float(np.clip(fib_dist, -10, 10)),
        "fib_touch": fib_touch,
        "body_align": float(np.clip(body_align, -10, 10)),
        "reject_wick": float(np.clip(reject_wick, 0, 10)),
    }
    eligible = (
        abs(vals["sr_dist"]) <= 0.35
        or abs(vals["pw_dist"]) <= 0.35
        or vals["orb_near"] <= 0.35
        or vals["fvg_touch"] > 0
        or vals["fib_touch"] > 0
        or vals["sr_sweep"] > 0
        or vals["pw_sweep"] > 0
    )
    vals["eligible"] = bool(eligible)
    return vals


def scan_indices(x, w):
    ck_t = w + pd.Timedelta(days=4, hours=12)
    ck = x.index.get_indexer([ck_t])
    if len(ck) == 0 or ck[0] < 0:
        return []
    a = int(x.index.searchsorted(w, side="left"))
    return list(range(a, int(ck[0]) + 1))


def build_partition_rows(x, tf, weeks, part):
    hold = 12 if tf == "H1" else 6
    rows = []
    for w in weeks:
        idxs = scan_indices(x, w)
        for i in idxs:
            if i + 1 >= len(x):
                continue
            for side in ("LONG", "SHORT"):
                f = feature_row(x, i, tf, side)
                if f is None:
                    continue
                tr = b8.execute(x, i, side, hold)
                if tr is None:
                    continue
                row = {
                    "partition": part,
                    "tf": tf,
                    "week": b8.week_key(w),
                    "week_start": w,
                    "signal_ts": x.index[i],
                    "signal_idx": i,
                    "side": side,
                    "eligible": f.pop("eligible"),
                    "net_positive": int(float(tr["net_ret"]) > 0),
                }
                row.update(f)
                row.update(tr)
                rows.append(row)
    return pd.DataFrame(rows)


def fit_model(dev):
    model = Pipeline([
        ("scale", StandardScaler()),
        ("lr", LogisticRegression(
            penalty="l2",
            C=0.5,
            solver="liblinear",
            max_iter=2000,
            random_state=20260821,
        )),
    ])
    model.fit(dev[FEATURES].to_numpy(float), dev.net_positive.to_numpy(int))
    return model


def score_rows(model, z):
    q = z.copy()
    if q.empty:
        q["prob"] = []
        return q
    q["prob"] = model.predict_proba(q[FEATURES].to_numpy(float))[:, 1]
    return q


def calibrate_threshold(dev_scored, weeks_total):
    best = (
        dev_scored.sort_values(["signal_ts", "prob"], ascending=[True, False])
        .groupby("signal_ts", as_index=False)
        .head(1)
    )
    elig = best[best.eligible].copy()
    m = len(elig)
    if m == 0 or weeks_total == 0:
        raise RuntimeError("no eligible development bars for threshold calibration")
    q = max(0.0, 1.0 - float(weeks_total) / float(m))
    threshold = float(np.quantile(elig.prob.to_numpy(float), q))
    return threshold, q, m


def select_weekly(scored, threshold, weeks):
    rows = []
    for w in weeks:
        wk = scored[scored.week == b8.week_key(w)].copy()
        if wk.empty:
            continue
        chosen = None
        route = None
        for _, g in wk.sort_values(["signal_ts", "prob"], ascending=[True, False]).groupby("signal_ts", sort=True):
            top = g.sort_values("prob", ascending=False).iloc[0]
            if bool(top.eligible) and float(top.prob) >= threshold:
                chosen = top
                route = "MODEL_TRIGGER"
                break
        if chosen is None:
            last_ts = wk.signal_ts.max()
            g = wk[wk.signal_ts == last_ts]
            if g.empty:
                continue
            chosen = g.sort_values("prob", ascending=False).iloc[0]
            route = "FORCED_FALLBACK"
        r = chosen.to_dict()
        r["route"] = route
        r["threshold"] = threshold
        rows.append(r)
    return pd.DataFrame(rows)


def stat(z, weeks_total):
    if z.empty:
        return {
            "weeks_total": int(weeks_total), "n": 0, "coverage": 0.0,
            "wins": 0, "losses": 0, "wr": None, "decisive_wr": None,
            "tp": 0, "sl": 0, "time": 0, "exp": None, "pf": None,
            "max_losing_streak": 0, "model_trigger": 0, "fallback": 0,
        }
    a = z.net_ret.to_numpy(float)
    pos = a > 0
    gp = float(a[pos].sum())
    gl = float(-a[~pos].sum())
    tp = int((z.reason == "TP").sum())
    sl = int((z.reason == "SL").sum())
    tm = int((z.reason == "TIME").sum())
    dec = tp + sl
    streak = mx = 0
    for v in a:
        if v <= 0:
            streak += 1
            mx = max(mx, streak)
        else:
            streak = 0
    return {
        "weeks_total": int(weeks_total),
        "n": int(len(z)),
        "coverage": float(z.week.nunique() / weeks_total) if weeks_total else 0.0,
        "wins": int(pos.sum()),
        "losses": int((~pos).sum()),
        "wr": float(pos.mean()),
        "decisive_wr": float(tp / dec) if dec else None,
        "tp": tp, "sl": sl, "time": tm,
        "exp": float(a.mean()),
        "pf": float(gp / gl) if gl > 0 else (999.0 if gp > 0 else 0.0),
        "max_losing_streak": int(mx),
        "model_trigger": int((z.route == "MODEL_TRIGGER").sum()),
        "fallback": int((z.route == "FORCED_FALLBACK").sum()),
    }


def blocks(z):
    if z.empty:
        return []
    q = z.sort_values("entry_ts").reset_index(drop=True)
    edges = np.linspace(0, len(q), 5, dtype=int)
    out = []
    for i in range(4):
        b = q.iloc[edges[i]:edges[i + 1]]
        s = stat(b, max(1, b.week.nunique()))
        s["block"] = f"B{i+1}"
        out.append(s)
    return out


def positive_blocks(bl):
    return sum(1 for b in bl if b.get("exp") is not None and b["exp"] > 0)


def pct(v):
    return "-" if v is None else f"{100.0 * float(v):.2f}%"


def num(v, n=3):
    return "-" if v is None else f"{float(v):.{n}f}"


def main():
    raw = dataio.load_1h().copy()
    raw["ts"] = pd.to_datetime(raw.ts, utc=True)
    raw = raw.sort_values("ts").drop_duplicates("ts")
    k = raw.set_index("ts")[["open", "high", "low", "close"]]
    data_end = raw.ts.max() + pd.Timedelta(hours=1)

    parts = {
        "external": (EXT0, EXT1),
        "development": (DEV0, DEV1),
        "reference_validation": (VAL0, VAL1),
        "august": (AUG0, data_end),
    }

    result = {
        "protocol": "BTC_WEEKLY_ENTRYMAP_B9",
        "implementation_revision": IMPLEMENTATION_REVISION,
        "coverage": {
            "first": str(raw.ts.min()),
            "last": str(raw.ts.max()),
            "h1_rows": int(len(raw)),
        },
        "fee": FEE,
        "timeframes": {},
        "robust_weekly_100": [],
        "high_precision_weekly": [],
        "live_bbc_untouched": True,
    }
    selected_all = []
    coef_all = []

    for tf in ("H1", "H4"):
        x = add_previous_week_levels(b8.prep(k, tf))
        rows_by_part = {}
        weeks_by_part = {}
        for name, (a, b) in parts.items():
            weeks = b8.complete_weeks(a, b)
            weeks_by_part[name] = weeks
            rows_by_part[name] = build_partition_rows(x, tf, weeks, name)

        dev = rows_by_part["development"]
        if dev.empty or dev.net_positive.nunique() < 2:
            raise RuntimeError(f"invalid B9 development sample for {tf}")
        model = fit_model(dev)
        scored = {name: score_rows(model, z) for name, z in rows_by_part.items()}
        threshold, quantile, eligible_m = calibrate_threshold(
            scored["development"], len(weeks_by_part["development"])
        )

        lr = model.named_steps["lr"]
        coefs = lr.coef_[0]
        for feature, coef in zip(FEATURES, coefs):
            coef_all.append({"tf": tf, "feature": feature, "coef_standardized": float(coef)})

        tf_result = {
            "threshold": threshold,
            "threshold_quantile": quantile,
            "development_eligible_bars": int(eligible_m),
            "training_rows": int(len(dev)),
            "training_positive_rate": float(dev.net_positive.mean()),
            "partitions": {},
            "blocks": {},
            "losing_weeks": {},
        }

        for name in parts:
            sel = select_weekly(scored[name], threshold, weeks_by_part[name])
            if not sel.empty:
                selected_all.append(sel)
            s = stat(sel, len(weeks_by_part[name]))
            bl = blocks(sel)
            tf_result["partitions"][name] = s
            tf_result["blocks"][name] = bl
            tf_result["losing_weeks"][name] = (
                [] if sel.empty else sel.loc[sel.net_ret <= 0, "week"].tolist()
            )

        e = tf_result["partitions"]["external"]
        v = tf_result["partitions"]["reference_validation"]
        eb = tf_result["blocks"]["external"]
        vb = tf_result["blocks"]["reference_validation"]
        common = (
            e["coverage"] == 1.0 and v["coverage"] == 1.0
            and e["n"] >= 20 and v["n"] >= 20
        )
        if (
            common and e["wr"] == 1.0 and v["wr"] == 1.0
            and e["exp"] > 0 and v["exp"] > 0
            and e["pf"] > 1 and v["pf"] > 1
            and positive_blocks(eb) == 4 and positive_blocks(vb) == 4
        ):
            result["robust_weekly_100"].append(tf)
        if (
            common and e["wr"] >= 0.80 and v["wr"] >= 0.80
            and e["exp"] > 0 and v["exp"] > 0
            and e["pf"] > 1 and v["pf"] > 1
            and e["max_losing_streak"] <= 2 and v["max_losing_streak"] <= 2
            and positive_blocks(eb) >= 3 and positive_blocks(vb) >= 3
        ):
            result["high_precision_weekly"].append(tf)

        result["timeframes"][tf] = tf_result

    result["verdict"] = (
        "B9_ROBUST_WEEKLY_100_PASS" if result["robust_weekly_100"]
        else "B9_HIGH_PRECISION_WEEKLY_PASS" if result["high_precision_weekly"]
        else "B9_NO_ROBUST_WEEKLY_100"
    )

    if selected_all:
        pd.concat(selected_all, ignore_index=True).sort_values(
            ["tf", "partition", "entry_ts"]
        ).to_csv(OUTC, index=False)
    pd.DataFrame(coef_all).to_csv(OUTCOEF, index=False)
    OUTJ.write_text(json.dumps(result, indent=2, default=str) + "\n")

    md = [
        "# BTC Weekly Entry Map B9 — Result",
        "",
        f"**Verdict: {result['verdict']}**",
        "",
        f"Implementation revision **{IMPLEMENTATION_REVISION}**.",
        "",
        f"Coverage **{result['coverage']['first']} -> {result['coverage']['last']}**, official H1 rows **{result['coverage']['h1_rows']:,}**.",
        "",
        "Development-only structural probability model; chronological first threshold crossing; forced Friday fallback; next-open execution; fee 0.15%; modeled net RR 1:1; adverse-first.",
        "",
        "| TF | Threshold | Partition | Weeks/N/Coverage | Trigger/Fallback | TP/SL/TIME | WR | Decisive WR | Exp | PF | Max LS |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    order = ["development", "reference_validation", "external", "august"]
    for tf in ("H1", "H4"):
        tr = result["timeframes"][tf]
        for part in order:
            s = tr["partitions"][part]
            md.append(
                f"| {tf} | {tr['threshold']:.4f} | {part} | "
                f"{s['weeks_total']} / {s['n']} / {100*s['coverage']:.1f}% | "
                f"{s['model_trigger']} / {s['fallback']} | "
                f"{s['tp']}/{s['sl']}/{s['time']} | {pct(s['wr'])} | {pct(s['decisive_wr'])} | "
                f"{pct(s['exp'])} | {num(s['pf'])} | {s['max_losing_streak']} |"
            )
        md += [
            "",
            f"## {tf} calibration",
            "",
            f"- Training rows: **{tr['training_rows']:,}**",
            f"- Training positive rate: **{pct(tr['training_positive_rate'])}**",
            f"- Structurally eligible development bars: **{tr['development_eligible_bars']:,}**",
            f"- Threshold quantile: **{tr['threshold_quantile']:.6f}**",
            f"- Frozen probability threshold: **{tr['threshold']:.6f}**",
        ]
        md += ["", f"## {tf} losing weeks"]
        for part in ("reference_validation", "external"):
            lw = tr["losing_weeks"][part]
            tail = "none" if not lw else ", ".join(lw[:40])
            md.append(f"- {part}: **{len(lw)}** losing weeks — {tail}")

    md += [
        "",
        "## Gates",
        "",
        f"- `B9_ROBUST_WEEKLY_100`: **{'PASS' if result['robust_weekly_100'] else 'FAIL'}**",
        f"- `B9_HIGH_PRECISION_WEEKLY`: **{'PASS' if result['high_precision_weekly'] else 'FAIL'}**",
        f"- Robust 100% timeframes: **{', '.join(result['robust_weekly_100']) if result['robust_weekly_100'] else 'none'}**",
        f"- High-precision timeframes: **{', '.join(result['high_precision_weekly']) if result['high_precision_weekly'] else 'none'}**",
        "",
        "Frozen preregistration honored. No post-result model/threshold/feature/RR/hold/fallback rescue. Live BBC untouched.",
        "",
    ]
    OUTM.write_text("\n".join(md))
    print(OUTM.read_text())


if __name__ == "__main__":
    main()
