#!/usr/bin/env python3
"""Saturday T-Method S5.7H — Frozen True-OOS Extension.

Research only; live BBC untouched.

This is the first genuinely unseen extension after the frozen research cutoff.
No signal, threshold, timing, TP/SL, or management definition may change.

Frozen champion under test (from S5.7G):
    NO_BULL_TOP_Q_30
    - base management = frozen A7.19
    - only after first +0.50% hinge
    - REJECTED_HINGE = upper wick >=50% of hinge candle full range
    - if rejected and still unresolved at +30m (has not already reached +0.80%)
    - if latest completed 5m candle is NOT bullish and closing in top quartile
      of its range, exit at the +30m actual open
    - otherwise preserve A7.19 exactly.

OOS entry window:
    [2026-07-30 00:00 UTC, 2026-08-17 00:00 UTC)
which contains Saturday 18:00 WIB entries on Aug 1, Aug 8, Aug 15.
Only completed daily data through Aug 16 are appended; Aug 17 partial data are
intentionally excluded.
"""
from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s51b_failure_no_ema_reclaim_cut as b51
import s52a_post_failure_recovery_forensics as a52
import s57c_hinge_rejection_robustness_management as c57
import s57d_rejected_hinge_excursion_monetization_atlas as d57
import s57e_post_rejection_expansion_stall_atlas as e57
import s57f_frozen_recovery_management_counterfactual as f57

OUT = Path(os.getenv("S57H_OUT", "s57h_out"))
OUT.mkdir(parents=True, exist_ok=True)
CACHE = Path(os.getenv("S57H_CACHE", "/tmp/s57h_cache"))
CACHE.mkdir(parents=True, exist_ok=True)

BASE = "https://data.binance.vision/data/futures/um"
SYMBOL = "BTCUSDT"
OOS_START = pd.Timestamp("2026-07-30 00:00:00", tz="UTC")
OOS_ENTRY_END = pd.Timestamp("2026-08-17 00:00:00", tz="UTC")
DAILY_START = pd.Timestamp("2026-08-01", tz="UTC")
DAILY_END = pd.Timestamp("2026-08-16", tz="UTC")
EXPECTED_ENTRY_DATES = ["2026-08-01", "2026-08-08", "2026-08-15"]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "bababot-discovery-s57h/1.0"})


def get_bytes(url: str, name: str) -> bytes:
    p = CACHE / name
    if p.exists():
        return p.read_bytes()
    r = SESSION.get(url, timeout=60)
    r.raise_for_status()
    p.write_bytes(r.content)
    return r.content


def read_zip(url: str, name: str, header="infer") -> pd.DataFrame:
    data = get_bytes(url, name)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError(f"no csv in {url}")
        with zf.open(names[0]) as fh:
            return pd.read_csv(fh, header=header)


def parse_kline_zip(day: pd.Timestamp) -> pd.DataFrame:
    ds = day.strftime("%Y-%m-%d")
    url = f"{BASE}/daily/klines/{SYMBOL}/5m/{SYMBOL}-5m-{ds}.zip"
    df = read_zip(url, f"{SYMBOL}-5m-{ds}.zip")
    if len(df.columns) == 12 and str(df.columns[0]).isdigit():
        df = read_zip(url, f"{SYMBOL}-5m-{ds}.zip", header=None)
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
    return df[["ts", "open", "high", "low", "close", "quote_volume", "taker_buy_quote"]]


def parse_funding_zip(day: pd.Timestamp) -> pd.DataFrame:
    ds = day.strftime("%Y-%m-%d")
    url = f"{BASE}/daily/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-{ds}.zip"
    df = read_zip(url, f"{SYMBOL}-fundingRate-{ds}.zip")
    df.columns = [str(c).strip().lower() for c in df.columns]
    time_col = "calc_time" if "calc_time" in df.columns else ("fundingtime" if "fundingtime" in df.columns else None)
    rate_col = "last_funding_rate" if "last_funding_rate" in df.columns else ("fundingrate" if "fundingrate" in df.columns else None)
    if time_col is None or rate_col is None:
        raise RuntimeError(f"unexpected daily funding columns {df.columns.tolist()} on {ds}")
    vals = pd.to_numeric(df[time_col], errors="coerce")
    if vals.notna().mean() > 0.9:
        unit = "us" if vals.dropna().median() > 1e14 else "ms"
        ts = pd.to_datetime(vals, unit=unit, utc=True)
    else:
        ts = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    return pd.DataFrame({"ts": ts, "rate": pd.to_numeric(df[rate_col], errors="coerce")})


def days(start: pd.Timestamp, end: pd.Timestamp):
    cur = start.normalize()
    while cur <= end.normalize():
        yield cur
        cur += pd.Timedelta(days=1)


def load_extended():
    # Historical base provides complete EMA warmup through Jul-31.
    hist_k = s50.load_klines().reset_index(drop=True)[
        ["ts", "open", "high", "low", "close", "quote_volume", "taker_buy_quote"]
    ]
    daily_k = [parse_kline_zip(d) for d in days(DAILY_START, DAILY_END)]
    k = pd.concat([hist_k, *daily_k], ignore_index=True)
    k = k.dropna(subset=["ts", "open", "high", "low", "close"]).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    k["ema20"] = k["close"].ewm(span=20, adjust=False).mean()
    k["ema7"] = k["close"].ewm(span=7, adjust=False).mean()
    k["taker_imb"] = np.where(k["quote_volume"] > 0, 2 * k["taker_buy_quote"] / k["quote_volume"] - 1.0, np.nan)
    k = k.set_index("ts", drop=False)

    hist_f = s50.load_funding()
    daily_f = [parse_funding_zip(d) for d in days(DAILY_START, DAILY_END)]
    f = pd.concat([hist_f, *daily_f], ignore_index=True).dropna().drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    return k, f


def oos_entries(k: pd.DataFrame):
    idx = k.index
    mask = (
        (idx >= OOS_START) & (idx < OOS_ENTRY_END) &
        (idx.dayofweek == 5) & (idx.hour == 11) & (idx.minute == 0)
    )
    return list(idx[mask])


def frozen_champion(k, f, t, tr):
    s240 = a50.state240(k, t, tr)
    a719 = float(a50.a719_pnl(k, f, t, tr, s240))
    a719_exit = f57.a719_exit_time(t, tr, s240)

    h05, _ = a52.first_hinges(k, t, tr)
    rejected = False
    unresolved30 = False
    bull_top_q30 = None
    action = False
    champion = a719
    action_t = None
    action_px = np.nan
    post_expand08 = False
    hinge_upper_wick_ratio = np.nan

    if h05 is not None:
        hinge_ts = h05 - pd.Timedelta(minutes=5)
        hinge = k.loc[hinge_ts]
        cm = c57.morph(hinge)
        hinge_upper_wick_ratio = float(cm["upper_wick_ratio"])
        rejected = bool(np.isfinite(hinge_upper_wick_ratio) and hinge_upper_wick_ratio >= 0.50)
        if rejected:
            post = d57.post_hinge_path(k, tr, h05)
            post_expand08 = bool(post["reach_080bp"])
            feat = e57.snapshot_features(k, tr, h05, hinge, 30)
            unresolved30 = bool(feat.get("unresolved", False))
            if unresolved30:
                bull_top_q30 = bool(feat["last_bull_top_q"])
                d = h05 + pd.Timedelta(minutes=30)
                if (not bull_top_q30) and d <= a719_exit and d in k.index:
                    action = True
                    champion, action_px = f57.exit_open_pnl(k, f, t, tr, d)
                    action_t = d

    return {
        "a719_pnl": a719,
        "a719_state240": s240["state240"],
        "h05": h05,
        "rejected_hinge": rejected,
        "hinge_upper_wick_ratio": hinge_upper_wick_ratio,
        "unresolved30": unresolved30,
        "bull_top_q30": bull_top_q30,
        "post_expand08": post_expand08,
        "action": action,
        "action_t": action_t,
        "action_px": action_px,
        "champion_pnl": float(champion),
        "delta_vs_a719": float(champion - a719),
    }


def main():
    k, f = load_extended()
    entries = oos_entries(k)
    dates = [t.strftime("%Y-%m-%d") for t in entries]
    if dates != EXPECTED_ENTRY_DATES:
        raise RuntimeError(f"unexpected OOS entries: {dates}")

    trades = [s50.simulate(k, f, t) for t in entries]
    rows = []
    for t, tr in zip(entries, trades):
        ch = frozen_champion(k, f, t, tr)
        rows.append({
            "date": tr.date,
            "entry_t": str(t),
            "entry": float(tr.entry),
            "parent_reason": tr.reason,
            "parent_exit_t": tr.exit_t,
            "parent_pnl": float(tr.pnl),
            "parent_mfe": float(tr.mfe),
            "parent_mae": float(tr.mae),
            "a719_pnl": ch["a719_pnl"],
            "a719_state240": ch["a719_state240"],
            "reached_hinge05": ch["h05"] is not None,
            "h05": None if ch["h05"] is None else str(ch["h05"]),
            "rejected_hinge": ch["rejected_hinge"],
            "hinge_upper_wick_ratio": ch["hinge_upper_wick_ratio"],
            "unresolved30": ch["unresolved30"],
            "bull_top_q30": ch["bull_top_q30"],
            "post_expand08": ch["post_expand08"],
            "champion_action": ch["action"],
            "champion_action_t": None if ch["action_t"] is None else str(ch["action_t"]),
            "champion_action_px": ch["action_px"],
            "champion_pnl": ch["champion_pnl"],
            "delta_vs_a719": ch["delta_vs_a719"],
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "s57h_true_oos_trades.csv", index=False)

    parent = df.parent_pnl.to_numpy(float)
    a719 = df.a719_pnl.to_numpy(float)
    champion = df.champion_pnl.to_numpy(float)
    summary = {
        "window": {
            "research_cutoff": str(OOS_START),
            "entry_end_exclusive": str(OOS_ENTRY_END),
            "completed_daily_data_through": str(DAILY_END.date()),
        },
        "n": int(len(df)),
        "dates": dates,
        "parent": b51.metrics(parent),
        "a719": b51.metrics(a719),
        "champion": b51.metrics(champion),
        "champion_delta_vs_a719": float((champion - a719).sum()),
        "champion_actions": int(df.champion_action.sum()),
        "rejected_hinges": int(df.rejected_hinge.sum()),
        "rejected_actions": int(df.champion_action.sum()),
        "trades": df.to_dict(orient="records"),
        "interpretation_guard": "Only 3 true-OOS Saturdays exist; this is an observation, not statistical confirmation or a reason to tune the frozen rule.",
    }
    (OUT / "s57h_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    def money(x): return f"${x:+.3f}"
    def pct(x): return f"{100*x:.2f}%"

    md = [
        "# BTC Temporal Saturday T-Method S5.7H — Frozen True-OOS Extension",
        "",
        "**Status:** COMPLETE — TRUE-OOS OBSERVATION ONLY; FROZEN RULE UNCHANGED",
        "**Research only:** live BBC untouched",
        "",
        "## Frozen OOS protocol",
        "- Research cutoff: **2026-07-30 00:00 UTC**.",
        "- OOS entries scored: Saturday 18:00 WIB on **2026-08-01, 2026-08-08, 2026-08-15**.",
        "- Only completed Binance daily data through **2026-08-16** were appended.",
        "- The S5.7G `NO_BULL_TOP_Q_30` rule is replayed with **zero definition changes**.",
        "- Historical pre-cutoff candles are used only as EMA/path warmup, never as OOS scoring rows.",
        "",
        "## Aggregate true-OOS results",
        f"- N: **{len(df)}**",
        f"- Static parent: **{money(parent.sum())}**, WR **{pct((parent>0).mean())}**",
        f"- A7.19: **{money(a719.sum())}**, WR **{pct((a719>0).mean())}**",
        f"- Frozen S5.7G champion: **{money(champion.sum())}**, WR **{pct((champion>0).mean())}**",
        f"- Champion delta vs A7.19: **{money((champion-a719).sum())}**",
        f"- Rejected hinges: **{int(df.rejected_hinge.sum())}**; champion actions: **{int(df.champion_action.sum())}**",
        "",
        "## Trade-by-trade",
        "| Date | Parent | A7.19 | Champion | +0.5? | Rejected? | +30 unresolved? | Bull-top-q? | Action? | Delta vs A7.19 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in df.itertuples(index=False):
        md.append(
            f"| {r.date} | {money(r.parent_pnl)} | {money(r.a719_pnl)} | {money(r.champion_pnl)} | "
            f"{'YES' if r.reached_hinge05 else 'NO'} | {'YES' if r.rejected_hinge else 'NO'} | "
            f"{'YES' if r.unresolved30 else 'NO'} | "
            f"{('YES' if r.bull_top_q30 else 'NO') if pd.notna(r.bull_top_q30) else 'NA'} | "
            f"{'YES' if r.champion_action else 'NO'} | {money(r.delta_vs_a719)} |"
        )

    md += [
        "",
        "## Interpretation guard",
        "Three OOS Saturdays are far too few for statistical confirmation. The valid question here is only whether the frozen rule encountered genuinely unseen states and whether its action helped or hurt them. No parameter may be changed from these observations.",
        "",
        "A7.19 and the frozen S5.7G champion remain research strategies; no live BBC modification is made.",
    ]
    (OUT / "S5.7H_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
