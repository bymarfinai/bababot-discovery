#!/usr/bin/env python3
from __future__ import annotations
import csv, io, json, os, tempfile, zipfile
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_A_SOURCE_AUDIT.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_A_SOURCE_AUDIT.json"
OUT_CSV=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_A_SOURCE_AUDIT.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7G_A_Status.txt"

BASE="https://data.binance.vision/data/futures/um/daily"
SYMBOL="SOLUSDT"
DATES=[
 "2023-01-15","2023-07-15","2024-01-15","2024-07-15",
 "2025-01-15","2025-07-15","2026-01-15","2026-07-15",
]
TYPES=["bookDepth","bookTicker","aggTrades","liquidationSnapshot"]

def url(dtype,date):
    return f"{BASE}/{dtype}/{SYMBOL}/{SYMBOL}-{dtype}-{date}.zip"

def head(sess,u):
    try:
        r=sess.head(u,allow_redirects=True,timeout=25)
        return r.status_code,int(r.headers.get("content-length","0") or 0),r.headers.get("last-modified")
    except Exception as e:
        return -1,0,str(e)

def first_csv_header(sess,u,max_bytes=300_000_000):
    r=sess.get(u,stream=True,timeout=60)
    r.raise_for_status()
    size=int(r.headers.get("content-length","0") or 0)
    if size and size>max_bytes:
        return None,f"SKIPPED_SIZE_{size}"
    with tempfile.NamedTemporaryFile(suffix=".zip",delete=False) as f:
        path=f.name
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk: f.write(chunk)
    try:
        with zipfile.ZipFile(path) as z:
            names=[n for n in z.namelist() if n.lower().endswith(".csv")]
            if not names: return None,"NO_CSV_IN_ZIP"
            with z.open(names[0]) as fh:
                line=fh.readline().decode("utf-8-sig",errors="replace").strip()
                second=fh.readline().decode("utf-8-sig",errors="replace").strip()
            return line,second
    finally:
        try: os.remove(path)
        except OSError: pass

def main():
    sess=requests.Session()
    sess.headers["User-Agent"]="bababot-research-source-audit/1.0"
    rows=[]
    for dtype in TYPES:
        for d in DATES:
            u=url(dtype,d)
            code,size,last=head(sess,u)
            rows.append({
                "data_type":dtype,"date":d,"url":u,"http_status":code,
                "exists":code==200,"content_length":size,"last_modified":last or "",
            })

    schemas={}
    schema_date="2023-01-15"
    for dtype in TYPES:
        u=url(dtype,schema_date)
        rec=next(x for x in rows if x["data_type"]==dtype and x["date"]==schema_date)
        if not rec["exists"]:
            # use first existing audit date
            ex=next((x for x in rows if x["data_type"]==dtype and x["exists"]),None)
            if ex: u=ex["url"]
            else:
                schemas[dtype]={"header":None,"sample":None,"status":"NO_FILE"}
                continue
        try:
            h,s=first_csv_header(sess,u)
            schemas[dtype]={"header":h,"sample":s,"status":"PARSED" if h else s}
        except Exception as e:
            schemas[dtype]={"header":None,"sample":None,"status":f"ERROR:{type(e).__name__}:{e}"}

    summary={}
    for dtype in TYPES:
        rr=[x for x in rows if x["data_type"]==dtype]
        exists={x["date"] for x in rr if x["exists"]}
        dev=any(d.startswith(("2023-","2024-")) for d in exists)
        v25=any(d.startswith("2025-") for d in exists)
        v26=any(d.startswith("2026-") for d in exists)
        candidate=dev and v25 and v26 and schemas[dtype]["header"] is not None
        core=sum(x["exists"] for x in rr)==len(DATES) and schemas[dtype]["header"] is not None
        summary[dtype]={
            "exists_n":sum(x["exists"] for x in rr),
            "audit_n":len(rr),
            "dev_present":dev,"validation_2025_present":v25,"validation_2026_present":v26,
            "schema":schemas[dtype],
            "historical_candidate":candidate,
            "core_eligible_by_8date_audit":core,
        }

    import pandas as pd
    pd.DataFrame(rows).to_csv(OUT_CSV,index=False)
    payload={"symbol":SYMBOL,"audit_dates":DATES,"summary":summary,"rows":rows}
    OUT_JSON.write_text(json.dumps(payload,indent=2)+"\n")

    eligible=[k for k,v in summary.items() if v["core_eligible_by_8date_audit"]]
    candidates=[k for k,v in summary.items() if v["historical_candidate"]]
    status="SOL_INDICATOR_RELATIONSHIP_S7G_A_COMPLETED"
    OUT_STATUS.write_text(status+"\n")

    lines=["# SOL Indicator Relationship Discovery — Stage 7G-A Source Audit","",
           f"Symbol: **{SYMBOL}**","",
           "| Source | Exists | DEV | 2025 | 2026 | Schema | Historical candidate | Core eligible (8-date audit) |",
           "|---|---:|---|---|---|---|---|---|"]
    for dtype in TYPES:
        s=summary[dtype]
        lines.append(
            f"| {dtype} | {s['exists_n']}/{s['audit_n']} | {'YES' if s['dev_present'] else 'NO'} | "
            f"{'YES' if s['validation_2025_present'] else 'NO'} | {'YES' if s['validation_2026_present'] else 'NO'} | "
            f"{s['schema']['status']} | {'YES' if s['historical_candidate'] else 'NO'} | "
            f"{'YES' if s['core_eligible_by_8date_audit'] else 'NO'} |"
        )
    lines += ["","## Parsed schema samples",""]
    for dtype in TYPES:
        s=summary[dtype]["schema"]
        lines.append(f"### {dtype}")
        lines.append(f"- header: \`{s['header']}\`")
        lines.append(f"- first row: \`{s['sample']}\`")
    lines += ["","## Outcome","",
              f"- Historical candidates: **{', '.join(candidates) if candidates else 'none'}**",
              f"- Core-eligible from 8-date audit: **{', '.join(eligible) if eligible else 'none'}**",
              "",
              "A full required-signal-date coverage audit is still required before Stage 7G-B uses any source.",
              "",
              f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
