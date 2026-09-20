#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_full_character_long_v1 as fc1
import sol_structure_library_v1 as lib
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_SELL_STRUCTURE_DETECTOR_V1"

MODEL_START = pd.Timestamp("2020-01-01", tz="UTC")
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
YEARS = (2020, 2021, 2022, 2023, 2024)

RANGE_LOOKBACK = 20
BOS_MAX_H1 = 12
DISPLACEMENT_MIN_RANGE_UNITS = 1.50
BEAR_EFF_MIN = 0.55
RETEST_MAX_5M = 7 * 24 * 12
REJECTION_MAX_5M = 12
FUTURE_60M_BARS = 12
ROUNDTRIP_COST_PCT = 0.15
NOTIONAL = 500.0


def _latest_unconsumed_high(high_hist, consumed):
    for h in reversed(high_hist):
        if int(h["pivot_i"]) not in consumed:
            return h
    return None


def _latest_low_after(low_hist, high_pivot_i):
    for l in reversed(low_hist):
        if int(l["pivot_i"]) > int(high_pivot_i):
            return l
    return None


def _pf(pnls):
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def _max_dd(pnls):
    a = pd.Series(pnls, dtype=float).dropna()
    if a.empty:
        return np.nan
    eq = a.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def _max_ls(pnls):
    best = cur = 0
    for x in pd.Series(pnls, dtype=float).dropna():
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def _econ(g):
    if g.empty:
        return {
            "n": 0, "wr60": np.nan, "expectancy60_pct": np.nan,
            "pf60": np.nan, "pnl60_usd": 0.0,
            "max_dd_usd": np.nan, "max_loss_streak": 0,
            "median_mfe60_short_pct": np.nan,
            "median_mae60_short_pct": np.nan,
            "median_mfe_mae_ratio": np.nan,
        }
    p = g.pnl60_usd.astype(float)
    net = g.net60_short_pct.astype(float)
    return {
        "n": int(len(g)),
        "wr60": float((net > 0).mean()),
        "expectancy60_pct": float(net.mean()),
        "pf60": float(_pf(p)),
        "pnl60_usd": float(p.sum()),
        "max_dd_usd": float(_max_dd(p)),
        "max_loss_streak": int(_max_ls(p)),
        "median_mfe60_short_pct": float(g.mfe60_short_pct.median()),
        "median_mae60_short_pct": float(g.mae60_short_pct.median()),
        "median_mfe_mae_ratio": float(g.mfe_mae_ratio.replace([np.inf, -np.inf], np.nan).median()),
    }


def detect_h1_stages(x5):
    h1 = fc1.build_h1(x5)
    idx = h1.index
    op = h1.open.astype(float).to_numpy()
    hi = h1.high.astype(float).to_numpy()
    lo = h1.low.astype(float).to_numpy()
    cl = h1.close.astype(float).to_numpy()

    lows_by_confirm, highs_by_confirm = lib.compute_pivots(hi, lo)
    high_hist, low_hist = [], []
    consumed_highs = set()
    stage_a, stage_b = [], []

    for i in range(max(30, RANGE_LOOKBACK + 3), len(h1) - BOS_MAX_H1 - 2):
        high_hist.extend(highs_by_confirm.get(i, []))
        low_hist.extend(lows_by_confirm.get(i, []))

        h0 = _latest_unconsumed_high(high_hist, consumed_highs)
        if h0 is None:
            continue
        l0 = _latest_low_after(low_hist, int(h0["pivot_i"]))
        if l0 is None:
            continue
        if int(h0["confirm_i"]) >= i or int(l0["confirm_i"]) >= i:
            continue

        level = float(h0["price"])
        if not (hi[i] > level and cl[i] < level):
            continue

        sweep_close_time = idx[i] + pd.Timedelta(hours=1)
        if sweep_close_time < MODEL_START or sweep_close_time >= MODEL_END:
            continue

        consumed_highs.add(int(h0["pivot_i"]))

        arow = {
            "structure_id": f"{idx[i]}__H{int(h0['pivot_i'])}__L{int(l0['pivot_i'])}",
            "sweep_i_h1": int(i),
            "sweep_time": idx[i],
            "sweep_close_time": sweep_close_time,
            "year": int(sweep_close_time.year),
            "liquidity_high": level,
            "liquidity_pivot_i": int(h0["pivot_i"]),
            "liquidity_confirm_i": int(h0["confirm_i"]),
            "significant_low": float(l0["price"]),
            "significant_low_pivot_i": int(l0["pivot_i"]),
            "significant_low_confirm_i": int(l0["confirm_i"]),
            "sweep_open": float(op[i]),
            "sweep_high": float(hi[i]),
            "sweep_low": float(lo[i]),
            "sweep_close": float(cl[i]),
            "sweep_depth_pct": float((hi[i] / level - 1.0) * 100.0),
        }
        stage_a.append(arow)

        j_bos = None
        for j in range(i + 1, min(i + BOS_MAX_H1 + 1, len(h1))):
            if cl[j] < float(l0["price"]):
                j_bos = j
                break
        if j_bos is None:
            continue

        prior_ranges = hi[i - RANGE_LOOKBACK:i] - lo[i - RANGE_LOOKBACK:i]
        med_range = float(np.median(prior_ranges))
        if not np.isfinite(med_range) or med_range <= 0:
            continue

        displacement = float(hi[i] - cl[j_bos])
        disp_units = displacement / med_range
        if disp_units < DISPLACEMENT_MIN_RANGE_UNITS:
            continue

        path_closes = cl[i:j_bos + 1]
        path = float(np.abs(np.diff(path_closes)).sum())
        net_down = float(cl[i] - cl[j_bos])
        bear_eff = net_down / path if path > 0 else np.nan
        if not np.isfinite(bear_eff) or bear_eff < BEAR_EFF_MIN:
            continue

        origin_i = None
        for k in range(j_bos - 1, i - 1, -1):
            if cl[k] > op[k]:
                origin_i = int(k)
                break
        if origin_i is None:
            continue

        zone_low = float(lo[origin_i])
        zone_high = float(hi[origin_i])
        if not (np.isfinite(zone_low) and np.isfinite(zone_high) and zone_high > zone_low):
            continue

        bos_close_time = idx[j_bos] + pd.Timedelta(hours=1)
        if bos_close_time >= MODEL_END:
            continue

        brow = {
            **arow,
            "bos_i_h1": int(j_bos),
            "bos_time": idx[j_bos],
            "bos_close_time": bos_close_time,
            "bos_close": float(cl[j_bos]),
            "bos_low": float(lo[j_bos]),
            "bars_sweep_to_bos": int(j_bos - i),
            "displacement_range_units": float(disp_units),
            "bear_path_efficiency": float(bear_eff),
            "origin_i_h1": int(origin_i),
            "origin_time": idx[origin_i],
            "origin_open": float(op[origin_i]),
            "origin_high": float(hi[origin_i]),
            "origin_low": float(lo[origin_i]),
            "origin_close": float(cl[origin_i]),
            "zone_low": zone_low,
            "zone_high": zone_high,
            "new_low_below_significant_pct": float((float(l0["price"]) - float(lo[j_bos])) / float(l0["price"]) * 100.0),
        }
        stage_b.append(brow)

    return h1, pd.DataFrame(stage_a), pd.DataFrame(stage_b)


def resolve_return_and_activation(stage_b, x5):
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()

    stage_c, stage_d, trades = [], [], []

    for _, b in stage_b.iterrows():
        start = int(idx.searchsorted(pd.Timestamp(b.bos_close_time)))
        if start >= len(x5):
            continue
        last = min(start + RETEST_MAX_5M - 1, len(x5) - 1)
        zone_low = float(b.zone_low)
        zone_high = float(b.zone_high)

        touch_i = None
        for i in range(start, last + 1):
            if idx[i] >= MODEL_END:
                break
            if hi[i] >= zone_low and lo[i] <= zone_high:
                touch_i = i
                break
        if touch_i is None:
            continue

        crow = {
            **b.to_dict(),
            "first_return_i_5m": int(touch_i),
            "first_return_time": idx[touch_i],
            "bos_to_return_min": float((idx[touch_i] - pd.Timestamp(b.bos_close_time)).total_seconds() / 60.0),
            "return_open": float(op[touch_i]),
            "return_high": float(hi[touch_i]),
            "return_low": float(lo[touch_i]),
            "return_close": float(cl[touch_i]),
        }
        stage_c.append(crow)

        trigger_i = None
        invalidated = False
        scan_last = min(touch_i + REJECTION_MAX_5M - 1, len(x5) - FUTURE_60M_BARS - 2)
        for i in range(touch_i, scan_last + 1):
            if idx[i] >= MODEL_END:
                break
            if cl[i] > zone_high:
                invalidated = True
                break
            bearish = cl[i] < op[i]
            reached_zone = hi[i] >= zone_low
            closed_back_below = cl[i] < zone_low
            if bearish and reached_zone and closed_back_below:
                trigger_i = i
                break

        if trigger_i is None:
            continue

        signal_time = idx[trigger_i] + pd.Timedelta(minutes=5)
        entry_i = trigger_i + 1
        last_i = entry_i + FUTURE_60M_BARS - 1
        if last_i >= len(x5):
            continue
        if idx[entry_i] >= MODEL_END or idx[last_i] >= MODEL_END:
            continue
        if idx[entry_i] != idx[trigger_i] + pd.Timedelta(minutes=5):
            continue
        if idx[last_i] != idx[entry_i] + pd.Timedelta(minutes=55):
            continue

        drow = {
            **crow,
            "activation_i_5m": int(trigger_i),
            "activation_bar_time": idx[trigger_i],
            "signal_time": signal_time,
            "return_to_activation_min": float((idx[trigger_i] - idx[touch_i]).total_seconds() / 60.0),
            "activation_open": float(op[trigger_i]),
            "activation_high": float(hi[trigger_i]),
            "activation_low": float(lo[trigger_i]),
            "activation_close": float(cl[trigger_i]),
            "invalidated_before_activation": int(invalidated),
        }
        stage_d.append(drow)

        entry = float(op[entry_i])
        exitp = float(cl[last_i])
        fhi = hi[entry_i:last_i + 1]
        flo = lo[entry_i:last_i + 1]
        if not (np.isfinite(entry) and entry > 0 and np.isfinite(exitp) and np.isfinite(fhi).all() and np.isfinite(flo).all()):
            continue

        gross = float((entry - exitp) / entry * 100.0)
        net = gross - ROUNDTRIP_COST_PCT
        mfe = float((entry - np.min(flo)) / entry * 100.0)
        mae = float((np.max(fhi) - entry) / entry * 100.0)
        ratio = float(mfe / mae) if mae > 1e-9 else np.nan

        trades.append({
            **drow,
            "entry_time": idx[entry_i],
            "entry_price": entry,
            "exit60_time": idx[last_i] + pd.Timedelta(minutes=5),
            "exit60_price": exitp,
            "gross60_short_pct": gross,
            "net60_short_pct": net,
            "pnl60_usd": net / 100.0 * NOTIONAL,
            "win60": int(net > 0),
            "mfe60_short_pct": mfe,
            "mae60_short_pct": mae,
            "mfe_mae_ratio": ratio,
            "time_to_mfe_min": int((np.argmin(flo) + 1) * 5),
            "time_to_mae_min": int((np.argmax(fhi) + 1) * 5),
        })

    return pd.DataFrame(stage_c), pd.DataFrame(stage_d), pd.DataFrame(trades)


def summarize(stage_a, stage_b, stage_c, stage_d, trades, coverage):
    na, nb, nc, nd = len(stage_a), len(stage_b), len(stage_c), len(stage_d)
    pooled = _econ(trades)

    years = []
    for y in YEARS:
        g = trades[trades.year == y].copy() if (not trades.empty and "year" in trades.columns) else pd.DataFrame()
        e = _econ(g)
        years.append({"year": y, **e})
    yearly = pd.DataFrame(years)

    funnel = pd.DataFrame([
        {"stage": "A_LIQUIDITY_SWEEP", "n": na, "conversion_from_prior": 1.0 if na else np.nan},
        {"stage": "B_DISPLACEMENT_BOS_ORIGIN", "n": nb, "conversion_from_prior": nb / na if na else np.nan},
        {"stage": "C_FIRST_RETURN_TO_BLOCK", "n": nc, "conversion_from_prior": nc / nb if nb else np.nan},
        {"stage": "D_REJECTION_SHORT_ACTIVATION", "n": nd, "conversion_from_prior": nd / nc if nc else np.nan},
    ])

    med_sweep_bos = float(stage_b.bars_sweep_to_bos.median()) if nb else np.nan
    med_bos_return = float(stage_c.bos_to_return_min.median()) if nc else np.nan
    med_return_activation = float(stage_d.return_to_activation_min.median()) if nd else np.nan

    summary = pd.DataFrame([{
        "coverage": coverage,
        "stage_a_n": na,
        "stage_b_n": nb,
        "stage_c_n": nc,
        "stage_d_n": nd,
        "a_to_b": nb / na if na else np.nan,
        "b_to_c": nc / nb if nb else np.nan,
        "c_to_d": nd / nc if nc else np.nan,
        "a_to_d": nd / na if na else np.nan,
        "median_sweep_to_bos_h1_bars": med_sweep_bos,
        "median_bos_to_return_min": med_bos_return,
        "median_return_to_activation_min": med_return_activation,
        **pooled,
        "status": "FULL_CHAIN_FOUND" if nd > 0 else "NO_FULL_CHAIN_MATCH",
    }])
    return funnel, summary, yearly


def _fmt_pct(v):
    return "n/a" if pd.isna(v) else f"{float(v) * 100:.2f}%"


def _fmt_num(v, digits=3):
    if pd.isna(v):
        return "n/a"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{digits}f}"


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    h1, stage_a, stage_b = detect_h1_stages(x5)
    stage_c, stage_d, trades = resolve_return_and_activation(stage_b, x5)

    funnel, summary, yearly = summarize(stage_a, stage_b, stage_c, stage_d, trades, coverage)

    stage_a.to_csv(ROOT / f"{PFX}_StageA_Sweeps.csv", index=False)
    stage_b.to_csv(ROOT / f"{PFX}_StageB_BOS.csv", index=False)
    stage_c.to_csv(ROOT / f"{PFX}_StageC_Returns.csv", index=False)
    stage_d.to_csv(ROOT / f"{PFX}_StageD_Activations.csv", index=False)
    trades.to_csv(ROOT / f"{PFX}_Trades.csv", index=False)
    funnel.to_csv(ROOT / f"{PFX}_Funnel.csv", index=False)
    summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    yearly.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)

    s = summary.iloc[0]
    lines = [
        "# SOL SELL Structure Detector V1 — Result",
        "",
        f"- 5m data coverage: **{coverage * 100:.6f}%**",
        "- Development window: **2020-2024**; 2025+ remained CLOSED.",
        "- Detector grammar: **buy-side liquidity sweep -> bearish displacement/BOS -> corrective return to bearish origin/break block -> rejection -> SHORT activation**.",
        "- This run evaluates detector structure first; +60m short return is diagnostic only.",
        "",
        "## Structural funnel",
        "",
        "| Stage | Meaning | N | Conversion |",
        "|---|---|---:|---:|",
        f"| A | Buy-side liquidity sweep/rejection | {len(stage_a)} | 100.00% |",
        f"| B | Bearish displacement + significant-low BOS + origin block | {len(stage_b)} | {_fmt_pct(len(stage_b)/len(stage_a) if len(stage_a) else np.nan)} |",
        f"| C | First corrective return into origin/break block | {len(stage_c)} | {_fmt_pct(len(stage_c)/len(stage_b) if len(stage_b) else np.nan)} |",
        f"| D | 5m rejection + SHORT activation | {len(stage_d)} | {_fmt_pct(len(stage_d)/len(stage_c) if len(stage_c) else np.nan)} |",
        "",
        f"Full-chain retention A -> D: **{_fmt_pct(len(stage_d)/len(stage_a) if len(stage_a) else np.nan)}**",
        "",
        "## Timing anatomy",
        "",
        f"- Median sweep -> BOS: **{_fmt_num(s.median_sweep_to_bos_h1_bars, 1)} H1 bars**",
        f"- Median BOS -> first block return: **{_fmt_num(s.median_bos_to_return_min, 1)} minutes**",
        f"- Median first return -> activation: **{_fmt_num(s.median_return_to_activation_min, 1)} minutes**",
        "",
        "## Fixed +60m SHORT diagnostic",
        "",
        "| N | WR60 | Exp60 | PF | PnL | Max DD | Max LS | MFE | MAE | MFE/MAE |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {int(s.n)} | {_fmt_pct(s.wr60)} | {_fmt_num(s.expectancy60_pct,4)}% | {_fmt_num(s.pf60,3)} | USD {float(s.pnl60_usd):.2f} | USD {float(s.max_dd_usd) if np.isfinite(s.max_dd_usd) else np.nan:.2f} | {int(s.max_loss_streak)} | {_fmt_num(s.median_mfe60_short_pct,3)}% | {_fmt_num(s.median_mae60_short_pct,3)}% | {_fmt_num(s.median_mfe_mae_ratio,3)} |",
        "",
        "## Yearly diagnostic",
        "",
        "| Year | N | WR60 | Exp60 | PF | PnL |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for _, y in yearly.iterrows():
        wr = _fmt_pct(y.wr60)
        exp = "n/a" if pd.isna(y.expectancy60_pct) else f"{float(y.expectancy60_pct):.4f}%"
        pnl = f"USD {float(y.pnl60_usd):.2f}"
        lines.append(f"| {int(y.year)} | {int(y.n)} | {wr} | {exp} | {_fmt_num(y.pf60,3)} | {pnl} |")

    lines += [
        "",
        "## Interpretation",
        "",
        "Stage D is the exact full detector chain. The important result at this phase is whether the four structural blocks can be found causally and how much each stage narrows the universe.",
        "Do not retune the frozen sweep, BOS, origin-zone, return, or rejection definitions on 2020-2024 after seeing this result. Any structural revision must be a new preregistered detector version.",
        "",
        f"OFFICIAL_STATUS={s.status}",
        f"FULL_MATCHES={int(s.stage_d_n)}",
        "2025_PLUS=CLOSED",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(
        f"OFFICIAL_STATUS={s.status}\nFULL_MATCHES={int(s.stage_d_n)}\n2025_PLUS=CLOSED\n",
        encoding="utf-8",
    )
    print(text)


if __name__ == "__main__":
    main()
