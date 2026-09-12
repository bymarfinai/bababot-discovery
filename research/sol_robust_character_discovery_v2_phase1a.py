#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_economic_first_h00_long_07_08wib_character as legacy

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_RCD_V2_PHASE1A"
LOOKBACKS = (15, 30, 60, 120, 240, 360)
HOLDS = (60, 120, 240, 360, 720, 960)
YEARS = (2022, 2023, 2024)
CLOCKS = tuple(range(0, 1440, 15))
ANCHORS = (0, 15, 30, 45)
SCALE_VARS = ("RAW_RANGE_LB", "RANGE_24H", "RANGE_72H", "RANGE_RATIO_24_72")
BANDS = ("LOW", "MID", "HIGH")
SCALE_STATES = ("NONE",) + tuple(f"{v}_{b}" for v in SCALE_VARS for b in BANDS)
NOTIONAL = 500.0
FEE = 0.75
BAR_MIN = 5


def out(name: str) -> Path:
    return ROOT / f"{PFX}_{name}"


def clip01(x: float) -> float:
    return 0.0 if not np.isfinite(x) else float(np.clip(x, 0.0, 1.0))


def longest_run(mask: np.ndarray) -> int:
    mask = np.asarray(mask, bool)
    if len(mask) == 0 or not mask.any():
        return 0
    d = np.diff(np.r_[False, mask, False].astype(np.int8))
    a, z = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return int(np.max(z - a)) if len(a) else 0


def stats(net: np.ndarray, full: bool = True) -> dict:
    net = np.asarray(net, float)
    if len(net) == 0:
        d = {"trades": 0, "win_rate": np.nan, "net_pnl": 0.0, "expectancy": np.nan, "pf": np.nan}
        if full:
            d.update(max_dd=np.nan, max_loss_streak=0, max_win_streak=0)
        return d
    pos = float(net[net > 0].sum())
    neg = float(-net[net < 0].sum())
    pf = np.inf if neg == 0 and pos > 0 else (pos / neg if neg > 0 else np.nan)
    d = {
        "trades": int(len(net)),
        "win_rate": float(np.mean(net > 0)),
        "net_pnl": float(net.sum()),
        "expectancy": float(net.mean()),
        "pf": float(pf),
    }
    if full:
        c = np.cumsum(net)
        p = np.maximum.accumulate(np.r_[0.0, c])
        d.update(
            max_dd=float(np.max(p[1:] - c)),
            max_loss_streak=longest_run(net <= 0),
            max_win_streak=longest_run(net > 0),
        )
    return d


def trailing_range(opens, highs, lows, entry_ix: int, bars: int) -> float:
    start = entry_ix - bars
    if start < 0 or opens[start] <= 0:
        return np.nan
    return float((np.max(highs[start:entry_ix]) - np.min(lows[start:entry_ix])) / opens[start])


def enhanced_frame(x5: pd.DataFrame, clock: int, lb: int) -> pd.DataFrame:
    f = legacy.state_frame(x5, clock, lb).copy()
    opens = x5.open.to_numpy(float)
    highs = x5.high.to_numpy(float)
    lows = x5.low.to_numpy(float)
    rr = np.full(len(f), np.nan)
    r24 = np.full(len(f), np.nan)
    r72 = np.full(len(f), np.nan)
    for j, (a, e) in enumerate(zip(f.pre_ix.to_numpy(int), f.entry_ix.to_numpy(int))):
        if a >= 0 and e > a and opens[a] > 0:
            rr[j] = (np.max(highs[a:e]) - np.min(lows[a:e])) / opens[a]
        r24[j] = trailing_range(opens, highs, lows, int(e), 24 * 60 // BAR_MIN)
        r72[j] = trailing_range(opens, highs, lows, int(e), 72 * 60 // BAR_MIN)
    ratio = np.divide(r24, r72, out=np.full(len(f), np.nan), where=np.isfinite(r24) & np.isfinite(r72) & (r72 > 0))
    f["RAW_RANGE_LB"] = rr
    f["RANGE_24H"] = r24
    f["RANGE_72H"] = r72
    f["RANGE_RATIO_24_72"] = ratio
    f["clock_min"] = clock
    f["hour_utc"] = clock // 60
    f["minute_anchor"] = clock % 60
    return f


def build_dev(x5: pd.DataFrame, lb: int) -> pd.DataFrame:
    a, z = base.PARTS["development"]
    pieces = []
    for clock in CLOCKS:
        f = enhanced_frame(x5, clock, lb)
        et = pd.DatetimeIndex(f.entry_ts)
        pt = pd.DatetimeIndex(f.pre_ts)
        m = (pt >= a) & (et >= a) & (et < z)
        if m.any():
            pieces.append(f.loc[m].copy())
    d = pd.concat(pieces, ignore_index=True)
    d["entry_ts"] = pd.to_datetime(d.entry_ts, utc=True)
    d["year"] = d.entry_ts.dt.year.astype(int)
    return d.sort_values(["entry_ts", "clock_min"]).reset_index(drop=True)


def frozen_bounds(df: pd.DataFrame, lb: int):
    b, rows = {}, []
    for v in SCALE_VARS:
        x = pd.to_numeric(df[v], errors="coerce").dropna().to_numpy(float)
        q1, q2 = float(np.quantile(x, 1 / 3)), float(np.quantile(x, 2 / 3))
        b[v] = (q1, q2)
        rows.append({"lookback_min": lb, "scale_variable": v, "q33": q1, "q67": q2, "n_fit": len(x), "fit_partition": "development_only"})
    return b, rows


def scale_masks(df: pd.DataFrame, bounds: dict):
    o = {"NONE": np.ones(len(df), bool)}
    for v in SCALE_VARS:
        x = df[v].to_numpy(float)
        q1, q2 = bounds[v]
        finite = np.isfinite(x)
        o[f"{v}_LOW"] = finite & (x <= q1)
        o[f"{v}_MID"] = finite & (x > q1) & (x <= q2)
        o[f"{v}_HIGH"] = finite & (x > q2)
    return o


def hold_arrays(x5: pd.DataFrame, df: pd.DataFrame, hold: int):
    et = pd.DatetimeIndex(df.entry_ts)
    xt = et + pd.Timedelta(minutes=hold)
    xi = x5.index.get_indexer(xt)
    ei = df.entry_ix.to_numpy(int)
    _, z = base.PARTS["development"]
    valid = (xi >= 0) & ((xi - ei) == hold // BAR_MIN) & (xt < z)
    ret = np.full(len(df), np.nan)
    ok = xi >= 0
    opens = x5.open.to_numpy(float)
    ep = df.entry_price.to_numpy(float)
    ret[ok] = (opens[xi[ok]] - ep[ok]) / ep[ok]
    return valid, NOTIONAL * ret - FEE


def parse_scale(s: str):
    if s == "NONE":
        return "RAW_RANGE_LB", "NONE"
    for v in SCALE_VARS:
        if s.startswith(v + "_"):
            return v, s[len(v) + 1:]
    raise ValueError(s)


def cid(rule: str, scale: str, lb: int, hold: int) -> str:
    return f"{rule}|{scale}|LB{lb}|H{hold}"


def adjacent_support(anchor_rows: list[dict], best: int) -> bool:
    m = {int(r["minute_anchor"]): r for r in anchor_rows}
    i = ANCHORS.index(best)
    for a in (ANCHORS[(i - 1) % 4], ANCHORS[(i + 1) % 4]):
        r = m[a]
        if r["trades"] and np.isfinite(r["expectancy"]) and r["expectancy"] > 0 and np.isfinite(r["pf"]) and r["pf"] >= 1.05:
            return True
    return False


def evaluate(rule, scale, lb, hold, idx, net_all, years, anchors):
    net = net_all[idx]
    s = stats(net, True)
    candidate = cid(rule, scale, lb, hold)
    yr_rows, yr_nets = [], []
    year_gate = True
    min_year_exp = np.inf
    for y in YEARS:
        ys = stats(net[years[idx] == y], False)
        ok = bool(ys["trades"] >= 40 and ys["net_pnl"] > 0 and np.isfinite(ys["expectancy"]) and ys["expectancy"] > 0 and np.isfinite(ys["pf"]) and ys["pf"] >= 1.05)
        year_gate &= ok
        min_year_exp = min(min_year_exp, ys["expectancy"] if np.isfinite(ys["expectancy"]) else -np.inf)
        yr_nets.append(max(0.0, ys["net_pnl"]))
        yr_rows.append({"candidate_id": candidate, "year": y, **ys, "year_gate": ok})
    a_rows, a_nets = [], []
    for a in ANCHORS:
        aa = stats(net[anchors[idx] == a], False)
        a_nets.append(max(0.0, aa["net_pnl"]))
        a_rows.append({"candidate_id": candidate, "minute_anchor": a, **aa})
    pooled_gate = bool(s["trades"] >= 180 and s["net_pnl"] > 0 and np.isfinite(s["expectancy"]) and s["expectancy"] > 0 and np.isfinite(s["pf"]) and s["pf"] >= 1.20 and s["max_loss_streak"] <= 10)
    sy = sum(yr_nets)
    sa = sum(a_nets)
    max_y = max(yr_nets) / sy if sy > 0 else np.nan
    max_a = max(a_nets) / sa if sa > 0 else np.nan
    best_a = int(ANCHORS[int(np.argmax(a_nets))]) if sa > 0 else -1
    yc = bool(np.isfinite(max_y) and max_y <= 0.65)
    ac = bool(np.isfinite(max_a) and (max_a <= 0.60 or adjacent_support(a_rows, best_a)))
    pv, band = parse_scale(scale)
    row = {
        "candidate_id": candidate, "shape_rule": rule, "scale_state": scale,
        "principal_scale_variable": pv, "scale_band": band,
        "lookback_min": lb, "hold_min": hold, **s,
        "pooled_gate": pooled_gate, "year_gate": bool(year_gate),
        "max_year_positive_net_share": max_y, "max_anchor_positive_net_share": max_a,
        "best_minute_anchor": best_a, "year_concentration_ok": yc,
        "anchor_concentration_ok": ac, "concentration_gate": bool(yc and ac),
        "pre_plateau_hard_gate": bool(pooled_gate and year_gate and yc and ac),
        "min_year_expectancy": float(min_year_exp),
    }
    for r in yr_rows:
        r.update(shape_rule=rule, scale_state=scale, lookback_min=lb, hold_min=hold)
    for r in a_rows:
        r.update(shape_rule=rule, scale_state=scale, lookback_min=lb, hold_min=hold)
    return row, yr_rows, a_rows


def build_economics(x5: pd.DataFrame):
    econ, yrs, ans, b_rows = [], [], [], []
    frames, bounds_cache = {}, {}
    for lb in LOOKBACKS:
        df = build_dev(x5, lb)
        bounds, br = frozen_bounds(df, lb)
        frames[lb], bounds_cache[lb] = df, bounds
        b_rows += br
        sm = legacy.masks_for_frame(df)
        am = scale_masks(df, bounds)
        years, anchors = df.year.to_numpy(int), df.minute_anchor.to_numpy(int)
        hc = {h: hold_arrays(x5, df, h) for h in HOLDS}
        for rule in legacy.RULES:
            for scale in SCALE_STATES:
                base_idx = np.flatnonzero(sm[rule] & am[scale])
                for hold in HOLDS:
                    valid, net_all = hc[hold]
                    idx = base_idx[valid[base_idx]]
                    r, y, a = evaluate(rule, scale, lb, hold, idx, net_all, years, anchors)
                    econ.append(r); yrs += y; ans += a
    e = pd.DataFrame(econ)
    expected = len(legacy.RULES) * len(SCALE_STATES) * len(LOOKBACKS) * len(HOLDS)
    if len(e) != expected:
        raise AssertionError(f"expected {expected}, got {len(e)}")
    return e, pd.DataFrame(yrs), pd.DataFrame(ans), pd.DataFrame(b_rows), frames, bounds_cache


def plateau_table(econ: pd.DataFrame):
    li = {x: i for i, x in enumerate(LOOKBACKS)}
    hi = {x: i for i, x in enumerate(HOLDS)}
    look = {(r.shape_rule, r.scale_state, int(r.lookback_min), int(r.hold_min)): r for r in econ.itertuples(index=False)}
    rows = []
    for r in econ.itertuples(index=False):
        ns = []
        for dl in (-1, 0, 1):
            for dh in (-1, 0, 1):
                a, b = li[int(r.lookback_min)] + dl, hi[int(r.hold_min)] + dh
                if 0 <= a < len(LOOKBACKS) and 0 <= b < len(HOLDS):
                    ns.append(look[(r.shape_rule, r.scale_state, LOOKBACKS[a], HOLDS[b])])
        ex = np.array([n.expectancy for n in ns], float)
        pf = np.array([n.pf for n in ns], float)
        pn = np.clip(np.array([n.net_pnl for n in ns], float), 0, None)
        pe = int(np.sum(np.isfinite(ex) & (ex > 0)))
        pp = int(np.sum(np.isfinite(pf) & (pf >= 1.10)))
        med = float(np.nanmedian(ex)) if np.isfinite(ex).any() else np.nan
        denom = float(pn.sum())
        share = max(0.0, float(r.net_pnl)) / denom if denom > 0 else np.nan
        ok = bool(pe >= 3 and pp >= 2 and np.isfinite(med) and med > 0 and np.isfinite(share) and share <= 0.55)
        rows.append({"candidate_id": r.candidate_id, "shape_rule": r.shape_rule, "scale_state": r.scale_state, "lookback_min": r.lookback_min, "hold_min": r.hold_min, "neighborhood_points": len(ns), "positive_expectancy_points": pe, "pf_ge_1_10_points": pp, "median_neighborhood_expectancy": med, "center_positive_net_share": share, "plateau_pass": ok})
    return pd.DataFrame(rows)


def selected_candidate(x5, df, bounds, rule, scale, hold):
    mask = legacy.masks_for_frame(df)[rule] & scale_masks(df, bounds)[scale]
    valid, net = hold_arrays(x5, df, hold)
    idx = np.flatnonzero(mask & valid)
    return idx, net


def hour_diagnostics(x5, eligible, frames, bounds_cache, anchor_df):
    rows, diag = [], {}
    agroups = {k: g for k, g in anchor_df.groupby("candidate_id", sort=False)}
    for r in eligible.itertuples(index=False):
        df = frames[int(r.lookback_min)]
        idx, net_all = selected_candidate(x5, df, bounds_cache[int(r.lookback_min)], r.shape_rule, r.scale_state, int(r.hold_min))
        net = net_all[idx]
        hours = df.hour_utc.to_numpy(int)[idx]
        anchors = df.minute_anchor.to_numpy(int)[idx]
        local = []
        for h in range(24):
            s = stats(net[hours == h], False)
            rr = {"candidate_id": r.candidate_id, "shape_rule": r.shape_rule, "scale_state": r.scale_state, "lookback_min": r.lookback_min, "hold_min": r.hold_min, "hour_utc": h, **s}
            rows.append(rr); local.append(rr)
        best_h = int(max(local, key=lambda x: x["net_pnl"])["hour_utc"]) if local else -1
        keep_h = hours != best_h
        rem_h = float(net[keep_h].mean()) if keep_h.any() else np.nan
        ag = agroups[r.candidate_id]
        best_a = int(ag.sort_values("net_pnl", ascending=False).iloc[0].minute_anchor)
        keep_a = anchors != best_a
        rem_a = float(net[keep_a].mean()) if keep_a.any() else np.nan
        diag[r.candidate_id] = {"best_hour_utc": best_h, "remove_best_hour_expectancy": rem_h, "remove_best_anchor_expectancy": rem_a}
    return pd.DataFrame(rows), diag


def score(eligible, years, anchors, hours, plateau, diag, econ):
    yg = {k: g for k, g in years.groupby("candidate_id", sort=False)}
    ag = {k: g for k, g in anchors.groupby("candidate_id", sort=False)}
    hg = {k: g for k, g in hours.groupby("candidate_id", sort=False)} if len(hours) else {}
    pmap = plateau.set_index("candidate_id")
    emap = econ.set_index(["shape_rule", "scale_state", "lookback_min", "hold_min"])
    rows = []
    for r in eligible.itertuples(index=False):
        yq = []
        for y in YEARS:
            q = yg[r.candidate_id][yg[r.candidate_id].year == y].iloc[0]
            yq.append(0.5 * clip01(q.expectancy / 1.50) + 0.5 * clip01((q.pf - 1.0) / 0.30))
        sc_cal = 25 * float(np.mean(yq))
        p = pmap.loc[r.candidate_id]
        sc_pl = min(20.0, 10 * p.positive_expectancy_points / p.neighborhood_points + 10 * p.pf_ge_1_10_points / p.neighborhood_points)
        sc_pool = min(15.0, 7.5 * clip01(r.expectancy / 2.0) + 7.5 * clip01((r.pf - 1.0) / 0.50))
        aa = ag[r.candidate_id]
        af = float(np.mean(pd.to_numeric(aa.expectancy, errors="coerce").fillna(-np.inf) > 0))
        hh = hg.get(r.candidate_id, pd.DataFrame())
        he = hh[hh.trades >= 20] if len(hh) else hh
        hf = float(np.mean(pd.to_numeric(he.expectancy, errors="coerce").fillna(-np.inf) > 0)) if len(he) else 0.0
        d = diag[r.candidate_id]
        sc_clock = min(15.0, 5 * af + 5 * hf + (2.5 if np.isfinite(d["remove_best_anchor_expectancy"]) and d["remove_best_anchor_expectancy"] > 0 else 0) + (2.5 if np.isfinite(d["remove_best_hour_expectancy"]) and d["remove_best_hour_expectancy"] > 0 else 0))
        principal = r.principal_scale_variable
        bx = {}
        for b in BANDS:
            key = (r.shape_rule, f"{principal}_{b}", int(r.lookback_min), int(r.hold_min))
            bx[b] = float(emap.loc[key].expectancy)
        if r.scale_state == "NONE":
            sc_reg = 5 * sum(int(np.isfinite(bx[b]) and bx[b] > 0) for b in BANDS)
        else:
            order = list(BANDS); i = order.index(r.scale_band); adj = []
            if i > 0: adj.append(order[i - 1])
            if i < 2: adj.append(order[i + 1])
            sc_reg = min(15.0, 10 + 2.5 * sum(int(np.isfinite(bx[b]) and bx[b] > 0) for b in adj))
        sc_sample = min(10.0, 5 * clip01(r.trades / 600.0) + 2.5 * (1 - clip01(r.max_year_positive_net_share / 0.65)) + 2.5 * (1 - clip01(r.max_anchor_positive_net_share / 0.60)))
        total = sc_cal + sc_pl + sc_pool + sc_clock + sc_reg + sc_sample
        rows.append({"candidate_id": r.candidate_id, "shape_rule": r.shape_rule, "scale_state": r.scale_state, "principal_scale_variable": principal, "scale_band": r.scale_band, "lookback_min": r.lookback_min, "hold_min": r.hold_min, "trades": r.trades, "win_rate": r.win_rate, "net_pnl": r.net_pnl, "expectancy": r.expectancy, "pf": r.pf, "max_dd": r.max_dd, "max_loss_streak": r.max_loss_streak, "min_year_expectancy": r.min_year_expectancy, "calendar_score": sc_cal, "plateau_score": sc_pl, "pooled_economic_score": sc_pool, "clock_score": sc_clock, "regime_score": sc_reg, "sample_concentration_score": sc_sample, "robustness_score": total, "anchor_positive_fraction": af, "evaluable_hours": len(he), "hour_positive_fraction": hf, **d, "principal_low_expectancy": bx["LOW"], "principal_mid_expectancy": bx["MID"], "principal_high_expectancy": bx["HIGH"]})
    return pd.DataFrame(rows)


def freeze(scores: pd.DataFrame):
    if scores.empty:
        return scores.copy()
    q = scores.sort_values(["robustness_score", "min_year_expectancy", "pf"], ascending=[False, False, False])
    seen, rows = set(), []
    for r in q.itertuples(index=False):
        family = (r.shape_rule, r.principal_scale_variable)
        if family in seen:
            continue
        seen.add(family); rows.append(r._asdict())
        if len(rows) == 5:
            break
    z = pd.DataFrame(rows)
    z.insert(0, "freeze_rank", np.arange(1, len(z) + 1))
    z["freeze_status"] = "FROZEN_BEFORE_HISTORICAL_CONFIRMATION"
    return z


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")
    econ, years, anchors, bounds, frames, bounds_cache = build_economics(x5)
    plateau = plateau_table(econ)
    pmap = plateau.set_index("candidate_id").plateau_pass
    econ["plateau_pass"] = econ.candidate_id.map(pmap).fillna(False).astype(bool)
    econ["eligible"] = econ.pre_plateau_hard_gate & econ.plateau_pass
    eligible = econ[econ.eligible].copy()
    if len(eligible):
        hours, diag = hour_diagnostics(x5, eligible, frames, bounds_cache, anchors)
        scores = score(eligible, years, anchors, hours, plateau, diag, econ)
        finalists = freeze(scores)
    else:
        hours = pd.DataFrame(columns=["candidate_id", "shape_rule", "scale_state", "lookback_min", "hold_min", "hour_utc", "trades", "win_rate", "net_pnl", "expectancy", "pf"])
        scores = pd.DataFrame(columns=["candidate_id", "shape_rule", "scale_state", "principal_scale_variable", "scale_band", "lookback_min", "hold_min", "robustness_score"])
        finalists = scores.copy()
    universe = econ[["candidate_id", "shape_rule", "scale_state", "principal_scale_variable", "scale_band", "lookback_min", "hold_min"]].copy()
    rejection = econ[["candidate_id", "shape_rule", "scale_state", "lookback_min", "hold_min", "pooled_gate", "year_gate", "concentration_gate", "plateau_pass", "eligible"]].copy()
    rejection["rejection_reason"] = ["ELIGIBLE" if r.eligible else "|".join((["POOLED_GATE"] if not r.pooled_gate else []) + (["YEAR_GATE"] if not r.year_gate else []) + (["CONCENTRATION_GATE"] if not r.concentration_gate else []) + (["PLATEAU_GATE"] if not r.plateau_pass else [])) for r in econ.itertuples(index=False)]
    universe.to_csv(out("CandidateUniverse.csv"), index=False)
    econ.to_csv(out("CandidateEconomics.csv"), index=False)
    years.to_csv(out("YearEconomics.csv"), index=False)
    anchors.to_csv(out("AnchorEconomics.csv"), index=False)
    hours.to_csv(out("HourEconomics.csv"), index=False)
    bounds.to_csv(out("ScaleBoundaries.csv"), index=False)
    plateau.to_csv(out("Plateau.csv"), index=False)
    rejection.to_csv(out("Rejections.csv"), index=False)
    scores.to_csv(out("RobustnessScores.csv"), index=False)
    finalists.to_csv(out("FrozenFinalists.csv"), index=False)
    lines = [
        "# SOL Robust Character Discovery v2 — Phase 1A Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        f"Candidate points evaluated: **{len(econ):,}**.",
        "Development 2022–2024 only; External / Reference Validation / August were not evaluated.", "",
        "## Funnel", "",
        f"- pooled gate: **{int(econ.pooled_gate.sum()):,}**",
        f"- 3-year gate: **{int(econ.year_gate.sum()):,}**",
        f"- concentration gate: **{int(econ.concentration_gate.sum()):,}**",
        f"- all pre-plateau hard gates: **{int(econ.pre_plateau_hard_gate.sum()):,}**",
        f"- plateau pass: **{int(econ.plateau_pass.sum()):,}**",
        f"- fully eligible robust regions: **{len(eligible):,}**",
        f"- frozen structurally distinct finalists: **{len(finalists)}**", "",
    ]
    if len(finalists):
        lines += ["## Frozen finalists", "", "| Rank | Character | Scale | LB | Hold | N | WR | Net | Exp | PF | DD | LS | Score |", "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in finalists.itertuples(index=False):
            lines.append(f"| {int(r.freeze_rank)} | `{r.shape_rule}` | `{r.scale_state}` | {int(r.lookback_min)} | {int(r.hold_min)} | {int(r.trades)} | {100*r.win_rate:.2f}% | ${r.net_pnl:+.2f} | ${r.expectancy:+.2f} | {r.pf:.3f} | ${r.max_dd:.2f} | {int(r.max_loss_streak)} | {r.robustness_score:.2f} |")
        status = f"SOL_RCD_V2_PHASE1A_FROZEN_{len(finalists)}_FINALISTS"
    else:
        lines += ["## Scientific verdict", "", "**ZERO finalists survived the preregistered robustness process.**", "", "Per stop rule no gate is loosened and no historical data are exposed to rescue the search."]
        status = "SOL_RCD_V2_PHASE1A_ZERO_FINALISTS"
    out("Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out("Status.txt").write_text(status + "\n", encoding="utf-8")
    print(status)
    print(out("Result.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
