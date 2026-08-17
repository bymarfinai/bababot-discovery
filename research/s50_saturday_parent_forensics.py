#!/usr/bin/env python3
"""Saturday T-Method S5.0 — frozen parent loss forensics.

Mirrors the Tuesday A5.0 research process on the frozen Saturday parent.
Research only; live BBC is untouched.
"""
from __future__ import annotations

import io
import json
import os
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

BASE = "https://data.binance.vision/data/futures/um"
SYMBOL = "BTCUSDT"
NOTIONAL = 500.0
FEE = 0.0015 * NOTIONAL
TP = 0.026
SL = 0.012
HOLD_MIN = 18 * 60
START = pd.Timestamp("2023-12-02", tz="UTC")
END = pd.Timestamp("2026-07-30", tz="UTC")
CACHE = Path(os.getenv("S50_CACHE", "/tmp/s50_cache"))
OUT = Path(os.getenv("S50_OUT", "s50_out"))
CACHE.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "bababot-discovery-s50/1.0"})


def month_iter(start: pd.Timestamp, end: pd.Timestamp):
    cur = pd.Timestamp(start.year, start.month, 1, tz="UTC")
    last = pd.Timestamp(end.year, end.month, 1, tz="UTC")
    while cur <= last:
        yield cur.year, cur.month
        cur = cur + pd.offsets.MonthBegin(1)


def get_zip_bytes(url: str, cache_name: str) -> bytes:
    p = CACHE / cache_name
    if p.exists():
        return p.read_bytes()
    r = SESSION.get(url, timeout=60)
    r.raise_for_status()
    p.write_bytes(r.content)
    return r.content


def read_zip_csv(url: str, cache_name: str, header="infer") -> pd.DataFrame:
    data = get_zip_bytes(url, cache_name)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError(f"no csv in {url}")
        with zf.open(names[0]) as fh:
            return pd.read_csv(fh, header=header)


def load_klines() -> pd.DataFrame:
    frames = []
    # Nov-2023 warmup plus enough post-END bars to finish the last Saturday hold.
    for y, m in month_iter(pd.Timestamp("2023-11-01", tz="UTC"), pd.Timestamp("2026-07-31", tz="UTC")):
        ym = f"{y:04d}-{m:02d}"
        url = f"{BASE}/monthly/klines/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip"
        df = read_zip_csv(url, f"{SYMBOL}-5m-{ym}.zip")
        if len(df.columns) == 12 and str(df.columns[0]).isdigit():
            df = read_zip_csv(url, f"{SYMBOL}-5m-{ym}.zip", header=None)
        df = df.iloc[:, :12].copy()
        df.columns = [
            "open_time", "open", "high", "low", "close", "volume", "close_time",
            "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
        ]
        for c in ["open", "high", "low", "close", "quote_volume", "taker_buy_quote"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        ot = pd.to_numeric(df["open_time"], errors="coerce")
        unit = "us" if ot.dropna().median() > 1e14 else "ms"
        df["ts"] = pd.to_datetime(ot, unit=unit, utc=True)
        frames.append(df[["ts", "open", "high", "low", "close", "quote_volume", "taker_buy_quote"]])
    k = pd.concat(frames, ignore_index=True).dropna(subset=["ts", "open", "high", "low", "close"])
    k = k.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    k["ema20"] = k["close"].ewm(span=20, adjust=False).mean()
    k["taker_imb"] = np.where(k["quote_volume"] > 0, 2 * k["taker_buy_quote"] / k["quote_volume"] - 1.0, np.nan)
    return k.set_index("ts", drop=False)


def load_funding() -> pd.DataFrame:
    frames = []
    for y, m in month_iter(pd.Timestamp("2023-12-01", tz="UTC"), pd.Timestamp("2026-07-31", tz="UTC")):
        ym = f"{y:04d}-{m:02d}"
        url = f"{BASE}/monthly/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-{ym}.zip"
        df = read_zip_csv(url, f"{SYMBOL}-fundingRate-{ym}.zip")
        df.columns = [str(c).strip().lower() for c in df.columns]
        time_col = "calc_time" if "calc_time" in df.columns else ("fundingtime" if "fundingtime" in df.columns else None)
        rate_col = "last_funding_rate" if "last_funding_rate" in df.columns else ("fundingrate" if "fundingrate" in df.columns else None)
        if time_col is None or rate_col is None:
            raise RuntimeError(f"unexpected funding columns {df.columns.tolist()}")
        vals = pd.to_numeric(df[time_col], errors="coerce")
        if vals.notna().mean() > 0.9:
            unit = "us" if vals.dropna().median() > 1e14 else "ms"
            ts = pd.to_datetime(vals, unit=unit, utc=True)
        else:
            ts = pd.to_datetime(df[time_col], utc=True, errors="coerce")
        out = pd.DataFrame({"ts": ts, "rate": pd.to_numeric(df[rate_col], errors="coerce")})
        frames.append(out)
    f = pd.concat(frames, ignore_index=True).dropna().drop_duplicates("ts").sort_values("ts")
    return f.reset_index(drop=True)


def saturday_entries(k: pd.DataFrame) -> list[pd.Timestamp]:
    # Saturday 18:00 WIB = Saturday 11:00 UTC.
    idx = k.index
    mask = (idx >= START) & (idx < END) & (idx.dayofweek == 5) & (idx.hour == 11) & (idx.minute == 0)
    return list(idx[mask])


def funding_cost(k: pd.DataFrame, f: pd.DataFrame, entry_t: pd.Timestamp, exit_t: pd.Timestamp, entry_px: float) -> tuple[float, int]:
    # Charge only settlements strictly after entry and no later than the exit instant.
    rows = f[(f.ts > entry_t) & (f.ts <= exit_t)]
    qty = NOTIONAL / entry_px
    total = 0.0
    n = 0
    for r in rows.itertuples(index=False):
        if r.ts in k.index:
            px = float(k.loc[r.ts, "open"])
        else:
            # Canonical A7.3/A7.5b fallback when funding timestamp has no exact 5m open.
            px = entry_px
        total += qty * px * float(r.rate)
        n += 1
    return total, n


@dataclass
class Trade:
    date: str
    entry_t: str
    exit_t: str
    entry: float
    exit_px: float
    reason: str
    gross_ret: float
    price_pnl: float
    fee: float
    funding: float
    pnl: float
    mfe: float
    mae: float
    funding_events: int


def simulate(k: pd.DataFrame, f: pd.DataFrame, entry_t: pd.Timestamp) -> Trade:
    entry = float(k.loc[entry_t, "open"])
    tp_px = entry * (1 + TP)
    sl_px = entry * (1 - SL)
    end_t = entry_t + pd.Timedelta(minutes=HOLD_MIN)
    bars = k[(k.index >= entry_t) & (k.index < end_t)]
    if len(bars) != HOLD_MIN // 5:
        raise RuntimeError(f"incomplete bars {entry_t}: {len(bars)}")
    mfe = 0.0
    mae = 0.0
    reason = "TIMEOUT"
    exit_t = end_t
    exit_px = float(bars.iloc[-1].close)
    for b in bars.itertuples(index=False):
        mfe = max(mfe, float(b.high) / entry - 1.0)
        mae = max(mae, 1.0 - float(b.low) / entry)
        hit_sl = float(b.low) <= sl_px
        hit_tp = float(b.high) >= tp_px
        # Frozen parent: adverse-first on same-5m ambiguity.
        if hit_sl:
            reason = "SL"
            exit_t = b.ts + pd.Timedelta(minutes=5)
            exit_px = sl_px
            break
        if hit_tp:
            reason = "TP"
            exit_t = b.ts + pd.Timedelta(minutes=5)
            exit_px = tp_px
            break
    gross_ret = exit_px / entry - 1.0
    price_pnl = NOTIONAL * gross_ret
    fund, fn = funding_cost(k, f, entry_t, exit_t, entry)
    pnl = price_pnl - FEE - fund
    return Trade(
        date=str(entry_t.date()), entry_t=str(entry_t), exit_t=str(exit_t), entry=entry, exit_px=exit_px,
        reason=reason, gross_ret=gross_ret, price_pnl=price_pnl, fee=FEE, funding=fund, pnl=pnl,
        mfe=mfe, mae=mae, funding_events=fn,
    )


def checkpoint_state(k: pd.DataFrame, entry_t: pd.Timestamp, minutes: int, entry: float) -> Optional[dict]:
    # Information from completed bars only through the bar ending at checkpoint.
    t = entry_t + pd.Timedelta(minutes=minutes)
    bars = k[(k.index >= entry_t) & (k.index < t)]
    if len(bars) != minutes // 5:
        return None
    last = bars.iloc[-1]
    prog = float(last.close) / entry - 1.0
    taker = float(np.nanmean(bars.taker_imb.to_numpy()))
    mfe = float(bars.high.max()) / entry - 1.0
    mae = 1.0 - float(bars.low.min()) / entry
    ema_dist = float(last.close) / float(last.ema20) - 1.0
    return {"progress": prog, "taker": taker, "mfe": mfe, "mae": mae, "ema20_dist": ema_dist}


def max_drawdown(pnls: list[float]) -> float:
    eq = np.cumsum(np.array(pnls, dtype=float))
    peaks = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peaks[1:] - eq
    return float(dd.max()) if len(dd) else 0.0


def max_loss_streak(pnls: list[float]) -> int:
    best = cur = 0
    for x in pnls:
        if x <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def profit_factor(pnls: list[float]) -> float:
    pos = sum(x for x in pnls if x > 0)
    neg = -sum(x for x in pnls if x <= 0)
    return float(pos / neg) if neg > 0 else float("inf")


def opposite_short_oracle(k: pd.DataFrame, trade: Trade, entry_t: pd.Timestamp, checkpoint_min: int, tp: float = SL, sl: float = SL) -> bool:
    """Diagnostic only: close BUY at checkpoint close then hypothetical SHORT; true if combined net becomes positive.
    Uses one extra round-trip fee for the SHORT. This is capacity, not a causal rule.
    """
    cp_t = entry_t + pd.Timedelta(minutes=checkpoint_min)
    if pd.Timestamp(trade.exit_t) <= cp_t:
        return False
    completed = k[(k.index >= entry_t) & (k.index < cp_t)]
    if completed.empty:
        return False
    short_entry = float(completed.iloc[-1].close)
    buy_ret = short_entry / trade.entry - 1.0
    buy_leg = NOTIONAL * buy_ret - FEE
    end_t = entry_t + pd.Timedelta(minutes=HOLD_MIN)
    bars = k[(k.index >= cp_t) & (k.index < end_t)]
    tp_px = short_entry * (1 - tp)
    sl_px = short_entry * (1 + sl)
    short_exit = float(bars.iloc[-1].close)
    for b in bars.itertuples(index=False):
        # adverse-first for short = SL first
        if float(b.high) >= sl_px:
            short_exit = sl_px
            break
        if float(b.low) <= tp_px:
            short_exit = tp_px
            break
    short_ret = 1.0 - short_exit / short_entry
    combined = buy_leg + NOTIONAL * short_ret - FEE
    return combined > 0


def main():
    k = load_klines()
    f = load_funding()
    entries = saturday_entries(k)
    trades = [simulate(k, f, t) for t in entries]
    rows = pd.DataFrame([asdict(x) for x in trades])
    pnls = rows.pnl.tolist()
    wins = int((rows.pnl > 0).sum())
    losses = len(rows) - wins
    summary = {
        "n": len(rows), "wins": wins, "losses": losses, "wr": wins / len(rows),
        "pnl": float(rows.pnl.sum()), "expectancy": float(rows.pnl.mean()),
        "pf": profit_factor(pnls), "max_dd": max_drawdown(pnls), "max_loss_streak": max_loss_streak(pnls),
        "tp": int((rows.reason == "TP").sum()), "sl": int((rows.reason == "SL").sum()),
        "timeout": int((rows.reason == "TIMEOUT").sum()), "funding": float(rows.funding.sum()),
        "funding_events": int(rows.funding_events.sum()),
    }

    # Reproduction gate against frozen A7 parent. Tolerance allows archive parsing/rounding only.
    gate = {
        "n": summary["n"] == 139,
        "wins": summary["wins"] == 65,
        "wr": abs(summary["wr"] - 0.4676258993) < 1e-6,
        "pnl": abs(summary["pnl"] - 87.20) < 0.20,
        "funding": abs(summary["funding"] - 6.96) < 0.25,
    }
    if not all(gate.values()):
        raise RuntimeError(f"S5.0 reproduction gate FAILED: {summary} gate={gate}")

    pos = rows[rows.pnl > 0]
    neg = rows[rows.pnl <= 0]
    for label, df in [("winner", pos), ("loser", neg)]:
        summary[f"{label}_mfe_median"] = float(df.mfe.median())
        summary[f"{label}_mae_median"] = float(df.mae.median())

    # Same core A5.0 questions.
    summary["loser_mfe_counts"] = {str(x): int((neg.mfe >= x).sum()) for x in [0.003, 0.004, 0.005, 0.006, 0.008, 0.010]}

    # Checkpoint path separation.
    cp = {m: {"winner": [], "loser": []} for m in [5, 10, 15, 30, 60]}
    entry_map = {str(t.date()): t for t in entries}
    for tr in trades:
        et = entry_map[tr.date]
        for m in cp:
            st = checkpoint_state(k, et, m, tr.entry)
            if st is not None:
                cp[m]["winner" if tr.pnl > 0 else "loser"].append(st)
    cp_out = {}
    for m, groups in cp.items():
        cp_out[str(m)] = {}
        for label, arr in groups.items():
            d = pd.DataFrame(arr)
            cp_out[str(m)][label] = {c: float(d[c].median()) for c in d.columns}
    summary["checkpoints"] = cp_out

    # Delayed-entry capacity: among SLs, how many later touch original TP before original 18h horizon?
    delayed = 0
    for tr in trades:
        if tr.reason != "SL":
            continue
        et = entry_map[tr.date]
        original_end = et + pd.Timedelta(minutes=HOLD_MIN)
        after_sl = k[(k.index >= pd.Timestamp(tr.exit_t)) & (k.index < original_end)]
        if not after_sl.empty and float(after_sl.high.max()) >= tr.entry * (1 + TP):
            delayed += 1
    summary["sl_later_hit_original_tp"] = delayed

    # Wrong-direction oracle capacity at early checkpoints, among parent-negative trades still alive.
    oracle = {}
    for m in [10, 15, 30, 60]:
        alive_neg = 0
        positive = 0
        for tr in trades:
            if tr.pnl > 0:
                continue
            et = entry_map[tr.date]
            cp_t = et + pd.Timedelta(minutes=m)
            if pd.Timestamp(tr.exit_t) <= cp_t:
                continue
            alive_neg += 1
            if opposite_short_oracle(k, tr, et, m):
                positive += 1
        oracle[str(m)] = {"negative_alive": alive_neg, "oracle_total_positive": positive}
    summary["wrong_direction_oracle"] = oracle

    # Discovery / validation baseline to preserve chronology.
    for name, df in [("discovery", rows.iloc[:83]), ("validation", rows.iloc[83:])]:
        summary[name] = {
            "n": int(len(df)), "wins": int((df.pnl > 0).sum()), "wr": float((df.pnl > 0).mean()),
            "pnl": float(df.pnl.sum()), "pf": profit_factor(df.pnl.tolist()), "max_dd": max_drawdown(df.pnl.tolist()),
        }

    rows.to_csv(OUT / "s50_rows.csv", index=False)
    (OUT / "s50_summary.json").write_text(json.dumps({"gate": gate, "summary": summary}, indent=2), encoding="utf-8")

    md = []
    md.append("# Saturday T-Method S5.0 — Parent Loss Forensics\n")
    md.append("**Status:** COMPLETE — parent reproduced; forensics only; A7.19/A7.26 preserved separately.\n")
    md.append("## Frozen static parent reproduction")
    md.append(f"- N {summary['n']} / wins {summary['wins']} / losses {summary['losses']} / WR {summary['wr']*100:.2f}%")
    md.append(f"- PnL +${summary['pnl']:.3f} / expectancy ${summary['expectancy']:.4f}/trade / PF {summary['pf']:.3f}")
    md.append(f"- DD ${summary['max_dd']:.3f} / max loss streak {summary['max_loss_streak']}")
    md.append(f"- TP/SL/timeout {summary['tp']}/{summary['sl']}/{summary['timeout']}")
    md.append(f"- funding cost ${summary['funding']:.3f} across {summary['funding_events']} settlements")
    md.append("\n## Winner vs loser paths")
    md.append(f"- winner MFE/MAE medians {summary['winner_mfe_median']*100:.4f}% / {summary['winner_mae_median']*100:.4f}%")
    md.append(f"- loser MFE/MAE medians {summary['loser_mfe_median']*100:.4f}% / {summary['loser_mae_median']*100:.4f}%")
    md.append("\n## Giveback capacity among negative trades")
    for x, n in summary['loser_mfe_counts'].items():
        md.append(f"- MFE >= {float(x)*100:.2f}%: {n}")
    md.append(f"\nSL losses that later reached original +2.6% target inside the same 18h horizon: **{delayed}**")
    md.append("\n## Early path separation")
    for m in [5,10,15,30,60]:
        w = cp_out[str(m)]['winner']; l = cp_out[str(m)]['loser']
        md.append(f"- {m}m progress winner/loser: {w['progress']*100:+.4f}% / {l['progress']*100:+.4f}%; taker {w['taker']:+.4f} / {l['taker']:+.4f}")
    md.append("\n## Wrong-direction oracle capacity (diagnostic only)")
    for m in [10,15,30,60]:
        o = oracle[str(m)]
        md.append(f"- {m}m: {o['oracle_total_positive']}/{o['negative_alive']} alive negative trades could theoretically become total-positive with a symmetric 1.2/1.2 SHORT")
    md.append("\n## Chronology")
    md.append(f"- discovery first83: WR {summary['discovery']['wr']*100:.2f}% / PnL ${summary['discovery']['pnl']:+.3f}")
    md.append(f"- validation last56: WR {summary['validation']['wr']*100:.2f}% / PnL ${summary['validation']['pnl']:+.3f}")
    md.append("\n## Scientific interpretation")
    md.append("S5.0 mirrors Tuesday A5.0: first determine whether Saturday's main weakness is wrong direction, delayed entry, or profitable-then-giveback losses. No management rule is selected in this milestone. Existing A7.19 full-coverage champion and A7.26 selective candidate remain preserved and unchanged.")
    (OUT / "S5.0_CHECKPOINT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"gate": gate, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
