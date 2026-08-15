#!/usr/bin/env python3
"""V7-K — third prior 120d test for frozen pair×side×FIB candidates.

Candidates were selected in V7-J from blocks 7 and 8 only:
- BTCUSDT SUPPLY, FIB 38.2-50
- BNBUSDT SUPPLY, FIB <38.2

Primary test is block 6 (the immediately preceding 120d). No band/side/TP-SL
changes are allowed. Blocks 7/8 are reproduced only for parity/context.
Research only; no live changes.
"""
import json, os, sqlite3
from datetime import datetime, timedelta, timezone
from research import v7_j_fib_pair_120d_vs_120d as j

CANDIDATES = [
    {"name":"BTC_SUPPLY_38.2-50","pair":"BTCUSDT","side":"SUPPLY","band":"38.2-50"},
    {"name":"BNB_SUPPLY_<38.2","pair":"BNBUSDT","side":"SUPPLY","band":"<38.2"},
]


def stat(rows):
    n=len(rows); w=sum(int(r["win"]) for r in rows)
    return {"n":n,"wins":w,"losses":n-w,"wr_pct":round(100.0*w/n,2) if n else None}


def main():
    coverage=j.build_db(); os.environ["DB_PATH"]=j.DB
    import v4_context_fib_forensic_endpoint as fib
    fib._load=j.fixed_load

    events=[]; errors={}
    for p in j.PAIRS:
        d=fib.context_fib_forensic(symbols=p,days=j.DAYS,rr=1.0,confirm_bars=3,sample_limit=500)
        if d.get("errors"): errors[p]=d.get("errors")
        sample=d.get("sample") or []
        if int((d.get("overall") or {}).get("n",0) or 0)>len(sample): raise RuntimeError(f"sample truncated {p}")
        for x in sample:
            if x.get("outcome") not in ("BOUNCE","BREAK") or x.get("fib_band") not in j.BANDS: continue
            t=datetime.fromisoformat(x["confirm_time"])
            if t.tzinfo is None:t=t.replace(tzinfo=timezone.utc)
            t=t.astimezone(timezone.utc)
            delta=(t-j.WINDOW_START).total_seconds()
            block=int(delta//(j.BLOCK_DAYS*86400))+1 if delta>=0 else 0
            events.append({"pair":p,"side":x.get("side"),"band":x.get("fib_band"),"block":block,
                           "t":t,"win":1 if x.get("outcome")=="BOUNCE" else 0})

    def select(c,b):
        return [r for r in events if r["block"]==b and r["pair"]==c["pair"] and r["side"]==c["side"] and r["band"]==c["band"]]

    report=[]
    for c in CANDIDATES:
        b6=select(c,6); b7=select(c,7); b8=select(c,8)
        report.append({**c,
            "third_prior_120d_block6":stat(b6),
            "previous_120d_block7":stat(b7),
            "latest_120d_block8":stat(b8),
            "three_block_combined":stat(b6+b7+b8),
            "block6_to_block8_wr":[stat(x)["wr_pct"] for x in (b6,b7,b8)],
        })

    b6_start=j.WINDOW_START+timedelta(days=j.BLOCK_DAYS*5); b6_end=b6_start+timedelta(days=j.BLOCK_DAYS)
    b7_start=b6_end; b7_end=b7_start+timedelta(days=j.BLOCK_DAYS)
    b8_start=b7_end; b8_end=b8_start+timedelta(days=j.BLOCK_DAYS)

    pooled=[]
    for c in CANDIDATES:
        pooled.extend(select(c,6))
    result={
        "phase":"V7-K","status":"FROZEN_CANDIDATE_THIRD_PRIOR_120D_TEST",
        "definition":{"candidate_selection_source":"V7-J blocks 7+8 only",
                      "primary_test":"block 6 immediately preceding those selection windows",
                      "block6":{"start":b6_start.isoformat(),"end_exclusive":b6_end.isoformat()},
                      "block7":{"start":b7_start.isoformat(),"end_exclusive":b7_end.isoformat()},
                      "block8":{"start":b8_start.isoformat(),"end_exclusive":b8_end.isoformat()},
                      "rr":1.0,"confirm_bars":3,"threshold_sweep":False,"side_or_band_changes":False,"live_changes":False},
        "coverage":coverage,"errors":errors,"candidates":report,
        "primary_block6_pooled":stat(pooled),
        "interpretation_lock":"Block 6 is the only new temporal test. Blocks 7/8 are selection-era parity/context and must not be counted as independent validation."
    }
    print("V7_K_RESULT",json.dumps(result,separators=(",",":"),default=str))

if __name__=="__main__": main()
