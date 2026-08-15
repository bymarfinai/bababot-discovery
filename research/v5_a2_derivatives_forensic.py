#!/usr/bin/env python3
"""V5-A2 — frozen derivatives positioning winner/loser forensic.

Research-only. Reuses frozen V4-B reaction/absorption outcomes and joins only
information available at/before the decision. No thresholds or trade filters.

Causality guard:
- V4-B enters after the 5m confirmation candle closes.
- Binance metrics are joined only through <= confirmation candle OPEN time,
  intentionally leaving a one-5m-bar publication guard.
- Funding is joined only if fundingTime <= that same guarded cutoff.
"""
import bisect
import csv
import io
import json
import math
import statistics
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "https://web-production-b6a05.up.railway.app"
DATA = "https://data.binance.vision/data/futures/um/daily/metrics"
FAPI = "https://fapi.binance.com/fapi/v1/fundingRate"
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
DAYS = 120
RR = 1.0
CONFIRM_BARS = 3

FEATURES = [
    "oi_change_30m_pct", "oi_change_60m_pct", "oi_touch_to_confirm_pct",
    "oi_value_change_30m_pct", "oi_value_change_60m_pct",
    "top_account_lsr", "top_account_delta_30m", "top_account_delta_60m",
    "top_position_lsr", "top_position_delta_30m", "top_position_delta_60m",
    "global_lsr", "global_delta_30m", "global_delta_60m",
    "top_position_minus_global", "top_account_minus_global",
    "taker_lsr", "taker_lsr_30m_mean", "taker_lsr_60m_mean",
    "crowd_bias_toward_trade", "top_position_bias_toward_trade",
    "taker_bias_toward_trade", "funding_rate", "funding_delta_prev",
    "funding_bias_toward_trade",
]


def http_bytes(url, timeout=25, tries=5):
    last = None
    for i in range(tries):
        try:
            req = Request(url, headers={"User-Agent": "BabaBot-V5-A2/1.0"})
            with urlopen(req, timeout=timeout) as r:
                return r.read()
        except (HTTPError, URLError, TimeoutError) as e:
            last = e
            time.sleep(min(1 + i, 4))
    raise RuntimeError(f"GET failed {url}: {last}")


def get_json(url):
    return json.loads(http_bytes(url).decode("utf-8"))


def dt(s):
    x = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if x.tzinfo is None:
        x = x.replace(tzinfo=timezone.utc)
    return x.astimezone(timezone.utc)


def finite(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def median(xs):
    z = [finite(x) for x in xs]
    z = [x for x in z if x is not None]
    return round(statistics.median(z), 8) if z else None


def pct(a, b):
    return 100.0 * a / b if b else None


def safe_pct_change(a, b):
    # current=a, past=b
    a = finite(a); b = finite(b)
    if a is None or b is None or b == 0:
        return None
    return 100.0 * (a / b - 1.0)


def safe_log_ratio(v):
    v = finite(v)
    return math.log(v) if v is not None and v > 0 else None


def fetch_v4_events(symbol):
    q = urlencode({"symbol": symbol, "days": DAYS, "rr": RR,
                   "confirm_bars": CONFIRM_BARS, "sample_limit": 200})
    d = get_json(f"{BASE}/v4/reaction-absorption?{q}")
    rows = []
    for r in d.get("results_sample", []):
        if r.get("signal_status") == "CONFIRMED" and r.get("outcome") in ("BOUNCE", "BREAK"):
            rows.append({
                "symbol": symbol,
                "side": r.get("side"),
                "zone_id": r.get("zone_id"),
                "touch_time": r.get("touch_time"),
                "confirm_time": r.get("confirm_time"),
                "outcome": r.get("outcome"),
            })
    return rows, d.get("overall", {})


METRICS_CACHE = {}

def load_metrics_day(symbol, day):
    key = (symbol, day.isoformat())
    if key in METRICS_CACHE:
        return METRICS_CACHE[key]
    ds = day.isoformat()
    url = f"{DATA}/{symbol}/{symbol}-metrics-{ds}.zip"
    raw = http_bytes(url)
    z = zipfile.ZipFile(io.BytesIO(raw))
    txt = z.read(z.namelist()[0]).decode("utf-8-sig")
    out = []
    for r in csv.DictReader(io.StringIO(txt)):
        t = datetime.strptime(r["create_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        out.append({
            "t": t,
            "oi": finite(r.get("sum_open_interest")),
            "oi_value": finite(r.get("sum_open_interest_value")),
            "top_account": finite(r.get("count_toptrader_long_short_ratio")),
            "top_position": finite(r.get("sum_toptrader_long_short_ratio")),
            "global_lsr": finite(r.get("count_long_short_ratio")),
            "taker_lsr": finite(r.get("sum_taker_long_short_vol_ratio")),
        })
    METRICS_CACHE[key] = out
    return out


def rows_for_event(symbol, cutoff):
    # Need at least 60m history; previous day covers midnight boundary safely.
    days = [cutoff.date() - timedelta(days=1), cutoff.date()]
    rows = []
    for d in days:
        rows.extend(load_metrics_day(symbol, d))
    rows.sort(key=lambda x: x["t"])
    return rows


def latest_at(rows, when):
    ts = [r["t"] for r in rows]
    i = bisect.bisect_right(ts, when) - 1
    return rows[i] if i >= 0 else None


def mean_between(rows, field, start, end):
    vals = [finite(r.get(field)) for r in rows if start < r["t"] <= end]
    vals = [x for x in vals if x is not None]
    return sum(vals) / len(vals) if vals else None


def fetch_funding(symbol, start, end):
    q = urlencode({"symbol": symbol, "startTime": int(start.timestamp()*1000),
                   "endTime": int(end.timestamp()*1000), "limit": 1000})
    arr = get_json(f"{FAPI}?{q}")
    out = []
    for x in arr:
        out.append({
            "t": datetime.fromtimestamp(int(x["fundingTime"])/1000, tz=timezone.utc),
            "rate": finite(x.get("fundingRate")),
        })
    out.sort(key=lambda x: x["t"])
    return out


def funding_at(rows, cutoff):
    ts = [r["t"] for r in rows]
    i = bisect.bisect_right(ts, cutoff) - 1
    if i < 0:
        return None, None, None
    cur = rows[i]
    prev = rows[i-1] if i > 0 else None
    delta = cur["rate"] - prev["rate"] if prev and cur["rate"] is not None and prev["rate"] is not None else None
    age = (cutoff - cur["t"]).total_seconds()/60.0
    return cur["rate"], delta, age


def enrich(event, funding_rows):
    confirm_open = dt(event["confirm_time"])
    # Entry decision occurs after this 5m candle closes. We only use metrics
    # available at/before its OPEN, a conservative one-bar publication guard.
    cutoff = confirm_open
    touch = dt(event["touch_time"])
    rows = rows_for_event(event["symbol"], cutoff)
    cur = latest_at(rows, cutoff)
    p30 = latest_at(rows, cutoff - timedelta(minutes=30))
    p60 = latest_at(rows, cutoff - timedelta(minutes=60))
    ptouch = latest_at(rows, touch)
    if not cur:
        return None

    side_sign = 1.0 if event["side"] == "DEMAND" else -1.0
    funding, funding_delta, funding_age = funding_at(funding_rows, cutoff)
    glog = safe_log_ratio(cur.get("global_lsr"))
    tposlog = safe_log_ratio(cur.get("top_position"))
    takerlog = safe_log_ratio(cur.get("taker_lsr"))

    x = dict(event)
    x.update({
        "metrics_cutoff": cutoff.isoformat(),
        "metrics_latest": cur["t"].isoformat(),
        "metrics_lag_min": round((cutoff-cur["t"]).total_seconds()/60.0, 2),
        "oi_change_30m_pct": safe_pct_change(cur.get("oi"), p30.get("oi") if p30 else None),
        "oi_change_60m_pct": safe_pct_change(cur.get("oi"), p60.get("oi") if p60 else None),
        "oi_touch_to_confirm_pct": safe_pct_change(cur.get("oi"), ptouch.get("oi") if ptouch else None),
        "oi_value_change_30m_pct": safe_pct_change(cur.get("oi_value"), p30.get("oi_value") if p30 else None),
        "oi_value_change_60m_pct": safe_pct_change(cur.get("oi_value"), p60.get("oi_value") if p60 else None),
        "top_account_lsr": cur.get("top_account"),
        "top_account_delta_30m": (cur.get("top_account")-p30.get("top_account")) if p30 and cur.get("top_account") is not None and p30.get("top_account") is not None else None,
        "top_account_delta_60m": (cur.get("top_account")-p60.get("top_account")) if p60 and cur.get("top_account") is not None and p60.get("top_account") is not None else None,
        "top_position_lsr": cur.get("top_position"),
        "top_position_delta_30m": (cur.get("top_position")-p30.get("top_position")) if p30 and cur.get("top_position") is not None and p30.get("top_position") is not None else None,
        "top_position_delta_60m": (cur.get("top_position")-p60.get("top_position")) if p60 and cur.get("top_position") is not None and p60.get("top_position") is not None else None,
        "global_lsr": cur.get("global_lsr"),
        "global_delta_30m": (cur.get("global_lsr")-p30.get("global_lsr")) if p30 and cur.get("global_lsr") is not None and p30.get("global_lsr") is not None else None,
        "global_delta_60m": (cur.get("global_lsr")-p60.get("global_lsr")) if p60 and cur.get("global_lsr") is not None and p60.get("global_lsr") is not None else None,
        "top_position_minus_global": (cur.get("top_position")-cur.get("global_lsr")) if cur.get("top_position") is not None and cur.get("global_lsr") is not None else None,
        "top_account_minus_global": (cur.get("top_account")-cur.get("global_lsr")) if cur.get("top_account") is not None and cur.get("global_lsr") is not None else None,
        "taker_lsr": cur.get("taker_lsr"),
        "taker_lsr_30m_mean": mean_between(rows, "taker_lsr", cutoff-timedelta(minutes=30), cutoff),
        "taker_lsr_60m_mean": mean_between(rows, "taker_lsr", cutoff-timedelta(minutes=60), cutoff),
        "crowd_bias_toward_trade": side_sign*glog if glog is not None else None,
        "top_position_bias_toward_trade": side_sign*tposlog if tposlog is not None else None,
        "taker_bias_toward_trade": side_sign*takerlog if takerlog is not None else None,
        "funding_rate": funding,
        "funding_delta_prev": funding_delta,
        "funding_age_min": funding_age,
        "funding_bias_toward_trade": side_sign*funding if funding is not None else None,
    })
    return x


def stat(rows):
    n = len(rows); w = sum(r["outcome"] == "BOUNCE" for r in rows)
    return {"n": n, "wins": w, "losses": n-w, "wr_pct": round(pct(w,n),2) if n else None}


def compare(rows, features):
    wins = [r for r in rows if r["outcome"] == "BOUNCE"]
    losses = [r for r in rows if r["outcome"] == "BREAK"]
    out = {}
    for f in features:
        wm = median([r.get(f) for r in wins]); lm = median([r.get(f) for r in losses])
        out[f] = {"winner_median": wm, "loser_median": lm,
                  "median_diff": round(wm-lm,8) if wm is not None and lm is not None else None}
    return out


def quartiles(rows, feature):
    valid = [(r, finite(r.get(feature))) for r in rows]
    valid = [(r,v) for r,v in valid if v is not None]
    if len(valid) < 16:
        return []
    vals = sorted(v for _,v in valid)
    def q(p): return vals[min(len(vals)-1, max(0, int(round((len(vals)-1)*p))))]
    cuts = [q(.25), q(.5), q(.75)]
    buckets = [[],[],[],[]]
    for r,v in valid:
        i = 0 if v <= cuts[0] else 1 if v <= cuts[1] else 2 if v <= cuts[2] else 3
        buckets[i].append(r)
    return [{"bucket":i+1, "n":len(b), "wr_pct":round(pct(sum(x["outcome"]=="BOUNCE" for x in b),len(b)),2) if b else None}
            for i,b in enumerate(buckets)]


def pair_direction(rows, feature):
    out = {}
    for p in PAIRS:
        xs = [r for r in rows if r["symbol"] == p]
        wm = median([r.get(feature) for r in xs if r["outcome"] == "BOUNCE"])
        lm = median([r.get(feature) for r in xs if r["outcome"] == "BREAK"])
        direction = None if wm is None or lm is None else ("HIGHER_IN_WINNERS" if wm > lm else "LOWER_IN_WINNERS" if wm < lm else "EQUAL")
        out[p] = {"winner_median":wm, "loser_median":lm, "direction":direction}
    return out


def main():
    events=[]; baseline={}; errors={}
    for p in PAIRS:
        try:
            ev, st = fetch_v4_events(p)
            events.extend(ev); baseline[p] = st
        except Exception as e:
            errors[p] = f"V4 fetch: {e}"

    if not events:
        raise SystemExit("NO_V4_EVENTS")
    start = min(dt(e["confirm_time"]) for e in events) - timedelta(days=2)
    end = max(dt(e["confirm_time"]) for e in events) + timedelta(days=1)
    funding = {}
    for p in PAIRS:
        try: funding[p] = fetch_funding(p,start,end)
        except Exception as e:
            errors[p] = (errors.get(p,"") + f" funding:{e}").strip()
            funding[p] = []

    enriched=[]
    for i,e in enumerate(events,1):
        try:
            x=enrich(e,funding.get(e["symbol"],[]))
            if x: enriched.append(x)
        except Exception as ex:
            errors[f"event_{i}_{e['symbol']}"] = str(ex)

    feature_coverage={f:{"n":sum(finite(r.get(f)) is not None for r in enriched),
                         "pct":round(100*sum(finite(r.get(f)) is not None for r in enriched)/len(enriched),2) if enriched else 0}
                      for f in FEATURES}
    result={
        "phase":"V5-A2",
        "status":"DERIVATIVES_WINNER_LOSER_FORENSIC_ONLY",
        "frozen_definition":{
            "base_signal":"V4-B 1H structural zone + 5m reaction/absorption, confirm_bars=3, RR=1",
            "history_days":DAYS,
            "metrics_source":"official Binance USD-M daily metrics archive, 5m",
            "funding_source":"Binance USD-M fundingRate history",
            "causality_guard":"metrics/funding timestamp <= confirmation 5m candle OPEN; decision occurs at that candle CLOSE",
            "thresholds":None,
            "trade_filtering":False,
            "features":FEATURES,
        },
        "baseline_reported_by_endpoint":baseline,
        "events_before_join":stat(events),
        "events_after_join":stat(enriched),
        "by_pair":{p:stat([r for r in enriched if r["symbol"]==p]) for p in PAIRS},
        "by_side":{s:stat([r for r in enriched if r["side"]==s]) for s in ("DEMAND","SUPPLY")},
        "feature_coverage":feature_coverage,
        "winner_vs_loser":compare(enriched,FEATURES),
        "winner_vs_loser_by_side":{s:compare([r for r in enriched if r["side"]==s],FEATURES) for s in ("DEMAND","SUPPLY")},
        "quartile_wr":{f:quartiles(enriched,f) for f in FEATURES},
        "pair_direction_consistency":{f:pair_direction(enriched,f) for f in FEATURES},
        "errors":errors,
        "notes":{
            "interpretation":"Descriptive discovery only. A feature is not an edge merely because one quartile has high WR.",
            "next_gate":"Only predeclare a V5-A3 mechanism if winner/loser separation is directionally coherent across pairs/sides and not a tiny bucket artifact.",
        },
    }
    print("V5_A2_RESULT",json.dumps(result,separators=(",",":")))

if __name__ == "__main__":
    main()
