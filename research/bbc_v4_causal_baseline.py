#!/usr/bin/env python3
"""BBC V4 strict causal baseline.

Research-only. Does not call exchange endpoints and does not modify live BBC.

Compares two executable-timing controls using the same frozen BBC state machine:
1) close_proxy: signal is known at completed 1H close and the backtest books that
   same close as the entry reference (existing V7-E style control).
2) next_open_strict: signal is known at completed 1H close, then the position is
   actually opened at the NEXT 1H candle open. This is the primary V4 baseline.

Both controls disable legacy same-hour 15m MTF, skip SIDEWAYS trades, retain
EMA7 / body filters / direct transitions, and charge frozen 0.15% total costs.
Market data comes only from public Binance USD-M Futures Data Vision archives.
"""
from __future__ import annotations

import csv
import io
import json
import math
import sys
import time
import zipfile
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mode3_bbc import Mode3BBCConfig, Switcher, Position, compute_ema_series, compute_va_at_bar

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
WINDOWS = [90, 120, 971]
END_EXCLUSIVE = datetime(2026, 8, 19, 0, 0, tzinfo=timezone.utc)
WARMUP_DAYS = 60
TF = "1h"
MONTHLY_BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
DAILY_BASE = "https://data.binance.vision/data/futures/um/daily/klines"
OUT_JSON = ROOT / "BTC_BBC_V4_Causal_Baseline.json"
OUT_MD = ROOT / "BTC_BBC_V4_Causal_Baseline.md"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "bababot-v4-causal-baseline/1.0"})


def cfg() -> Mode3BBCConfig:
    return Mode3BBCConfig(
        ema_period=7,
        tp_pct=0.013,
        sl_pct=0.013,
        bear_tp_pct=0.0,
        bear_sl_pct=0.0,
        enable_sideways_trades=False,
        direct_transition_enabled=True,
        use_wick_exit=True,
        entry_usd=10.0,
        leverage=50.0,
        fee_pct_roundtrip=0.001,
        slippage_pct=0.0005,
        bull_mtf_15m_enabled=False,
        bear_mtf_15m_enabled=False,
        sideways_mtf_15m_enabled=False,
        bull_body_ratio_min=0.5,
        bear_body_ratio_min=0.6,
        sideways_body_ratio_min=0.6,
        trailing_ema_enabled=False,
        bull_poc_entry_enabled=False,
        bull_wait_retest_enabled=False,
        bull_use_swing_break=False,
        bull_use_26_support=False,
        sideways_poc_breakout_enabled=False,
    )


def normalize_ts(v: str) -> int:
    x = int(v)
    # Defensive normalization if archive timestamps are microseconds.
    while x > 10**14:
        x //= 1000
    return x


def parse_zip(raw: bytes) -> list[tuple]:
    zf = zipfile.ZipFile(io.BytesIO(raw))
    name = zf.namelist()[0]
    out = []
    with zf.open(name) as fh:
        rd = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
        for r in rd:
            if len(r) < 6:
                continue
            try:
                ts = normalize_ts(r[0])
                o, h, l, c, v = map(float, r[1:6])
            except (ValueError, TypeError):
                continue
            out.append((ts, o, h, l, c, v))
    return out


def get_zip(url: str, attempts: int = 4) -> tuple[int, bytes]:
    err = None
    for n in range(attempts):
        try:
            r = SESSION.get(url, timeout=45)
            if r.status_code == 404:
                return 404, b""
            r.raise_for_status()
            return r.status_code, r.content
        except Exception as exc:
            err = exc
            time.sleep(1.0 + n)
    raise RuntimeError(f"download failed {url}: {err}")


def month_iter(start: date, end_exclusive: date):
    cur = date(start.year, start.month, 1)
    while cur < end_exclusive:
        yield cur
        cur = date(cur.year + (cur.month == 12), 1 if cur.month == 12 else cur.month + 1, 1)


def next_month(d: date) -> date:
    return date(d.year + (d.month == 12), 1 if d.month == 12 else d.month + 1, 1)


def fetch_symbol(symbol: str, start_dt: datetime, end_dt: datetime) -> list[tuple]:
    rows: list[tuple] = []
    start_d = start_dt.date()
    end_d = end_dt.date()
    for m in month_iter(start_d, end_d):
        ym = m.strftime("%Y-%m")
        monthly = f"{MONTHLY_BASE}/{symbol}/{TF}/{symbol}-{TF}-{ym}.zip"
        status, raw = get_zip(monthly)
        if status == 200:
            rows.extend(parse_zip(raw))
            print(f"{symbol} {ym}: monthly OK")
            continue

        # Current/unpublished monthly archive: fall back to completed daily files.
        lo = max(m, start_d)
        hi = min(next_month(m), end_d)
        d = lo
        while d < hi:
            ds = d.isoformat()
            daily = f"{DAILY_BASE}/{symbol}/{TF}/{symbol}-{TF}-{ds}.zip"
            st, dr = get_zip(daily)
            if st == 200:
                rows.extend(parse_zip(dr))
            elif st != 404:
                raise RuntimeError(f"unexpected HTTP {st} for {daily}")
            d += timedelta(days=1)
        print(f"{symbol} {ym}: daily fallback")

    lo_ms = int(start_dt.timestamp() * 1000)
    hi_ms = int(end_dt.timestamp() * 1000)
    dedup = {r[0]: r for r in rows if lo_ms <= r[0] < hi_ms}
    out = [dedup[k] for k in sorted(dedup)]
    if not out:
        raise RuntimeError(f"no data for {symbol}")
    # Require near-hourly continuity; gaps are reported and tolerated only if tiny.
    expected = max(1, int((end_dt - start_dt).total_seconds() // 3600))
    coverage = len(out) / expected
    if coverage < 0.985:
        raise RuntimeError(f"{symbol} coverage too low: {len(out)}/{expected}={coverage:.3%}")
    return out


def arrays(rows):
    O = np.asarray([r[1] for r in rows], float)
    H = np.asarray([r[2] for r in rows], float)
    L = np.asarray([r[3] for r in rows], float)
    C = np.asarray([r[4] for r in rows], float)
    V = np.asarray([r[5] for r in rows], float)
    ema = compute_ema_series(C, 7)
    c = cfg()
    vah, val, poc = [], [], []
    for i in range(len(rows)):
        a, b, cc = compute_va_at_bar(H, L, C, V, i, c.va_window, c.va_percentile_high, c.va_percentile_low)
        vah.append(a); val.append(b); poc.append(cc)
    return O, H, L, C, V, ema, vah, val, poc


def signal_from_position(sw: Switcher, bar_idx: int, ts: int, ema_at_signal: float):
    p = sw.position
    if p is None:
        return None
    sig = {
        "tool": p.tool,
        "side": p.side,
        "signal_bar": bar_idx,
        "signal_time": ts,
        "entry_trigger": p.entry_trigger,
        "ema_at_signal": float(ema_at_signal),
    }
    sw.position = None
    return sig


def inject_at_open(sw: Switcher, sig: dict, bar_idx: int, open_price: float):
    c = sw.config
    side = sig["side"]
    if side == "LONG":
        sl = open_price * (1.0 - c.sl_pct)
        tp = open_price * (1.0 + c.tp_pct)
    else:
        sl = open_price * (1.0 + c.get_bear_sl_pct())
        tp = open_price * (1.0 - c.get_bear_tp_pct())
    sw.position = Position(
        tool=sig["tool"],
        side=side,
        entry_price=float(open_price),
        entry_bar=bar_idx,
        entry_high=float(open_price),
        entry_low=float(open_price),
        sl_level=float(sl),
        tp_level=float(tp),
        peak_high=float(open_price),
        trough_low=float(open_price),
        ema_at_entry=float(sig["ema_at_signal"]),
        entry_trigger=sig.get("entry_trigger", ""),
        original_sl=float(sl),
    )


def run_close_proxy(rows):
    c = cfg(); sw = Switcher(c)
    O,H,L,C,V,ema,vah,val,poc = arrays(rows)
    for i, r in enumerate(rows):
        sw.process_candle(i, O[i], H[i], L[i], C[i], ema[i], vah[i], val[i], poc[i])
    return sw.trades


def run_next_open(rows):
    c = cfg(); sw = Switcher(c)
    O,H,L,C,V,ema,vah,val,poc = arrays(rows)
    pending = None
    for i, r in enumerate(rows):
        real_at_start = sw.position is not None
        if not real_at_start and pending is not None:
            inject_at_open(sw, pending, i, O[i])
            pending = None
            real_at_start = True

        sw.process_candle(i, O[i], H[i], L[i], C[i], ema[i], vah[i], val[i], poc[i])

        # A position appearing from a flat start was generated by the just-closed
        # 1H signal candle. Convert it into a pending NEXT-open order instead of
        # booking the already-known close price.
        if not real_at_start and sw.position is not None:
            pending = signal_from_position(sw, i, int(r[0]), ema[i])
    return sw.trades


def trade_record(symbol: str, rows: list[tuple], t) -> dict:
    ebar = int(t.entry_bar); xbar = int(t.exit_bar)
    return {
        "symbol": symbol,
        "tool": t.tool,
        "side": t.side,
        "entry_time": int(rows[ebar][0]),
        "exit_time": int(rows[xbar][0]),
        "entry_price": float(t.entry_price),
        "exit_price": float(t.exit_price),
        "exit_type": t.exit_type,
        "pnl_usd": float(t.pnl_usd),
        "pnl_pct": float(t.pnl_pct),
    }


def stat(xs: list[dict]) -> dict:
    xs = sorted(xs, key=lambda x: (x["exit_time"], x["symbol"], x["entry_time"]))
    n = len(xs)
    wins = [x["pnl_usd"] for x in xs if x["pnl_usd"] > 0]
    losses = [x["pnl_usd"] for x in xs if x["pnl_usd"] <= 0]
    gross_win = sum(wins); gross_loss = -sum(losses)
    pnl = gross_win - gross_loss
    eq = peak = dd = 0.0
    streak = max_streak = 0
    for x in xs:
        eq += x["pnl_usd"]
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
        if x["pnl_usd"] <= 0:
            streak += 1; max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "wr_pct": round(100 * len(wins) / n, 2) if n else None,
        "pnl_usd": round(pnl, 2),
        "expectancy_usd": round(pnl / n, 4) if n else None,
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else None,
        "max_drawdown_usd": round(dd, 2),
        "max_loss_streak": max_streak,
    }


def render_md(payload: dict) -> str:
    lines = [
        "# BBC V4 — Strict Causal Live Baseline",
        "",
        "**Research-only. Live BBC files and exchange execution are untouched.**",
        "",
        f"Frozen end-exclusive: `{payload['end_exclusive_utc']}`",
        "",
        "Primary V4 definition: completed 1H signal → **entry at next 1H open**; MTF 15m disabled; SIDEWAYS skipped; EMA7; TP/SL 1.3%/1.3%; bull body ≥0.5; bear body ≥0.6; 0.15% modeled round-trip cost.",
        "",
        "The `close_proxy` control books the just-completed 1H close and exists only to quantify execution-timing sensitivity.",
        "",
    ]
    for days in WINDOWS:
        w = payload["windows"][str(days)]
        lines += [f"## {days} days", "", "| Mode | Trades | WR | PnL | Exp/trade | PF | Max DD |", "|---|---:|---:|---:|---:|---:|---:|"]
        for mode in ("close_proxy", "next_open_strict"):
            s = w[mode]["overall"]
            lines.append(
                f"| {mode} | {s['trades']} | {s['wr_pct'] if s['wr_pct'] is not None else '-'}% | ${s['pnl_usd']:+.2f} | ${s['expectancy_usd'] if s['expectancy_usd'] is not None else 0:+.4f} | {s['profit_factor'] if s['profit_factor'] is not None else '-'} | ${s['max_drawdown_usd']:.2f} |"
            )
        d = w["timing_delta_next_open_minus_close"]
        lines += ["", f"Timing delta (next-open minus close): PnL **${d['pnl_usd']:+.2f}**, WR **{d['wr_pct']:+.2f} pp**, expectancy **${d['expectancy_usd']:+.4f}/trade**.", "", "### Next-open by pair", "", "| Pair | Trades | WR | PnL | PF | DD |", "|---|---:|---:|---:|---:|---:|"]
        for p in PAIRS:
            s = w["next_open_strict"]["by_pair"][p]
            lines.append(f"| {p} | {s['trades']} | {s['wr_pct'] if s['wr_pct'] is not None else '-'}% | ${s['pnl_usd']:+.2f} | {s['profit_factor'] if s['profit_factor'] is not None else '-'} | ${s['max_drawdown_usd']:.2f} |")
        lines.append("")
    lines += [
        "## Interpretation rule",
        "",
        "Do not tune thresholds from this run. First determine whether the strict next-open baseline remains economically positive and reasonably stable across 90d, 120d, 971d, pairs, and chronological blocks. Only then open a separately preregistered improvement study.",
        "",
    ]
    return "\n".join(lines)


def main():
    longest_start = END_EXCLUSIVE - timedelta(days=max(WINDOWS))
    data_start = longest_start - timedelta(days=WARMUP_DAYS)
    raw_by_pair = {}
    meta = {}
    for p in PAIRS:
        rr = fetch_symbol(p, data_start, END_EXCLUSIVE)
        raw_by_pair[p] = rr
        meta[p] = {
            "bars": len(rr),
            "first_utc": datetime.fromtimestamp(rr[0][0]/1000, timezone.utc).isoformat(),
            "last_open_utc": datetime.fromtimestamp(rr[-1][0]/1000, timezone.utc).isoformat(),
        }

    payload = {
        "phase": "BBC_V4_CAUSAL_BASELINE",
        "status": "RESEARCH_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "end_exclusive_utc": END_EXCLUSIVE.isoformat(),
        "pairs": PAIRS,
        "windows_days": WINDOWS,
        "definition": {
            "primary_entry": "next_1h_open_after_completed_1h_signal",
            "control_entry": "completed_1h_close_proxy",
            "same_hour_15m_mtf": False,
            "sideways_trades": False,
            "ema_period": 7,
            "tp_pct": 0.013,
            "sl_pct": 0.013,
            "bull_body_ratio_min": 0.5,
            "bear_body_ratio_min": 0.6,
            "roundtrip_cost_pct": 0.0015,
            "reference_notional_usd": 500.0,
            "threshold_sweep": False,
        },
        "data": meta,
        "windows": {},
    }

    for days in WINDOWS:
        start = END_EXCLUSIVE - timedelta(days=days)
        start_ms = int(start.timestamp() * 1000)
        mode_records = {"close_proxy": [], "next_open_strict": []}
        for p in PAIRS:
            all_rows = raw_by_pair[p]
            sim_start = start - timedelta(days=WARMUP_DAYS)
            sim_ms = int(sim_start.timestamp() * 1000)
            rows = [r for r in all_rows if sim_ms <= r[0] < int(END_EXCLUSIVE.timestamp()*1000)]
            for mode, runner in (("close_proxy", run_close_proxy), ("next_open_strict", run_next_open)):
                trades = runner(rows)
                recs = [trade_record(p, rows, t) for t in trades]
                recs = [x for x in recs if start_ms <= x["entry_time"] < int(END_EXCLUSIVE.timestamp()*1000)]
                mode_records[mode].extend(recs)

        win_out = {}
        for mode in ("close_proxy", "next_open_strict"):
            xs = mode_records[mode]
            overall = stat(xs)
            by_pair = {p: stat([x for x in xs if x["symbol"] == p]) for p in PAIRS}
            # Four equal chronological blocks of the requested window.
            span = (END_EXCLUSIVE - start) / 4
            by_block = {}
            for j in range(4):
                lo = int((start + span*j).timestamp()*1000)
                hi = int((start + span*(j+1)).timestamp()*1000)
                by_block[f"Q{j+1}"] = stat([x for x in xs if lo <= x["entry_time"] < hi])
            win_out[mode] = {"overall": overall, "by_pair": by_pair, "by_block": by_block}

        a = win_out["close_proxy"]["overall"]
        b = win_out["next_open_strict"]["overall"]
        win_out["timing_delta_next_open_minus_close"] = {
            "pnl_usd": round(b["pnl_usd"] - a["pnl_usd"], 2),
            "wr_pct": round((b["wr_pct"] or 0) - (a["wr_pct"] or 0), 2),
            "expectancy_usd": round((b["expectancy_usd"] or 0) - (a["expectancy_usd"] or 0), 4),
        }
        payload["windows"][str(days)] = win_out

    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    OUT_MD.write_text(render_md(payload))
    print(render_md(payload))


if __name__ == "__main__":
    main()
