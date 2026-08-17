#!/usr/bin/env python3
"""S6.1 — Saturday Pre-Entry Causal Direction Feature Atlas.

Research only; live BBC untouched. No classifier or trading rule is created.

Purpose
-------
Test whether frozen static BUY-vs-SHORT economic preference can be separated
using ONLY information available before Saturday 18:00 WIB / 11:00 UTC entry.

Frozen outcome labels (hindsight targets only):
- SHORT_BETTER: mirrored static SHORT PnL > frozen static BUY PnL.
- Outcome taxonomy: BUY_ONLY_WIN / SHORT_ONLY_WIN / BOTH_LOSE / BOTH_WIN.

All features end at the last completed 5m candle before entry (10:55 UTC).
No post-entry state, no +0.50 label, no threshold sweep, no classifier.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s60_saturday_dynamic_direction_oracle as s60

OUT = Path(os.getenv("S61_OUT", "s61_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83

FEATURES = [
    "ret15", "ret30", "ret60", "ret120", "ret240", "ret480", "ret1440",
    "ema7_dist", "ema20_dist", "ema7_20_spread",
    "ema7_slope15", "ema7_slope60", "ema20_slope60", "ema20_slope240",
    "loc_1h", "loc_4h", "loc_24h",
    "dist_1h_high", "dist_1h_low", "dist_4h_high", "dist_4h_low",
    "rv1h", "rv4h", "rv24h",
    "taker15", "taker60", "taker240",
    "posbar_frac60", "posbar_frac240",
    "volume_ratio_1h_24h",
    "last_body_ratio", "last_upper_wick_ratio", "last_lower_wick_ratio", "last_close_location",
]

BINARY = [
    "ret60_pos", "ret240_pos", "ret1440_pos",
    "above_ema7", "above_ema20", "ema7_above20",
    "ema20_slope60_pos", "ema20_slope240_pos",
    "taker60_pos", "taker240_pos",
    "last_bull", "last_top_quartile", "last_bottom_quartile",
    "last_upper_wick_dom", "last_lower_wick_dom",
]


def rank_auc(y, score):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    m = np.isfinite(score)
    y, score = y[m], score[m]
    n1 = int(y.sum()); n0 = int(len(y) - n1)
    if n1 == 0 or n0 == 0:
        return np.nan
    ranks = pd.Series(score).rank(method="average").to_numpy()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def ret_from(k, done, minutes):
    old = done - pd.Timedelta(minutes=minutes)
    if old not in k.index:
        return np.nan
    a = float(k.loc[old, "close"]); b = float(k.loc[done, "close"])
    return b / a - 1.0 if a else np.nan


def ema_slope(k, done, col, minutes):
    old = done - pd.Timedelta(minutes=minutes)
    if old not in k.index:
        return np.nan
    a = float(k.loc[old, col]); b = float(k.loc[done, col])
    return b / a - 1.0 if a else np.nan


def window(k, t, minutes):
    w = k[(k.index >= t - pd.Timedelta(minutes=minutes)) & (k.index < t)]
    expected = minutes // 5
    if len(w) != expected:
        raise RuntimeError(f"bad pre-window {minutes}m at {t}: {len(w)} != {expected}")
    return w


def range_loc(close, w):
    lo = float(w.low.min()); hi = float(w.high.max())
    return (close - lo) / (hi - lo) if hi > lo else 0.5


def rv(w):
    c = w.close.astype(float).to_numpy()
    if len(c) < 2:
        return np.nan
    lr = np.diff(np.log(c))
    return float(np.sqrt(np.sum(lr * lr)))


def candle_morph(row):
    o, h, l, c = map(float, [row.open, row.high, row.low, row.close])
    rg = h - l
    if rg <= 0:
        return {"body": 0.0, "uw": 0.0, "lw": 0.0, "cl": 0.5}
    body = abs(c - o) / rg
    uw = (h - max(o, c)) / rg
    lw = (min(o, c) - l) / rg
    cl = (c - l) / rg
    return {"body": body, "uw": uw, "lw": lw, "cl": cl}


def pre_features(k, t):
    done = t - pd.Timedelta(minutes=5)
    last = k.loc[done]
    close = float(last.close)
    w15 = window(k, t, 15)
    w60 = window(k, t, 60)
    w240 = window(k, t, 240)
    w1440 = window(k, t, 1440)
    m = candle_morph(last)

    qv60 = float(w60.quote_volume.sum())
    qv24 = float(w1440.quote_volume.sum())
    hourly_baseline = qv24 / 24.0 if qv24 > 0 else np.nan

    f = {
        "ret15": ret_from(k, done, 15),
        "ret30": ret_from(k, done, 30),
        "ret60": ret_from(k, done, 60),
        "ret120": ret_from(k, done, 120),
        "ret240": ret_from(k, done, 240),
        "ret480": ret_from(k, done, 480),
        "ret1440": ret_from(k, done, 1440),
        "ema7_dist": close / float(last.ema7) - 1.0,
        "ema20_dist": close / float(last.ema20) - 1.0,
        "ema7_20_spread": float(last.ema7) / float(last.ema20) - 1.0,
        "ema7_slope15": ema_slope(k, done, "ema7", 15),
        "ema7_slope60": ema_slope(k, done, "ema7", 60),
        "ema20_slope60": ema_slope(k, done, "ema20", 60),
        "ema20_slope240": ema_slope(k, done, "ema20", 240),
        "loc_1h": range_loc(close, w60),
        "loc_4h": range_loc(close, w240),
        "loc_24h": range_loc(close, w1440),
        "dist_1h_high": close / float(w60.high.max()) - 1.0,
        "dist_1h_low": close / float(w60.low.min()) - 1.0,
        "dist_4h_high": close / float(w240.high.max()) - 1.0,
        "dist_4h_low": close / float(w240.low.min()) - 1.0,
        "rv1h": rv(w60), "rv4h": rv(w240), "rv24h": rv(w1440),
        "taker15": float(np.nanmean(w15.taker_imb.to_numpy(dtype=float))),
        "taker60": float(np.nanmean(w60.taker_imb.to_numpy(dtype=float))),
        "taker240": float(np.nanmean(w240.taker_imb.to_numpy(dtype=float))),
        "posbar_frac60": float((w60.close.astype(float) > w60.open.astype(float)).mean()),
        "posbar_frac240": float((w240.close.astype(float) > w240.open.astype(float)).mean()),
        "volume_ratio_1h_24h": qv60 / hourly_baseline if np.isfinite(hourly_baseline) and hourly_baseline > 0 else np.nan,
        "last_body_ratio": m["body"], "last_upper_wick_ratio": m["uw"],
        "last_lower_wick_ratio": m["lw"], "last_close_location": m["cl"],
    }
    f.update({
        "ret60_pos": f["ret60"] > 0,
        "ret240_pos": f["ret240"] > 0,
        "ret1440_pos": f["ret1440"] > 0,
        "above_ema7": close > float(last.ema7),
        "above_ema20": close > float(last.ema20),
        "ema7_above20": float(last.ema7) > float(last.ema20),
        "ema20_slope60_pos": f["ema20_slope60"] > 0,
        "ema20_slope240_pos": f["ema20_slope240"] > 0,
        "taker60_pos": f["taker60"] > 0,
        "taker240_pos": f["taker240"] > 0,
        "last_bull": float(last.close) > float(last.open),
        "last_top_quartile": m["cl"] >= 0.75,
        "last_bottom_quartile": m["cl"] <= 0.25,
        "last_upper_wick_dom": m["uw"] >= 0.50,
        "last_lower_wick_dom": m["lw"] >= 0.50,
    })
    return f


def period_name(idx):
    return "discovery" if idx < SPLIT else "validation"


def cont_atlas(df):
    rows = []
    for feat in FEATURES:
        for period, g in [("full", df), ("discovery", df[df.idx < SPLIT]), ("validation", df[df.idx >= SPLIT])]:
            y = g.short_better.astype(int).to_numpy()
            auc = rank_auc(y, g[feat].to_numpy(float))
            sb = g[g.short_better][feat]
            bb = g[~g.short_better][feat]
            rows.append({
                "feature": feat, "period": period, "n": int(len(g)),
                "short_better_n": int(g.short_better.sum()),
                "auc_short_better_high": auc,
                "short_better_median": float(sb.median()) if len(sb) else np.nan,
                "buy_better_median": float(bb.median()) if len(bb) else np.nan,
            })
    return pd.DataFrame(rows)


def binary_atlas(df):
    rows = []
    for sig in BINARY:
        for period, g in [("full", df), ("discovery", df[df.idx < SPLIT]), ("validation", df[df.idx >= SPLIT])]:
            yes = g[g[sig].astype(bool)]
            no = g[~g[sig].astype(bool)]
            rows.append({
                "signal": sig, "period": period, "n": int(len(g)),
                "yes_n": int(len(yes)), "no_n": int(len(no)),
                "yes_short_better_rate": float(yes.short_better.mean()) if len(yes) else np.nan,
                "no_short_better_rate": float(no.short_better.mean()) if len(no) else np.nan,
                "effect_yes_minus_no": (float(yes.short_better.mean()) - float(no.short_better.mean())) if len(yes) and len(no) else np.nan,
            })
    return pd.DataFrame(rows)


def stability(cont):
    out = []
    for feat in FEATURES:
        x = cont[cont.feature == feat].set_index("period")
        af = float(x.loc["full", "auc_short_better_high"])
        ad = float(x.loc["discovery", "auc_short_better_high"])
        av = float(x.loc["validation", "auc_short_better_high"])
        full_dir = "HIGH_SHORT" if af > 0.5 else ("LOW_SHORT" if af < 0.5 else "TIE")
        same_side = bool(np.isfinite(ad) and np.isfinite(av) and (ad - .5) * (av - .5) > 0)
        # Descriptive robustness screen only; not a trading threshold.
        robust = bool(same_side and abs(af - .5) >= .07)
        out.append({"feature": feat, "auc_full": af, "auc_disc": ad, "auc_val": av,
                    "direction": full_dir, "same_side_dv": same_side, "robust_screen": robust})
    return pd.DataFrame(out).sort_values(["robust_screen", "auc_full"], ascending=[False, False])


def main():
    k = s50.load_klines().copy()
    k["ema7"] = k["close"].ewm(span=7, adjust=False).mean()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    longs = [s50.simulate(k, f, t) for t in entries]
    shorts = [s60.simulate_short(k, f, t) for t in entries]

    if len(entries) != 139 or abs(sum(x.pnl for x in longs) - 87.199692) > .02:
        raise RuntimeError("parent parity fail")

    recs = []
    for i, (t, lg, sh) in enumerate(zip(entries, longs, shorts)):
        if lg.pnl > 0 and sh.pnl <= 0:
            tax = "BUY_ONLY_WIN"
        elif sh.pnl > 0 and lg.pnl <= 0:
            tax = "SHORT_ONLY_WIN"
        elif lg.pnl > 0 and sh.pnl > 0:
            tax = "BOTH_WIN"
        else:
            tax = "BOTH_LOSE"
        r = {
            "idx": i, "period": period_name(i), "date": lg.date, "entry_t": str(t),
            "buy_pnl": float(lg.pnl), "short_pnl": float(sh.pnl),
            "buy_win": bool(lg.pnl > 0), "short_win": bool(sh.pnl > 0),
            "short_better": bool(sh.pnl > lg.pnl), "pnl_edge_short_minus_buy": float(sh.pnl - lg.pnl),
            "outcome_taxonomy": tax,
            "buy_no05": bool(lg.mfe < .005 - 1e-12),
        }
        r.update(pre_features(k, t))
        recs.append(r)

    df = pd.DataFrame(recs)
    df.to_csv(OUT / "s61_preentry_rows.csv", index=False)

    cont = cont_atlas(df); cont.to_csv(OUT / "s61_continuous_atlas.csv", index=False)
    binary = binary_atlas(df); binary.to_csv(OUT / "s61_binary_atlas.csv", index=False)
    stab = stability(cont); stab.to_csv(OUT / "s61_feature_stability.csv", index=False)

    tax = []
    for period, g0 in [("full", df), ("discovery", df[df.idx < SPLIT]), ("validation", df[df.idx >= SPLIT])]:
        for label, g in g0.groupby("outcome_taxonomy"):
            tax.append({"period": period, "taxonomy": label, "n": int(len(g)),
                        "buy_pnl": float(g.buy_pnl.sum()), "short_pnl": float(g.short_pnl.sum())})
    taxdf = pd.DataFrame(tax); taxdf.to_csv(OUT / "s61_outcome_taxonomy.csv", index=False)

    # Focused separability on cases where exactly one direction wins.
    decisive = df[df.outcome_taxonomy.isin(["BUY_ONLY_WIN", "SHORT_ONLY_WIN"])].copy()
    decisive["short_only"] = decisive.outcome_taxonomy.eq("SHORT_ONLY_WIN")
    dec_rows = []
    for feat in FEATURES:
        for period, g in [("full", decisive), ("discovery", decisive[decisive.idx < SPLIT]), ("validation", decisive[decisive.idx >= SPLIT])]:
            dec_rows.append({"feature": feat, "period": period, "n": int(len(g)),
                             "short_only_n": int(g.short_only.sum()),
                             "auc_short_only_high": rank_auc(g.short_only.astype(int), g[feat])})
    decdf = pd.DataFrame(dec_rows); decdf.to_csv(OUT / "s61_decisive_direction_auc.csv", index=False)

    robust = stab[stab.robust_screen]
    summary = {
        "parity": {"n": len(df), "buy_pnl": float(df.buy_pnl.sum()),
                   "buy_wins": int(df.buy_win.sum()), "short_wins": int(df.short_win.sum())},
        "labels": {
            "short_better_n": int(df.short_better.sum()),
            "buy_better_or_equal_n": int((~df.short_better).sum()),
            "taxonomy_full": df.outcome_taxonomy.value_counts().to_dict(),
            "decisive_n": int(len(decisive)),
        },
        "robust_feature_screen": robust.to_dict(orient="records"),
        "robust_feature_n": int(len(robust)),
    }
    (OUT / "s61_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def pct(x): return f"{100*x:.1f}%"
    md = [
        "# S6.1 — Saturday Pre-Entry Causal Direction Feature Atlas", "",
        "**Status:** COMPLETE — FORENSIC FEATURE ATLAS ONLY; NO CLASSIFIER/RULE", "",
        "## Causal boundary",
        "All features use completed information strictly before 18:00 WIB entry; latest candle is 17:55 WIB / 10:55 UTC. Outcome labels are hindsight targets only.", "",
        "## Outcome labels",
        f"- total **{len(df)}**",
        f"- SHORT_BETTER **{int(df.short_better.sum())}** / BUY_BETTER_OR_EQUAL **{int((~df.short_better).sum())}**",
        f"- taxonomy: **{df.outcome_taxonomy.value_counts().to_dict()}**",
        f"- decisive one-direction-wins cases: **{len(decisive)}**", "",
        "## Robust continuous feature screen",
        "Screen is descriptive only: D and V AUC must lie on the same side of 0.50 and full |AUC-0.50| >= 0.07. No cutoff is selected.", "",
        "| Feature | Full AUC | D AUC | V AUC | Direction |",
        "|---|---:|---:|---:|---|",
    ]
    for r in robust.itertuples(index=False):
        md.append(f"| {r.feature} | {r.auc_full:.3f} | {r.auc_disc:.3f} | {r.auc_val:.3f} | {r.direction} |")
    if len(robust) == 0:
        md.append("| NONE | - | - | - | - |")

    # Top decisive-direction AUCs by distance from 0.5, requiring D/V same side.
    piv = decdf.pivot(index="feature", columns="period", values="auc_short_only_high").reset_index()
    piv["gap"] = (piv["full"] - .5).abs()
    piv["same_side"] = (piv["discovery"] - .5) * (piv["validation"] - .5) > 0
    topdec = piv[piv.same_side].sort_values("gap", ascending=False).head(10)
    md += ["", "## Decisive BUY-only vs SHORT-only cases", "",
           "| Feature | Full AUC(short-only high) | D | V |", "|---|---:|---:|---:|"]
    for r in topdec.itertuples(index=False):
        md.append(f"| {r.feature} | {r.full:.3f} | {r.discovery:.3f} | {r.validation:.3f} |")
    if len(topdec) == 0:
        md.append("| NONE | - | - | - |")

    md += ["", "## Research decision",
           "S6.1 does not create a direction selector. If multiple pre-entry features show stable D/V separation, the next milestone may freeze a small candidate set and test causal walk-forward classification. If separation is weak/inconsistent, do not force ML merely to chase the hindsight 70% ceiling."]
    (OUT / "S6.1_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
