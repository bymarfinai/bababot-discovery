#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e3_drive_strength_fast as e3
import eth_economic_first_e11_market_state_character as e11

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E12A_LONG_13_14WIB_CHARACTER"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_ATLAS = ROOT / f"{PFX}_SelectedAnchorAtlas.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (360, 375, 390, 405)  # 06:00, 06:15, 06:30, 06:45 UTC = 13:00..13:45 WIB
LOOKBACKS = (15, 30, 60, 120, 240, 360)
HOLDS = (60, 120, 240, 360, 720, 960)
YEARS = (2022, 2023, 2024)
NOTIONAL = 500.0
FEE = 0.75

STR_RULES = ("STR_B0_20", "STR_B20_40", "STR_B40_60", "STR_B60_80", "STR_B80_100")
SINGLE_STATE_RULES = tuple(r[0] for r in e11.RULES if "__" not in r[0])
E11_RULES = tuple(r[0] for r in e11.RULES)


def all_rules():
    rules = ["ALL", "DRIVE_UP", "DRIVE_DOWN"]
    rules += list(STR_RULES)
    rules += list(E11_RULES)
    for side in ("DRIVE_UP", "DRIVE_DOWN"):
        for s in SINGLE_STATE_RULES:
            rules.append(f"{side}__{s}")
        for s in STR_RULES:
            rules.append(f"{side}__{s}")
    if len(rules) != 90:
        raise AssertionError(f"expected 90 rules, got {len(rules)}")
    if len(set(rules)) != len(rules):
        raise AssertionError("duplicate character rules")
    return tuple(rules)

RULES = all_rules()
E11_RULE_MAP = {r[0]: r for r in e11.RULES}


def pct(x):
    return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"


def money(x):
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def summarize(net, gross):
    net = np.asarray(net, float)
    gross = np.asarray(gross, float)
    if len(net) == 0:
        return {
            "trades": 0, "win_rate": np.nan, "net_pnl": 0.0, "expectancy": np.nan,
            "pf": np.nan, "max_dd": np.nan, "max_loss_streak": 0, "max_win_streak": 0,
        }
    return e3.summarize(net, gross, 0)


def strength_mask(x, name):
    x = np.asarray(x, float)
    f = np.isfinite(x)
    bounds = {
        "STR_B0_20": (0.0, .20, False),
        "STR_B20_40": (.20, .40, False),
        "STR_B40_60": (.40, .60, False),
        "STR_B60_80": (.60, .80, False),
        "STR_B80_100": (.80, 1.00, True),
    }
    lo, hi, inclusive = bounds[name]
    return f & (x >= lo) & ((x <= hi) if inclusive else (x < hi))


def masks_for_frame(S: pd.DataFrame):
    drive = S.drive_return.to_numpy(float)
    out = {
        "ALL": np.ones(len(S), dtype=bool),
        "DRIVE_UP": drive > 0,
        "DRIVE_DOWN": drive < 0,
    }
    strength = S.strength_pct.to_numpy(float)
    for name in STR_RULES:
        out[name] = strength_mask(strength, name)
    for name, rule in E11_RULE_MAP.items():
        out[name] = e11.rule_mask(S, rule)
    for side in ("DRIVE_UP", "DRIVE_DOWN"):
        sm = out[side]
        for s in SINGLE_STATE_RULES:
            out[f"{side}__{s}"] = sm & out[s]
        for s in STR_RULES:
            out[f"{side}__{s}"] = sm & out[s]
    if set(out) != set(RULES):
        raise AssertionError("mask/rule mismatch")
    return out


def prep(x5):
    cache = {}
    for lb in LOOKBACKS:
        for clock in CLOCKS:
            S = e11.state_frame(x5, clock, lb)
            ent = pd.DatetimeIndex(S.entry_ts)
            pre = pd.DatetimeIndex(S.pre_ts)
            masks = masks_for_frame(S)
            for hold in HOLDS:
                ex, valid, xp, delta, _ = e3.hold_base(x5, S, hold)
                cache[(clock, lb, hold)] = (S, ent, pre, ex, valid, xp, delta, masks)
    return cache


def candidate(cache, lb, hold, rule):
    pa, pz = base.PARTS["development"]
    anchor_stats = []
    pooled = []
    for clock in CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        m = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & masks[rule]
        gross = NOTIONAL * delta[m]  # LONG only
        net = gross - FEE
        ts = ent[m]
        s = summarize(net, gross)
        evaluable = s["trades"] >= 40
        supportive = bool(
            evaluable and s["win_rate"] >= .52 and s["net_pnl"] > 0 and
            s["expectancy"] > 0 and s["pf"] >= 1.05 and
            s["max_dd"] <= 125 and s["max_loss_streak"] <= 10
        )
        anchor_stats.append((clock, s, evaluable, supportive))
        if len(net):
            pooled.append(pd.DataFrame({"entry_ts": ts, "gross": gross, "net": net, "clock": clock}))

    if pooled:
        T = pd.concat(pooled, ignore_index=True).sort_values(["entry_ts", "clock"]).reset_index(drop=True)
        ps = summarize(T.net.to_numpy(float), T.gross.to_numpy(float))
    else:
        T = pd.DataFrame(columns=["entry_ts", "gross", "net", "clock"])
        ps = summarize(np.array([]), np.array([]))

    row = {
        "lookback_min": lb, "hold_min": hold, "character_rule": rule,
        **ps,
        "evaluable_anchors": int(sum(x[2] for x in anchor_stats)),
        "supportive_anchors": int(sum(x[3] for x in anchor_stats)),
    }
    for clock, s, ev, sup in anchor_stats:
        k = f"a{clock}"
        row.update({
            f"{k}_trades": s["trades"], f"{k}_wr": s["win_rate"], f"{k}_net": s["net_pnl"],
            f"{k}_exp": s["expectancy"], f"{k}_pf": s["pf"], f"{k}_dd": s["max_dd"],
            f"{k}_evaluable": ev, f"{k}_supportive": sup,
        })

    good_years_wr55 = 0
    min_year_exp = np.inf
    era_gate = True
    for y in YEARS:
        if len(T):
            ym = pd.DatetimeIndex(T.entry_ts).year == y
            ys = summarize(T.loc[ym, "net"].to_numpy(float), T.loc[ym, "gross"].to_numpy(float))
        else:
            ys = summarize(np.array([]), np.array([]))
        row.update({
            f"y{y}_trades": ys["trades"], f"y{y}_wr": ys["win_rate"], f"y{y}_net": ys["net_pnl"],
            f"y{y}_exp": ys["expectancy"], f"y{y}_pf": ys["pf"],
        })
        ok = bool(
            ys["trades"] >= 40 and np.isfinite(ys["win_rate"]) and ys["win_rate"] >= .52 and
            ys["net_pnl"] > 0 and np.isfinite(ys["expectancy"]) and ys["expectancy"] > 0 and
            np.isfinite(ys["pf"]) and ys["pf"] >= 1.05
        )
        era_gate &= ok
        good_years_wr55 += int(np.isfinite(ys["win_rate"]) and ys["win_rate"] >= .55)
        min_year_exp = min(min_year_exp, ys["expectancy"] if np.isfinite(ys["expectancy"]) else -np.inf)

    row["years_wr55"] = good_years_wr55
    row["min_year_exp"] = float(min_year_exp)
    row["anchor_gate"] = row["evaluable_anchors"] >= 3 and row["supportive_anchors"] >= 3
    row["pooled_gate"] = bool(
        row["trades"] >= 160 and np.isfinite(row["win_rate"]) and row["win_rate"] >= .55 and
        row["net_pnl"] > 0 and np.isfinite(row["expectancy"]) and row["expectancy"] >= .50 and
        np.isfinite(row["pf"]) and row["pf"] >= 1.20 and row["max_dd"] <= 125 and
        row["max_loss_streak"] <= 8
    )
    row["era_gate"] = bool(era_gate and good_years_wr55 >= 2)
    row["candidate_gate"] = bool(row["anchor_gate"] and row["pooled_gate"] and row["era_gate"])
    return row


def build_grid(cache):
    rows = [candidate(cache, lb, hold, rule) for lb in LOOKBACKS for hold in HOLDS for rule in RULES]
    D = pd.DataFrame(rows)
    if len(D) != 3240:
        raise AssertionError(f"expected 3240 candidates, got {len(D)}")
    C = D[D.candidate_gate].copy().sort_values(
        ["min_year_exp", "supportive_anchors", "expectancy", "win_rate", "pf", "max_dd",
         "max_loss_streak", "hold_min", "lookback_min", "character_rule"],
        ascending=[False, False, False, False, False, True, True, True, True, True],
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C) + 1)
    return D, C


def selected_anchor_atlas(D, sel):
    rows = []
    for clock in CLOCKS:
        k = f"a{clock}"
        rows.append({
            "clock_utc": e11.hhmm(clock), "clock_wib": e11.wib(clock),
            "trades": int(sel[f"{k}_trades"]), "win_rate": sel[f"{k}_wr"],
            "net_pnl": sel[f"{k}_net"], "expectancy": sel[f"{k}_exp"],
            "pf": sel[f"{k}_pf"], "max_dd": sel[f"{k}_dd"],
            "evaluable": bool(sel[f"{k}_evaluable"]), "supportive": bool(sel[f"{k}_supportive"]),
        })
    return pd.DataFrame(rows)


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")
    cache = prep(x5)
    D, C = build_grid(cache)
    D.to_csv(OUT_GRID, index=False)
    C.to_csv(OUT_LEADER, index=False)

    lines = [
        "# ETH Economic-First E12A — 13:00–14:00 WIB LONG Character Discovery Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Direction: **LONG only**.",
        "Time habitat: **13:00–14:00 WIB only** (06:00, 06:15, 06:30, 06:45 UTC anchors).",
        "Development only; OOS remained closed by preregistration.",
        f"Character rules: **{len(RULES)}**; total Development candidates: **{len(D)}**; full-gate passers: **{len(C)}**.", "",
        "## Best Development LONG characters", "",
        "| # | Character | LB | Hold | N | WR | Net | Exp | PF | DD | Anchors | 2022 WR/Exp | 2023 | 2024 | Gate |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    top = D.sort_values(
        ["candidate_gate", "min_year_exp", "supportive_anchors", "expectancy", "win_rate", "pf"],
        ascending=[False, False, False, False, False, False],
    ).head(25)
    for i, r in enumerate(top.itertuples(index=False), 1):
        lines.append(
            f"| {i} | {r.character_rule} | {int(r.lookback_min)}m | {int(r.hold_min)}m | {int(r.trades)} | "
            f"{pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | "
            f"{int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | {pct(r.y2022_wr)}/{money(r.y2022_exp)} | "
            f"{pct(r.y2023_wr)}/{money(r.y2023_exp)} | {pct(r.y2024_wr)}/{money(r.y2024_exp)} | "
            f"{'YES' if r.candidate_gate else 'NO'} |"
        )

    if len(C) == 0:
        status = "ETH_ECONOMIC_FIRST_E12A_NO_LONG_CHARACTER"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", f"**Status: {status}**", "",
                  "No 13:00–14:00 WIB LONG character passed the preregistered anchor-stability + pooled-economics + all-era gates.",
                  "No gate relaxation and no OOS exposure.", "", "Research/shadow only."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text())
        return

    sel = C.iloc[0]
    atlas = selected_anchor_atlas(D, sel)
    atlas.to_csv(OUT_ATLAS, index=False)
    status = "ETH_ECONOMIC_FIRST_E12A_LONG_CHARACTER_FOUND"
    OUT_STATUS.write_text(status + "\n")
    lines += ["", "## Development-selected LONG character", "",
              f"**{sel['character_rule']} / LB{int(sel['lookback_min'])} / hold{int(sel['hold_min'])}m**", "",
              f"Pooled descriptive N **{int(sel['trades'])}**, WR **{pct(sel['win_rate'])}**, net **{money(sel['net_pnl'])}**, "
              f"exp **{money(sel['expectancy'])}/trade**, PF **{float(sel['pf']):.3f}**, DD **{money(sel['max_dd'])}**, "
              f"loss streak **{int(sel['max_loss_streak'])}**, supportive anchors **{int(sel['supportive_anchors'])}/4**.", "",
              "### Anchor atlas", "",
              "| UTC | WIB | N | WR | Net | Exp | PF | DD | Supportive |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in atlas.itertuples(index=False):
        lines.append(f"| {r.clock_utc} | {r.clock_wib} | {r.trades} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {'YES' if r.supportive else 'NO'} |")
    lines += ["", "### Cross-era", "",
              f"2022: N {int(sel['y2022_trades'])}, WR {pct(sel['y2022_wr'])}, exp {money(sel['y2022_exp'])}, PF {float(sel['y2022_pf']):.3f}.",
              f"2023: N {int(sel['y2023_trades'])}, WR {pct(sel['y2023_wr'])}, exp {money(sel['y2023_exp'])}, PF {float(sel['y2023_pf']):.3f}.",
              f"2024: N {int(sel['y2024_trades'])}, WR {pct(sel['y2024_wr'])}, exp {money(sel['y2024_exp'])}, PF {float(sel['y2024_pf']):.3f}.", "",
              f"**Status: {status}**", "",
              "E12A is discovery-only. OOS remains unopened. The exact selected character must be frozen before any E12B validation/refinement.", "",
              "Research/shadow only; no live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
