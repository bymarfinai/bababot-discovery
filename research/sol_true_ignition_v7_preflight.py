#!/usr/bin/env python3
from __future__ import annotations

import io, json, os, zipfile
from pathlib import Path

import pandas as pd
import requests

from coindesk_microstructure import CoinDeskAccessError, CoinDeskCoverageError, CoinDeskMicrostructureClient

ROOT=Path(__file__).resolve().parent.parent
OUT_JSON=ROOT/"SOL_TRUE_IGNITION_V7_PREFLIGHT.json"
OUT_MD=ROOT/"SOL_TRUE_IGNITION_V7_PREFLIGHT.md"
DATES=["2023-03-15","2023-10-15","2024-03-15","2024-10-15","2025-03-15","2025-10-15","2026-03-15","2026-09-15"]
UA={"User-Agent":"bababot-sol-v7-preflight/1.0"}

SOURCES={
    "futures_raw_trades":"https://data.binance.vision/data/futures/um/daily/trades/SOLUSDT/SOLUSDT-trades-{date}.zip",
    "futures_aggTrades":"https://data.binance.vision/data/futures/um/daily/aggTrades/SOLUSDT/SOLUSDT-aggTrades-{date}.zip",
    "spot_raw_trades":"https://data.binance.vision/data/spot/daily/trades/SOLUSDT/SOLUSDT-trades-{date}.zip",
    "spot_aggTrades":"https://data.binance.vision/data/spot/daily/aggTrades/SOLUSDT/SOLUSDT-aggTrades-{date}.zip",
}

def probe_url(url):
    try:
        r=requests.head(url,timeout=30,allow_redirects=True,headers=UA)
        return {"status":r.status_code,"exists":r.status_code==200,"bytes":int(r.headers.get("content-length") or 0),"content_type":r.headers.get("content-type")}
    except Exception as e:
        return {"status":None,"exists":False,"bytes":0,"error":f"{type(e).__name__}: {e}"}

def parse_sample(url,max_bytes=80_000_000):
    try:
        h=probe_url(url)
        if not h.get("exists"):
            return {"parsed":False,"reason":"not_found"}
        if h.get("bytes",0)>max_bytes:
            return {"parsed":False,"reason":"too_large_for_schema_sample","bytes":h.get("bytes",0)}
        r=requests.get(url,timeout=120,headers=UA)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:return {"parsed":False,"reason":"no_csv"}
            with zf.open(names[0]) as fh:
                df=pd.read_csv(fh,nrows=5,header=None)
        return {
            "parsed":True,
            "rows_sampled":len(df),
            "columns_n":len(df.columns),
            "sample":[[str(v) for v in row] for row in df.astype(str).values.tolist()],
        }
    except Exception as e:
        return {"parsed":False,"reason":f"{type(e).__name__}: {e}"}

def coindesk_preflight():
    out={
        "api_key_present":bool(os.getenv("COINDESK_API_KEY","").strip()),
        "market":os.getenv("COINDESK_FUTURES_MARKET","binance"),
        "instrument":os.getenv("COINDESK_FUTURES_INSTRUMENT","SOL-USDT-VANILLA-PERPETUAL"),
        "status":"BLOCKED_DATA_ACCESS",
    }
    if not out["api_key_present"]:
        out["message"]="COINDESK_API_KEY is not configured"
        return out
    old=os.environ.get("COINDESK_FUTURES_INSTRUMENT")
    os.environ["COINDESK_FUTURES_INSTRUMENT"]=out["instrument"]
    try:
        c=CoinDeskMicrostructureClient.from_env()
        c.instrument=out["instrument"]
        meta=c.instrument_metadata()
        out["metadata_resolved"]=bool(meta)
        # Probe a short historical window only; no labels.
        end=pd.Timestamp("2025-10-15T12:00:00Z")
        start=end-pd.Timedelta(minutes=2)
        tr=c.trades(start,end)
        out["trade_probe_count"]=len(tr)
        try:
            l2=c.replay_l2_features(start,end,objective_level=200.0,depth=100)
            out["l2_updates"]=int(l2.get("l2_updates",0))
            out["l2_snapshots"]=int(l2.get("l2_snapshots",0))
            out["l2_ok"]=out["l2_snapshots"]>=1 and out["l2_updates"]>0
        except (CoinDeskAccessError,CoinDeskCoverageError) as e:
            out["l2_ok"]=False
            out["l2_error"]=str(e)
        out["status"]="PREFLIGHT_PASS" if out.get("metadata_resolved") and out.get("trade_probe_count",0)>0 and out.get("l2_ok") else "BLOCKED_DATA_COVERAGE"
    except CoinDeskAccessError as e:
        out["message"]=str(e);out["status"]="BLOCKED_DATA_ACCESS"
    except CoinDeskCoverageError as e:
        out["message"]=str(e);out["status"]="BLOCKED_DATA_COVERAGE"
    except Exception as e:
        out["message"]=f"{type(e).__name__}: {e}";out["status"]="BLOCKED_DATA_ACCESS"
    finally:
        if old is None:os.environ.pop("COINDESK_FUTURES_INSTRUMENT",None)
        else:os.environ["COINDESK_FUTURES_INSTRUMENT"]=old
    return out

def main():
    probes=[]
    for source,tmpl in SOURCES.items():
        for ds in DATES:
            p=probe_url(tmpl.format(date=ds))
            probes.append({"source":source,"date":ds,**p})
    p=pd.DataFrame(probes)
    source_summary={}
    for s in SOURCES:
        z=p[p.source==s]
        source_summary[s]={
            "available":int(z.exists.sum()),
            "total":len(z),
            "coverage":float(z.exists.mean()),
            "median_bytes":float(z.loc[z.exists,"bytes"].median()) if z.exists.any() else None,
        }

    samples={}
    # Prefer latest representative date that exists; parse one file per source only.
    for source,tmpl in SOURCES.items():
        z=p[(p.source==source)&(p.exists)].sort_values("date")
        if len(z):
            ds=str(z.iloc[-1].date)
            samples[source]={"date":ds,**parse_sample(tmpl.format(date=ds))}
        else:
            samples[source]={"parsed":False,"reason":"no_available_probe_date"}

    cd=coindesk_preflight()

    usable_raw=(source_summary["futures_raw_trades"]["coverage"]>=.75)
    usable_agg=(source_summary["futures_aggTrades"]["coverage"]>=.75)
    if cd.get("status")=="PREFLIGHT_PASS":
        verdict="TIER_A_COINDESK_L2_AVAILABLE"
    elif usable_raw:
        verdict="TIER_B_BINANCE_RAW_TRADES_AVAILABLE__NO_L2"
    elif usable_agg:
        verdict="TIER_B_BINANCE_AGGTRADES_AVAILABLE__NO_L2"
    else:
        verdict="BLOCKED_HIGH_RES_TRADE_DATA"

    out={
        "protocol":"SOL_TRUE_IGNITION_V7_PREFLIGHT",
        "labels_inspected":False,
        "dates":DATES,
        "coindesk":cd,
        "binance_source_summary":source_summary,
        "binance_schema_samples":samples,
        "probes":probes,
        "verdict":verdict,
    }
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+"\n",encoding="utf-8")

    lines=[
        "# SOL True Ignition V7 — Data Preflight",
        "",
        f"**Verdict: {verdict}**",
        "",
        "No winner/loser labels were inspected.",
        "",
        "## CoinDesk Tier A",
        "",
        f"- API key present: **{cd.get('api_key_present')}**",
        f"- status: **{cd.get('status')}**",
        f"- market/instrument: \`{cd.get('market')} / {cd.get('instrument')}\`",
        f"- message: {cd.get('message','-')}",
        "",
        "## Binance Data Vision historical coverage",
        "",
        "| Source | Available dates | Coverage | Median ZIP size |",
        "|---|---:|---:|---:|",
    ]
    for s,v in source_summary.items():
        mb=(v["median_bytes"]/1024/1024) if v["median_bytes"] is not None else None
        lines.append(f"| {s} | {v['available']}/{v['total']} | {v['coverage']*100:.1f}% | {mb:.1f} MB |" if mb is not None else f"| {s} | {v['available']}/{v['total']} | {v['coverage']*100:.1f}% | - |")
    lines += ["","## Schema samples",""]
    for s,v in samples.items():
        lines.append(f"- **{s}**: date {v.get('date','-')}, parsed={v.get('parsed')}, columns={v.get('columns_n','-')}, reason={v.get('reason','-')}")
        if v.get("parsed"):
            lines.append(f"  first row: \`{v.get('sample',[[]])[0]}\`")
    lines += ["","Preflight only. No strategy result is implied."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,default=str))

if __name__=="__main__":
    main()
