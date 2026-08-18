#!/usr/bin/env python3
"""SUN2.2 — Frozen Sunday16 dynamic router true-OOS extension.

Research only; live BBC untouched.

Frozen candidate under test (defined entirely from pre-cutoff history):
- Base = SUN2.0 natural-state engine.
- Additional conservative decision from SUN2.1: F-|S-|U+ => WAIT.
- All other SUN2.0 decisions remain unchanged.
- Entry = Sunday 16:00 WIB actual 5m open.
- BUY/SELL geometry = TP 2.5%, SL 1.4%, max hold 18h.
- $500 reference notional, 0.15% round-trip fee, historical funding.
- Adverse-first if TP and SL touch in the same 5m bar.

True-OOS scoring window:
- Research cutoff: 2026-07-30 00:00 UTC.
- Score Sunday 16:00 WIB on 2026-08-02, 2026-08-09, 2026-08-16.
- No OOS observation may alter any router decision.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import s57h_true_oos_extension as h57
import sun17_sunday16_loss_prevday_forensics as sun17
import sun19_sunday16_dynamic_direction_engine as sun19

OUT = Path(os.getenv("SUN22_OUT", "sun22_out"))
OUT.mkdir(parents=True, exist_ok=True)

DISC_N = 83
TARGET = {"F+|S+|U-", "F+|S-|U+", "F-|S+|U+", "F-|S-|U+"}
BAD_WAIT = "F-|S-|U+"
OOS_START = pd.Timestamp("2026-07-30 00:00:00", tz="UTC")
OOS_END = pd.Timestamp("2026-08-18 00:00:00", tz="UTC")
DAILY_START = pd.Timestamp("2026-08-01", tz="UTC")
DAILY_END = pd.Timestamp("2026-08-17", tz="UTC")
EXPECTED = ["2026-08-02", "2026-08-09", "2026-08-16"]


def metrics(a):
    a = np.asarray(a, float)
    if len(a) == 0:
        return {"n": 0, "wins": 0, "wr": None, "pnl": 0.0, "pf": None, "exp": None}
    wins = int((a > 0).sum())
    gp = float(a[a > 0].sum())
    gl = float(-a[a <= 0].sum())
    return {
        "n": int(len(a)),
        "wins": wins,
        "wr": float(wins / len(a)),
        "pnl": float(a.sum()),
        "pf": float(gp / gl) if gl > 0 else 999.0,
        "exp": float(a.mean()),
    }


def choose(d_sell, d_buy):
    ms = metrics(d_sell)
    mb = metrics(d_buy)
    best = "SELL" if ms["pnl"] >= mb["pnl"] else "BUY"
    return best if max(ms["pnl"], mb["pnl"]) > 0 else "WAIT"


def sign(x):
    return "+" if x >= 0 else "-"


def load_recent_funding():
    start = int(DAILY_START.timestamp() * 1000)
    end = int(OOS_END.timestamp() * 1000) - 1
    params = {"symbol": "BTCUSDT", "startTime": start, "endTime": end, "limit": 1000}
    endpoints = [
        "https://fapi.binance.com/fapi/v1/fundingRate",
        "https://www.binance.com/fapi/v1/fundingRate",
    ]
    errors = []
    for url in endpoints:
        try:
            r = requests.get(url, params=params, timeout=60, headers={"User-Agent": "bababot-discovery-sun22/1.0"})
            if r.status_code != 200:
                errors.append(f"{url}: HTTP {r.status_code}")
                continue
            data = r.json()
            if not isinstance(data, list) or not data:
                errors.append(f"{url}: empty/non-list")
                continue
            d = pd.DataFrame(data)
            out = pd.DataFrame({
                "ts": pd.to_datetime(pd.to_numeric(d["fundingTime"], errors="coerce"), unit="ms", utc=True),
                "rate": pd.to_numeric(d["fundingRate"], errors="coerce"),
            }).dropna()
            out = out[(out.ts >= DAILY_START) & (out.ts < OOS_END)]
            if len(out) < 45:
                errors.append(f"{url}: suspicious funding rows {len(out)}")
                continue
            return out.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
        except Exception as e:
            errors.append(f"{url}: {type(e).__name__}: {e}")
    raise RuntimeError("unable to load recent funding: " + " | ".join(errors))


def load_extended():
    hist_k = s50.load_klines().reset_index(drop=True)[
        ["ts", "open", "high", "low", "close", "quote_volume", "taker_buy_quote"]
    ]
    recent = [h57.parse_kline_zip(d) for d in h57.days(DAILY_START, DAILY_END)]
    k = pd.concat([hist_k, *recent], ignore_index=True)
    k = k.dropna(subset=["ts", "open", "high", "low", "close"]).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    k["ema20"] = k["close"].ewm(span=20, adjust=False).mean()
    k["ema7"] = k["close"].ewm(span=7, adjust=False).mean()
    k["taker_imb"] = np.where(k["quote_volume"] > 0, 2 * k["taker_buy_quote"] / k["quote_volume"] - 1.0, np.nan)
    k = k.set_index("ts", drop=False)

    hist_f = s50.load_funding()
    recent_f = load_recent_funding()
    f = pd.concat([hist_f, recent_f], ignore_index=True).dropna().drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    return k, f


def historical_router():
    """Reconstruct SUN2.0 from historical discovery only, then freeze BAD_WAIT."""
    k = f517.load_klines()
    f = s50.load_funding()
    es = sun19.entries(k)
    rows, sell, buy = [], [], []
    for i, t in enumerate(es):
        ctx = sun17.pre_context(k, t)
        s = sun19.simulate(k, f, t, -1)
        b = sun19.simulate(k, f, t, 1)
        rows.append({
            "i": i,
            "coarse": sun19.state_key(ctx),
            "thu_sign": sign(ctx["thu_day_ret"]),
            "l4_sign": sign(ctx["sun12_to16_ret"]),
        })
        sell.append(s["pnl"])
        buy.append(b["pnl"])
    df = pd.DataFrame(rows)
    sell = np.asarray(sell, float)
    buy = np.asarray(buy, float)

    coarse_dec = {}
    for st in sorted(df.coarse.unique()):
        idx = np.flatnonzero(df.coarse.to_numpy() == st)
        d = idx[idx < DISC_N]
        runner = "|S-|U-" in st
        coarse_dec[st] = "SELL" if runner else choose(sell[d], buy[d])

    p19 = []
    for i, r in df.iterrows():
        dec = coarse_dec[r.coarse]
        if dec != "WAIT":
            p19.append(sell[i] if dec == "SELL" else buy[i])
    m19 = metrics(p19)
    if not (m19["n"] == 76 and abs(m19["pnl"] - 190.6360904374706) < 0.25):
        raise RuntimeError(f"SUN1.9 parity failed: {m19}")

    thu_dec, l4_dec = {}, {}
    for st in sorted(TARGET):
        for sg in ["+", "-"]:
            idx1 = np.flatnonzero((df.coarse.to_numpy() == st) & (df.thu_sign.to_numpy() == sg) & (df.i.to_numpy() < DISC_N))
            idx2 = np.flatnonzero((df.coarse.to_numpy() == st) & (df.l4_sign.to_numpy() == sg) & (df.i.to_numpy() < DISC_N))
            thu_dec[(st, sg)] = choose(sell[idx1], buy[idx1])
            l4_dec[(st, sg)] = choose(sell[idx2], buy[idx2])

    def decision_for(coarse, thu_s, l4_s):
        if coarse == BAD_WAIT:
            return "WAIT"
        if coarse not in TARGET:
            return coarse_dec[coarse]
        a = thu_dec[(coarse, thu_s)]
        b = l4_dec[(coarse, l4_s)]
        return a if (a == b and a != "WAIT") else "WAIT"

    cand, cand_i, dirs = [], [], []
    for i, r in df.iterrows():
        dec = decision_for(r.coarse, r.thu_sign, r.l4_sign)
        if dec == "WAIT":
            continue
        cand.append(sell[i] if dec == "SELL" else buy[i])
        cand_i.append(i)
        dirs.append(dec)
    cand = np.asarray(cand, float)
    cidx = np.asarray(cand_i, int)
    hist = {
        "full": metrics(cand),
        "D": metrics(cand[cidx < DISC_N]),
        "V": metrics(cand[cidx >= DISC_N]),
        "sell_n": int(sum(x == "SELL" for x in dirs)),
        "buy_n": int(sum(x == "BUY" for x in dirs)),
        "wait_n": int(139 - len(cand)),
    }
    if hist["full"]["n"] != 85:
        raise RuntimeError(f"frozen candidate expected 85 historical trades, got {hist}")
    return decision_for, hist


def oos_entries(k):
    idx = k.index
    local = idx + pd.Timedelta(hours=7)
    m = (
        (idx >= OOS_START) & (idx < OOS_END) &
        (local.dayofweek == 6) & (local.hour == 16) & (local.minute == 0)
    )
    return list(idx[m])


def main():
    decision_for, hist = historical_router()
    k, f = load_extended()
    es = oos_entries(k)
    dates = [t.strftime("%Y-%m-%d") for t in es]
    if dates != EXPECTED:
        raise RuntimeError(f"unexpected OOS Sunday entries {dates}")

    rows, trade_pnls = [], []
    for t in es:
        ctx = sun17.pre_context(k, t)
        coarse = sun19.state_key(ctx)
        thu_s = sign(ctx["thu_day_ret"])
        l4_s = sign(ctx["sun12_to16_ret"])
        dec = decision_for(coarse, thu_s, l4_s)
        pnl, reason, exit_t = None, "WAIT", None
        entry = float(k.loc[t, "open"])
        if dec in ("BUY", "SELL"):
            tr = sun19.simulate(k, f, t, 1 if dec == "BUY" else -1)
            pnl = float(tr["pnl"])
            reason = tr["reason"]
            exit_t = str(tr["exit_t"])
            trade_pnls.append(pnl)
        rows.append({
            "date": t.strftime("%Y-%m-%d"),
            "entry_t": str(t),
            "entry": entry,
            "coarse_state": coarse,
            "thu_sign": thu_s,
            "fri_sign": sign(ctx["fri_day_ret"]),
            "sat_sign": sign(ctx["sat_day_ret"]),
            "sun_pre16_sign": sign(ctx["sun_pre16_ret"]),
            "sun12_16_sign": l4_s,
            "decision": dec,
            "reason": reason,
            "exit_t": exit_t,
            "pnl": pnl,
        })

    df = pd.DataFrame(rows)
    tm = metrics(trade_pnls)
    summary = {
        "status": "COMPLETE_TRUE_OOS_FROZEN_ROUTER",
        "research_cutoff": str(OOS_START),
        "dates": dates,
        "frozen_definition": "SUN2.0 natural-state router + F-|S-|U+ forced WAIT; TP2.5 SL1.4 hold18h",
        "historical_frozen_candidate": hist,
        "oos_opportunities": int(len(df)),
        "oos_trades": int((df.decision != "WAIT").sum()),
        "oos_waits": int((df.decision == "WAIT").sum()),
        "oos_metrics_on_trades": tm,
        "rows": df.to_dict(orient="records"),
        "guardrail": "Only three post-cutoff Sundays are available. This is a true-OOS observation of the frozen router, not statistical confirmation and not a reason to retune from N=3.",
    }
    df.to_csv(OUT / "sun22_true_oos_trades.csv", index=False)
    (OUT / "sun22_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    wr = "-" if tm["wr"] is None else f"{100*tm['wr']:.1f}%"
    pf = "-" if tm["pf"] is None else f"{tm['pf']:.2f}"
    md = [
        "# SUN2.2 — Sunday16 Frozen Router True-OOS",
        "",
        "**Status: COMPLETE — TRUE-OOS OBSERVATION; RULE FROZEN; live BBC untouched.**",
        "",
        "## Frozen rule",
        "- SUN2.0 natural-state router.",
        "- `F-|S-|U+` is forced to WAIT from the pre-OOS SUN2.1 decision.",
        "- BUY/SELL: TP 2.5%, SL 1.4%, max hold 18h.",
        "- No August observation is used to change a decision.",
        "",
        "## Historical frozen candidate (pre-cutoff only)",
        f"- Trades {hist['full']['n']}/139, WR {100*hist['full']['wr']:.2f}%, PnL ${hist['full']['pnl']:+.2f}, PF {hist['full']['pf']:.2f}.",
        f"- D: {hist['D']['n']} trades, WR {100*hist['D']['wr']:.2f}%, PnL ${hist['D']['pnl']:+.2f}.",
        f"- V: {hist['V']['n']} trades, WR {100*hist['V']['wr']:.2f}%, PnL ${hist['V']['pnl']:+.2f}.",
        "",
        "## True-OOS August 2026",
        f"- Opportunities: {len(df)}; trades {int((df.decision!='WAIT').sum())}; WAIT {int((df.decision=='WAIT').sum())}.",
        f"- Traded WR: {wr}; PnL ${tm['pnl']:+.2f}; PF {pf}.",
        "",
        "| Date | State | Thu | L4 | Decision | Outcome | PnL |",
        "|---|---|---:|---:|---|---|---:|",
    ]
    for r in rows:
        p = "-" if r["pnl"] is None else f"${r['pnl']:+.2f}"
        md.append(f"| {r['date']} | {r['coarse_state']} | {r['thu_sign']} | {r['sun12_16_sign']} | **{r['decision']}** | {r['reason']} | {p} |")
    md += ["", "## Guardrail", summary["guardrail"]]
    (OUT / "SUN2.2_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
