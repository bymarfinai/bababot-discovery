#!/usr/bin/env python3
"""G6 — preregistered weekly pooled-regime health governor.

Historical test uses frozen causal G1 hourly predictions only. Weekly health is
mean(p_sell - causal baseline_p_sell) across exactly 168 completed hourly states
before each Tuesday opportunity. Research only; live BBC untouched.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import g0_global_pooled_regime_dataset as g0
import g0_global_pooled_regime_dataset_fast as g0fast
import g1_embargoed_pooled_regime_walkforward as g1
import tuesday_a511_true_oos_august as tue

OUT = Path(os.getenv("G6_OUT", "g6_out"))
OUT.mkdir(parents=True, exist_ok=True)
G1_POOL = Path(os.getenv("G1_POOL", "../BTC_Global_Regime_G1_Pooled_WalkForward_Predictions.csv"))
G1_TUE = Path(os.getenv("G1_TUE", "../BTC_Global_Regime_G1_Tuesday_Overlay.csv"))
G1_AUG = Path(os.getenv("G1_AUG", "../BTC_Global_Regime_G1_August_Tuesday.csv"))
G0_DATA = Path(os.getenv("G0_DATA", "../BTC_Global_Regime_G0_Pooled_Hourly_States.csv"))
LOOKBACK_HOURS = 168


def trade_metrics(pnls: np.ndarray, traded: np.ndarray | None = None) -> dict:
    p = np.asarray(pnls, float)
    if traded is None:
        traded = np.ones(len(p), dtype=bool)
    else:
        traded = np.asarray(traded, bool)
    realized = np.where(traded, p, 0.0)
    x = p[traded]
    wins = int((x > 0).sum()) if len(x) else 0
    gp = float(x[x > 0].sum()) if len(x) else 0.0
    gl = float(-x[x <= 0].sum()) if len(x) else 0.0
    eq = np.cumsum(realized)
    if len(eq):
        peak = np.maximum.accumulate(np.r_[0.0, eq])
        dd = float(np.max(peak[1:] - eq))
    else:
        dd = 0.0
    return {
        "opportunities": int(len(p)), "trades": int(traded.sum()), "waits": int((~traded).sum()),
        "coverage": float(traded.mean()) if len(traded) else None,
        "wins": wins, "losses": int(len(x) - wins),
        "trade_wr": float(wins / len(x)) if len(x) else None,
        "pnl": float(realized.sum()),
        "exp_per_opportunity": float(realized.mean()) if len(realized) else None,
        "exp_per_trade": float(x.mean()) if len(x) else None,
        "pf": float(gp / gl) if gl > 0 else (999.0 if gp > 0 else None),
        "max_dd": dd,
    }


def historical_rows() -> pd.DataFrame:
    pool = pd.read_csv(G1_POOL)
    pool["decision_t_utc"] = pd.to_datetime(pool.decision_t_utc, utc=True)
    pool = pool.sort_values("decision_t_utc").reset_index(drop=True)
    pool["sell_delta"] = pool.p_sell - pool.baseline_p_sell
    pidx = pool.set_index("decision_t_utc")

    td = pd.read_csv(G1_TUE)
    td["decision_t_utc"] = pd.to_datetime(td.decision_t_utc, utc=True)
    td = td.sort_values("decision_t_utc").reset_index(drop=True)
    rows = []
    for r in td.itertuples(index=False):
        t = r.decision_t_utc
        start = t - pd.Timedelta(hours=LOOKBACK_HOURS)
        # Strictly pre-entry completed hourly predictions.
        w = pidx[(pidx.index >= start) & (pidx.index < t)]
        if len(w) != LOOKBACK_HOURS:
            continue
        expected = pd.date_range(start=start, periods=LOOKBACK_HOURS, freq="1h", tz="UTC")
        if not w.index.equals(expected):
            continue
        health = float(w.sell_delta.mean())
        rows.append({
            "date_wib": r.date_wib,
            "decision_t_utc": t,
            "weekly_sell_health": health,
            "mean_p_sell_168h": float(w.p_sell.mean()),
            "mean_baseline_p_sell_168h": float(w.baseline_p_sell.mean()),
            "trade": bool(health >= 0.0),
            "a511_pnl": float(r.a511_pnl),
            "a511_win": bool(r.a511_win),
        })
    return pd.DataFrame(rows).sort_values("decision_t_utc").reset_index(drop=True)


def fit_frozen_final_g1(hist: pd.DataFrame):
    model = g1.make_model()
    model.fit(hist[g1.FEATURES], hist.label)
    return model


def score_august_windows() -> pd.DataFrame:
    hist = pd.read_csv(G0_DATA)
    hist["decision_t_utc"] = pd.to_datetime(hist.decision_t_utc, utc=True)
    hist = hist.sort_values("decision_t_utc").reset_index(drop=True)
    model = fit_frozen_final_g1(hist)
    prior_sell = float((hist.label == "SELL_COMPATIBLE").mean())

    raw = tue.load_extended()
    k = g0.prepare(raw)
    aug = pd.read_csv(G1_AUG)
    aug["decision_t_utc"] = pd.to_datetime(aug.decision_t_utc, utc=True)
    rows = []
    for r in aug.itertuples(index=False):
        t = r.decision_t_utc
        hours = pd.date_range(start=t - pd.Timedelta(hours=LOOKBACK_HOURS), periods=LOOKBACK_HOURS, freq="1h", tz="UTC")
        feats = []
        for h in hours:
            f, ferr = g0fast.feature_row_fast(k, h)
            if ferr:
                raise RuntimeError(f"August G6 feature error {h}: {ferr}")
            feats.append({x: f[x] for x in g1.FEATURES})
        X = pd.DataFrame(feats)
        probs = g1.normalize_proba(model, X)
        p_sell = probs[:, g1.CLASSES.index("SELL_COMPATIBLE")]
        health = float(np.mean(p_sell - prior_sell))
        rows.append({
            "date_wib": r.date_wib,
            "decision_t_utc": t,
            "weekly_sell_health": health,
            "mean_p_sell_168h": float(np.mean(p_sell)),
            "baseline_p_sell": prior_sell,
            "trade": bool(health >= 0.0),
            "a511_pnl": float(r.a511_pnl),
        })
    return pd.DataFrame(rows)


def main() -> None:
    td = historical_rows()
    if len(td) < 120:
        # Still write what we have for transparent diagnosis before failing gate.
        pass
    pnls = td.a511_pnl.to_numpy(float)
    trade = td.trade.to_numpy(bool)
    base = trade_metrics(pnls)
    gate = trade_metrics(pnls, trade)

    positive = td[td.weekly_sell_health >= 0]
    negative = td[td.weekly_sell_health < 0]
    attr = {
        "health_ge_0": trade_metrics(positive.a511_pnl.to_numpy(float)),
        "health_lt_0": trade_metrics(negative.a511_pnl.to_numpy(float)),
    }

    blocks = []
    for b, idx in enumerate(np.array_split(np.arange(len(td)), 4), start=1):
        x = td.iloc[idx]
        xb = trade_metrics(x.a511_pnl.to_numpy(float))
        xg = trade_metrics(x.a511_pnl.to_numpy(float), x.trade.to_numpy(bool))
        blocks.append({
            "block": b, "start": x.iloc[0].date_wib, "end": x.iloc[-1].date_wib,
            "baseline": xb, "g6": xg, "pnl_delta": float(xg["pnl"] - xb["pnl"]),
        })

    checks = {
        "eligible_opportunities_ge_120": bool(len(td) >= 120),
        "coverage_ge_35pct": bool(gate["coverage"] >= 0.35),
        "exp_per_opportunity_improves": bool(gate["exp_per_opportunity"] > base["exp_per_opportunity"]),
        "total_pnl_ge_baseline": bool(gate["pnl"] >= base["pnl"]),
        "trade_wr_improves": bool(gate["trade_wr"] > base["trade_wr"]),
        "max_dd_improves": bool(gate["max_dd"] < base["max_dd"]),
        "positive_delta_3_of_4_blocks": bool(sum(x["pnl_delta"] > 0 for x in blocks) >= 3),
    }

    aug = score_august_windows()
    aug["g6_realized_pnl"] = np.where(aug.trade, aug.a511_pnl, 0.0)
    aug_summary = {
        "n": int(len(aug)), "trades": int(aug.trade.sum()), "waits": int((~aug.trade).sum()),
        "baseline_pnl": float(aug.a511_pnl.sum()), "g6_pnl": float(aug.g6_realized_pnl.sum()),
    }

    summary = {
        "status": "G6_WEEKLY_HEALTH_SHADOW_PASS" if all(checks.values()) else "G6_WEEKLY_HEALTH_GATE_FAILED",
        "lookback_hours": LOOKBACK_HOURS,
        "rule": "TRADE iff mean prior-168h (p_sell - causal baseline_p_sell) >= 0",
        "health_distribution": {
            "mean": float(td.weekly_sell_health.mean()),
            "median": float(td.weekly_sell_health.median()),
            "min": float(td.weekly_sell_health.min()),
            "max": float(td.weekly_sell_health.max()),
        },
        "baseline": base, "g6": gate, "attribution": attr,
        "blocks": blocks, "acceptance_checks": checks, "pass": bool(all(checks.values())),
        "august_report_only": aug_summary,
        "guardrail": "Exactly 168h slow health, zero threshold, no tuning; August report-only; live BBC untouched.",
    }

    td.to_csv(OUT / "g6_tuesday_rows.csv", index=False)
    aug.to_csv(OUT / "g6_august.csv", index=False)
    (OUT / "g6_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    def pct(v):
        return "-" if v is None else f"{100*v:.2f}%"

    lines = [
        "# BTC Global/Pooled Regime Engine — G6 Weekly Regime Health",
        "",
        f"**Status: {summary['status']}**",
        "",
        "Research only; live BBC untouched.",
        "",
        "## Frozen slow-state rule",
        "Use exactly the 168 completed hourly pooled predictions before each Tuesday.",
        "",
        "`WEEKLY_SELL_HEALTH = mean(pSELL - causal SELL prior)`",
        "",
        "TRADE iff weekly health >= 0; otherwise WAIT.",
        "",
        "## Historical Tuesday comparison",
        f"- Eligible opportunities: **{len(td)}**",
        f"- Health mean / median: **{summary['health_distribution']['mean']:+.5f} / {summary['health_distribution']['median']:+.5f}**",
        f"- Health range: **{summary['health_distribution']['min']:+.5f} → {summary['health_distribution']['max']:+.5f}**",
        "",
        "| Policy | Trades | Coverage | WR | PnL | Exp/oppty | PF | Max DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| Always A5.11 | {base['trades']} | {pct(base['coverage'])} | {pct(base['trade_wr'])} | ${base['pnl']:+.2f} | ${base['exp_per_opportunity']:+.4f} | {base['pf']:.3f} | ${base['max_dd']:.2f} |",
        f"| G6 weekly health | {gate['trades']} | {pct(gate['coverage'])} | {pct(gate['trade_wr'])} | ${gate['pnl']:+.2f} | ${gate['exp_per_opportunity']:+.4f} | {gate['pf']:.3f} | ${gate['max_dd']:.2f} |",
        "",
        "## Outcome attribution",
        "| Weekly state | N | WR | PnL | Exp/trade | PF |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, label in [("health_ge_0", "health >= 0"), ("health_lt_0", "health < 0")]:
        m = attr[key]
        pf = "-" if m["pf"] is None else f"{m['pf']:.3f}"
        lines.append(f"| {label} | {m['trades']} | {pct(m['trade_wr'])} | ${m['pnl']:+.2f} | ${m['exp_per_trade']:+.4f} | {pf} |")

    lines += ["", "## Acceptance gate"]
    for name, ok in checks.items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — `{name}`")
    lines += [
        "",
        "## Four chronological blocks",
        "| Block | Dates | Baseline PnL | G6 PnL | Delta |",
        "|---:|---|---:|---:|---:|",
    ]
    for b in blocks:
        lines.append(f"| {b['block']} | {b['start']} → {b['end']} | ${b['baseline']['pnl']:+.2f} | ${b['g6']['pnl']:+.2f} | ${b['pnl_delta']:+.2f} |")

    lines += [
        "",
        "## August 2026 — report only",
        "| Date WIB | Weekly health | Mean pSELL | Decision | A5.11 PnL | G6 realized |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for r in aug.to_dict(orient="records"):
        lines.append(f"| {r['date_wib']} | {r['weekly_sell_health']:+.5f} | {100*r['mean_p_sell_168h']:.2f}% | {'TRADE' if r['trade'] else 'WAIT'} | ${r['a511_pnl']:+.2f} | ${r['g6_realized_pnl']:+.2f} |")
    lines += [
        "",
        f"August baseline: **${aug_summary['baseline_pnl']:+.2f}**; G6: **${aug_summary['g6_pnl']:+.2f}**.",
        "",
        f"**Final G6 verdict: {'PASS — eligible as weekly regime-health shadow candidate only.' if summary['pass'] else 'FAIL — preserve result; no lookback or threshold tuning inside G6.'}**",
        "",
        "No live BBC changes were made.",
    ]
    (OUT / "BTC_GLOBAL_REGIME_G6_RESULT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
