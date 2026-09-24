#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
import math

import numpy as np
import pandas as pd

import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_MTF_15M_CHARACTER_V1"
COST_PCT = 0.15
NOTIONAL = 500.0
TP_PCT = 1.0
SL_GRID = (1.0, 1.25, 1.5)
LOOKBACKS = (4, 8, 12, 24)
CLOSE_LOCS = (0.55, 0.65, 0.75)
DEPTHS = (0.0, 0.10, 0.20)
TRIGGERS = ("SR_ANY", "SR_BULL", "SR_DISP", "SR_FOLLOW")
CONTEXTS = ("LOC80", "LOC65", "LOC80_4H_ABOVE", "LOC80_4H_UP")
HOLD_5M = 288

PARTITIONS = (
    ("DEV_2023_2024", pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")),
    ("REF_2025", pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC")),
    ("REF_2026", pd.Timestamp("2026-01-01", tz="UTC"), None),
)


def resample_complete(x5: pd.DataFrame, rule: str, expected: int) -> pd.DataFrame:
    z = x5.resample(rule, label="left", closed="left").agg(
        open=("open","first"), high=("high","max"), low=("low","min"),
        close=("close","last"), n=("close","count")
    )
    return z[z.n == expected].drop(columns=["n"]).dropna().copy()


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df.close.shift(1)
    return pd.concat([
        df.high - df.low,
        (df.high - pc).abs(),
        (df.low - pc).abs()
    ], axis=1).max(axis=1)


def build_features(x5: pd.DataFrame):
    q15 = resample_complete(x5, "15min", 3)
    h1 = resample_complete(x5, "1h", 12)
    h4 = resample_complete(x5, "4h", 48)

    h1["r72_lo"] = h1.low.rolling(72, min_periods=72).min()
    h1["r72_hi"] = h1.high.rolling(72, min_periods=72).max()
    den = (h1.r72_hi - h1.r72_lo).replace(0, np.nan)
    h1["loc72"] = (h1.close - h1.r72_lo) / den
    h1_ctx = h1[["loc72"]].copy()
    h1_ctx["avail_time"] = h1_ctx.index + pd.Timedelta(hours=1)

    h4["ema20"] = h4.close.ewm(span=20, adjust=False, min_periods=20).mean()
    h4["ema20_prev"] = h4.ema20.shift(1)
    h4["above20"] = h4.close >= h4.ema20
    h4["ema_up"] = h4.ema20 > h4.ema20_prev
    h4_ctx = h4[["above20","ema_up"]].copy()
    h4_ctx["avail_time"] = h4_ctx.index + pd.Timedelta(hours=4)

    q15["signal_end"] = q15.index + pd.Timedelta(minutes=15)
    q15["rng"] = q15.high - q15.low
    q15["close_loc"] = (q15.close - q15.low) / q15.rng.replace(0, np.nan)
    q15["body_abs"] = (q15.close - q15.open).abs()
    q15["body_med20"] = q15.body_abs.shift(1).rolling(20, min_periods=20).median()
    q15["body_mult"] = q15.body_abs / q15.body_med20.replace(0, np.nan)
    q15["atr20"] = true_range(q15).shift(1).rolling(20, min_periods=20).mean()
    q15["bull"] = q15.close > q15.open

    q15 = pd.merge_asof(
        q15.sort_values("signal_end"),
        h1_ctx.dropna().sort_values("avail_time"),
        left_on="signal_end", right_on="avail_time",
        direction="backward"
    ).set_index(q15.sort_values("signal_end").index)

    q15 = pd.merge_asof(
        q15.reset_index(drop=False).sort_values("signal_end"),
        h4_ctx.dropna().sort_values("avail_time"),
        left_on="signal_end", right_on="avail_time",
        direction="backward",
        suffixes=("","_h4")
    )
    q15.index = pd.DatetimeIndex(q15["index"])
    q15 = q15.drop(columns=["index"])
    return q15.sort_index(), h1, h4


def build_signal_masks(q15: pd.DataFrame):
    masks = {}
    for lb in LOOKBACKS:
        prior_low = q15.low.shift(1).rolling(lb, min_periods=lb).min()
        sweep = q15.low < prior_low
        reclaim = q15.close > prior_low
        depth = (prior_low - q15.low) / q15.atr20.replace(0, np.nan)
        base = sweep & reclaim
        prev_sr_bull = (base & q15.bull).shift(1).fillna(False)
        for cloc in CLOSE_LOCS:
            loc_ok = q15.close_loc >= cloc
            for dep in DEPTHS:
                dep_ok = depth >= dep
                common = base & loc_ok & dep_ok
                masks[(lb, cloc, dep, "SR_ANY")] = common
                masks[(lb, cloc, dep, "SR_BULL")] = common & q15.bull
                masks[(lb, cloc, dep, "SR_DISP")] = common & q15.bull & (q15.body_mult >= 1.25)
                masks[(lb, cloc, dep, "SR_FOLLOW")] = (
                    prev_sr_bull & q15.bull & (q15.close > q15.high.shift(1)) & loc_ok
                )
    return masks


def context_mask(q15: pd.DataFrame, name: str):
    if name == "LOC80":
        return q15.loc72 <= 0.80
    if name == "LOC65":
        return q15.loc72 <= 0.65
    if name == "LOC80_4H_ABOVE":
        return (q15.loc72 <= 0.80) & q15.above20.fillna(False)
    if name == "LOC80_4H_UP":
        return (q15.loc72 <= 0.80) & q15.above20.fillna(False) & q15.ema_up.fillna(False)
    raise KeyError(name)


def pf(pnls):
    a = np.asarray(pnls, dtype=float)
    pos = a[a > 0].sum()
    neg = -a[a < 0].sum()
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return float(pos / neg)


def max_dd(pnls):
    if not pnls:
        return 0.0
    a = np.cumsum(np.asarray(pnls, dtype=float))
    peaks = np.maximum.accumulate(np.maximum(a, 0.0))
    return float(np.max(peaks - a))


@dataclass
class Trade:
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry: float
    exit: float
    outcome: str
    gross_pct: float
    net_pct: float
    pnl_usd: float


def simulate(mask: pd.Series, q15: pd.DataFrame, x5: pd.DataFrame, sl_pct: float):
    idx5 = x5.index
    op5 = x5.open.astype(float).to_numpy()
    hi5 = x5.high.astype(float).to_numpy()
    lo5 = x5.low.astype(float).to_numpy()
    cl5 = x5.close.astype(float).to_numpy()
    trades = []
    active_until = pd.Timestamp.min.tz_localize("UTC")
    sig_idx = q15.index[mask.fillna(False).to_numpy()]
    for st in sig_idx:
        entry_time = st + pd.Timedelta(minutes=15)
        if entry_time <= active_until:
            continue
        pos = int(idx5.searchsorted(entry_time))
        if pos >= len(idx5) or idx5[pos] != entry_time:
            continue
        entry = float(op5[pos])
        if not np.isfinite(entry) or entry <= 0:
            continue
        tp = entry * (1.0 + TP_PCT/100.0)
        sl = entry * (1.0 - sl_pct/100.0)
        last = min(pos + HOLD_5M - 1, len(idx5) - 1)
        outcome = "TIME"
        exit_i = last
        exit_px = float(cl5[last])
        gross = (exit_px/entry - 1.0) * 100.0
        for j in range(pos, last + 1):
            hit_tp = hi5[j] >= tp
            hit_sl = lo5[j] <= sl
            if hit_tp and hit_sl:
                outcome = "SL_AMBIG"
                exit_i = j
                exit_px = sl
                gross = -sl_pct
                break
            if hit_sl:
                outcome = "SL"
                exit_i = j
                exit_px = sl
                gross = -sl_pct
                break
            if hit_tp:
                outcome = "TP"
                exit_i = j
                exit_px = tp
                gross = TP_PCT
                break
        net = gross - COST_PCT
        pnl = net/100.0 * NOTIONAL
        active_until = idx5[exit_i]
        trades.append(Trade(st, entry_time, idx5[exit_i], entry, exit_px, outcome, gross, net, pnl))
    return trades


def partition_summary(trades, end_available):
    rows = []
    for name, start, end in PARTITIONS:
        stop = end if end is not None else end_available
        z = [t for t in trades if t.entry_time >= start and t.entry_time < stop]
        days = (stop - start).total_seconds()/86400.0
        n = len(z)
        wins = sum(t.outcome == "TP" for t in z)
        pnls = [t.pnl_usd for t in z]
        nets = [t.net_pct for t in z]
        rows.append({
            "partition": name,
            "n": n,
            "wins": wins,
            "wr": wins/n if n else np.nan,
            "trades_per_day": n/days if days > 0 else np.nan,
            "net_expectancy_pct": float(np.mean(nets)) if nets else np.nan,
            "pnl_usd": float(np.sum(pnls)) if pnls else 0.0,
            "pf": pf(pnls) if pnls else np.nan,
            "max_dd_usd": max_dd(pnls),
            "timeouts": sum(t.outcome == "TIME" for t in z),
            "ambiguous_losses": sum(t.outcome == "SL_AMBIG" for t in z),
        })
    return rows


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")
    x5 = x5.sort_index()
    q15, _, _ = build_features(x5)
    masks = build_signal_masks(q15)
    end_available = min(
        pd.Timestamp("2026-09-24", tz="UTC"),
        x5.index[-1] + pd.Timedelta(minutes=5)
    )

    all_rows = []
    trade_rows = []
    contexts = {c: context_mask(q15, c) for c in CONTEXTS}
    for (lb, cloc, dep, trig), base_mask in masks.items():
        for ctx in CONTEXTS:
            m = base_mask & contexts[ctx]
            for sl in SL_GRID:
                trades = simulate(m, q15, x5, sl)
                ps = partition_summary(trades, end_available)
                by = {r["partition"]: r for r in ps}
                valid = all(by[p]["n"] > 0 for p,_,_ in PARTITIONS)
                min_wr = min(by[p]["wr"] for p,_,_ in PARTITIONS) if valid else np.nan
                min_tpd = min(by[p]["trades_per_day"] for p,_,_ in PARTITIONS) if valid else np.nan
                min_exp = min(by[p]["net_expectancy_pct"] for p,_,_ in PARTITIONS) if valid else np.nan
                full_pass = bool(valid and min_wr >= 0.70 and min_tpd >= 1.0 and min_exp > 0)
                econ_freq_pass = bool(valid and min_tpd >= 1.0 and min_exp > 0)
                row = {
                    "lookback15": lb, "close_loc_min": cloc, "sweep_depth_atr_min": dep,
                    "trigger": trig, "context": ctx, "tp_pct": TP_PCT, "sl_pct": sl,
                    "min_wr": min_wr, "min_trades_per_day": min_tpd,
                    "min_net_expectancy_pct": min_exp,
                    "full_pass": full_pass, "econ_freq_pass": econ_freq_pass,
                }
                for r in ps:
                    pref = r["partition"].replace("DEV_","D_").replace("REF_","R_")
                    for k,v in r.items():
                        if k != "partition":
                            row[f"{pref}_{k}"] = v
                all_rows.append(row)

    out = pd.DataFrame(all_rows)
    out = out.sort_values(
        ["full_pass","econ_freq_pass","min_wr","min_net_expectancy_pct","min_trades_per_day"],
        ascending=[False,False,False,False,False]
    ).reset_index(drop=True)

    shortlist = out[out.econ_freq_pass].head(40).copy()
    full = out[out.full_pass].copy()
    out.to_csv(ROOT/f"{PFX}_Grid.csv", index=False)
    shortlist.to_csv(ROOT/f"{PFX}_Shortlist.csv", index=False)
    full.to_csv(ROOT/f"{PFX}_FullPass.csv", index=False)

    lines = [
        "# SOL MTF 15M Character V1 — Result","",
        f"- 5m data coverage: **{coverage*100:.5f}%**",
        f"- Complete 15m bars: **{len(q15):,}**",
        f"- Tested configurations: **{len(out):,}**",
        f"- Full target passes: **{len(full):,}**",
        f"- Positive-economics + >=1/day all-period configs: **{int(out.econ_freq_pass.sum()):,}**","",
        "Frozen target: **TP +1.0%, WR >=70%, >=1 trade/day, positive after-cost expectancy in 2023-24 / 2025 / 2026, one position active.**","",
        "## Top robust configurations","",
        "| Rank | Trigger | LB | CloseLoc | DepthATR | Context | SL | DEV WR / tpd / exp | 2025 WR / tpd / exp | 2026 WR / tpd / exp | Min WR | PASS |",
        "|---:|---|---:|---:|---:|---|---:|---|---|---|---:|---|",
    ]
    for i, r in out.head(20).iterrows():
        lines.append(
            f"| {i+1} | {r.trigger} | {int(r.lookback15)} | {r.close_loc_min:.2f} | {r.sweep_depth_atr_min:.2f} | {r.context} | {r.sl_pct:.2f}% | "
            f"{r.D_2023_2024_wr*100:.1f}% / {r.D_2023_2024_trades_per_day:.2f} / {r.D_2023_2024_net_expectancy_pct:.3f}% | "
            f"{r.R_2025_wr*100:.1f}% / {r.R_2025_trades_per_day:.2f} / {r.R_2025_net_expectancy_pct:.3f}% | "
            f"{r.R_2026_wr*100:.1f}% / {r.R_2026_trades_per_day:.2f} / {r.R_2026_net_expectancy_pct:.3f}% | "
            f"{r.min_wr*100:.1f}% | {'YES' if r.full_pass else 'NO'} |"
        )
    if len(full):
        best = full.iloc[0]
        lines += ["","## Best full pass","",
                  f"- {best.trigger}, LB={int(best.lookback15)}, close_loc>={best.close_loc_min:.2f}, depthATR>={best.sweep_depth_atr_min:.2f}, context={best.context}, SL={best.sl_pct:.2f}%.",
                  f"- Worst-period WR **{best.min_wr*100:.2f}%**, worst-period frequency **{best.min_trades_per_day:.3f}/day**, worst-period net expectancy **{best.min_net_expectancy_pct:.4f}%/trade**."]
        verdict = "FULL_TARGET_PASS_FOUND"
    else:
        best = out.iloc[0]
        lines += ["","## Frontier","",
                  f"- No configuration met the full frozen target.",
                  f"- Best robust frontier by current ordering: {best.trigger}, LB={int(best.lookback15)}, close_loc>={best.close_loc_min:.2f}, depthATR>={best.sweep_depth_atr_min:.2f}, context={best.context}, SL={best.sl_pct:.2f}%.",
                  f"- Worst-period WR **{best.min_wr*100:.2f}%**; frequency **{best.min_trades_per_day:.3f}/day**; net expectancy floor **{best.min_net_expectancy_pct:.4f}%/trade**."]
        verdict = "NO_FULL_PASS__CHARACTER_FRONTIER_MAPPED"
    lines += ["","## Interpretation","",
              "This screen tests whether causal 15m sweep/reclaim microstructure, with only completed 1H/4H context, can bridge the frequency-vs-WR gap.",
              "Do not treat 2025/2026 as pristine holdout because those periods have already been inspected in prior SOL discovery.",
              "",f"# VERDICT: {verdict}"]
    text = "\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
