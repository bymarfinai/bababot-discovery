#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base


ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ECONOMIC_FIRST_H00_LONG_07_08WIB_CHARACTER"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_ATLAS = ROOT / f"{PFX}_SelectedAnchorAtlas.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (0, 15, 30, 45)  # 00:00..00:45 UTC = 07:00..07:45 WIB
LOOKBACKS = (15, 30, 60, 120, 240, 360)
HOLDS = (60, 120, 240, 360, 720, 960)
YEARS = (2022, 2023, 2024)
NOTIONAL = 500.0
FEE = 0.75
BAR_MIN = 5
ROLL_N = 60
MIN_HIST = 40
BINS = ("LOW", "MID", "HIGH")
FEATURES = ("EFF", "RV", "RANGE", "EXT")
PAIR_FEATURES = (("EFF", "RV"), ("EFF", "RANGE"), ("EFF", "EXT"), ("RV", "RANGE"))
STR_RULES = ("STR_B0_20", "STR_B20_40", "STR_B40_60", "STR_B60_80", "STR_B80_100")


def hhmm(minutes: int) -> str:
    minutes %= 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def wib(minutes: int) -> str:
    return hhmm(minutes + 420)


def pct(value: float) -> str:
    return "nan" if not np.isfinite(value) else f"{100 * float(value):.2f}%"


def money(value: float) -> str:
    return "nan" if not np.isfinite(value) else f"${float(value):+.2f}"


def profit_factor(pnls: np.ndarray) -> float:
    positive = float(pnls[pnls > 0].sum())
    negative = float(-pnls[pnls < 0].sum())
    if negative == 0:
        return np.inf if positive > 0 else np.nan
    return positive / negative


def max_drawdown(pnls: np.ndarray) -> float:
    if len(pnls) == 0:
        return np.nan
    cumulative = np.cumsum(pnls.astype(float))
    peaks = np.maximum.accumulate(np.r_[0.0, cumulative])
    return float(np.max(peaks[1:] - cumulative))


def streaks(pnls: np.ndarray) -> tuple[int, int]:
    max_loss = max_win = current_loss = current_win = 0
    for pnl in pnls:
        if pnl > 0:
            current_win += 1
            current_loss = 0
            max_win = max(max_win, current_win)
        else:
            current_loss += 1
            current_win = 0
            max_loss = max(max_loss, current_loss)
    return max_loss, max_win


def summarize(net: np.ndarray, gross: np.ndarray) -> dict:
    net = np.asarray(net, float)
    gross = np.asarray(gross, float)
    if len(net) == 0:
        return {
            "trades": 0,
            "win_rate": np.nan,
            "net_pnl": 0.0,
            "expectancy": np.nan,
            "pf": np.nan,
            "max_dd": np.nan,
            "max_loss_streak": 0,
            "max_win_streak": 0,
        }
    max_loss, max_win = streaks(net)
    return {
        "trades": int(len(net)),
        "win_rate": float((net > 0).mean()),
        "net_pnl": float(net.sum()),
        "expectancy": float(net.mean()),
        "pf": float(profit_factor(net)),
        "max_dd": float(max_drawdown(net)),
        "max_loss_streak": int(max_loss),
        "max_win_streak": int(max_win),
    }


def causal_percentile(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, float)
    out = np.full(len(values), np.nan, float)
    for i in range(MIN_HIST, len(values)):
        previous = values[max(0, i - ROLL_N):i]
        previous = previous[np.isfinite(previous)]
        if len(previous) >= MIN_HIST and np.isfinite(values[i]):
            out[i] = float(np.mean(previous <= values[i]))
    return out


def signal_frame(x5: pd.DataFrame, clock: int, lookback: int) -> pd.DataFrame:
    days = pd.date_range(x5.index.min().normalize(), x5.index.max().normalize(), freq="D", tz="UTC")
    days = days[np.array([day.weekday() < 5 for day in days], dtype=bool)]
    entry_ts = days + pd.Timedelta(minutes=clock)
    pre_ts = entry_ts - pd.Timedelta(minutes=lookback)
    pre_ix = x5.index.get_indexer(pre_ts)
    entry_ix = x5.index.get_indexer(entry_ts)
    valid = (pre_ix >= 0) & (entry_ix >= 0) & ((entry_ix - pre_ix) == lookback // BAR_MIN)
    entry_ts = entry_ts[valid]
    pre_ts = pre_ts[valid]
    pre_ix = pre_ix[valid]
    entry_ix = entry_ix[valid]
    opens = x5.open.to_numpy(float)
    pre_price = opens[pre_ix]
    entry_price = opens[entry_ix]
    drive = (entry_price - pre_price) / pre_price
    nonzero = drive != 0.0
    entry_ts = entry_ts[nonzero]
    pre_ts = pre_ts[nonzero]
    pre_ix = pre_ix[nonzero]
    entry_ix = entry_ix[nonzero]
    pre_price = pre_price[nonzero]
    entry_price = entry_price[nonzero]
    drive = drive[nonzero]
    return pd.DataFrame({
        "pre_ts": pre_ts,
        "entry_ts": entry_ts,
        "pre_ix": pre_ix,
        "entry_ix": entry_ix,
        "pre_price": pre_price,
        "entry_price": entry_price,
        "drive_return": drive,
        "strength_pct": causal_percentile(np.abs(drive)),
    })


def state_frame(x5: pd.DataFrame, clock: int, lookback: int) -> pd.DataFrame:
    frame = signal_frame(x5, clock, lookback).copy()
    opens = x5.open.to_numpy(float)
    highs = x5.high.to_numpy(float)
    lows = x5.low.to_numpy(float)
    efficiency = np.full(len(frame), np.nan, float)
    realized_volatility = np.full(len(frame), np.nan, float)
    realized_range = np.full(len(frame), np.nan, float)
    terminal_location = np.full(len(frame), np.nan, float)
    drive = frame.drive_return.to_numpy(float)

    for row, (start, end) in enumerate(zip(frame.pre_ix.to_numpy(int), frame.entry_ix.to_numpy(int))):
        if start < 0 or end <= start or (end - start) != lookback // BAR_MIN:
            continue
        path = opens[start:end + 1]
        changes = np.diff(path)
        denominator = float(np.abs(changes).sum())
        efficiency[row] = abs(path[-1] - path[0]) / denominator if denominator > 0 else np.nan
        log_returns = np.diff(np.log(path))
        realized_volatility[row] = float(np.std(log_returns, ddof=0)) if len(log_returns) else np.nan
        high = float(np.max(highs[start:end]))
        low = float(np.min(lows[start:end]))
        width = high - low
        realized_range[row] = width / path[0] if path[0] > 0 else np.nan
        if width > 0:
            raw = (path[-1] - low) / width if drive[row] > 0 else (high - path[-1]) / width
            terminal_location[row] = float(np.clip(raw, 0.0, 1.0))

    frame["eff_pct"] = causal_percentile(efficiency)
    frame["rv_pct"] = causal_percentile(realized_volatility)
    frame["range_pct"] = causal_percentile(realized_range)
    frame["ext_pct"] = causal_percentile(terminal_location)
    return frame


def bin_mask(values: np.ndarray, band: str) -> np.ndarray:
    values = np.asarray(values, float)
    finite = np.isfinite(values)
    if band == "LOW":
        return finite & (values >= 0.0) & (values < 1 / 3)
    if band == "MID":
        return finite & (values >= 1 / 3) & (values < 2 / 3)
    if band == "HIGH":
        return finite & (values >= 2 / 3) & (values <= 1.0)
    raise ValueError(band)


def strength_mask(values: np.ndarray, name: str) -> np.ndarray:
    bounds = {
        "STR_B0_20": (0.0, 0.20, False),
        "STR_B20_40": (0.20, 0.40, False),
        "STR_B40_60": (0.40, 0.60, False),
        "STR_B60_80": (0.60, 0.80, False),
        "STR_B80_100": (0.80, 1.00, True),
    }
    values = np.asarray(values, float)
    low, high, inclusive = bounds[name]
    finite = np.isfinite(values)
    return finite & (values >= low) & ((values <= high) if inclusive else (values < high))


def character_rules() -> tuple[str, ...]:
    singles = tuple(f"{feature}_{band}" for feature in FEATURES for band in BINS)
    pairs = tuple(
        f"{first}_{first_band}__{second}_{second_band}"
        for first, second in PAIR_FEATURES
        for first_band in BINS
        for second_band in BINS
    )
    rules = ["ALL", "DRIVE_UP", "DRIVE_DOWN", *STR_RULES, *singles, *pairs]
    for side in ("DRIVE_UP", "DRIVE_DOWN"):
        rules.extend(f"{side}__{state}" for state in singles)
        rules.extend(f"{side}__{state}" for state in STR_RULES)
    if len(rules) != 90 or len(set(rules)) != 90:
        raise AssertionError(f"expected 90 unique rules, got {len(rules)} / {len(set(rules))}")
    return tuple(rules)


RULES = character_rules()
FEATURE_COLUMN = {"EFF": "eff_pct", "RV": "rv_pct", "RANGE": "range_pct", "EXT": "ext_pct"}


def state_rule_mask(frame: pd.DataFrame, rule: str) -> np.ndarray:
    mask = np.ones(len(frame), dtype=bool)
    for token in rule.split("__"):
        feature, band = token.rsplit("_", 1)
        mask &= bin_mask(frame[FEATURE_COLUMN[feature]].to_numpy(float), band)
    return mask


def masks_for_frame(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    drive = frame.drive_return.to_numpy(float)
    masks = {
        "ALL": np.ones(len(frame), dtype=bool),
        "DRIVE_UP": drive > 0,
        "DRIVE_DOWN": drive < 0,
    }
    strength = frame.strength_pct.to_numpy(float)
    for rule in STR_RULES:
        masks[rule] = strength_mask(strength, rule)
    singles = tuple(f"{feature}_{band}" for feature in FEATURES for band in BINS)
    pairs = tuple(
        f"{first}_{first_band}__{second}_{second_band}"
        for first, second in PAIR_FEATURES
        for first_band in BINS
        for second_band in BINS
    )
    for rule in (*singles, *pairs):
        masks[rule] = state_rule_mask(frame, rule)
    for side in ("DRIVE_UP", "DRIVE_DOWN"):
        for rule in singles:
            masks[f"{side}__{rule}"] = masks[side] & masks[rule]
        for rule in STR_RULES:
            masks[f"{side}__{rule}"] = masks[side] & masks[rule]
    if set(masks) != set(RULES):
        raise AssertionError("character mask/rule mismatch")
    return masks


def hold_returns(x5: pd.DataFrame, frame: pd.DataFrame, hold: int):
    entry_ts = pd.DatetimeIndex(frame.entry_ts)
    exit_ts = entry_ts + pd.Timedelta(minutes=hold)
    exit_ix = x5.index.get_indexer(exit_ts)
    entry_ix = frame.entry_ix.to_numpy(int)
    valid = (exit_ix >= 0) & ((exit_ix - entry_ix) == hold // BAR_MIN)
    exit_price = np.full(len(frame), np.nan, float)
    available = exit_ix >= 0
    exit_price[available] = x5.open.to_numpy(float)[exit_ix[available]]
    returns = (exit_price - frame.entry_price.to_numpy(float)) / frame.entry_price.to_numpy(float)
    return exit_ts, valid, returns


def prepare(x5: pd.DataFrame) -> dict:
    cache = {}
    for lookback in LOOKBACKS:
        for clock in CLOCKS:
            frame = state_frame(x5, clock, lookback)
            entry_ts = pd.DatetimeIndex(frame.entry_ts)
            pre_ts = pd.DatetimeIndex(frame.pre_ts)
            masks = masks_for_frame(frame)
            for hold in HOLDS:
                exit_ts, valid, returns = hold_returns(x5, frame, hold)
                cache[(clock, lookback, hold)] = (entry_ts, pre_ts, exit_ts, valid, returns, masks)
    return cache


def evaluate_candidate(cache: dict, lookback: int, hold: int, rule: str) -> dict:
    part_start, part_end = base.PARTS["development"]
    anchor_stats = []
    pooled = []
    for clock in CLOCKS:
        entry_ts, pre_ts, exit_ts, valid, returns, masks = cache[(clock, lookback, hold)]
        selected = valid & (pre_ts >= part_start) & (entry_ts >= part_start) & (exit_ts < part_end) & masks[rule]
        gross = NOTIONAL * returns[selected]
        net = gross - FEE
        stats = summarize(net, gross)
        evaluable = stats["trades"] >= 40
        supportive = bool(
            evaluable
            and stats["win_rate"] >= 0.52
            and stats["net_pnl"] > 0
            and stats["expectancy"] > 0
            and stats["pf"] >= 1.05
            and stats["max_dd"] <= 125
            and stats["max_loss_streak"] <= 10
        )
        anchor_stats.append((clock, stats, evaluable, supportive))
        if len(net):
            pooled.append(pd.DataFrame({"entry_ts": entry_ts[selected], "gross": gross, "net": net, "clock": clock}))

    if pooled:
        trades = pd.concat(pooled, ignore_index=True).sort_values(["entry_ts", "clock"]).reset_index(drop=True)
        pooled_stats = summarize(trades.net.to_numpy(float), trades.gross.to_numpy(float))
    else:
        trades = pd.DataFrame(columns=["entry_ts", "gross", "net", "clock"])
        pooled_stats = summarize(np.array([]), np.array([]))

    row = {
        "lookback_min": lookback,
        "hold_min": hold,
        "character_rule": rule,
        **pooled_stats,
        "evaluable_anchors": int(sum(item[2] for item in anchor_stats)),
        "supportive_anchors": int(sum(item[3] for item in anchor_stats)),
    }
    for clock, stats, evaluable, supportive in anchor_stats:
        key = f"a{clock}"
        row.update({
            f"{key}_trades": stats["trades"],
            f"{key}_wr": stats["win_rate"],
            f"{key}_net": stats["net_pnl"],
            f"{key}_exp": stats["expectancy"],
            f"{key}_pf": stats["pf"],
            f"{key}_dd": stats["max_dd"],
            f"{key}_evaluable": evaluable,
            f"{key}_supportive": supportive,
        })

    years_wr55 = 0
    minimum_year_expectancy = np.inf
    era_gate = True
    for year in YEARS:
        if len(trades):
            year_mask = pd.DatetimeIndex(trades.entry_ts).year == year
            year_stats = summarize(
                trades.loc[year_mask, "net"].to_numpy(float),
                trades.loc[year_mask, "gross"].to_numpy(float),
            )
        else:
            year_stats = summarize(np.array([]), np.array([]))
        row.update({
            f"y{year}_trades": year_stats["trades"],
            f"y{year}_wr": year_stats["win_rate"],
            f"y{year}_net": year_stats["net_pnl"],
            f"y{year}_exp": year_stats["expectancy"],
            f"y{year}_pf": year_stats["pf"],
        })
        year_ok = bool(
            year_stats["trades"] >= 40
            and np.isfinite(year_stats["win_rate"])
            and year_stats["win_rate"] >= 0.52
            and year_stats["net_pnl"] > 0
            and np.isfinite(year_stats["expectancy"])
            and year_stats["expectancy"] > 0
            and np.isfinite(year_stats["pf"])
            and year_stats["pf"] >= 1.05
        )
        era_gate &= year_ok
        years_wr55 += int(np.isfinite(year_stats["win_rate"]) and year_stats["win_rate"] >= 0.55)
        minimum_year_expectancy = min(
            minimum_year_expectancy,
            year_stats["expectancy"] if np.isfinite(year_stats["expectancy"]) else -np.inf,
        )

    row["years_wr55"] = years_wr55
    row["min_year_exp"] = float(minimum_year_expectancy)
    row["anchor_gate"] = row["evaluable_anchors"] >= 3 and row["supportive_anchors"] >= 3
    row["pooled_gate"] = bool(
        row["trades"] >= 160
        and np.isfinite(row["win_rate"])
        and row["win_rate"] >= 0.55
        and row["net_pnl"] > 0
        and np.isfinite(row["expectancy"])
        and row["expectancy"] >= 0.50
        and np.isfinite(row["pf"])
        and row["pf"] >= 1.20
        and row["max_dd"] <= 125
        and row["max_loss_streak"] <= 8
    )
    row["era_gate"] = bool(era_gate and years_wr55 >= 2)
    row["candidate_gate"] = bool(row["anchor_gate"] and row["pooled_gate"] and row["era_gate"])
    return row


def build_grid(cache: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = [
        evaluate_candidate(cache, lookback, hold, rule)
        for lookback in LOOKBACKS
        for hold in HOLDS
        for rule in RULES
    ]
    development = pd.DataFrame(rows)
    if len(development) != 3240:
        raise AssertionError(f"expected 3240 candidates, got {len(development)}")
    candidates = development[development.candidate_gate].copy().sort_values(
        [
            "min_year_exp", "supportive_anchors", "expectancy", "win_rate", "pf",
            "max_dd", "max_loss_streak", "hold_min", "lookback_min", "character_rule",
        ],
        ascending=[False, False, False, False, False, True, True, True, True, True],
    ).reset_index(drop=True)
    candidates["dev_rank"] = np.arange(1, len(candidates) + 1)
    return development, candidates


def selected_anchor_atlas(selected: pd.Series) -> pd.DataFrame:
    rows = []
    for clock in CLOCKS:
        key = f"a{clock}"
        rows.append({
            "clock_utc": hhmm(clock),
            "clock_wib": wib(clock),
            "trades": int(selected[f"{key}_trades"]),
            "win_rate": selected[f"{key}_wr"],
            "net_pnl": selected[f"{key}_net"],
            "expectancy": selected[f"{key}_exp"],
            "pf": selected[f"{key}_pf"],
            "max_dd": selected[f"{key}_dd"],
            "evaluable": bool(selected[f"{key}_evaluable"]),
            "supportive": bool(selected[f"{key}_supportive"]),
        })
    return pd.DataFrame(rows)


def main() -> None:
    base.synthetic_tests()
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")
    cache = prepare(x5)
    development, candidates = build_grid(cache)
    development.to_csv(OUT_GRID, index=False)
    candidates.to_csv(OUT_LEADER, index=False)

    top = development.sort_values(
        ["candidate_gate", "min_year_exp", "supportive_anchors", "expectancy", "win_rate", "pf"],
        ascending=[False, False, False, False, False, False],
    ).head(25)
    lines = [
        "# SOL Economic-First H00 — 07:00–08:00 WIB LONG Character Discovery Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        "Direction: **LONG only**.",
        "Time habitat: **00:00–01:00 UTC / 07:00–08:00 WIB only**.",
        "No inherited SOL parent, Fibonacci, reference range, visit, breakout, TP, or SL.",
        "Development only; OOS remained closed by preregistration.",
        f"Character rules: **{len(RULES)}**; Development candidates: **{len(development)}**; full-gate passers: **{len(candidates)}**.",
        "",
        "## Best Development LONG characters",
        "",
        "| # | Character | LB | Hold | N | WR | Net | Exp | PF | DD | Anchors | 2022 WR/Exp | 2023 | 2024 | Gate |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, row in enumerate(top.itertuples(index=False), 1):
        lines.append(
            f"| {rank} | {row.character_rule} | {int(row.lookback_min)}m | {int(row.hold_min)}m | "
            f"{int(row.trades)} | {pct(row.win_rate)} | {money(row.net_pnl)} | {money(row.expectancy)} | "
            f"{row.pf:.3f} | {money(row.max_dd)} | {int(row.supportive_anchors)}/{int(row.evaluable_anchors)} | "
            f"{pct(row.y2022_wr)}/{money(row.y2022_exp)} | {pct(row.y2023_wr)}/{money(row.y2023_exp)} | "
            f"{pct(row.y2024_wr)}/{money(row.y2024_exp)} | {'YES' if row.candidate_gate else 'NO'} |"
        )

    if len(candidates) == 0:
        status = "SOL_ECONOMIC_FIRST_H00_NO_LONG_CHARACTER"
        lines += [
            "",
            f"**Status: {status}**",
            "",
            "No 07:00–08:00 WIB LONG character passed the frozen anchor, pooled-economic, and all-era gates.",
            "The next hour must reopen all 3,240 candidates; no rule transfer, gate relaxation, or OOS exposure.",
            "",
            "Research/shadow only.",
        ]
    else:
        selected = candidates.iloc[0]
        atlas = selected_anchor_atlas(selected)
        atlas.to_csv(OUT_ATLAS, index=False)
        status = "SOL_ECONOMIC_FIRST_H00_LONG_CHARACTER_FOUND"
        lines += [
            "",
            "## Development-selected LONG character",
            "",
            f"**{selected['character_rule']} / LB{int(selected['lookback_min'])} / hold{int(selected['hold_min'])}m**",
            "",
            f"N **{int(selected['trades'])}**, WR **{pct(selected['win_rate'])}**, net **{money(selected['net_pnl'])}**, "
            f"expectancy **{money(selected['expectancy'])}/trade**, PF **{float(selected['pf']):.3f}**, "
            f"DD **{money(selected['max_dd'])}**, loss streak **{int(selected['max_loss_streak'])}**, "
            f"supportive anchors **{int(selected['supportive_anchors'])}/{int(selected['evaluable_anchors'])}**.",
            "",
            "### Cross-era Development",
            "",
            f"- 2022: N {int(selected['y2022_trades'])}, WR {pct(selected['y2022_wr'])}, exp {money(selected['y2022_exp'])}, PF {float(selected['y2022_pf']):.3f}",
            f"- 2023: N {int(selected['y2023_trades'])}, WR {pct(selected['y2023_wr'])}, exp {money(selected['y2023_exp'])}, PF {float(selected['y2023_pf']):.3f}",
            f"- 2024: N {int(selected['y2024_trades'])}, WR {pct(selected['y2024_wr'])}, exp {money(selected['y2024_exp'])}, PF {float(selected['y2024_pf']):.3f}",
            "",
            "### Quarter-hour anchor atlas",
            "",
            "| UTC | WIB | N | WR | Net | Exp | PF | DD | Supportive |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for row in atlas.itertuples(index=False):
            lines.append(
                f"| {row.clock_utc} | {row.clock_wib} | {row.trades} | {pct(row.win_rate)} | "
                f"{money(row.net_pnl)} | {money(row.expectancy)} | {row.pf:.3f} | {money(row.max_dd)} | "
                f"{'YES' if row.supportive else 'NO'} |"
            )
        lines += [
            "",
            f"**Status: {status}**",
            "",
            "Winner remains Development-only. The next hour must reopen the complete grammar; OOS stays closed.",
            "",
            "Research/shadow only.",
        ]

    OUT_STATUS.write_text(status + "\n")
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
