#!/usr/bin/env python3
"""V7-L — full historical 120d chain for frozen V7-J candidates.

Candidates were selected from blocks 7 and 8 only:
- BTCUSDT SUPPLY, FIB 38.2-50
- BNBUSDT SUPPLY, FIB <38.2

Blocks 1-6 are all temporally prior to candidate selection and are treated as
historical holdout diagnostics. No threshold, side, band, RR, or confirmation
changes are allowed after seeing V7-K block 6.

Research only; no live changes.
"""
import json, os
from datetime import datetime, timedelta, timezone
from research import v7_j_fib_pair_120d_vs_120d as j

CANDIDATES=[
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
            events.append({"pair":p,"side":x.get("side"),"band":x.get("fib_band"),"block":block,"t":t,
                           "win":1 if x.get("outcome")=="BOUNCE" else 0})

    reports=[]
    for c in CANDIDATES:
        def sel(blocks):
            bs=set(blocks)
            return [r for r in events if r["block"] in bs and r["pair"]==c["pair"] and r["side"]==c["side"] and r["band"]==c["band"]]
        block_stats=[]
        for b in range(1,9):
            lo=j.WINDOW_START+timedelta(days=j.BLOCK_DAYS*(b-1)); hi=lo+timedelta(days=j.BLOCK_DAYS)
            xs=sel([b])
            block_stats.append({"block":b,"start":lo.isoformat(),"end_exclusive":hi.isoformat(),**stat(xs)})
        holdout=sel(range(1,7)); selection=sel([7,8]); all8=sel(range(1,9))
        eligible=[x for x in block_stats[:6] if x["n"]>=2]
        checks={
            "holdout_n_ge15":len(holdout)>=15,
            "holdout_wr_ge60":(stat(holdout)["wr_pct"] or 0)>=60.0,
            "at_least_4_holdout_blocks_n_ge2":len(eligible)>=4,
            "at_least_4_holdout_blocks_wr_ge50":sum((x["wr_pct"] or 0)>=50.0 for x in eligible)>=4,
        }
        reports.append({**c,"blocks_120d":block_stats,
                        "holdout_blocks_1_6":stat(holdout),
                        "selection_blocks_7_8":stat(selection),
                        "all_8_blocks":stat(all8),
                        "eligible_holdout_blocks_n_ge2":len(eligible),
                        "holdout_gate":{"checks":checks,"passed":all(checks.values())}})

    result={
        "phase":"V7-L","status":"FROZEN_PAIR_SIDE_FIB_FULL_120D_CHAIN",
        "definition":{"selection_blocks":[7,8],"historical_holdout_blocks":[1,2,3,4,5,6],
                      "rr":1.0,"confirm_bars":3,"threshold_sweep":False,"side_or_band_changes":False,"live_changes":False,
                      "interpretation":"candidate identity remains frozen from V7-J; all blocks 1-6 are reported, none may be discarded post hoc"},
        "coverage":coverage,"errors":errors,"candidates":reports,
    }
    print("V7_L_RESULT",json.dumps(result,separators=(",",":"),default=str))

if __name__=="__main__": main()
