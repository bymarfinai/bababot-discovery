#!/usr/bin/env python3
"""V6-B — actual Binance forced-liquidation cascade pipeline.

Research-only. No live integration.

Two modes:
1) ENTITLED_CONTINUOUS when TARDIS_API_KEY is present: the downloader is capable
   of authenticated daily Tardis liquidation CSV requests. This script does not
   silently claim a full scientific result unless continuous history is present.
2) PUBLIC_SAMPLE_MECHANICS without a key: uses only Tardis' public first-day-of-
   month samples on a fixed sparse calendar to validate parsing, side mapping,
   5m aggregation, causal shock detection and RR1 outcome tracking.

IMPORTANT: PUBLIC_SAMPLE_MECHANICS is NOT an unbiased backtest. Those dates are
structurally selected by Tardis' public-sample policy and have gaps between them.
No WR from this mode may be promoted as an edge or used to tune parameters.

Frozen public-sample mechanics definition before results:
- 11 fixed first-of-month dates spanning Jan-2024 through Jul-2026.
- aggregate raw liquidations into UTC 5m bins by side and notional price*amount.
- side='sell' means long position liquidated; side='buy' means short liquidated.
- after 6h same-day warmup, compute z-score of same-side 5m liquidation notional
  versus the previous 72 completed 5m bins (6h), current bin excluded.
- shock when side notional z >= 2.0 and side notional > opposite-side notional.
- first transition only for a same-side shock cluster.
- long-liquidation shock -> reversal LONG; short-liquidation shock -> reversal SHORT.
- entry at shock 5m close; stop at shock-bar extreme; target 1R.
- track from next 5m bar for up to 24h; same-child TP+SL ambiguous excluded.

The eventual scientific continuous test should use continuous historical data and
predeclare its own trailing baseline before results; this sparse test exists only
for pipeline/mechanics validation.
"""
import csv
import gzip
import io
import json
import math
import os
import statistics
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone

EXCHANGE = "binance-futures"
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
TARDIS_BASE = "https://datasets.tardis.dev/v1/binance-futures/liquidations"
BINANCE_KLINES = "https://data.binance.vision/data/futures/um/daily/klines"
API_KEY = os.environ.get("TARDIS_API_KEY", "").strip()
UA = "bababot-v6-liquidation/1.0"
SAMPLE_DATES = [
    "2024-01-01", "2024-04-01", "2024-07-01", "2024-10-01",
    "2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01",
    "2026-01-01", "2026-04-01", "2026-07-01",
]
WARMUP_BARS = 72  # 6h of 5m bins
Z_THRESHOLD = 2.0
HORIZON_BARS = 24 * 12


def req(url, timeout=45, api_key=None):
    headers = {"User-Agent": UA}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout)


def day_path(date_str):
    y, m, d = date_str.split("-")
    return y, m, d


def load_liquidations(symbol, date_str, api_key=None):
    y, m, d = day_path(date_str)
    url = f"{TARDIS_BASE}/{y}/{m}/{d}/{symbol}.csv.gz"
    rows = []
    try:
        with req(url, api_key=api_key) as r:
            gz = gzip.GzipFile(fileobj=r)
            txt = io.TextIOWrapper(gz, encoding="utf-8-sig", newline="")
            for x in csv.DictReader(txt):
                try:
                    ts = datetime.fromtimestamp(int(x["timestamp"]) / 1_000_000.0, tz=timezone.utc)
                    side = str(x.get("side", "")).lower()
                    price = float(x["price"]); amount = float(x["amount"])
                except Exception:
                    continue
                if side not in ("buy", "sell") or price <= 0 or amount <= 0:
                    continue
                rows.append({"t": ts, "side": side, "price": price, "amount": amount,
                             "notional": price * amount})
        return rows, 200, None
    except urllib.error.HTTPError as e:
        return [], e.code, e.read(256).decode("utf-8", "replace")
    except Exception as e:
        return [], None, str(e)


def load_klines(symbol, date_str):
    url = f"{BINANCE_KLINES}/{symbol}/5m/{symbol}-5m-{date_str}.zip"
    with req(url, timeout=30) as r:
        raw = r.read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    txt = z.read(z.namelist()[0]).decode("utf-8-sig")
    out = []
    for r in csv.reader(io.StringIO(txt)):
        if not r:
            continue
        try:
            t = datetime.fromtimestamp(int(float(r[0]))/1000.0, tz=timezone.utc)
            o,h,l,c = map(float, (r[1],r[2],r[3],r[4]))
        except Exception:
            continue
        out.append({"t": t, "open": o, "high": h, "low": l, "close": c})
    out.sort(key=lambda x:x["t"])
    return out


def floor5(t):
    return t.replace(minute=(t.minute//5)*5, second=0, microsecond=0)


def aggregate_5m(liqs, klines):
    agg = defaultdict(lambda: {"long_liq":0.0, "short_liq":0.0, "long_n":0, "short_n":0})
    for x in liqs:
        b = floor5(x["t"])
        # Tardis normalized side semantics:
        # sell = long position liquidated; buy = short position liquidated.
        if x["side"] == "sell":
            agg[b]["long_liq"] += x["notional"]; agg[b]["long_n"] += 1
        else:
            agg[b]["short_liq"] += x["notional"]; agg[b]["short_n"] += 1
    out=[]
    for k in klines:
        a=agg[k["t"]]
        out.append({**k, **a, "total_liq":a["long_liq"]+a["short_liq"]})
    return out


def zscore(current, hist):
    if len(hist) < 20:
        return None
    mu = statistics.mean(hist)
    sd = statistics.pstdev(hist)
    if sd <= 0:
        return None
    return (current-mu)/sd


def detect(rows, symbol, date_str):
    events=[]
    prev_active=None
    for i in range(WARMUP_BARS, len(rows)):
        long_hist=[rows[j]["long_liq"] for j in range(i-WARMUP_BARS,i)]
        short_hist=[rows[j]["short_liq"] for j in range(i-WARMUP_BARS,i)]
        zl=zscore(rows[i]["long_liq"],long_hist)
        zs=zscore(rows[i]["short_liq"],short_hist)
        candidates=[]
        if zl is not None and zl >= Z_THRESHOLD and rows[i]["long_liq"] > rows[i]["short_liq"]:
            candidates.append(("LONG_LIQ",zl,rows[i]["long_liq"],1))
        if zs is not None and zs >= Z_THRESHOLD and rows[i]["short_liq"] > rows[i]["long_liq"]:
            candidates.append(("SHORT_LIQ",zs,rows[i]["short_liq"],-1))
        active=max(candidates,key=lambda x:x[1]) if candidates else None
        active_name=active[0] if active else None
        if active and active_name != prev_active:
            shock,z,notional,trade_dir=active
            b=rows[i]
            entry=b["close"]
            stop=b["low"] if trade_dir>0 else b["high"]
            risk=(entry-stop) if trade_dir>0 else (stop-entry)
            if risk>0:
                target=entry+trade_dir*risk
                events.append({
                    "symbol":symbol,"sample_date":date_str,"i":i,"signal_time":b["t"],
                    "shock":shock,"trade_direction":"LONG" if trade_dir>0 else "SHORT",
                    "dir":trade_dir,"entry":entry,"stop":stop,"target":target,
                    "risk_pct":100*risk/entry,"liq_z":z,"shock_notional":notional,
                    "opposite_notional":b["short_liq"] if shock=="LONG_LIQ" else b["long_liq"],
                    "long_liq":b["long_liq"],"short_liq":b["short_liq"],
                })
        prev_active=active_name
    return events


def resolve(event, rows_today, rows_next):
    rows=rows_today+rows_next
    # identify signal index in concatenated rows by timestamp
    pos=None
    for j,b in enumerate(rows):
        if b["t"]==event["signal_time"]:
            pos=j; break
    if pos is None:
        return "CENSORED",None
    d=event["dir"]; stop=event["stop"]; tp=event["target"]
    end=min(len(rows),pos+1+HORIZON_BARS)
    for b in rows[pos+1:end]:
        hit_tp=(b["high"]>=tp) if d>0 else (b["low"]<=tp)
        hit_sl=(b["low"]<=stop) if d>0 else (b["high"]>=stop)
        if hit_tp and hit_sl: return "AMBIGUOUS",b["t"]
        if hit_tp: return "WIN",b["t"]
        if hit_sl: return "LOSS",b["t"]
    return "CENSORED", rows[end-1]["t"] if end>pos+1 else None


def stats(events):
    r=[e for e in events if e.get("outcome") in ("WIN","LOSS")]
    w=sum(e["outcome"]=="WIN" for e in r)
    return {"events":len(events),"resolved":len(r),"wins":w,"losses":len(r)-w,
            "wr_pct":round(100*w/len(r),2) if r else None,
            "ambiguous":sum(e.get("outcome")=="AMBIGUOUS" for e in events),
            "censored":sum(e.get("outcome")=="CENSORED" for e in events)}


def main():
    mode="ENTITLED_CONTINUOUS_CAPABLE" if API_KEY else "PUBLIC_SAMPLE_MECHANICS"
    result={"phase":"V6-B","mode":mode,"scientific_status":"MECHANICS_ONLY_NOT_EDGE_EVIDENCE",
            "frozen_sample_definition":{
                "dates":SAMPLE_DATES,"warmup":"previous 72 completed 5m bins within same sample day",
                "shock":"same-side liquidation notional z>=2 and > opposite-side notional",
                "side_mapping":"sell=long liquidation->reversal LONG; buy=short liquidation->reversal SHORT",
                "entry":"shock 5m close","stop":"shock 5m extreme","target":"1R",
                "tracking":"next 5m onward, <=24h, same-child ambiguity excluded",
                "parameter_sweep":False,
            },
            "api_key_present":bool(API_KEY),"coverage":{},"errors":{},"events":[]}
    all_events=[]
    for p in PAIRS:
        pcov={"sample_days_attempted":0,"sample_days_liquidation_ok":0,"liquidation_rows":0,"events":0}
        for ds in SAMPLE_DATES:
            pcov["sample_days_attempted"]+=1
            liqs,status,err=load_liquidations(p,ds,api_key=API_KEY or None)
            if status!=200:
                result["errors"][f"{p}_{ds}_liquidations"]={"status":status,"error":err}
                continue
            pcov["sample_days_liquidation_ok"]+=1; pcov["liquidation_rows"]+=len(liqs)
            try:
                k0=load_klines(p,ds)
                nxt=(datetime.fromisoformat(ds).date()+timedelta(days=1)).isoformat()
                k1=load_klines(p,nxt)
            except Exception as e:
                result["errors"][f"{p}_{ds}_klines"]=str(e); continue
            rows=aggregate_5m(liqs,k0)
            ev=detect(rows,p,ds)
            for e in ev:
                outcome,ot=resolve(e,rows,aggregate_5m([],k1))
                e["outcome"]=outcome; e["outcome_time"]=ot.isoformat() if ot else None
                # keep compact event audit fields only in output
                all_events.append(e)
            pcov["events"]+=len(ev)
        result["coverage"][p]=pcov
    result["overall"]=stats(all_events)
    result["by_pair"]={p:stats([e for e in all_events if e["symbol"]==p]) for p in PAIRS}
    result["by_shock"]={s:stats([e for e in all_events if e["shock"]==s]) for s in ("LONG_LIQ","SHORT_LIQ")}
    result["by_date"]={ds:stats([e for e in all_events if e["sample_date"]==ds]) for ds in SAMPLE_DATES}
    result["diagnostics"]={
        "median_liq_z":round(statistics.median([e["liq_z"] for e in all_events]),4) if all_events else None,
        "median_shock_notional_usdt":round(statistics.median([e["shock_notional"] for e in all_events]),2) if all_events else None,
        "median_risk_pct":round(statistics.median([e["risk_pct"] for e in all_events]),4) if all_events else None,
    }
    result["next_if_entitled"]={
        "action":"run a separate predeclared continuous 120d V6-B scientific screen using authenticated daily liquidation history",
        "auth_header":"Authorization: Bearer TARDIS_API_KEY",
        "do_not_reuse_public_sample_wr_as_prior":True,
    }
    # Include only a few event examples for auditability, not full payload.
    result["event_examples"]=[{k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in e.items() if k not in ("i","dir")}
                              for e in all_events[:8]]
    print("V6_B_RESULT",json.dumps(result,separators=(",",":")))

if __name__=="__main__":
    main()
