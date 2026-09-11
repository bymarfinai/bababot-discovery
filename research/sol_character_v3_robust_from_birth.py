#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

import sol_economic_first_h00_long_07_08wib_character as core

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_CHARACTER_V3_ROBUST_FROM_BIRTH"
RESEARCH_START = pd.Timestamp("2022-01-01T00:00:00Z")
RESEARCH_END = pd.Timestamp("2026-07-30T00:00:00Z")
HISTORY_START = pd.Timestamp("2020-01-01T00:00:00Z")
LOAD_END_MONTH = pd.Timestamp("2026-08-01T00:00:00Z")
YEARS = (2022, 2023, 2024, 2025, 2026)
LOOKBACKS = core.LOOKBACKS
HOLDS = core.HOLDS
NOTIONAL = core.NOTIONAL
FEE = core.FEE
BAR5 = pd.Timedelta(minutes=5)

MECHANISMS = (
    "DOWN_SHOCK_REVERSAL",
    "DOWN_INEFFICIENT_SNAPBACK",
    "DOWN_RANGE_EXHAUSTION",
    "DOWN_VOL_EXHAUSTION",
    "UP_SHOCK_CONTINUATION",
    "UP_EFFICIENT_CONTINUATION",
    "UP_VOL_EXPANSION_CONTINUATION",
    "UP_COMPRESSION_CONTINUATION",
)


def pct(x: float) -> str:
    return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"


def money(x: float) -> str:
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def v3_urls(symbol: str) -> list[str]:
    urls = []
    m = pd.Timestamp(HISTORY_START.year, HISTORY_START.month, 1, tz="UTC")
    while m < LOAD_END_MONTH:
        ym = m.strftime("%Y-%m")
        urls.append(f"{core.base.BASE}/monthly/klines/{symbol}/5m/{symbol}-5m-{ym}.zip")
        m += pd.offsets.MonthBegin(1)
    return urls


def load5_v3(symbol: str) -> tuple[pd.DataFrame, float]:
    frames = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(core.base.fetch_one, url) for url in v3_urls(symbol)]
        for fut in as_completed(futs):
            z = fut.result()
            if z is not None and len(z):
                frames.append(z)
    if not frames:
        raise RuntimeError(f"no {symbol} data")
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x.ts, errors="coerce")
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x["ts"] = pd.to_datetime(t, unit="ms", utc=True, errors="coerce")
    for c in ("open", "high", "low", "close"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna().drop_duplicates("ts").sort_values("ts")
    x = x[(x.ts >= HISTORY_START) & (x.ts < RESEARCH_END)].set_index("ts")
    if len(x) == 0:
        raise RuntimeError("empty V3 load")
    expected = int((x.index[-1] - x.index[0]) / BAR5) + 1
    coverage = len(x) / expected
    if coverage < 0.995:
        raise RuntimeError(f"SOL V3 coverage too low: {coverage:.6%}")
    if x.index.max() >= pd.Timestamp("2026-08-01T00:00:00Z"):
        raise AssertionError("August 2026 entered V3 loader")
    return x, coverage


def mechanism_masks(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    drive = frame.drive_return.to_numpy(float)
    strength = frame.strength_pct.to_numpy(float)
    eff = frame.eff_pct.to_numpy(float)
    rv = frame.rv_pct.to_numpy(float)
    rng = frame.range_pct.to_numpy(float)
    masks = {
        "DOWN_SHOCK_REVERSAL": (drive < 0) & np.isfinite(strength) & (strength >= 0.80),
        "DOWN_INEFFICIENT_SNAPBACK": (drive < 0) & np.isfinite(eff) & (eff < 1/3),
        "DOWN_RANGE_EXHAUSTION": (drive < 0) & np.isfinite(rng) & (rng >= 2/3),
        "DOWN_VOL_EXHAUSTION": (drive < 0) & np.isfinite(rv) & (rv >= 2/3),
        "UP_SHOCK_CONTINUATION": (drive > 0) & np.isfinite(strength) & (strength >= 0.80),
        "UP_EFFICIENT_CONTINUATION": (drive > 0) & np.isfinite(eff) & (eff >= 2/3),
        "UP_VOL_EXPANSION_CONTINUATION": (drive > 0) & np.isfinite(rv) & (rv >= 2/3),
        "UP_COMPRESSION_CONTINUATION": (drive > 0) & np.isfinite(rng) & (rng < 1/3),
    }
    if tuple(masks) != MECHANISMS:
        raise AssertionError("mechanism mismatch")
    return masks


def session_clocks(session_idx: int) -> tuple[int, ...]:
    if not 0 <= session_idx < 12:
        raise ValueError(session_idx)
    start = session_idx * 120
    return tuple(start + 15*i for i in range(8))


def prepare_session(x5: pd.DataFrame, clocks: tuple[int, ...]) -> dict:
    cache = {}
    for lb in LOOKBACKS:
        for clock in clocks:
            frame = core.state_frame(x5, clock, lb)
            entry_ts = pd.DatetimeIndex(frame.entry_ts)
            pre_ts = pd.DatetimeIndex(frame.pre_ts)
            masks = mechanism_masks(frame)
            for hold in HOLDS:
                exit_ts, valid, returns = core.hold_returns(x5, frame, hold)
                cache[(clock, lb, hold)] = (entry_ts, pre_ts, pd.DatetimeIndex(exit_ts), valid, returns, masks)
    return cache


def exposure_clusters(trades: pd.DataFrame) -> int:
    if trades.empty:
        return 0
    z = trades.sort_values(["entry_ts", "exit_ts"]).reset_index(drop=True)
    clusters = 0
    current_end = None
    for entry, exit_ in zip(z.entry_ts, z.exit_ts):
        if current_end is None or entry >= current_end:
            clusters += 1
            current_end = exit_
        elif exit_ > current_end:
            current_end = exit_
    return clusters


def stats_frame(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return core.summarize(np.array([]), np.array([]))
    z = trades.sort_values(["entry_ts", "clock"])
    return core.summarize(z.net.to_numpy(float), z.gross.to_numpy(float))


def evaluate_candidate(cache: dict, clocks: tuple[int, ...], session_idx: int, lb: int, hold: int, mech: str) -> dict:
    parts = []
    anchor_rows = []
    for clock in clocks:
        entry_ts, pre_ts, exit_ts, valid, returns, masks = cache[(clock, lb, hold)]
        selected = (
            valid
            & (pre_ts >= RESEARCH_START)
            & (entry_ts >= RESEARCH_START)
            & (exit_ts < RESEARCH_END)
            & masks[mech]
        )
        gross = NOTIONAL * returns[selected]
        net = gross - FEE
        a = pd.DataFrame({
            "entry_ts": entry_ts[selected],
            "exit_ts": exit_ts[selected],
            "gross": gross,
            "net": net,
            "clock": clock,
        })
        st = stats_frame(a)
        evaluable = st["trades"] >= 25
        supportive = bool(
            evaluable
            and np.isfinite(st["win_rate"]) and st["win_rate"] >= 0.54
            and st["expectancy"] > 0
            and np.isfinite(st["pf"]) and st["pf"] >= 1.10
            and st["max_dd"] <= 150
            and st["max_loss_streak"] <= 10
        )
        catastrophic = bool(
            evaluable and (
                (not np.isfinite(st["expectancy"])) or st["expectancy"] < -0.50
                or (not np.isfinite(st["pf"])) or st["pf"] < 0.90
            )
        )
        anchor_rows.append((clock, st, evaluable, supportive, catastrophic))
        if not a.empty:
            parts.append(a)

    trades = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["entry_ts", "exit_ts", "gross", "net", "clock"]
    )
    trades = trades.sort_values(["entry_ts", "clock"]).reset_index(drop=True)
    pooled = stats_frame(trades)
    row = {
        "session_idx": session_idx,
        "session_utc": f"{session_idx*2:02d}-{(session_idx*2+2)%24:02d}",
        "session_wib": f"{(session_idx*2+7)%24:02d}-{(session_idx*2+9)%24:02d}",
        "mechanism": mech,
        "lookback_min": lb,
        "hold_min": hold,
        **pooled,
    }

    years_wr60 = 0
    min_year_exp = np.inf
    era_ok = True
    positive_years = 0
    for year in YEARS:
        yt = trades[pd.DatetimeIndex(trades.entry_ts).year == year] if not trades.empty else trades
        st = stats_frame(yt)
        row.update({
            f"y{year}_n": st["trades"],
            f"y{year}_wr": st["win_rate"],
            f"y{year}_exp": st["expectancy"],
            f"y{year}_pf": st["pf"],
            f"y{year}_net": st["net_pnl"],
        })
        ok = bool(
            st["trades"] >= 30
            and np.isfinite(st["win_rate"]) and st["win_rate"] >= 0.55
            and st["net_pnl"] > 0
            and np.isfinite(st["expectancy"]) and st["expectancy"] > 0
            and np.isfinite(st["pf"]) and st["pf"] >= 1.15
        )
        era_ok &= ok
        years_wr60 += int(np.isfinite(st["win_rate"]) and st["win_rate"] >= 0.60)
        positive_years += int(np.isfinite(st["expectancy"]) and st["expectancy"] > 0)
        min_year_exp = min(min_year_exp, st["expectancy"] if np.isfinite(st["expectancy"]) else -np.inf)
    row["years_wr60"] = years_wr60
    row["positive_years"] = positive_years
    row["min_year_exp"] = float(min_year_exp)
    row["era_gate"] = bool(era_ok and years_wr60 >= 3)

    start_hour = session_idx * 2
    hour_supports = 0
    for j, hour in enumerate((start_hour, start_hour + 1)):
        ht = trades[(trades.clock // 60) == hour] if not trades.empty else trades
        st = stats_frame(ht)
        row.update({
            f"h{j}_n": st["trades"],
            f"h{j}_wr": st["win_rate"],
            f"h{j}_exp": st["expectancy"],
            f"h{j}_pf": st["pf"],
            f"h{j}_dd": st["max_dd"],
            f"h{j}_ls": st["max_loss_streak"],
        })
        h_ok = bool(
            st["trades"] >= 100
            and np.isfinite(st["win_rate"]) and st["win_rate"] >= 0.56
            and np.isfinite(st["expectancy"]) and st["expectancy"] >= 0.50
            and np.isfinite(st["pf"]) and st["pf"] >= 1.25
            and st["max_dd"] <= 200
            and st["max_loss_streak"] <= 10
        )
        hour_supports += int(h_ok)
    row["supportive_hours"] = hour_supports

    eval_anchors = sum(int(x[2]) for x in anchor_rows)
    supportive_anchors = sum(int(x[3]) for x in anchor_rows)
    catastrophic_anchors = sum(int(x[4]) for x in anchor_rows)
    row["evaluable_anchors"] = eval_anchors
    row["supportive_anchors"] = supportive_anchors
    row["catastrophic_anchors"] = catastrophic_anchors
    row["habitat_gate"] = bool(
        hour_supports == 2
        and eval_anchors >= 7
        and supportive_anchors >= 6
        and catastrophic_anchors == 0
    )

    eff_n = exposure_clusters(trades)
    eff_ratio = eff_n / len(trades) if len(trades) else 0.0
    row["effective_n"] = eff_n
    row["effective_n_ratio"] = eff_ratio
    row["effective_n_gate"] = bool(eff_n >= 120 and eff_ratio >= 0.35)

    row["pooled_gate"] = bool(
        pooled["trades"] >= 300
        and np.isfinite(pooled["win_rate"]) and pooled["win_rate"] >= 0.60
        and pooled["net_pnl"] > 0
        and np.isfinite(pooled["expectancy"]) and pooled["expectancy"] >= 1.50
        and np.isfinite(pooled["pf"]) and pooled["pf"] >= 1.70
        and pooled["max_dd"] <= 175
        and pooled["max_loss_streak"] <= 8
    )
    row["pre_neighborhood_gate"] = bool(
        row["pooled_gate"] and row["era_gate"] and row["habitat_gate"] and row["effective_n_gate"]
    )
    return row


def neighbor_is_supportive(row: pd.Series) -> bool:
    positive_years = sum(
        int(np.isfinite(row[f"y{year}_exp"]) and row[f"y{year}_exp"] > 0)
        for year in YEARS
    )
    return bool(
        np.isfinite(row.win_rate) and row.win_rate >= 0.57
        and np.isfinite(row.expectancy) and row.expectancy >= 1.00
        and np.isfinite(row.pf) and row.pf >= 1.40
        and row.net_pnl > 0
        and row.max_dd <= 225
        and positive_years >= 4
        and np.isfinite(row.h0_exp) and row.h0_exp > 0
        and np.isfinite(row.h1_exp) and row.h1_exp > 0
    )


def apply_neighborhood(grid: pd.DataFrame) -> pd.DataFrame:
    grid = grid.copy()
    keymap = {
        (r.mechanism, int(r.lookback_min), int(r.hold_min)): idx
        for idx, r in grid.iterrows()
    }
    lb_i = {v: i for i, v in enumerate(LOOKBACKS)}
    h_i = {v: i for i, v in enumerate(HOLDS)}
    available_list = []
    supportive_list = []
    for _, r in grid.iterrows():
        lb = int(r.lookback_min)
        hold = int(r.hold_min)
        mech = r.mechanism
        keys = []
        i = lb_i[lb]
        if i > 0:
            keys.append((mech, LOOKBACKS[i-1], hold))
        if i + 1 < len(LOOKBACKS):
            keys.append((mech, LOOKBACKS[i+1], hold))
        j = h_i[hold]
        if j > 0:
            keys.append((mech, lb, HOLDS[j-1]))
        if j + 1 < len(HOLDS):
            keys.append((mech, lb, HOLDS[j+1]))
        neighbors = [grid.loc[keymap[k]] for k in keys if k in keymap]
        available_list.append(len(neighbors))
        supportive_list.append(sum(int(neighbor_is_supportive(n)) for n in neighbors))
    grid["available_neighbors"] = available_list
    grid["supportive_neighbors"] = supportive_list
    grid["neighborhood_gate"] = (
        (grid.available_neighbors >= 3) & (grid.supportive_neighbors >= 2)
    )
    grid["candidate_gate"] = grid.pre_neighborhood_gate & grid.neighborhood_gate
    return grid


def run_session(session_idx: int, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    core.base.synthetic_tests()
    x5, coverage = load5_v3("SOLUSDT")
    clocks = session_clocks(session_idx)
    cache = prepare_session(x5, clocks)
    rows = [
        evaluate_candidate(cache, clocks, session_idx, lb, hold, mech)
        for lb in LOOKBACKS
        for hold in HOLDS
        for mech in MECHANISMS
    ]
    grid = apply_neighborhood(pd.DataFrame(rows))
    if len(grid) != 288:
        raise AssertionError(f"expected 288 candidates, got {len(grid)}")
    grid["coverage"] = coverage
    path = outdir / f"{PFX}_Session_{session_idx:02d}_Grid.csv"
    grid.to_csv(path, index=False)
    status = "FOUND" if grid.candidate_gate.any() else "NO_CHARACTER"
    (outdir / f"{PFX}_Session_{session_idx:02d}_Status.txt").write_text(status + "\n")
    print(f"session={session_idx:02d} candidates={len(grid)} full={int(grid.candidate_gate.sum())} pre_neigh={int(grid.pre_neighborhood_gate.sum())} era={int(grid.era_gate.sum())}")


def aggregate(indir: Path, outdir: Path) -> None:
    paths = sorted(indir.rglob(f"{PFX}_Session_*_Grid.csv"))
    if len(paths) != 12:
        raise AssertionError(f"expected 12 session grids, found {len(paths)}")
    grid = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    if len(grid) != 3456:
        raise AssertionError(f"expected 3456 candidates, got {len(grid)}")
    if grid.session_idx.nunique() != 12:
        raise AssertionError("missing V3 session")
    outdir.mkdir(parents=True, exist_ok=True)
    grid.to_csv(outdir / f"{PFX}_Grid.csv", index=False)

    passers = grid[grid.candidate_gate].copy().sort_values(
        ["min_year_exp", "supportive_neighbors", "win_rate", "expectancy", "pf", "effective_n", "max_dd", "hold_min", "lookback_min", "mechanism", "session_idx"],
        ascending=[False, False, False, False, False, False, True, True, True, True, True],
    ).reset_index(drop=True)
    passers["rank"] = np.arange(1, len(passers)+1)
    passers.to_csv(outdir / f"{PFX}_Passers.csv", index=False)

    g = grid.copy()
    g["gate_count"] = g[["pooled_gate", "era_gate", "habitat_gate", "effective_n_gate", "neighborhood_gate"]].astype(int).sum(axis=1)
    top = g.sort_values(
        ["candidate_gate", "pre_neighborhood_gate", "gate_count", "era_gate", "habitat_gate", "pooled_gate", "min_year_exp", "win_rate", "expectancy", "pf"],
        ascending=[False, False, False, False, False, False, False, False, False, False],
    ).head(50)
    top.to_csv(outdir / f"{PFX}_Top50.csv", index=False)

    coverage = float(grid.coverage.min())
    lines = [
        "# SOL Character Discovery V3 — Robust-from-Birth Result",
        "",
        f"SOLUSDT 5m coverage through the research cutoff: **{coverage:.4%}**.",
        "**August 2026 was not downloaded, loaded, scored, ranked, or used for tie-breaking.**",
        f"Raw V3 universe: **{len(grid):,} mechanism-region candidates**.",
        f"Full robustness-from-birth passers: **{len(passers)}**.",
        "",
        "## Frozen gate counts",
        "",
        f"- pooled performance gate: **{int(grid.pooled_gate.sum())}**",
        f"- all-era gate: **{int(grid.era_gate.sum())}**",
        f"- two-hour habitat plateau gate: **{int(grid.habitat_gate.sum())}**",
        f"- overlap-adjusted effective-N gate: **{int(grid.effective_n_gate.sum())}**",
        f"- LB/hold neighborhood plateau gate: **{int(grid.neighborhood_gate.sum())}**",
        f"- pre-neighborhood passers: **{int(grid.pre_neighborhood_gate.sum())}**",
        f"- full passers: **{int(grid.candidate_gate.sum())}**",
        "",
    ]
    if len(passers):
        s = passers.iloc[0]
        status = "SOL_CHARACTER_V3_ROBUST_CHARACTER_FOUND"
        lines += [
            "## Selected robust-from-birth SOL LONG character",
            "",
            f"**{s['mechanism']} / {s['session_utc']} UTC ({s['session_wib']} WIB) / LB{int(s['lookback_min'])} / hold{int(s['hold_min'])}m**",
            "",
            f"N **{int(s['trades'])}**, effective N **{int(s['effective_n'])} ({pct(s['effective_n_ratio'])})**, WR **{pct(s['win_rate'])}**, net **{money(s['net_pnl'])}**, expectancy **{money(s['expectancy'])}/trade**, PF **{s['pf']:.3f}**, DD **{money(s['max_dd'])}**, loss streak **{int(s['max_loss_streak'])}**.",
            "",
            f"Habitat: both hours supportive; anchors **{int(s['supportive_anchors'])}/{int(s['evaluable_anchors'])}** supportive; parameter neighbors **{int(s['supportive_neighbors'])}/{int(s['available_neighbors'])}** supportive.",
            "",
            "### Cross-era",
            "",
            "| Year | N | WR | Exp | PF |",
            "|---:|---:|---:|---:|---:|",
        ]
        for year in YEARS:
            lines.append(f"| {year} | {int(s[f'y{year}_n'])} | {pct(s[f'y{year}_wr'])} | {money(s[f'y{year}_exp'])} | {s[f'y{year}_pf']:.3f} |")
        lines += ["", f"**Status: {status}**", "", "Research/shadow only. Freeze before any August holdout test."]
    else:
        status = "SOL_CHARACTER_V3_ROBUST_FROM_BIRTH_NO_CHARACTER"
        lines += [
            "## Decision",
            "",
            "No mechanism-region candidate passed every preregistered high-performance and robustness gate. No threshold was relaxed.",
            "",
            "## Closest diagnostics",
            "",
            "| # | WIB | Mechanism | LB | Hold | N | EffN | WR | Exp | PF | DD | Pool | Era | Habitat | EffN | Neigh | Gates |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---:|",
        ]
        for rank, r in enumerate(top.head(20).itertuples(index=False), 1):
            lines.append(
                f"| {rank} | {r.session_wib} | {r.mechanism} | {int(r.lookback_min)} | {int(r.hold_min)} | {int(r.trades)} | {int(r.effective_n)} | {pct(r.win_rate)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {'Y' if r.pooled_gate else 'N'} | {'Y' if r.era_gate else 'N'} | {'Y' if r.habitat_gate else 'N'} | {'Y' if r.effective_n_gate else 'N'} | {'Y' if r.neighborhood_gate else 'N'} | {int(r.gate_count)} |"
            )
        if len(top):
            c = top.iloc[0]
            lines += [
                "",
                "### Closest candidate cross-era",
                "",
                f"**{c['mechanism']} / {c['session_utc']} UTC ({c['session_wib']} WIB) / LB{int(c['lookback_min'])} / hold{int(c['hold_min'])}m**",
                "",
                "| Year | N | WR | Exp | PF |",
                "|---:|---:|---:|---:|---:|",
            ]
            for year in YEARS:
                lines.append(f"| {year} | {int(c[f'y{year}_n'])} | {pct(c[f'y{year}_wr'])} | {money(c[f'y{year}_exp'])} | {c[f'y{year}_pf']:.3f} |")
            lines += [
                "",
                f"Hours supportive: **{int(c['supportive_hours'])}/2**; anchors supportive: **{int(c['supportive_anchors'])}/{int(c['evaluable_anchors'])}**; neighbors supportive: **{int(c['supportive_neighbors'])}/{int(c['available_neighbors'])}**.",
            ]
        lines += ["", f"**Status: {status}**", "", "Research/shadow only. August 2026 remains pristine."]

    (outdir / f"{PFX}_Result.md").write_text("\n".join(lines) + "\n")
    (outdir / f"{PFX}_Status.txt").write_text(status + "\n")
    print((outdir / f"{PFX}_Result.md").read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--session", type=int)
    g.add_argument("--aggregate", type=Path)
    ap.add_argument("--outdir", type=Path, default=ROOT)
    args = ap.parse_args()
    if args.session is not None:
        run_session(args.session, args.outdir)
    else:
        aggregate(args.aggregate, args.outdir)


if __name__ == "__main__":
    main()
