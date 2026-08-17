#!/usr/bin/env python3
"""F6.16 — Friday post-+1R causal profit-protection test.

Research only; live BBC untouched. No retuning of F6.12/F6.9/F6.5.

Predeclared from F6.15 forensic evidence. A +1R milestone is first known only
when its 5m bar completes. We then observe through the bar 15 minutes after
that milestone bar and, if a rule fires, exit at the NEXT actual 5m open
(hit bar open + 20 minutes). This avoids hindsight/intrabar decision bias.

Four fixed candidates, all evaluated at that same decision time:
 P1 FLOW_EMA15: median taker flow < 0 AND latest completed close < EMA7.
 P2 FLOW_EMA_DD025R15: P1 AND drawdown from observed best >= 0.25R.
 P3 STRETCH1618_FLOW_EMA15: P1 AND nearest fully-known pre-entry 2h Fib
    resistance/extension context at milestone is 1.618 extension.
 P4 REJECTION_FLOW_EMA15: P1 AND milestone candle upper wick > body.

Natural R = parent SL = 0.70%; 0.25R = 0.175%.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f611_friday_fibonacci_forensic as f611
import f612_friday_fib_early5_cut as f612
import f615_friday_giveback_momentum_forensic as f615
import f69_friday_early_sink_candidate_robustness as f69

OUT = Path(os.getenv("F616_OUT", "f616_out")); OUT.mkdir(parents=True, exist_ok=True)
R = f517.SL
DECISION_OFFSET_MIN = 20  # hit bar + 3 further bars completed => next open
DD025R = 0.25 * R


def metrics(pnls):
    p = np.asarray(pnls, dtype=float)
    wins = int((p > 0).sum())
    gp = float(p[p > 0].sum()); gl = float(-p[p <= 0].sum())
    eq = np.cumsum(p); peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = float((peak[1:] - eq).max()) if len(eq) else 0.0
    ls = cur = 0
    for x in p:
        if x <= 0: cur += 1; ls = max(ls, cur)
        else: cur = 0
    return {"n": int(len(p)), "wins": wins, "losses": int(len(p)-wins),
            "wr": float(wins/len(p)) if len(p) else np.nan,
            "pnl": float(p.sum()), "pf": float(gp/gl) if gl > 0 else math.inf,
            "dd": dd, "ls": int(ls)}


def cut_pnl(entry, px):
    return f517.NOTIONAL * (px / entry - 1.0) - f517.ROUND_TRIP_FEE


def fib5_state(k, t, tr):
    f2 = f611.fib_features(k, t, float(tr.entry), 120)
    baseline = f612.rolling_2h_range_baseline(k, t)
    if f2 is None or not np.isfinite(baseline): return False
    return bool(float(k.loc[t].close) < tr.entry and
                tr.exit_t > t + pd.Timedelta(minutes=5) and
                float(f2["retr_depth"]) <= 0.382 and
                float(f2["range_pct"]) > baseline)


def first_hit(k, tr, thr):
    px = tr.entry * (1 + thr)
    bars = k[(k.index >= tr.entry_t) & (k.index < tr.exit_t)]
    z = bars[bars.high >= px]
    return None if z.empty else z.iloc[0].ts


def protection_state(k, tr):
    """Return causal +1R protection state at actual decision open."""
    ht = first_hit(k, tr, 1.0 * R)
    if ht is None: return None
    decision_t = ht + pd.Timedelta(minutes=DECISION_OFFSET_MIN)
    if decision_t not in k.index or tr.exit_t <= decision_t:
        return None

    # Completed bars known exactly at decision_t: ht, ht+5, ht+10, ht+15.
    w = k[(k.index >= ht) & (k.index < decision_t)]
    if len(w) != 4:
        return None
    last = w.iloc[-1]
    taker_med = float(w.taker_imb.median())
    below_ema7 = bool(last.close < last.ema7)
    best = float(w.high.max())
    drawdown = float(last.close / best - 1.0)

    milestone = k.loc[ht]
    cf = f615.candle_feat(milestone)
    fib2 = f615.pre_fib_resistance(k, tr.entry_t, float(milestone.high), 2)
    stretch1618 = bool(fib2 is not None and fib2.get("name") == "ext_1.618")
    reject = bool(cf["upper_wick_gt_body"])
    base = bool(taker_med < 0 and below_ema7)

    return {
        "hit_t": ht, "decision_t": decision_t,
        "decision_open": float(k.loc[decision_t, "open"]),
        "taker_med": taker_med, "below_ema7": below_ema7,
        "drawdown_from_best": drawdown,
        "milestone_upper_wick_ratio": float(cf["upper_wick_ratio"]),
        "milestone_reject": reject,
        "fib2_nearest": None if fib2 is None else fib2.get("name"),
        "stretch1618": stretch1618,
        "P1_FLOW_EMA15": base,
        "P2_FLOW_EMA_DD025R15": bool(base and drawdown <= -DD025R),
        "P3_STRETCH1618_FLOW_EMA15": bool(base and stretch1618),
        "P4_REJECTION_FLOW_EMA15": bool(base and reject),
    }


def existing_events(k, t, tr):
    ev = []
    if fib5_state(k, t, tr):
        dt = t + pd.Timedelta(minutes=5)
        if tr.exit_t > dt: ev.append((dt, "FIB5", cut_pnl(tr.entry, float(k.loc[dt, "open"]))))
    if f69.early_state(k, t, tr):
        dt = t + pd.Timedelta(minutes=10)
        if tr.exit_t > dt: ev.append((dt, "EARLY10", cut_pnl(tr.entry, float(k.loc[dt, "open"]))))
    if f69.f65_state(k, t, tr):
        dt = t + pd.Timedelta(minutes=60)
        if tr.exit_t > dt: ev.append((dt, "F65_60", cut_pnl(tr.entry, float(k.loc[dt, "open"]))))
    return sorted(ev, key=lambda x: x[0])


def apply_rule(k, t, tr, pstate, rule):
    events = existing_events(k, t, tr)
    if pstate is not None and pstate[rule]:
        dt = pstate["decision_t"]
        events.append((dt, rule, cut_pnl(tr.entry, pstate["decision_open"])))
    if not events: return float(tr.pnl), "PARENT", None
    events.sort(key=lambda x: x[0])
    dt, layer, pnl = events[0]
    return float(pnl), layer, dt


def main():
    k = f517.load_klines()
    days = [d for d in pd.date_range(f517.START, f517.END, inclusive="left", freq="D") if d.weekday() == 4]
    parents = []
    rows = []
    rules = ["P1_FLOW_EMA15", "P2_FLOW_EMA_DD025R15", "P3_STRETCH1618_FLOW_EMA15", "P4_REJECTION_FLOW_EMA15"]

    for i, d0 in enumerate(days):
        t = pd.Timestamp(d0.date(), tz="UTC") + pd.Timedelta(hours=8)
        tr = f517.simulate_parent(k, t); parents.append(tr)
        pstate = protection_state(k, tr)
        existing = existing_events(k, t, tr)
        base_pnl, base_layer, base_dt = (float(tr.pnl), "PARENT", None) if not existing else (float(existing[0][2]), existing[0][1], existing[0][0])
        row = {
            "i": i, "period": "discovery" if i < f517.SPLIT_N else "validation", "date": tr.date,
            "parent_pnl": float(tr.pnl), "parent_win": bool(tr.pnl > 0), "parent_mfe_r": float(tr.mfe/R),
            "existing_pnl": base_pnl, "existing_layer": base_layer,
            "existing_dt": None if base_dt is None else str(base_dt),
            "reached_1r": bool(pstate is not None),
        }
        if pstate is not None:
            for key, val in pstate.items():
                row[f"p_{key}"] = str(val) if isinstance(val, pd.Timestamp) else val
        for rule in rules:
            pnl, layer, dt = apply_rule(k, t, tr, pstate, rule)
            row[f"{rule}_pnl"] = pnl; row[f"{rule}_layer"] = layer
            row[f"{rule}_dt"] = None if dt is None else str(dt)
            row[f"{rule}_incremental"] = pnl - base_pnl
        rows.append(row)

    f517.assert_parent(parents)
    df = pd.DataFrame(rows); df.to_csv(OUT/"f616_rows.csv", index=False)
    parent_m = metrics(df.parent_pnl)
    existing_m = metrics(df.existing_pnl)

    # Parity with F6.13 three-layer stack.
    if abs(existing_m["pnl"] - 105.8182) > 0.08:
        raise AssertionError(f"existing stack parity mismatch: {existing_m}")

    out = {"parent": parent_m, "existing_three_layer": existing_m, "rules": {}}
    for rule in rules:
        col = f"{rule}_pnl"; lay = f"{rule}_layer"; inc = f"{rule}_incremental"
        m = metrics(df[col])
        acts = df[df[lay] == rule].copy()
        d = df[df.i < f517.SPLIT_N]; v = df[df.i >= f517.SPLIT_N]
        residual_givebacks = acts[(acts.parent_pnl <= 0) & (acts.parent_mfe_r >= 1.0) & (acts.parent_mfe_r < 2.0)]
        out["rules"][rule] = {
            "metrics": m,
            "incremental_vs_existing": float(m["pnl"] - existing_m["pnl"]),
            "incremental_discovery": float(d[inc].sum()),
            "incremental_validation": float(v[inc].sum()),
            "actions": int(len(acts)),
            "actions_discovery": int((acts.i < f517.SPLIT_N).sum()),
            "actions_validation": int((acts.i >= f517.SPLIT_N).sum()),
            "parent_winners_acted": int(acts.parent_win.sum()),
            "parent_losses_acted": int((~acts.parent_win).sum()),
            "residual_1r_givebacks_acted": int(len(residual_givebacks)),
            "actions_exit_positive": int((acts[col] > 0).sum()),
            "loss_to_positive_conversions": int(((acts.parent_pnl <= 0) & (acts[col] > 0)).sum()),
            "action_incremental_sum": float(acts[inc].sum()),
            "action_incremental_positive": int((acts[inc] > 0).sum()),
            "action_incremental_negative": int((acts[inc] < 0).sum()),
            "dd_improvement_vs_existing": float(existing_m["dd"] - m["dd"]),
            "wr_gain_pp_vs_existing": float((m["wr"] - existing_m["wr"])*100),
            "action_dates": acts[["date","period","parent_pnl","parent_mfe_r",col,inc,"p_taker_med","p_below_ema7","p_drawdown_from_best","p_milestone_reject","p_fib2_nearest"]].to_dict("records") if len(acts) else [],
        }
        rr = out["rules"][rule]
        rr["screen_pass"] = bool(rr["incremental_vs_existing"] > 0 and rr["incremental_discovery"] >= 0 and rr["incremental_validation"] >= 0 and rr["loss_to_positive_conversions"] > 0)

    # Predeclared selection discipline: report all; choose best only among screen-pass by total incremental, no threshold tuning.
    passed = [r for r in rules if out["rules"][r]["screen_pass"]]
    out["screen_pass_rules"] = passed
    out["best_predeclared"] = max(passed, key=lambda r: out["rules"][r]["incremental_vs_existing"]) if passed else None

    (OUT/"f616_summary.json").write_text(json.dumps(out, indent=2, default=str))
    md = [
        "# Friday F6.16 — Post-+1R Profit Protection",
        "", "**Status: COMPLETE — causal management test; no threshold sweep.**",
        "**Live BBC untouched; F6.12/F6.9/F6.5 unchanged.**", "",
        "## Causal timing", "First +1R hit is known at milestone 5m close. Observe through +15m bar, act only at next actual 5m open (= milestone bar open +20m).", "",
        f"Existing three-layer PnL **{existing_m['pnl']:+.3f}**, WR **{existing_m['wr']*100:.2f}%**, PF **{existing_m['pf']:.3f}**, DD **{existing_m['dd']:.3f}**.", "",
        "## Predeclared rule results",
    ]
    for rule in rules:
        r = out["rules"][rule]; m = r["metrics"]
        md += [f"### {rule}",
               f"- actions {r['actions']} (D {r['actions_discovery']} / V {r['actions_validation']}); parent winners acted {r['parent_winners_acted']}",
               f"- incremental vs existing **{r['incremental_vs_existing']:+.3f}**; D/V **{r['incremental_discovery']:+.3f} / {r['incremental_validation']:+.3f}**",
               f"- loss→positive conversions **{r['loss_to_positive_conversions']}**; residual +1R givebacks acted **{r['residual_1r_givebacks_acted']}**",
               f"- managed PnL **{m['pnl']:+.3f}**, WR **{m['wr']*100:.2f}%**, PF **{m['pf']:.3f}**, DD **{m['dd']:.3f}**",
               f"- screen {'PASS' if r['screen_pass'] else 'FAIL'}", ""]
    md += ["## Verdict", f"Predeclared screen-pass rules: {', '.join(passed) if passed else 'none'}.", f"Best predeclared: **{out['best_predeclared']}**." if out['best_predeclared'] else "No rule promoted."]
    (OUT/"F6.16_CHECKPOINT.md").write_text("\n".join(md)+"\n")
    print(json.dumps(out, indent=2, default=str), flush=True)

if __name__ == "__main__": main()
