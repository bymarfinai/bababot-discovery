#!/usr/bin/env python3
"""Stage 7H-A: audit true price-level L2 replay feasibility without reading outcomes."""
from __future__ import annotations
import csv, gzip, io, json, os, math
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7H_A_SOURCE_AUDIT.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7H_A_SOURCE_AUDIT.json"
OUT_CSV=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7H_A_SOURCE_AUDIT.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S7H_A_Status.txt"

EXCHANGE="binance-futures"
SYMBOL="SOLUSDT"
DTYPE="incremental_book_L2"
DATES=["2023-01-01","2024-01-01","2025-01-01","2026-01-01","2026-09-01"]
EXPECTED=["exchange","symbol","timestamp","local_timestamp","is_snapshot","side","price","amount"]

def url(date):
    y,m,d=date.split("-")
    return f"https://datasets.tardis.dev/v1/{EXCHANGE}/{DTYPE}/{y}/{m}/{d}/{SYMBOL}.csv.gz"

def parse_bool(x):
    return str(x).strip().lower()=="true"

def sample_audit(date, max_rows=1_000_000):
    u=url(date)
    h=requests.head(u,allow_redirects=True,timeout=30,headers={"User-Agent":"bababot-stage7h-a/1.0"})
    size=int(h.headers.get("content-length","0") or 0)
    status=h.status_code
    rec={
        "date":date,"http_status":status,"compressed_bytes":size,
        "header_ok":False,"snapshot_seen":False,"bid_seen":False,"ask_seen":False,
        "rows_read":0,"timestamp_non_decreasing":True,
        "replay_ok":False,"best_bid":None,"best_ask":None,
        "first_snapshot_local_timestamp":None,"note":"",
    }
    if status!=200:
        rec["note"]=f"HEAD_{status}"
        return rec
    try:
        with requests.get(u,stream=True,timeout=120,headers={"User-Agent":"bababot-stage7h-a/1.0"}) as r:
            r.raise_for_status()
            r.raw.decode_content=False
            gz=gzip.GzipFile(fileobj=r.raw)
            txt=io.TextIOWrapper(gz,encoding="utf-8",newline="")
            reader=csv.DictReader(txt)
            rec["header_ok"]=reader.fieldnames==EXPECTED
            bids={};asks={}
            snapshot_started=False
            snapshot_finished=False
            applied_after_snapshot=0
            last_local=None
            for i,row in enumerate(reader,1):
                rec["rows_read"]=i
                if i>max_rows:
                    rec["note"]="MAX_ROWS_REACHED"
                    break
                side=row.get("side")
                if side=="bid": rec["bid_seen"]=True
                elif side=="ask": rec["ask_seen"]=True

                try:
                    lt=int(row["local_timestamp"])
                    px=float(row["price"]); amt=float(row["amount"])
                except Exception:
                    continue

                if last_local is not None and lt<last_local:
                    # Tardis row order is authoritative; exchange timestamps can be non-monotonic,
                    # but local_timestamp is expected to preserve capture order.
                    rec["timestamp_non_decreasing"]=False
                last_local=lt

                snap=parse_bool(row.get("is_snapshot"))
                if snap and not snapshot_started:
                    snapshot_started=True
                    rec["snapshot_seen"]=True
                    rec["first_snapshot_local_timestamp"]=lt
                    bids.clear();asks.clear()
                elif snapshot_started and not snap and not snapshot_finished:
                    snapshot_finished=True

                # Ignore buffered non-snapshot updates before first snapshot.
                if not snapshot_started:
                    continue

                book=bids if side=="bid" else asks if side=="ask" else None
                if book is None or not math.isfinite(px) or not math.isfinite(amt):
                    continue
                if amt==0:
                    book.pop(px,None)
                elif amt>0:
                    book[px]=amt

                if snapshot_finished and not snap:
                    applied_after_snapshot+=1
                    if applied_after_snapshot>=500:
                        break

            if bids and asks:
                bb=max(bids); ba=min(asks)
                rec["best_bid"]=bb;rec["best_ask"]=ba
                rec["replay_ok"]=bool(bb<ba and rec["snapshot_seen"] and snapshot_finished and applied_after_snapshot>0)
            if not rec["note"]:
                rec["note"]="OK" if rec["replay_ok"] else "REPLAY_INCOMPLETE"
    except Exception as e:
        rec["note"]=f"{type(e).__name__}:{e}"
    return rec

def metadata():
    try:
        r=requests.get("https://api.tardis.dev/v1/exchanges/binance-futures",timeout=30,
                       headers={"User-Agent":"bababot-stage7h-a/1.0"})
        r.raise_for_status()
        obj=r.json()
        # response can be object or wrapped; find SOLUSDT recursively in datasets.symbols.
        datasets=obj.get("datasets",{}) if isinstance(obj,dict) else {}
        syms=datasets.get("symbols",[]) if isinstance(datasets,dict) else []
        sol=next((x for x in syms if x.get("id")=="SOLUSDT"),None)
        if sol:
            return {
                "found":True,
                "available_since":sol.get("availableSince"),
                "available_to":sol.get("availableTo"),
                "data_types":sol.get("dataTypes"),
                "supports_incremental_book_L2":"incremental_book_L2" in (sol.get("dataTypes") or []),
            }
        return {"found":False}
    except Exception as e:
        return {"found":False,"error":f"{type(e).__name__}:{e}"}

def auth_probe():
    key=os.getenv("TARDIS_API_KEY","").strip()
    bin_key=os.getenv("BINANCE_API_KEY","").strip()
    bin_secret=os.getenv("BINANCE_API_SECRET","").strip()
    out={
        "tardis_key_configured":bool(key),
        "binance_api_key_configured":bool(bin_key),
        "binance_api_secret_configured":bool(bin_secret),
        "tardis_non_sample_access":False,
        "tardis_non_sample_status":None,
    }
    if key:
        u="https://datasets.tardis.dev/v1/binance-futures/incremental_book_L2/2023/01/02/SOLUSDT.csv.gz"
        try:
            r=requests.get(u,stream=True,timeout=30,
                headers={"Authorization":f"Bearer {key}","User-Agent":"bababot-stage7h-a/1.0"})
            out["tardis_non_sample_status"]=r.status_code
            if r.status_code==200:
                # Read a tiny amount only to prove entitlement; do not retain data.
                chunk=next(r.iter_content(chunk_size=64),b"")
                out["tardis_non_sample_access"]=len(chunk)>0
            r.close()
        except Exception as e:
            out["tardis_non_sample_status"]=f"{type(e).__name__}"
    return out

def main():
    rows=[sample_audit(d) for d in DATES]
    import pandas as pd
    df=pd.DataFrame(rows)
    df.to_csv(OUT_CSV,index=False)

    meta=metadata()
    auth=auth_probe()
    sample_pass=bool(
        len(df)==len(DATES)
        and (df.http_status==200).all()
        and df.header_ok.all()
        and df.snapshot_seen.all()
        and df.bid_seen.all()
        and df.ask_seen.all()
        and df.replay_ok.all()
    )
    full_access=bool(auth["tardis_non_sample_access"])
    # Binance credential presence is not treated as entitlement proof.
    status=(
        "SOL_INDICATOR_RELATIONSHIP_S7H_A_FULL_HISTORY_ACCESS_READY"
        if sample_pass and full_access else
        "SOL_INDICATOR_RELATIONSHIP_S7H_A_REPLAY_FEASIBLE_ACCESS_REQUIRED"
        if sample_pass else
        "SOL_INDICATOR_RELATIONSHIP_S7H_A_SOURCE_FAIL"
    )
    payload={
        "status":status,
        "sample_replay_pass":sample_pass,
        "full_history_access_ready":full_access,
        "tardis_metadata":meta,
        "credential_probe":auth,
        "samples":rows,
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    OUT_STATUS.write_text(status+"\n")

    lines=[
        "# SOL Indicator Relationship Discovery — Stage 7H-A Source Audit","",
        "**True price-level L2 feasibility; no trading outcomes read.**","",
        "| Date | HTTP | Compressed | Schema | Snapshot | Bid+Ask | Replay | Rows sampled |",
        "|---|---:|---:|---|---|---|---|---:|"
    ]
    for r in rows:
        lines.append(
            f"| {r['date']} | {r['http_status']} | {r['compressed_bytes']:,} | "
            f"{'PASS' if r['header_ok'] else 'FAIL'} | {'YES' if r['snapshot_seen'] else 'NO'} | "
            f"{'YES' if r['bid_seen'] and r['ask_seen'] else 'NO'} | {'PASS' if r['replay_ok'] else 'FAIL'} | "
            f"{r['rows_read']:,} |"
        )
    lines += [
        "",
        f"Sample replay gate: **{'PASS' if sample_pass else 'FAIL'}**.",
        "",
        "## Access gate","",
        f"- Tardis key configured: **{'YES' if auth['tardis_key_configured'] else 'NO'}**",
        f"- Authenticated non-sample Tardis day accessible: **{'YES' if auth['tardis_non_sample_access'] else 'NO'}**",
        f"- Binance API key configured: **{'YES' if auth['binance_api_key_configured'] else 'NO'}**",
        f"- Binance API secret configured: **{'YES' if auth['binance_api_secret_configured'] else 'NO'}**",
        "",
        "Credential values are never printed or persisted.",
        "",
        "## Decision",""
    ]
    if sample_pass and full_access:
        lines += [
            "**FULL-HISTORY ACCESS GATE: PASS.**",
            "Stage 7H-B may proceed to causal full-history reconstruction and single-mechanism anatomy."
        ]
    elif sample_pass:
        lines += [
            "**REPLAY FEASIBILITY: PASS; FULL-HISTORY ACCESS: NOT AVAILABLE IN THIS WORKFLOW.**",
            "The source/schema is valid, but free first-of-month samples cannot be used as a substitute for DEV→2025→2026 full-history testing."
        ]
    else:
        lines += [
            "**SOURCE/REPLAY GATE: FAIL.**",
            "Stage 7H cannot proceed to outcome-bearing true-L2 analysis with this source."
        ]
    lines += ["",f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
