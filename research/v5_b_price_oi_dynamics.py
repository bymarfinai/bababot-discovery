#!/usr/bin/env python3
"""V5-B — frozen Price x Open Interest dynamics forensic.

Research-only. No threshold sweep, no trade filtering, no live integration.
Reuses the frozen V4-B reaction/absorption outcomes, then reconstructs the
last 60 minutes of fully completed 5m price candles and Binance USD-M metrics
available before the confirmation candle begins.

Predeclared four-state mapping, relative to intended trade direction:
- AGAINST_PRICE_OI_UP   : price moves against intended trade while OI rises
- AGAINST_PRICE_OI_DOWN : price moves against intended trade while OI falls
- TOWARD_PRICE_OI_UP    : price moves toward intended trade while OI rises
- TOWARD_PRICE_OI_DOWN  : price moves toward intended trade while OI falls

Primary frozen mechanism hypothesis:
A successful reaction should be more likely when the adverse approach is
FLUSH_DOMINANT, meaning adverse price movement accompanied by OI contraction
exceeds adverse price movement accompanied by OI expansion over the prior 60m.
This uses only a natural majority comparison; no fitted threshold.
"""
import csv
import io
import json
import math
import statistics
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone

import v5_a2_derivatives_forensic as base

KLINES = "https://data.binance.vision/data/futures/um/daily/klines"
PAIRS = base.PAIRS
DAYS = 120

KLINE_CACHE = {}


def stat(rows):
    n = len(rows)
    w = sum(r["outcome"] == "BOUNCE" for r in rows)
    return {"n": n, "wins": w, "losses": n-w,
            "wr_pct": round(100.0*w/n, 2) if n else None}


def _dt_ms(v):
    return datetime.fromtimestamp(int(float(v))/1000.0, tz=timezone.utc)


def load_klines_day(symbol, day):
    key = (symbol, day.isoformat())
    if key in KLINE_CACHE:
        return KLINE_CACHE[key]
    ds = day.isoformat()
    url = f"{KLINES}/{symbol}/5m/{symbol}-5m-{ds}.zip"
    raw = base.http_bytes(url)
    z = zipfile.ZipFile(io.BytesIO(raw))
    txt = z.read(z.namelist()[0]).decode("utf-8-sig")
    rows = []
    for r in csv.reader(io.StringIO(txt)):
        if not r:
            continue
        try:
            t = _dt_ms(r[0])
            close_t = _dt_ms(r[6])
            o = float(r[1]); c = float(r[4])
        except Exception:
            # public archive may include a header on some generated files
            continue
        rows.append({"t": t, "close_t": close_t, "open": o, "close": c})
    rows.sort(key=lambda x: x["t"])
    KLINE_CACHE[key] = rows
    return rows


def klines_for_event(symbol, cutoff):
    rows = []
    for d in (cutoff.date()-timedelta(days=1), cutoff.date()):
        rows.extend(load_klines_day(symbol, d))
    rows.sort(key=lambda x: x["t"])
    return rows


def metrics_for_event(symbol, cutoff):
    rows = base.rows_for_event(symbol, cutoff)
    return rows


def latest_metric_at(metrics, when):
    return base.latest_at(metrics, when)


def classify_step(side_sign, price_ret, oi_change):
    p = side_sign * price_ret
    if p < 0:
        return "AGAINST_PRICE_OI_UP" if oi_change > 0 else "AGAINST_PRICE_OI_DOWN"
    if p > 0:
        return "TOWARD_PRICE_OI_UP" if oi_change > 0 else "TOWARD_PRICE_OI_DOWN"
    return "FLAT_PRICE"


def event_sequence(event):
    confirm_open = base.dt(event["confirm_time"])
    cutoff = confirm_open
    side_sign = 1.0 if event["side"] == "DEMAND" else -1.0
    kl = klines_for_event(event["symbol"], cutoff)
    mt = metrics_for_event(event["symbol"], cutoff)

    # Only candles fully closed before the confirmation candle begins.
    bars = [x for x in kl if cutoff-timedelta(minutes=65) <= x["t"] < cutoff]
    bars.sort(key=lambda x: x["t"])
    steps = []
    prev_close = None
    prev_oi = None
    prev_t = None
    for b in bars:
        m = latest_metric_at(mt, b["t"])
        oi = base.finite(m.get("oi")) if m else None
        if prev_close is not None and prev_oi is not None and oi is not None and prev_close != 0 and prev_oi != 0:
            pr = b["close"]/prev_close - 1.0
            od = oi/prev_oi - 1.0
            st = classify_step(side_sign, pr, od)
            steps.append({"t": b["t"], "price_ret": pr, "oi_ret": od,
                          "signed_price_ret": side_sign*pr, "state": st})
        prev_close = b["close"]
        prev_oi = oi
        prev_t = b["t"]

    steps60 = [s for s in steps if cutoff-timedelta(minutes=60) <= s["t"] < cutoff]
    steps30 = [s for s in steps if cutoff-timedelta(minutes=30) <= s["t"] < cutoff]
    if len(steps60) < 8:
        return None

    def features(xs):
        counts = Counter(s["state"] for s in xs)
        n = len(xs)
        adverse_flush = sum(abs(s["signed_price_ret"]) for s in xs
                            if s["state"] == "AGAINST_PRICE_OI_DOWN")
        adverse_build = sum(abs(s["signed_price_ret"]) for s in xs
                            if s["state"] == "AGAINST_PRICE_OI_UP")
        toward_new = sum(abs(s["signed_price_ret"]) for s in xs
                         if s["state"] == "TOWARD_PRICE_OI_UP")
        toward_cover = sum(abs(s["signed_price_ret"]) for s in xs
                           if s["state"] == "TOWARD_PRICE_OI_DOWN")
        adverse_total = adverse_flush + adverse_build
        return {
            "n": n,
            "against_oi_up_share": counts["AGAINST_PRICE_OI_UP"]/n if n else None,
            "against_oi_down_share": counts["AGAINST_PRICE_OI_DOWN"]/n if n else None,
            "toward_oi_up_share": counts["TOWARD_PRICE_OI_UP"]/n if n else None,
            "toward_oi_down_share": counts["TOWARD_PRICE_OI_DOWN"]/n if n else None,
            "adverse_flush_move": adverse_flush,
            "adverse_build_move": adverse_build,
            "adverse_flush_share_of_adverse_move": adverse_flush/adverse_total if adverse_total > 0 else None,
            "toward_new_move": toward_new,
            "toward_cover_move": toward_cover,
            "flush_minus_build": adverse_flush-adverse_build,
        }

    f60 = features(steps60)
    f30 = features(steps30)
    recent3 = steps60[-3:]
    recent3_counts = Counter(s["state"] for s in recent3)

    out = dict(event)
    for k,v in f60.items(): out[f"m60_{k}"] = v
    for k,v in f30.items(): out[f"m30_{k}"] = v
    out["recent3_states"] = [s["state"] for s in recent3]
    out["recent3_flush_count"] = recent3_counts["AGAINST_PRICE_OI_DOWN"]
    out["recent3_build_count"] = recent3_counts["AGAINST_PRICE_OI_UP"]
    out["m60_mechanism"] = (
        "FLUSH_DOMINANT" if f60["adverse_flush_move"] > f60["adverse_build_move"]
        else "BUILDUP_DOMINANT" if f60["adverse_build_move"] > f60["adverse_flush_move"]
        else "EQUAL_NO_ADVERSE"
    )
    out["m30_mechanism"] = (
        "FLUSH_DOMINANT" if f30["adverse_flush_move"] > f30["adverse_build_move"]
        else "BUILDUP_DOMINANT" if f30["adverse_build_move"] > f30["adverse_flush_move"]
        else "EQUAL_NO_ADVERSE"
    )
    return out


def median(rows, key):
    xs = [base.finite(r.get(key)) for r in rows]
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 8) if xs else None


def compare(rows, keys):
    w = [r for r in rows if r["outcome"] == "BOUNCE"]
    l = [r for r in rows if r["outcome"] == "BREAK"]
    out = {}
    for k in keys:
        wm = median(w,k); lm = median(l,k)
        out[k] = {"winner_median": wm, "loser_median": lm,
                  "median_diff": round(wm-lm,8) if wm is not None and lm is not None else None}
    return out


def by_time(rows):
    if not rows:
        return {}
    end = max(base.dt(r["confirm_time"]) for r in rows)
    cut = end-timedelta(days=60)
    return {
        "first_60d": stat([r for r in rows if base.dt(r["confirm_time"]) < cut]),
        "last_60d": stat([r for r in rows if base.dt(r["confirm_time"]) >= cut]),
    }


def main():
    events=[]; baseline={}; errors={}
    for p in PAIRS:
        try:
            ev, st = base.fetch_v4_events(p)
            events.extend(ev); baseline[p]=st
        except Exception as e:
            errors[p]=f"V4 fetch: {e}"
    if not events:
        raise SystemExit("NO_V4_EVENTS")

    enriched=[]
    for i,e in enumerate(events,1):
        try:
            x=event_sequence(e)
            if x: enriched.append(x)
        except Exception as ex:
            errors[f"event_{i}_{e['symbol']}"]=str(ex)

    keys=[
        "m60_against_oi_up_share","m60_against_oi_down_share",
        "m60_toward_oi_up_share","m60_toward_oi_down_share",
        "m60_adverse_flush_share_of_adverse_move","m60_flush_minus_build",
        "m30_against_oi_up_share","m30_against_oi_down_share",
        "m30_adverse_flush_share_of_adverse_move","m30_flush_minus_build",
        "recent3_flush_count","recent3_build_count",
    ]

    mechanisms=("FLUSH_DOMINANT","BUILDUP_DOMINANT","EQUAL_NO_ADVERSE")
    m60={m:stat([r for r in enriched if r["m60_mechanism"]==m]) for m in mechanisms}
    m30={m:stat([r for r in enriched if r["m30_mechanism"]==m]) for m in mechanisms}
    cand=[r for r in enriched if r["m60_mechanism"]=="FLUSH_DOMINANT"]
    by_pair={p:stat([r for r in cand if r["symbol"]==p]) for p in PAIRS}
    by_side={s:stat([r for r in cand if r["side"]==s]) for s in ("DEMAND","SUPPLY")}
    t=by_time(cand)
    pair_ok=sum(1 for p,z in by_pair.items() if z["n"]>=3 and (z["wr_pct"] or 0)>50)
    side_ok=all(by_side[s]["n"]>=5 and (by_side[s]["wr_pct"] or 0)>50 for s in by_side)
    time_ok=bool(t) and all(t[k]["n"]>=5 and (t[k]["wr_pct"] or 0)>50 for k in ("first_60d","last_60d"))
    cs=stat(cand)

    result={
        "phase":"V5-B",
        "status":"PRICE_X_OI_DYNAMICS_FORENSIC_AND_FROZEN_MECHANISM_CHECK",
        "frozen_definition":{
            "base_signal":"V4-B 1H structural zone + 5m reaction/absorption, confirm_bars=3, RR=1",
            "history_days":120,
            "price_source":"official Binance USD-M 5m kline daily archive",
            "oi_source":"official Binance USD-M 5m metrics daily archive",
            "causality_guard":"only fully completed 5m price bars before confirmation candle OPEN; OI metrics at/before each bar OPEN",
            "four_states":["AGAINST_PRICE_OI_UP","AGAINST_PRICE_OI_DOWN","TOWARD_PRICE_OI_UP","TOWARD_PRICE_OI_DOWN"],
            "primary_hypothesis":"60m adverse approach FLUSH_DOMINANT should outperform BUILDUP_DOMINANT",
            "flush_dominant_definition":"sum adverse price move on OI-down bars > sum adverse price move on OI-up bars",
            "threshold_sweep":False,
            "trade_filtering":False,
        },
        "predeclared_candidate_gate":{
            "overall_wr_pct":">=70",
            "candidate_n":">=20",
            "pair_distribution":">=3 of 4 pairs each n>=3 and WR>50",
            "both_sides":"each n>=5 and WR>50",
            "both_60d_halves":"each n>=5 and WR>50",
        },
        "events_before_join":stat(events),
        "events_enriched":stat(enriched),
        "unusable_n":len(events)-len(enriched),
        "winner_vs_loser":compare(enriched,keys),
        "m60_mechanism":m60,
        "m30_mechanism":m30,
        "flush_candidate":{
            "stats":cs,
            "by_pair":by_pair,
            "by_side":by_side,
            "by_time":t,
            "pairs_passing_distribution_check":pair_ok,
            "side_check":side_ok,
            "time_check":time_ok,
            "earns_next_frozen_validation":bool(cs["n"]>=20 and (cs["wr_pct"] or 0)>=70 and pair_ok>=3 and side_ok and time_ok),
        },
        "errors":errors,
        "notes":{
            "interpretation":"No alternate threshold, lookback, or mechanism may be selected post-hoc from this same 120d sample.",
            "next":"Only a predeclared passing mechanism earns a separate longer-history validation.",
        },
    }
    print("V5_B_RESULT",json.dumps(result,separators=(",",":")))


if __name__ == "__main__":
    main()
