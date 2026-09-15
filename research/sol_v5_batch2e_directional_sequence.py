#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import sol_v5_batch2d_state_time_direction as b2d

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_V5_BATCH2E_DIRECTIONAL_SEQUENCE"
SEQ_BARS = 24
SELECT_Q = 0.90
TEST_YEARS = b2d.TEST_YEARS
ROUNDTRIP_COST_PCT = b2d.ROUNDTRIP_COST_PCT

STATE_CONTEXT = ["pred_impulse", "state_margin", "sigma60_pct", "impulse_threshold_pct"]
CHANNELS = (
    "path_close", "ret", "range", "body_frac", "close_loc",
    "lower_wick", "upper_wick", "logvol", "hh", "hl", "lh", "ll",
    "dist_run_high", "dist_run_low",
)
RELATIONAL = [
    *(f"structure_balance_{n}" for n in (4, 8, 12, 24)),
    *(f"body_balance_{n}" for n in (4, 8, 12, 24)),
    "close_loc_shift_4",
    "volume_shift_4",
    "range_expansion_4",
    "displacement_accel_4",
    "downside_sweep_reclaim_6v18",
    "upside_sweep_reject_6v18",
]
SEQ_FEATURES = [f"{ch}_{i:02d}" for ch in CHANNELS for i in range(SEQ_BARS)]
FEATURES = STATE_CONTEXT + SEQ_FEATURES + RELATIONAL

B2D_AUC = 0.5553
B2D_UP_FIRST = 0.4138
B2D_EXPECTANCY = -0.0754
B2D_PF = 0.886


def pfmt(v) -> str:
    if pd.isna(v):
        return "n/a"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.3f}"


def directional_sequence(q: pd.DataFrame, sigma_pct: float) -> dict | None:
    if len(q) != SEQ_BARS:
        return None
    op = q.open.astype(float).to_numpy()
    hi = q.high.astype(float).to_numpy()
    lo = q.low.astype(float).to_numpy()
    cl = q.close.astype(float).to_numpy()
    vol = q.volume.astype(float).to_numpy()
    if not all(np.isfinite(a).all() for a in (op, hi, lo, cl, vol)):
        return None
    if np.any(op <= 0) or np.any(hi <= 0) or np.any(lo <= 0) or np.any(cl <= 0):
        return None

    sigma = max(abs(float(sigma_pct)), 1e-6)
    span = hi - lo
    path_close = (cl / cl[0] - 1.0) * 100.0 / sigma
    ret = np.zeros(SEQ_BARS, dtype=float)
    ret[1:] = (cl[1:] / cl[:-1] - 1.0) * 100.0 / sigma
    range_norm = (hi / lo - 1.0) * 100.0 / sigma
    body_frac = np.divide(cl - op, span, out=np.zeros_like(cl), where=span > 0)
    close_loc = np.divide(cl - lo, span, out=np.full_like(cl, 0.5), where=span > 0)
    lower = np.maximum(0.0, np.minimum(op, cl) - lo)
    upper = np.maximum(0.0, hi - np.maximum(op, cl))
    lower_wick = np.divide(lower, span, out=np.zeros_like(cl), where=span > 0)
    upper_wick = np.divide(upper, span, out=np.zeros_like(cl), where=span > 0)

    med_vol = float(np.median(vol))
    if not np.isfinite(med_vol) or med_vol <= 0:
        return None
    logvol = np.log(np.maximum(vol, 1e-12) / med_vol)

    hh = np.zeros(SEQ_BARS, dtype=float)
    hl = np.zeros(SEQ_BARS, dtype=float)
    lh = np.zeros(SEQ_BARS, dtype=float)
    ll = np.zeros(SEQ_BARS, dtype=float)
    hh[1:] = (hi[1:] > hi[:-1]).astype(float)
    hl[1:] = (lo[1:] > lo[:-1]).astype(float)
    lh[1:] = (hi[1:] < hi[:-1]).astype(float)
    ll[1:] = (lo[1:] < lo[:-1]).astype(float)

    run_hi = np.maximum.accumulate(hi)
    run_lo = np.minimum.accumulate(lo)
    dist_run_high = (cl / run_hi - 1.0) * 100.0 / sigma
    dist_run_low = (cl / run_lo - 1.0) * 100.0 / sigma

    arrays = {
        "path_close": path_close,
        "ret": ret,
        "range": range_norm,
        "body_frac": body_frac,
        "close_loc": close_loc,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "logvol": logvol,
        "hh": hh,
        "hl": hl,
        "lh": lh,
        "ll": ll,
        "dist_run_high": dist_run_high,
        "dist_run_low": dist_run_low,
    }

    out: dict[str, float] = {}
    for ch, arr in arrays.items():
        for i, v in enumerate(arr):
            out[f"{ch}_{i:02d}"] = float(v)

    structure_signed = (hh + hl) - (lh + ll)
    for n in (4, 8, 12, 24):
        out[f"structure_balance_{n}"] = float(np.mean(structure_signed[-n:]))
        out[f"body_balance_{n}"] = float(np.mean(body_frac[-n:]))

    out["close_loc_shift_4"] = float(np.mean(close_loc[-4:]) - np.mean(close_loc[:4]))
    out["volume_shift_4"] = float(np.mean(logvol[-4:]) - np.mean(logvol[:4]))
    first_range = float(np.mean(range_norm[:4]))
    out["range_expansion_4"] = float(np.mean(range_norm[-4:]) / first_range) if first_range > 1e-12 else 1.0

    final4 = float((cl[-1] / cl[-5] - 1.0) * 100.0 / sigma)
    prev4 = float((cl[-5] / cl[-9] - 1.0) * 100.0 / sigma)
    out["displacement_accel_4"] = final4 - prev4

    prior18_hi = float(np.max(hi[:18])); prior18_lo = float(np.min(lo[:18]))
    last6_hi = float(np.max(hi[18:])); last6_lo = float(np.min(lo[18:])); last_close = float(cl[-1])
    out["downside_sweep_reclaim_6v18"] = float(last6_lo < prior18_lo and last_close > prior18_lo)
    out["upside_sweep_reject_6v18"] = float(last6_hi > prior18_hi and last_close < prior18_hi)

    vals = np.asarray(list(out.values()), dtype=float)
    return out if np.isfinite(vals).all() else None


def add_sequence_features(x5: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    positions = x5.index.get_indexer(pd.DatetimeIndex(pd.to_datetime(episodes.entry_time, utc=True)))
    rows = []
    for (_, e), p in zip(episodes.iterrows(), positions):
        if p < SEQ_BARS:
            continue
        t = pd.Timestamp(e.entry_time)
        q = x5.iloc[p-SEQ_BARS:p]
        if len(q) != SEQ_BARS:
            continue
        if q.index[0] != t - pd.Timedelta(minutes=SEQ_BARS * 5):
            continue
        if q.index[-1] != t - pd.Timedelta(minutes=5):
            continue
        f = directional_sequence(q, float(e.sigma60_pct))
        if f is None:
            continue
        r = e.to_dict()
        r.update(f)
        rows.append(r)
    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("no episodes with complete causal pre-state sequence")
    miss = [c for c in FEATURES if c not in out.columns]
    if miss:
        raise RuntimeError(f"missing Batch2E features: {miss[:10]}")
    a = out[FEATURES].astype(float).to_numpy()
    if not np.isfinite(a).all():
        raise RuntimeError("non-finite Batch2E features")
    return out.sort_values("entry_time").reset_index(drop=True)


def walk_forward(episodes: pd.DataFrame):
    preds, imps = [], []
    for y in TEST_YEARS:
        train_years = b2d.b2.train_years_for(y)
        tr = episodes[episodes.test_year.isin(train_years)].copy()
        te = episodes[episodes.test_year == y].copy()
        if tr.empty or te.empty or tr.target_up_first.nunique() < 2:
            raise RuntimeError(f"bad directional sequence split for {y}")

        clf = b2d.b2.activation_model()
        Xtr = tr[FEATURES].astype(float).to_numpy()
        ytr = tr.target_up_first.astype(int).to_numpy()
        clf.fit(Xtr, ytr)
        train_score = clf.predict_proba(Xtr)[:, 1]
        cutoff = float(np.quantile(train_score, SELECT_Q))

        te = te.copy()
        te["sequence_long_score"] = clf.predict_proba(te[FEATURES].astype(float).to_numpy())[:, 1]
        te["sequence_long_cutoff"] = cutoff
        te["selected_long"] = te.sequence_long_score >= cutoff
        preds.append(te)
        imps.append(pd.DataFrame({
            "test_year": y,
            "feature": FEATURES,
            "importance": clf.feature_importances_,
        }))
    return (
        pd.concat(preds, ignore_index=True).sort_values("entry_time").reset_index(drop=True),
        pd.concat(imps, ignore_index=True),
    )


def channel_name(feature: str) -> str:
    if feature in STATE_CONTEXT:
        return "state_context"
    for ch in CHANNELS:
        if feature.startswith(ch + "_"):
            return ch
    return "relational"


def yearly_summary(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in TEST_YEARS:
        g = pred[pred.test_year == y].copy()
        s = g[g.selected_long].copy()
        base_up = float(g.target_up_first.mean()) if len(g) else np.nan
        sel_up = float(s.target_up_first.mean()) if len(s) else np.nan
        ee = b2d.b2.econ_returns(s.net60_pct if len(s) else pd.Series(dtype=float))
        be = b2d.b2.econ_returns(g.net60_pct if len(g) else pd.Series(dtype=float))
        auc = float(roc_auc_score(g.target_up_first.astype(int), g.sequence_long_score.astype(float))) if g.target_up_first.nunique() > 1 else np.nan
        rows.append({
            "test_year": y,
            "episode_n": int(len(g)),
            "baseline_up_first_rate": base_up,
            "selected_n": int(len(s)),
            "selection_rate": float(len(s)/len(g)) if len(g) else np.nan,
            "selected_up_first_rate": sel_up,
            "up_first_lift": sel_up/base_up if np.isfinite(base_up) and base_up > 0 and np.isfinite(sel_up) else np.nan,
            "auc": auc,
            "selected_wr60": ee["wr"],
            "selected_expectancy60_pct": ee["expectancy_pct"],
            "selected_pf60": ee["pf"],
            "selected_pnl60_usd": ee["net_pnl_usd"],
            "selected_max_dd_usd": ee["max_dd_usd"],
            "selected_max_ls": ee["max_ls"],
            "baseline_expectancy60_pct": be["expectancy_pct"],
            "baseline_pf60": be["pf"],
        })
    return pd.DataFrame(rows)


def main():
    b2d.b2.b1.v4.v3.v1.base.fetch_one = b2d.b2.b1.v4.v3.v1.fetch_one_with_volume
    x5, coverage = b2d.b2.b1.v4.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    base_episodes, _ = b2d.build_episode_table(x5)
    episodes = add_sequence_features(x5, base_episodes)
    pred, imp = walk_forward(episodes)
    selected = pred[pred.selected_long].copy().sort_values("entry_time").reset_index(drop=True)

    auc = float(roc_auc_score(pred.target_up_first.astype(int), pred.sequence_long_score.astype(float))) if pred.target_up_first.nunique() > 1 else np.nan
    base_up = float(pred.target_up_first.mean())
    sel_up = float(selected.target_up_first.mean()) if len(selected) else np.nan
    lift = sel_up/base_up if base_up > 0 and np.isfinite(sel_up) else np.nan
    selected_e = b2d.b2.econ_returns(selected.net60_pct if len(selected) else pd.Series(dtype=float))
    base_e = b2d.b2.econ_returns(pred.net60_pct)
    yr = yearly_summary(pred)
    fi = imp.groupby("feature", as_index=False).importance.mean().sort_values("importance", ascending=False)
    fi["channel"] = fi.feature.map(channel_name)
    ci = fi.groupby("channel", as_index=False).importance.sum().sort_values("importance", ascending=False)
    pos_years = int((yr.selected_pnl60_usd > 0).sum())

    gates = {
        "selected_n_ge_200": int(len(selected)) >= 200,
        "oos_auc_ge_0_55": bool(np.isfinite(auc) and auc >= .55),
        "selected_up_first_ge_50pct": bool(np.isfinite(sel_up) and sel_up >= .50),
        "selected_up_first_lift_ge_1_35x": bool(np.isfinite(lift) and lift >= 1.35),
        "selected_expectancy_positive": bool(np.isfinite(selected_e["expectancy_pct"]) and selected_e["expectancy_pct"] > 0),
        "selected_pf_ge_1_10": bool(np.isfinite(selected_e["pf"]) and selected_e["pf"] >= 1.10),
        "positive_selected_pnl_years_ge_2_of_3": pos_years >= 2,
    }
    passed = bool(all(gates.values()))
    verdict = "READY_FOR_BATCH3_RISK_ENVELOPE" if passed else "DIRECTIONAL_SEQUENCE_NOT_READY"

    pred.to_csv(ROOT / f"{PFX}_Predictions.csv", index=False)
    selected.to_csv(ROOT / f"{PFX}_SelectedEntries.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    fi.to_csv(ROOT / f"{PFX}_FeatureImportance.csv", index=False)
    ci.to_csv(ROOT / f"{PFX}_ChannelImportance.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    lines = [
        "# SOL V5 Batch 2E — Directional Sequence Representation Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- OOS HIGH_STATE test episodes 2022-2024: **{len(pred)}**",
        f"- Selected LONG at state onset: **{len(selected)}**",
        f"- Selection rate: **{len(selected)/len(pred)*100:.2f}%**",
        f"- OOS ROC AUC: **{auc:.4f}**",
        "- Sequence: **24 completed 5m bars immediately before HIGH_STATE onset**",
        "- 2025+ reference_validation remained CLOSED.", "",
        "## Direction separation", "",
        f"- All HIGH_STATE UP_FIRST rate: **{base_up*100:.2f}%**",
        f"- Selected UP_FIRST rate: **{sel_up*100:.2f}%**",
        f"- UP_FIRST lift: **{lift:.3f}x**", "",
        "## Fixed +60m diagnostic", "",
        f"- Selected WR: **{selected_e['wr']*100:.2f}%**",
        f"- Selected expectancy: **{selected_e['expectancy_pct']:.4f}%**",
        f"- Selected PF: **{pfmt(selected_e['pf'])}**",
        f"- Selected net PnL: **${selected_e['net_pnl_usd']:.2f}**",
        f"- Selected max DD: **${selected_e['max_dd_usd']:.2f}**",
        f"- Selected max loss streak: **{selected_e['max_ls']}**", "",
        f"- All HIGH_STATE baseline expectancy: **{base_e['expectancy_pct']:.4f}%**",
        f"- All HIGH_STATE baseline PF: **{pfmt(base_e['pf'])}**", "",
        "## Frozen Batch 2D historical comparison", "",
        f"- Batch 2D AUC: **{B2D_AUC:.4f}**",
        f"- Batch 2D selected UP_FIRST: **{B2D_UP_FIRST*100:.2f}%**",
        f"- Batch 2D selected expectancy: **{B2D_EXPECTANCY:.4f}%**",
        f"- Batch 2D selected PF: **{B2D_PF:.3f}**", "",
        "## Year stability", "",
        "| Year | Episodes | Base UP_FIRST | Selected | Sel UP_FIRST | Lift | AUC | WR60 | Exp60 | PF60 | PnL |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in yr.iterrows():
        lines.append(
            f"| {int(r.test_year)} | {int(r.episode_n)} | {float(r.baseline_up_first_rate)*100:.2f}% | {int(r.selected_n)} | {float(r.selected_up_first_rate)*100:.2f}% | {float(r.up_first_lift):.3f}x | {float(r.auc):.3f} | {float(r.selected_wr60)*100:.2f}% | {float(r.selected_expectancy60_pct):.4f}% | {pfmt(r.selected_pf60)} | ${float(r.selected_pnl60_usd):.2f} |"
        )

    lines += ["", "## Channel importance", ""]
    for _, r in ci.iterrows():
        lines.append(f"- `{r.channel}` — total importance {float(r.importance):.4f}")
    lines += ["", "## Top sequence features", ""]
    for _, r in fi.head(20).iterrows():
        lines.append(f"- `{r.feature}` — importance {float(r.importance):.4f}")
    lines += ["", "## Batch 2E decision audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "", f"# BATCH 2E VERDICT: {verdict}", "",
        "READY_FOR_BATCH3_RISK_ENVELOPE means explicit pre-state directional path representation identifies a positive-edge LONG subset at HIGH_STATE onset before any TP/SL optimization.",
        "DIRECTIONAL_SEQUENCE_NOT_READY means do not rescue this representation by sweeping sequence length, channels, model, percentile, hours, exit horizon, TP or SL on 2022-2024.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
