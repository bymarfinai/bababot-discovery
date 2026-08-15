#!/usr/bin/env python3
"""V7-O — frozen BNB SUPPLY Fibonacci 23.6%-38.2% validation.

The 23.6% boundary is a canonical Fibonacci level, chosen after V7-N showed
that the previously broad BNB SUPPLY <38.2 bucket had materially better
outcomes at deeper retracements. No numerical threshold sweep is performed.

Primary validation is the immediately preceding independent 971-day window
(2021-04..2023-12), which was outside the 2023-12..2026-08 event-geometry
forensic. The rule is fixed before loading the old-window outcomes:
  BNBUSDT + SUPPLY + 0.236 <= fib_retracement < 0.382 + frozen V4-B confirmation
  RR=1, confirm_bars=3.

Research only; no live/order changes.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from research import v7_f_fib_120d_archive_audit as archive

PAIR="BNBUSDT"
DAYS=971
BLOCK_DAYS=120
CUR_END=datetime.fromisoformat("2026-08-15T15:11:15.831175+00:00")
CUR_START=CUR_END-timedelta(days=DAYS)
OLD_END=CUR_START
OLD_START=OLD_END-timedelta(days=DAYS)
DB="/tmp/v7_o_bnb_236_382.db"
CURRENT_START=CUR_START
CURRENT_END=CUR_END


def stat(rows):
    n=len(rows);w=sum(int(r["win"]) for r in rows)
    return {"n":n,"wins":w,"losses":n-w,"wr_pct":round(100.0*w/n,2) if n else None}


def build_db():
    if os.path.exists(DB):os.unlink(DB)
    conn=sqlite3.connect(DB)
    conn.execute("""CREATE TABLE klines(
        symbol TEXT,timeframe TEXT,open_time INTEGER,
        open REAL,high REAL,low REAL,close REAL,volume REAL,
        close_time INTEGER,quote_volume REAL,trades INTEGER,
        taker_buy_volume REAL,taker_buy_quote_volume REAL,
        PRIMARY KEY(symbol,timeframe,open_time))""")
    coverage={}
    for tf in ("1h","5m"):
        rows=archive.load_series(PAIR,tf,OLD_START,CUR_END)
        conn.executemany("INSERT OR REPLACE INTO klines VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)
        conn.commit()
        coverage[tf]={"rows":len(rows),
                      "first":datetime.fromtimestamp(rows[0][2]/1000,tz=timezone.utc).isoformat() if rows else None,
                      "last":datetime.fromtimestamp(rows[-1][2]/1000,tz=timezone.utc).isoformat() if rows else None}
    conn.close();return coverage


def fixed_load(symbol,timeframe,days):
    conn=sqlite3.connect(DB)
    try:
        return conn.execute("""SELECT open_time,open,high,low,close,volume
            FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?
            ORDER BY open_time ASC""",
            (symbol,timeframe,int(CURRENT_START.timestamp()*1000),int(CURRENT_END.timestamp()*1000))).fetchall()
    finally:conn.close()


def run_window(start,end):
    global CURRENT_START,CURRENT_END
    CURRENT_START,CURRENT_END=start,end
    import v4_context_fib_forensic_endpoint as fib
    from v4_first_retest_endpoint import _build_a1_zones,HOUR_MS,_coverage
    from v4_reaction_absorption_endpoint import _load_child_full,_find_confirmation,_resolve_after_confirmation
    fib._load=fixed_load

    rows=fixed_load(PAIR,"1h",DAYS)
    T,O,H,L,C,ATR,zones=_build_a1_zones(rows,10,0.5,3,8,1.0,0.0)
    child=_load_child_full(PAIR,"5m",T[0],T[-1]+HOUR_MS)
    cov=_coverage(child,T[0],T[-1]+HOUR_MS,"5m")
    if cov["coverage_pct"]<95:raise RuntimeError(f"5m coverage {cov['coverage_pct']}")
    child_times=[int(r[0]) for r in child]
    anchors=fib._fib_anchor_map(T,H,L,ATR,zones)

    base=[]
    for z in zones:
        if z["side"]!="SUPPLY":continue
        conf=_find_confirmation(z,T,child,child_times,3,720)
        if conf.get("signal_status")!="CONFIRMED":continue
        out=_resolve_after_confirmation(z,conf,child,1.0,72)
        if out.get("outcome") not in {"BOUNCE","BREAK"}:continue
        ff=fib._fib_features(z,conf,child,anchors.get(z["zone_id"]))
        retr=ff.get("fib_retracement")
        if retr is None or not (float(retr)<0.382):continue
        dt=datetime.fromisoformat(conf["confirm_time"])
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        dt=dt.astimezone(timezone.utc)
        block=int(((dt-start).total_seconds())//(BLOCK_DAYS*86400))+1
        base.append({"t":dt,"block":block,"retr":float(retr),"win":1 if out["outcome"]=="BOUNCE" else 0})

    full8=[r for r in base if 1<=r["block"]<=8]
    remainder=[r for r in base if r["block"]==9]
    selected=[r for r in full8 if 0.236<=r["retr"]<0.382]
    shallow=[r for r in full8 if r["retr"]<0.236]
    blocks=[]
    for b in range(1,9):
        bb=[r for r in full8 if r["block"]==b]
        ss=[r for r in bb if 0.236<=r["retr"]<0.382]
        ll=[r for r in bb if r["retr"]<0.236]
        lo=start+timedelta(days=(b-1)*BLOCK_DAYS);hi=lo+timedelta(days=BLOCK_DAYS)
        blocks.append({"block":b,"start":lo.isoformat(),"end_exclusive":hi.isoformat(),
                       "base_lt382":stat(bb),"selected_236_382":stat(ss),"shallow_lt236":stat(ll)})
    return {"window":{"start":start.isoformat(),"end_exclusive":end.isoformat(),"days":DAYS},
            "coverage":cov,"base_lt382":stat(full8),"selected_236_382":stat(selected),
            "shallow_lt236":stat(shallow),"remainder_11d":{"base":stat(remainder),"selected":stat([r for r in remainder if r["retr"]>=0.236])},
            "blocks_120d":blocks}


def main():
    coverage=build_db();os.environ["DB_PATH"]=DB
    # Import DB-dependent modules only after DB_PATH is frozen.
    current=run_window(CUR_START,CUR_END)
    old=run_window(OLD_START,OLD_END)

    old_sel=old["selected_236_382"];old_shallow=old["shallow_lt236"]
    lift=(old_sel["wr_pct"] or 0)-(old_shallow["wr_pct"] or 0)
    eligible=[b["selected_236_382"] for b in old["blocks_120d"] if b["selected_236_382"]["n"]>=2]
    checks={
        "old_holdout_n_ge15":old_sel["n"]>=15,
        "old_holdout_wr_ge55":(old_sel["wr_pct"] or 0)>=55.0,
        "beats_shallow_by_ge10pp":lift>=10.0,
        "at_least_4_blocks_n_ge2":len(eligible)>=4,
        "majority_eligible_blocks_wr_ge50":sum((x["wr_pct"] or 0)>=50.0 for x in eligible)>=max(1,(len(eligible)+1)//2),
    }
    result={
        "phase":"V7-O","status":"FROZEN_BNB_SUPPLY_236_382_INDEPENDENT_HOLDOUT",
        "definition":{"pair":PAIR,"side":"SUPPLY","fib_rule":"0.236 <= retracement < 0.382",
                      "boundary_rationale":"canonical Fibonacci 23.6% level; no threshold sweep",
                      "rr":1.0,"confirm_bars":3,"primary_validation":"971 days immediately preceding V7-N window",
                      "threshold_sweep":False,"tp_sl_sweep":False,"live_changes":False},
        "archive_coverage":coverage,"current_context":current,"independent_old_holdout":old,
        "old_holdout_selected_vs_shallow_lift_pp":round(lift,2),
        "replication_gate":{"checks":checks,"passed":all(checks.values())},
        "verdict":"PASS_INDEPENDENT_236_382_REPLICATION" if all(checks.values()) else "FAIL_INDEPENDENT_236_382_REPLICATION",
        "interpretation_lock":"The 23.6% boundary may not be changed after this run. Failure is a rejection of this refinement, not an invitation to sweep a new cutoff.",
    }
    print("V7_O_RESULT",json.dumps(result,separators=(",",":"),default=str))

if __name__=="__main__":main()
