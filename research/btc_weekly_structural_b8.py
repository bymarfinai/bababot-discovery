#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import pandas as pd
import btc_h1_low_reject_structure_lr1 as dataio

ROOT = Path(__file__).resolve().parent.parent
OUTJ = ROOT / "BTC_WEEKLY_STRUCTURAL_B8_Result.json"
OUTM = ROOT / "BTC_WEEKLY_STRUCTURAL_B8_Result.md"
OUTC = ROOT / "BTC_WEEKLY_STRUCTURAL_B8_Selected.csv"
FEE = 0.0015
VARIANTS = {"CONF2_FORCED": 2, "CONF3_FORCED": 3}

EXT0 = pd.Timestamp("2020-01-01", tz="UTC")
EXT1 = pd.Timestamp("2022-01-01", tz="UTC")
DEV0 = pd.Timestamp("2022-01-01", tz="UTC")
DEV1 = pd.Timestamp("2025-01-01", tz="UTC")
VAL0 = pd.Timestamp("2025-01-01", tz="UTC")
VAL1 = pd.Timestamp("2026-07-30", tz="UTC")
AUG0 = pd.Timestamp("2026-08-01", tz="UTC")


def as_utc(v):
    t = pd.Timestamp(v)
    if t.tzinfo is None:
        return t.tz_localize("UTC")
    return t.tz_convert("UTC")


def prep(k, tf):
    x = k[["open", "high", "low", "close"]].copy()
    if tf == "H4":
        x = x.resample(
            "4h", origin="start_day", label="left", closed="left"
        ).agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        ).dropna()

    pc = x.close.shift(1)
    tr = pd.concat(
        [x.high - x.low, (x.high - pc).abs(), (x.low - pc).abs()], axis=1
    ).max(axis=1)
    x["atr"] = tr.rolling(14, min_periods=14).mean()
    x["hi20"] = x.high.shift(1).rolling(20, min_periods=20).max()
    x["lo20"] = x.low.shift(1).rolling(20, min_periods=20).min()
    x["mid20"] = (x.hi20 + x.lo20) / 2.0

    day_key = pd.Series(x.index.floor("D"), index=x.index)
    if tf == "H1":
        or_mask = (x.index.hour >= 0) & (x.index.hour < 4)
    else:
        or_mask = x.index.hour == 0
    x["or_hi"] = x.high.where(or_mask).groupby(day_key).transform("max")
    x["or_lo"] = x.low.where(or_mask).groupby(day_key).transform("min")
    return x.dropna(subset=["atr", "hi20", "lo20", "mid20"])


def orb_vote(x, i, tf):
    if i < 1:
        return None
    t = x.index[i]
    pt = x.index[i - 1]
    if t.floor("D") != pt.floor("D"):
        return None
    if tf == "H1" and t.hour < 5:
        return None
    if tf == "H4" and t.hour < 8:
        return None

    p = x.iloc[i - 1]
    b = x.iloc[i]
    oh, ol = float(b.or_hi), float(b.or_lo)
    if not np.isfinite(oh) or not np.isfinite(ol):
        return None

    if float(p.close) > oh and float(b.low) <= oh and float(b.close) > oh:
        return "LONG"
    if float(p.close) < ol and float(b.high) >= ol and float(b.close) < ol:
        return "SHORT"
    return None


def sr_vote(x, i):
    b = x.iloc[i]
    atr = float(b.atr)
    if not np.isfinite(atr) or atr <= 0:
        return None
    sup, res = float(b.lo20), float(b.hi20)
    tol = 0.15 * atr
    o, h, l, c = map(float, (b.open, b.high, b.low, b.close))
    body = max(abs(c - o), 1e-12)
    lower_wick = max(0.0, min(o, c) - l)
    upper_wick = max(0.0, h - max(o, c))

    long_ok = (
        l <= sup + tol
        and c >= sup
        and c > o
        and lower_wick >= 0.5 * body
    )
    short_ok = (
        h >= res - tol
        and c <= res
        and c < o
        and upper_wick >= 0.5 * body
    )
    if long_ok and not short_ok:
        return "LONG"
    if short_ok and not long_ok:
        return "SHORT"
    return None


def latest_fvg(x, i):
    lo = max(2, i - 12)
    for j in range(i - 1, lo - 1, -1):
        a = x.iloc[j - 2]
        c = x.iloc[j]

        if float(c.low) > float(a.high):
            zlo, zhi = float(a.high), float(c.low)
            prior = x.iloc[j + 1 : i]
            if len(prior) and float(prior.low.min()) <= zlo:
                continue
            return ("LONG", zlo, zhi)

        if float(c.high) < float(a.low):
            zlo, zhi = float(c.high), float(a.low)
            prior = x.iloc[j + 1 : i]
            if len(prior) and float(prior.high.max()) >= zhi:
                continue
            return ("SHORT", zlo, zhi)
    return None


def fvg_vote(x, i):
    g = latest_fvg(x, i)
    if g is None:
        return None
    side, zlo, zhi = g
    b = x.iloc[i]
    o, h, l, c = map(float, (b.open, b.high, b.low, b.close))
    mid = (zlo + zhi) / 2.0
    touched = l <= zhi and h >= zlo
    if side == "LONG" and touched and c > mid and c > o:
        return "LONG"
    if side == "SHORT" and touched and c < mid and c < o:
        return "SHORT"
    return None


def fib_vote(x, i):
    if i < 12:
        return None
    w = x.iloc[i - 12 : i]
    b = x.iloc[i]
    atr = float(b.atr)
    if not np.isfinite(atr) or atr <= 0:
        return None

    hi_pos = int(np.argmax(w.high.to_numpy(dtype=float)))
    lo_pos = int(np.argmin(w.low.to_numpy(dtype=float)))
    hi = float(w.high.iloc[hi_pos])
    lo = float(w.low.iloc[lo_pos])
    rng = hi - lo
    if rng < 2.0 * atr:
        return None

    o, h, l, c = map(float, (b.open, b.high, b.low, b.close))
    if lo_pos < hi_pos:
        zlo = hi - 0.618 * rng
        zhi = hi - 0.500 * rng
        if l <= zhi and h >= zlo and c > o and c >= zhi:
            return "LONG"
    elif hi_pos < lo_pos:
        zlo = lo + 0.500 * rng
        zhi = lo + 0.618 * rng
        if l <= zhi and h >= zlo and c < o and c <= zlo:
            return "SHORT"
    return None


def votes_at(x, i, tf):
    votes = {
        "ORB": orb_vote(x, i, tf),
        "SR": sr_vote(x, i),
        "FVG": fvg_vote(x, i),
        "FIB": fib_vote(x, i),
    }
    longs = [name for name, side in votes.items() if side == "LONG"]
    shorts = [name for name, side in votes.items() if side == "SHORT"]
    if len(longs) > len(shorts):
        return votes, "LONG", len(longs), longs, shorts
    if len(shorts) > len(longs):
        return votes, "SHORT", len(shorts), longs, shorts
    return votes, None, len(longs), longs, shorts


def week_key(w):
    iso = w.isocalendar()
    return f"{int(iso.year):04d}-W{int(iso.week):02d}"


def complete_weeks(start, end_exclusive):
    start = as_utc(start)
    end = as_utc(end_exclusive)
    first = start.floor("D") - pd.Timedelta(days=start.weekday())
    if first < start:
        first += pd.Timedelta(days=7)
    out = []
    w = first
    while w + pd.Timedelta(days=7) <= end:
        out.append(w)
        w += pd.Timedelta(days=7)
    return out


def checkpoint_index(x, w):
    target = w + pd.Timedelta(days=4, hours=12)
    loc = x.index.get_indexer([target])
    return int(loc[0]) if len(loc) and loc[0] >= 0 else None


def route_week(x, tf, w, conf):
    ck = checkpoint_index(x, w)
    if ck is None or ck + 1 >= len(x):
        return None

    start_loc = int(x.index.searchsorted(w, side="left"))
    for i in range(start_loc, ck + 1):
        if i + 1 >= len(x):
            break
        votes, side, count, longs, shorts = votes_at(x, i, tf)
        if side is not None and count >= conf:
            return {
                "signal_idx": i,
                "side": side,
                "route": "CONFLUENCE",
                "vote_count": count,
                "votes": votes,
                "long_votes": ",".join(longs),
                "short_votes": ",".join(shorts),
            }

    votes, side, count, longs, shorts = votes_at(x, ck, tf)
    if side is None:
        b = x.iloc[ck]
        side = "SHORT" if float(b.close) > float(b.mid20) else "LONG"
    return {
        "signal_idx": ck,
        "side": side,
        "route": "FALLBACK",
        "vote_count": count,
        "votes": votes,
        "long_votes": ",".join(longs),
        "short_votes": ",".join(shorts),
    }


def execute(x, signal_idx, side, hold):
    entry_idx = signal_idx + 1
    if entry_idx >= len(x):
        return None

    sig = x.iloc[signal_idx]
    entry = float(x.iloc[entry_idx].open)
    atr = float(sig.atr)
    if not np.isfinite(entry) or not np.isfinite(atr) or entry <= 0 or atr <= 0:
        return None

    risk_frac = atr / entry
    reward_frac = risk_frac + 2.0 * FEE
    if side == "LONG":
        sl = entry - atr
        tp = entry * (1.0 + reward_frac)
    else:
        sl = entry + atr
        tp = entry * (1.0 - reward_frac)

    fut = x.iloc[entry_idx : entry_idx + hold]
    if len(fut) < hold:
        return None

    px = float(fut.iloc[-1].close)
    exit_ts = fut.index[-1]
    reason = "TIME"
    for t, b in fut.iterrows():
        if side == "LONG":
            hit_sl = float(b.low) <= sl
            hit_tp = float(b.high) >= tp
        else:
            hit_sl = float(b.high) >= sl
            hit_tp = float(b.low) <= tp
        if hit_sl:
            px, exit_ts, reason = sl, t, "SL"
            break
        if hit_tp:
            px, exit_ts, reason = tp, t, "TP"
            break

    gross = (px / entry - 1.0) * (1.0 if side == "LONG" else -1.0)
    return {
        "entry_ts": x.index[entry_idx],
        "exit_ts": exit_ts,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "risk_frac": risk_frac,
        "net_ret": gross - FEE,
        "reason": reason,
    }


def stat(df, weeks_total):
    if df.empty:
        return {
            "weeks_total": weeks_total,
            "n": 0,
            "coverage": 0.0,
            "wins": 0,
            "losses": 0,
            "wr": None,
            "decisive_wr": None,
            "tp": 0,
            "sl": 0,
            "time": 0,
            "exp": None,
            "pf": None,
            "max_losing_streak": 0,
            "confluence": 0,
            "fallback": 0,
        }

    a = df.net_ret.to_numpy(dtype=float)
    positive = a > 0
    gp = float(a[positive].sum())
    gl = float(-a[~positive].sum())
    tp_n = int((df.reason == "TP").sum())
    sl_n = int((df.reason == "SL").sum())
    time_n = int((df.reason == "TIME").sum())
    decisive_n = tp_n + sl_n

    streak = max_streak = 0
    for v in a:
        if v <= 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return {
        "weeks_total": int(weeks_total),
        "n": int(len(df)),
        "coverage": float(df.week.nunique() / weeks_total) if weeks_total else 0.0,
        "wins": int(positive.sum()),
        "losses": int((~positive).sum()),
        "wr": float(positive.mean()),
        "decisive_wr": float(tp_n / decisive_n) if decisive_n else None,
        "tp": tp_n,
        "sl": sl_n,
        "time": time_n,
        "exp": float(a.mean()),
        "pf": float(gp / gl) if gl > 0 else (999.0 if gp > 0 else 0.0),
        "max_losing_streak": int(max_streak),
        "confluence": int((df.route == "CONFLUENCE").sum()),
        "fallback": int((df.route == "FALLBACK").sum()),
    }


def blocks(df):
    if df.empty:
        return []
    z = df.sort_values("entry_ts").reset_index(drop=True)
    edges = np.linspace(0, len(z), 5, dtype=int)
    out = []
    for i in range(4):
        q = z.iloc[edges[i] : edges[i + 1]]
        out.append(stat(q, max(1, q.week.nunique())))
    return out


def run_partition(x, tf, variant, conf, part, weeks):
    hold = 12 if tf == "H1" else 6
    rows = []
    for w in weeks:
        route = route_week(x, tf, w, conf)
        if route is None:
            continue
        trade = execute(x, route["signal_idx"], route["side"], hold)
        if trade is None:
            continue
        row = {
            "partition": part,
            "tf": tf,
            "variant": variant,
            "week": week_key(w),
            "week_start": w,
            "signal_ts": x.index[route["signal_idx"]],
            "side": route["side"],
            "route": route["route"],
            "vote_count": route["vote_count"],
            "long_votes": route["long_votes"],
            "short_votes": route["short_votes"],
            "votes_json": json.dumps(route["votes"], sort_keys=True),
        }
        row.update(trade)
        rows.append(row)
    return pd.DataFrame(rows)


def fmt_pct(v):
    return "-" if v is None else f"{100 * float(v):.2f}%"


def fmt_exp(v):
    return "-" if v is None else f"{100 * float(v):.3f}%"


def fmt_pf(v):
    return "-" if v is None else f"{float(v):.3f}"


def main():
    raw = dataio.load_1h().copy()
    raw["ts"] = pd.to_datetime(raw.ts, utc=True)
    raw = raw.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    k = raw.set_index("ts")[["open", "high", "low", "close"]].copy()

    data_end = raw.ts.max() + pd.Timedelta(hours=1)
    aug_end = min(data_end, pd.Timestamp("2026-09-01", tz="UTC"))
    parts = {
        "external": (EXT0, EXT1),
        "development": (DEV0, DEV1),
        "reference_validation": (VAL0, VAL1),
        "august": (AUG0, aug_end),
    }
    xmap = {"H1": prep(k, "H1"), "H4": prep(k, "H4")}

    all_rows = []
    results = []
    for tf, x in xmap.items():
        for variant, conf in VARIANTS.items():
            for part, (start, end) in parts.items():
                weeks = complete_weeks(start, end)
                df = run_partition(x, tf, variant, conf, part, weeks)
                if not df.empty:
                    all_rows.append(df)
                s = stat(df, len(weeks))
                losing_weeks = (
                    [] if df.empty else df.loc[df.net_ret <= 0, "week"].tolist()
                )
                results.append(
                    {
                        "tf": tf,
                        "variant": variant,
                        "partition": part,
                        "stats": s,
                        "blocks": blocks(df),
                        "losing_weeks": losing_weeks,
                    }
                )

    selected = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    if not selected.empty:
        selected = selected.sort_values(
            ["tf", "variant", "partition", "entry_ts"]
        ).reset_index(drop=True)
        selected.to_csv(OUTC, index=False)

    def get(tf, variant, part):
        for r in results:
            if (
                r["tf"] == tf
                and r["variant"] == variant
                and r["partition"] == part
            ):
                return r["stats"]
        return None

    robust = []
    high_precision = []
    for tf in ["H1", "H4"]:
        for variant in VARIANTS:
            e = get(tf, variant, "external")
            v = get(tf, variant, "reference_validation")
            if not e or not v:
                continue
            common_cov = e["coverage"] == 1.0 and v["coverage"] == 1.0
            common_n = e["n"] >= 20 and v["n"] >= 20
            if (
                common_cov
                and common_n
                and e["wr"] == 1.0
                and v["wr"] == 1.0
                and e["exp"] > 0
                and v["exp"] > 0
                and e["pf"] > 1
                and v["pf"] > 1
            ):
                robust.append({"tf": tf, "variant": variant})
            if (
                common_cov
                and common_n
                and e["wr"] >= 0.80
                and v["wr"] >= 0.80
                and e["exp"] > 0
                and v["exp"] > 0
                and e["pf"] > 1
                and v["pf"] > 1
                and e["max_losing_streak"] <= 2
                and v["max_losing_streak"] <= 2
            ):
                high_precision.append({"tf": tf, "variant": variant})

    verdict = (
        "B8_ROBUST_WEEKLY_100_PASS"
        if robust
        else (
            "B8_HIGH_PRECISION_WEEKLY_PASS"
            if high_precision
            else "B8_NO_ROBUST_WEEKLY_100"
        )
    )
    out = {
        "protocol": "BTC_WEEKLY_STRUCTURAL_B8",
        "coverage": {
            "first": str(raw.ts.min()),
            "last": str(raw.ts.max()),
            "h1_rows": int(len(raw)),
        },
        "fee": FEE,
        "robust_weekly_100": robust,
        "high_precision_weekly": high_precision,
        "verdict": verdict,
        "results": results,
        "guardrail": "Frozen B8 only; live BBC untouched; no post-result rescue.",
    }
    OUTJ.write_text(json.dumps(out, indent=2, default=str) + "\n")

    md = [
        "# BTC Weekly Structural Confluence B8 — Result",
        "",
        f"**Verdict: {verdict}**",
        "",
        (
            f"Coverage **{raw.ts.min()} -> {raw.ts.max()}**, official H1 rows "
            f"**{len(raw):,}**. Fee **{100 * FEE:.2f}%** round trip; modeled "
            "net RR **1:1**; adverse-first. Maximum one trade per complete ISO "
            "week; fixed Friday fallback is used when no earlier confluence exists."
        ),
        "",
        "| TF | Variant | Partition | Weeks/N/Coverage | Confluence/Fallback | TP/SL/TIME | WR | Decisive WR | Exp | PF | Max LS |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    order = ["development", "reference_validation", "external", "august"]
    for tf in ["H1", "H4"]:
        for variant in VARIANTS:
            for part in order:
                s = get(tf, variant, part)
                if s is None:
                    continue
                md.append(
                    f"| {tf} | {variant} | {part} | "
                    f"{s['weeks_total']} / {s['n']} / {100 * s['coverage']:.1f}% | "
                    f"{s['confluence']} / {s['fallback']} | "
                    f"{s['tp']}/{s['sl']}/{s['time']} | {fmt_pct(s['wr'])} | "
                    f"{fmt_pct(s['decisive_wr'])} | {fmt_exp(s['exp'])} | "
                    f"{fmt_pf(s['pf'])} | {s['max_losing_streak']} |"
                )

    md += ["", "## Losing weeks", ""]
    for r in results:
        if r["partition"] not in ("external", "reference_validation"):
            continue
        lw = r["losing_weeks"]
        suffix = f" — {', '.join(lw[:30])}" if lw else ""
        md.append(
            f"- {r['tf']} / {r['variant']} / {r['partition']}: "
            f"{len(lw)} losing weeks{suffix}"
        )

    md += [
        "",
        "## Gates",
        "",
        f"- `B8_ROBUST_WEEKLY_100`: **{'PASS' if robust else 'FAIL'}**",
        (
            f"- `B8_HIGH_PRECISION_WEEKLY`: "
            f"**{'PASS' if high_precision else 'FAIL'}**"
        ),
    ]
    if robust:
        md.append(f"- Robust 100% cells: `{robust}`")
    if high_precision:
        md.append(f"- High-precision cells: `{high_precision}`")
    md += [
        "",
        "Frozen preregistration honored. No post-result threshold/session/Fib/FVG/ORB/RR/hold rescue. Live BBC untouched.",
        "",
    ]
    OUTM.write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
