#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_economic_first_h00_long_07_08wib_character as legacy
import sol_robust_character_discovery_v2_phase1a as v2

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_RCD_V3"
LOOKBACKS = v2.LOOKBACKS
HOLDS = v2.HOLDS
YEARS = v2.YEARS
CLOCKS = v2.CLOCKS
ANCHORS = v2.ANCHORS
LOCAL_STATES = v2.SCALE_STATES
BROAD_STATES = ("BROAD_NONE", "BROAD_QUIET", "BROAD_NORMAL", "BROAD_ACTIVE")
BROAD_VARS = ("RANGE_24H", "RANGE_72H", "RANGE_7D")
NOTIONAL = v2.NOTIONAL
FEE = v2.FEE
BAR_MIN = v2.BAR_MIN


def out(name: str) -> Path:
    return ROOT / f"{PFX}_{name}"


def cid(rule: str, local: str, broad: str, lb: int, hold: int) -> str:
    return f"{rule}|{local}|{broad}|LB{lb}|H{hold}"


def add_range_7d(x5: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    z = df.copy()
    opens = x5.open.to_numpy(float)
    highs = x5.high.to_numpy(float)
    lows = x5.low.to_numpy(float)
    vals = np.full(len(z), np.nan, float)
    bars = 7 * 24 * 60 // BAR_MIN
    for j, e in enumerate(z.entry_ix.to_numpy(int)):
        vals[j] = v2.trailing_range(opens, highs, lows, int(e), bars)
    z["RANGE_7D"] = vals
    return z


def build_dev(x5: pd.DataFrame, lb: int) -> pd.DataFrame:
    return add_range_7d(x5, v2.build_dev(x5, lb))


def local_bounds(df: pd.DataFrame, lb: int):
    return v2.frozen_bounds(df, lb)


def broad_bounds(df: pd.DataFrame, lb: int):
    b, rows = {}, []
    for var in BROAD_VARS:
        x = pd.to_numeric(df[var], errors="coerce").dropna().to_numpy(float)
        q1, q2 = float(np.quantile(x, 1 / 3)), float(np.quantile(x, 2 / 3))
        b[var] = (q1, q2)
        rows.append({
            "lookback_min": lb,
            "broad_variable": var,
            "q33": q1,
            "q67": q2,
            "n_fit": len(x),
            "fit_partition": "development_only",
        })
    return b, rows


def broad_masks(df: pd.DataFrame, bounds: dict[str, tuple[float, float]]):
    low = np.zeros(len(df), int)
    high = np.zeros(len(df), int)
    finite_all = np.ones(len(df), bool)
    for var in BROAD_VARS:
        x = df[var].to_numpy(float)
        q1, q2 = bounds[var]
        f = np.isfinite(x)
        finite_all &= f
        low += (f & (x <= q1)).astype(int)
        high += (f & (x > q2)).astype(int)
    quiet = finite_all & (low >= 2)
    active = finite_all & (high >= 2)
    normal = finite_all & ~quiet & ~active
    return {
        "BROAD_NONE": finite_all,
        "BROAD_QUIET": quiet,
        "BROAD_NORMAL": normal,
        "BROAD_ACTIVE": active,
    }


def adjacent_anchor_support(anchor_stats: dict[int, dict], best: int) -> bool:
    i = ANCHORS.index(best)
    for a in (ANCHORS[(i - 1) % 4], ANCHORS[(i + 1) % 4]):
        s = anchor_stats[a]
        if s["trades"] and np.isfinite(s["expectancy"]) and s["expectancy"] > 0 and np.isfinite(s["pf"]) and s["pf"] >= 1.05:
            return True
    return False


def evaluate(rule, local, broad, lb, hold, idx, net_all, years, anchors):
    net = net_all[idx]
    s = v2.stats(net, True)
    candidate = cid(rule, local, broad, lb, hold)

    row = {
        "candidate_id": candidate,
        "shape_rule": rule,
        "local_scale_state": local,
        "broad_regime": broad,
        "lookback_min": lb,
        "hold_min": hold,
        **s,
    }

    year_positive = []
    year_gate = True
    min_year_exp = np.inf
    for y in YEARS:
        ys = v2.stats(net[years[idx] == y], False)
        ok = bool(
            ys["trades"] >= 40
            and ys["net_pnl"] > 0
            and np.isfinite(ys["expectancy"]) and ys["expectancy"] > 0
            and np.isfinite(ys["pf"]) and ys["pf"] >= 1.05
        )
        year_gate &= ok
        year_positive.append(max(0.0, ys["net_pnl"]))
        min_year_exp = min(min_year_exp, ys["expectancy"] if np.isfinite(ys["expectancy"]) else -np.inf)
        row.update({
            f"y{y}_trades": ys["trades"],
            f"y{y}_wr": ys["win_rate"],
            f"y{y}_net": ys["net_pnl"],
            f"y{y}_exp": ys["expectancy"],
            f"y{y}_pf": ys["pf"],
            f"y{y}_gate": ok,
        })

    anchor_stats = {}
    anchor_positive = []
    for a in ANCHORS:
        aa = v2.stats(net[anchors[idx] == a], False)
        anchor_stats[a] = aa
        anchor_positive.append(max(0.0, aa["net_pnl"]))
        row.update({
            f"a{a}_trades": aa["trades"],
            f"a{a}_exp": aa["expectancy"],
            f"a{a}_pf": aa["pf"],
            f"a{a}_net": aa["net_pnl"],
        })

    sy = float(sum(year_positive))
    sa = float(sum(anchor_positive))
    max_y = max(year_positive) / sy if sy > 0 else np.nan
    max_a = max(anchor_positive) / sa if sa > 0 else np.nan
    best_a = int(ANCHORS[int(np.argmax(anchor_positive))]) if sa > 0 else -1
    year_concentration_ok = bool(np.isfinite(max_y) and max_y <= 0.65)
    anchor_concentration_ok = bool(
        np.isfinite(max_a)
        and (max_a <= 0.60 or (best_a >= 0 and adjacent_anchor_support(anchor_stats, best_a)))
    )
    pooled_gate = bool(
        s["trades"] >= 180
        and s["net_pnl"] > 0
        and np.isfinite(s["expectancy"]) and s["expectancy"] > 0
        and np.isfinite(s["pf"]) and s["pf"] >= 1.20
        and s["max_loss_streak"] <= 10
    )
    local_var, local_band = v2.parse_scale(local)
    row.update({
        "principal_local_scale_variable": local_var,
        "local_scale_band": local_band,
        "pooled_gate": pooled_gate,
        "year_gate": bool(year_gate),
        "min_year_expectancy": float(min_year_exp),
        "max_year_positive_net_share": max_y,
        "max_anchor_positive_net_share": max_a,
        "best_minute_anchor": best_a,
        "year_concentration_ok": year_concentration_ok,
        "anchor_concentration_ok": anchor_concentration_ok,
        "concentration_gate": bool(year_concentration_ok and anchor_concentration_ok),
        "pre_plateau_hard_gate": bool(pooled_gate and year_gate and year_concentration_ok and anchor_concentration_ok),
    })
    return row


def build_economics(x5: pd.DataFrame):
    rows, local_boundary_rows, broad_boundary_rows = [], [], []
    frames, local_cache, broad_cache = {}, {}, {}
    for lb in LOOKBACKS:
        df = build_dev(x5, lb)
        lbound, lrows = local_bounds(df, lb)
        bbound, brows = broad_bounds(df, lb)
        frames[lb] = df
        local_cache[lb] = lbound
        broad_cache[lb] = bbound
        local_boundary_rows += lrows
        broad_boundary_rows += brows

        sm = legacy.masks_for_frame(df)
        lm = v2.scale_masks(df, lbound)
        bm = broad_masks(df, bbound)
        years = df.year.to_numpy(int)
        anchors = df.minute_anchor.to_numpy(int)
        hc = {h: v2.hold_arrays(x5, df, h) for h in HOLDS}

        for rule in legacy.RULES:
            for local in LOCAL_STATES:
                shape_local = sm[rule] & lm[local]
                for broad in BROAD_STATES:
                    base_idx = np.flatnonzero(shape_local & bm[broad])
                    for hold in HOLDS:
                        valid, net_all = hc[hold]
                        idx = base_idx[valid[base_idx]]
                        rows.append(evaluate(rule, local, broad, lb, hold, idx, net_all, years, anchors))

    econ = pd.DataFrame(rows)
    expected = len(legacy.RULES) * len(LOCAL_STATES) * len(BROAD_STATES) * len(LOOKBACKS) * len(HOLDS)
    if len(econ) != expected:
        raise AssertionError(f"expected {expected} candidates, got {len(econ)}")
    return (
        econ,
        pd.DataFrame(local_boundary_rows),
        pd.DataFrame(broad_boundary_rows),
        frames,
        local_cache,
        broad_cache,
    )


def plateau_table(econ: pd.DataFrame):
    li = {x: i for i, x in enumerate(LOOKBACKS)}
    hi = {x: i for i, x in enumerate(HOLDS)}
    lookup = {
        (r.shape_rule, r.local_scale_state, r.broad_regime, int(r.lookback_min), int(r.hold_min)): r
        for r in econ.itertuples(index=False)
    }
    rows = []
    for r in econ.itertuples(index=False):
        neighbors = []
        for dl in (-1, 0, 1):
            for dh in (-1, 0, 1):
                a = li[int(r.lookback_min)] + dl
                b = hi[int(r.hold_min)] + dh
                if 0 <= a < len(LOOKBACKS) and 0 <= b < len(HOLDS):
                    neighbors.append(lookup[(r.shape_rule, r.local_scale_state, r.broad_regime, LOOKBACKS[a], HOLDS[b])])
        ex = np.array([n.expectancy for n in neighbors], float)
        pf = np.array([n.pf for n in neighbors], float)
        pos_net = np.clip(np.array([n.net_pnl for n in neighbors], float), 0, None)
        pe = int(np.sum(np.isfinite(ex) & (ex > 0)))
        pp = int(np.sum(np.isfinite(pf) & (pf >= 1.10)))
        med = float(np.nanmedian(ex)) if np.isfinite(ex).any() else np.nan
        denom = float(pos_net.sum())
        share = max(0.0, float(r.net_pnl)) / denom if denom > 0 else np.nan
        ok = bool(pe >= 3 and pp >= 2 and np.isfinite(med) and med > 0 and np.isfinite(share) and share <= 0.55)
        rows.append({
            "candidate_id": r.candidate_id,
            "shape_rule": r.shape_rule,
            "local_scale_state": r.local_scale_state,
            "broad_regime": r.broad_regime,
            "lookback_min": r.lookback_min,
            "hold_min": r.hold_min,
            "neighborhood_points": len(neighbors),
            "positive_expectancy_points": pe,
            "pf_ge_1_10_points": pp,
            "median_neighborhood_expectancy": med,
            "center_positive_net_share": share,
            "plateau_pass": ok,
        })
    return pd.DataFrame(rows)


def selected_candidate(x5, df, lbound, bbound, rule, local, broad, hold):
    mask = legacy.masks_for_frame(df)[rule] & v2.scale_masks(df, lbound)[local] & broad_masks(df, bbound)[broad]
    valid, net = v2.hold_arrays(x5, df, hold)
    idx = np.flatnonzero(mask & valid)
    return idx, net


def eligible_diagnostics(x5, eligible, frames, local_cache, broad_cache):
    year_rows, anchor_rows, hour_rows, diag = [], [], [], {}
    for r in eligible.itertuples(index=False):
        lb = int(r.lookback_min)
        df = frames[lb]
        idx, net_all = selected_candidate(
            x5, df, local_cache[lb], broad_cache[lb],
            r.shape_rule, r.local_scale_state, r.broad_regime, int(r.hold_min)
        )
        net = net_all[idx]
        years = df.year.to_numpy(int)[idx]
        anchors = df.minute_anchor.to_numpy(int)[idx]
        hours = df.hour_utc.to_numpy(int)[idx]

        for y in YEARS:
            s = v2.stats(net[years == y], False)
            year_rows.append({"candidate_id": r.candidate_id, "year": y, **s})
        for a in ANCHORS:
            s = v2.stats(net[anchors == a], False)
            anchor_rows.append({"candidate_id": r.candidate_id, "minute_anchor": a, **s})

        hlocal = []
        for h in range(24):
            s = v2.stats(net[hours == h], False)
            rec = {"candidate_id": r.candidate_id, "hour_utc": h, **s}
            hour_rows.append(rec)
            hlocal.append(rec)
        best_h = int(max(hlocal, key=lambda x: x["net_pnl"])["hour_utc"])
        keep_h = hours != best_h
        rem_h = float(net[keep_h].mean()) if keep_h.any() else np.nan

        a_nets = []
        for a in ANCHORS:
            a_nets.append((a, float(net[anchors == a].sum())))
        best_a = max(a_nets, key=lambda x: x[1])[0]
        keep_a = anchors != best_a
        rem_a = float(net[keep_a].mean()) if keep_a.any() else np.nan
        diag[r.candidate_id] = {
            "best_hour_utc": best_h,
            "remove_best_hour_expectancy": rem_h,
            "remove_best_anchor_expectancy": rem_a,
        }
    return pd.DataFrame(year_rows), pd.DataFrame(anchor_rows), pd.DataFrame(hour_rows), diag


def score(eligible, plateau, hours, diag, econ):
    pmap = plateau.set_index("candidate_id")
    emap = econ.set_index(["shape_rule", "local_scale_state", "broad_regime", "lookback_min", "hold_min"])
    hg = {k: g for k, g in hours.groupby("candidate_id", sort=False)} if len(hours) else {}
    rows = []
    broad_order = ["BROAD_QUIET", "BROAD_NORMAL", "BROAD_ACTIVE"]

    for r in eligible.itertuples(index=False):
        yq = []
        for y in YEARS:
            exp = float(getattr(r, f"y{y}_exp"))
            pf = float(getattr(r, f"y{y}_pf"))
            yq.append(0.5 * v2.clip01(exp / 1.50) + 0.5 * v2.clip01((pf - 1.0) / 0.30))
        sc_cal = 25 * float(np.mean(yq))

        p = pmap.loc[r.candidate_id]
        sc_pl = min(20.0, 10 * p.positive_expectancy_points / p.neighborhood_points + 10 * p.pf_ge_1_10_points / p.neighborhood_points)
        sc_pool = min(15.0, 7.5 * v2.clip01(r.expectancy / 2.0) + 7.5 * v2.clip01((r.pf - 1.0) / 0.50))

        aex = np.array([float(getattr(r, f"a{a}_exp")) for a in ANCHORS], float)
        af = float(np.mean(np.isfinite(aex) & (aex > 0)))
        hh = hg.get(r.candidate_id, pd.DataFrame())
        he = hh[hh.trades >= 20] if len(hh) else hh
        hf = float(np.mean(pd.to_numeric(he.expectancy, errors="coerce").fillna(-np.inf) > 0)) if len(he) else 0.0
        d = diag[r.candidate_id]
        sc_clock = min(15.0, 5 * af + 5 * hf + (2.5 if np.isfinite(d["remove_best_anchor_expectancy"]) and d["remove_best_anchor_expectancy"] > 0 else 0) + (2.5 if np.isfinite(d["remove_best_hour_expectancy"]) and d["remove_best_hour_expectancy"] > 0 else 0))

        principal = r.principal_local_scale_variable
        bx = {}
        for band in v2.BANDS:
            key = (r.shape_rule, f"{principal}_{band}", r.broad_regime, int(r.lookback_min), int(r.hold_min))
            bx[band] = float(emap.loc[key].expectancy)
        if r.local_scale_state == "NONE":
            sc_local = (10.0 / 3.0) * sum(int(np.isfinite(bx[b]) and bx[b] > 0) for b in v2.BANDS)
        else:
            order = list(v2.BANDS)
            i = order.index(r.local_scale_band)
            adj = []
            if i > 0:
                adj.append(order[i - 1])
            if i < 2:
                adj.append(order[i + 1])
            sc_local = min(10.0, 6.0 + 2.0 * sum(int(np.isfinite(bx[b]) and bx[b] > 0) for b in adj))

        br_exp = {}
        for br in broad_order:
            key = (r.shape_rule, r.local_scale_state, br, int(r.lookback_min), int(r.hold_min))
            br_exp[br] = float(emap.loc[key].expectancy)
        if r.broad_regime == "BROAD_NONE":
            sc_broad = (5.0 / 3.0) * sum(int(np.isfinite(br_exp[b]) and br_exp[b] > 0) for b in broad_order)
        else:
            i = broad_order.index(r.broad_regime)
            adj = []
            if i > 0:
                adj.append(broad_order[i - 1])
            if i < 2:
                adj.append(broad_order[i + 1])
            sc_broad = min(5.0, 3.0 + 2.0 * int(any(np.isfinite(br_exp[b]) and br_exp[b] > 0 for b in adj)))

        sc_sample = min(10.0, 5 * v2.clip01(r.trades / 600.0) + 2.5 * (1 - v2.clip01(r.max_year_positive_net_share / 0.65)) + 2.5 * (1 - v2.clip01(r.max_anchor_positive_net_share / 0.60)))
        total = sc_cal + sc_pl + sc_pool + sc_clock + sc_local + sc_broad + sc_sample

        rows.append({
            "candidate_id": r.candidate_id,
            "shape_rule": r.shape_rule,
            "local_scale_state": r.local_scale_state,
            "principal_local_scale_variable": principal,
            "local_scale_band": r.local_scale_band,
            "broad_regime": r.broad_regime,
            "lookback_min": r.lookback_min,
            "hold_min": r.hold_min,
            "trades": r.trades,
            "win_rate": r.win_rate,
            "net_pnl": r.net_pnl,
            "expectancy": r.expectancy,
            "pf": r.pf,
            "max_dd": r.max_dd,
            "max_loss_streak": r.max_loss_streak,
            "min_year_expectancy": r.min_year_expectancy,
            "calendar_score": sc_cal,
            "plateau_score": sc_pl,
            "pooled_economic_score": sc_pool,
            "clock_score": sc_clock,
            "local_scale_support_score": sc_local,
            "broad_regime_support_score": sc_broad,
            "sample_concentration_score": sc_sample,
            "robustness_score": total,
            "anchor_positive_fraction": af,
            "evaluable_hours": len(he),
            "hour_positive_fraction": hf,
            **d,
            "local_low_expectancy": bx["LOW"],
            "local_mid_expectancy": bx["MID"],
            "local_high_expectancy": bx["HIGH"],
            "broad_quiet_expectancy": br_exp["BROAD_QUIET"],
            "broad_normal_expectancy": br_exp["BROAD_NORMAL"],
            "broad_active_expectancy": br_exp["BROAD_ACTIVE"],
        })
    return pd.DataFrame(rows)


def freeze(scores: pd.DataFrame):
    if scores.empty:
        return scores.copy()
    q = scores.sort_values(["robustness_score", "min_year_expectancy", "pf"], ascending=[False, False, False])
    seen, rows = set(), []
    for r in q.itertuples(index=False):
        family = (r.shape_rule, r.principal_local_scale_variable, r.broad_regime)
        if family in seen:
            continue
        seen.add(family)
        rows.append(r._asdict())
        if len(rows) == 5:
            break
    z = pd.DataFrame(rows)
    z.insert(0, "freeze_rank", np.arange(1, len(z) + 1))
    z["freeze_status"] = "FROZEN_BEFORE_SECONDARY_HISTORICAL_CONFIRMATION"
    return z


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    econ, local_b, broad_b, frames, local_cache, broad_cache = build_economics(x5)
    plateau = plateau_table(econ)
    pmap = plateau.set_index("candidate_id").plateau_pass
    econ["plateau_pass"] = econ.candidate_id.map(pmap).fillna(False).astype(bool)
    econ["eligible"] = econ.pre_plateau_hard_gate & econ.plateau_pass
    eligible = econ[econ.eligible].copy()

    if len(eligible):
        years, anchors, hours, diag = eligible_diagnostics(x5, eligible, frames, local_cache, broad_cache)
        scores = score(eligible, plateau, hours, diag, econ)
        finalists = freeze(scores)
    else:
        years = pd.DataFrame()
        anchors = pd.DataFrame()
        hours = pd.DataFrame()
        scores = pd.DataFrame()
        finalists = pd.DataFrame()

    econ.to_csv(out("CandidateEconomics.csv"), index=False)
    local_b.to_csv(out("LocalScaleBoundaries.csv"), index=False)
    broad_b.to_csv(out("BroadVolBoundaries.csv"), index=False)
    plateau.to_csv(out("Plateau.csv"), index=False)
    years.to_csv(out("EligibleYearEconomics.csv"), index=False)
    anchors.to_csv(out("EligibleAnchorEconomics.csv"), index=False)
    hours.to_csv(out("EligibleHourEconomics.csv"), index=False)
    scores.to_csv(out("RobustnessScores.csv"), index=False)
    finalists.to_csv(out("FrozenFinalists.csv"), index=False)

    rejection = econ[[
        "candidate_id", "shape_rule", "local_scale_state", "broad_regime", "lookback_min", "hold_min",
        "pooled_gate", "year_gate", "concentration_gate", "plateau_pass", "eligible"
    ]].copy()
    rejection["rejection_reason"] = [
        "ELIGIBLE" if r.eligible else "|".join(
            (["POOLED_GATE"] if not r.pooled_gate else [])
            + (["YEAR_GATE"] if not r.year_gate else [])
            + (["CONCENTRATION_GATE"] if not r.concentration_gate else [])
            + (["PLATEAU_GATE"] if not r.plateau_pass else [])
        )
        for r in econ.itertuples(index=False)
    ]
    rejection.to_csv(out("Rejections.csv"), index=False)

    lines = [
        "# SOL Robust Character Discovery v3 — Development Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        f"Candidate points evaluated: **{len(econ):,}**.",
        "Development 2022–2024 only. External / Reference Validation / August were not evaluated during discovery.", "",
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
        lines += [
            "## Frozen finalists", "",
            "| Rank | Character | Local scale | Broad regime | LB | Hold | N | WR | Net | Exp | PF | DD | LS | Score |",
            "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in finalists.itertuples(index=False):
            lines.append(
                f"| {int(r.freeze_rank)} | `{r.shape_rule}` | `{r.local_scale_state}` | `{r.broad_regime}` | "
                f"{int(r.lookback_min)} | {int(r.hold_min)} | {int(r.trades)} | {100*r.win_rate:.2f}% | "
                f"${r.net_pnl:+.2f} | ${r.expectancy:+.2f} | {r.pf:.3f} | ${r.max_dd:.2f} | "
                f"{int(r.max_loss_streak)} | {r.robustness_score:.2f} |"
            )
        status = f"SOL_RCD_V3_FROZEN_{len(finalists)}_FINALISTS"
    else:
        lines += [
            "## Scientific verdict", "",
            "**ZERO finalists survived the preregistered RCD-v3 robustness process.**", "",
            "Per stop rule, no gate is loosened and no historical partition is exposed for rescue.",
        ]
        status = "SOL_RCD_V3_ZERO_FINALISTS"

    out("Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out("Status.txt").write_text(status + "\n", encoding="utf-8")
    print(status)
    print(out("Result.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
