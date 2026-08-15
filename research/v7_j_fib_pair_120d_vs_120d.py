#!/usr/bin/env python3
"""V7-J — adjacent 120d vs 120d pair-specific Fibonacci audit.

Research only. No live changes and no threshold/TP-SL optimization.

Goal:
Compare the immediately previous 120-day block against the latest completed
120-day block inside the exact frozen V7-F 971-day event stream. We calculate
all FIB bands per pair, then diagnostic pair x side x band cells.

Important:
- The full 971d stream is reconstructed once from official Binance USD-M archive.
- Events are NOT recomputed independently per 120d window, avoiding boundary drift.
- RR=1 and confirm_bars=3 remain unchanged.
- This is a descriptive stability screen, not proof/OOS validation.
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from research import v7_f_fib_120d_archive_audit as archive

PAIRS=archive.PAIRS
DAYS=971
BLOCK_DAYS=120
BANDS=["<38.2","38.2-50","50-61.8","61.8-70.5","70.5-78.6",">=78.6"]
# Exact successful V7-F/V7-G frozen boundary.
WINDOW_END=datetime.fromisoformat("2026-08-15T15:11:15.831175+00:00")
WINDOW_START=WINDOW_END-timedelta(days=DAYS)
DB="/tmp/v7_j_pair_fib_120d.db"


def stat(rows):
    n=len(rows); w=sum(int(r["win"]) for r in rows)
    return {"n":n,"wins":w,"losses":n-w,"wr_pct":round(100.0*w/n,2) if n else None}


def build_db():
    if os.path.exists(DB): os.unlink(DB)
    conn=sqlite3.connect(DB)
    conn.execute("""CREATE TABLE klines(
        symbol TEXT,timeframe TEXT,open_time INTEGER,
        open REAL,high REAL,low REAL,close REAL,volume REAL,
        close_time INTEGER,quote_volume REAL,trades INTEGER,
        taker_buy_volume REAL,taker_buy_quote_volume REAL,
        PRIMARY KEY(symbol,timeframe,open_time))""")
    coverage={}
    for p in PAIRS:
        coverage[p]={}
        for tf in ("1h","5m"):
            rows=archive.load_series(p,tf,WINDOW_START,WINDOW_END)
            conn.executemany("INSERT OR REPLACE INTO klines VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)
            conn.commit()
            coverage[p][tf]={
                "rows":len(rows),
                "first":datetime.fromtimestamp(rows[0][2]/1000,tz=timezone.utc).isoformat() if rows else None,
                "last":datetime.fromtimestamp(rows[-1][2]/1000,tz=timezone.utc).isoformat() if rows else None,
            }
    conn.close(); return coverage


def fixed_load(symbol,timeframe,days):
    conn=sqlite3.connect(DB)
    try:
        return conn.execute("""SELECT open_time,open,high,low,close,volume
            FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?
            ORDER BY open_time ASC""",
            (symbol,timeframe,int(WINDOW_START.timestamp()*1000),int(WINDOW_END.timestamp()*1000))).fetchall()
    finally: conn.close()


def main():
    coverage=build_db(); os.environ["DB_PATH"]=DB
    import v4_context_fib_forensic_endpoint as fib
    fib._load=fixed_load

    events=[]; source={}; errors={}
    for p in PAIRS:
        d=fib.context_fib_forensic(symbols=p,days=DAYS,rr=1.0,confirm_bars=3,sample_limit=500)
        source[p]={"overall":d.get("overall"),"fib_bands":d.get("fib_bands"),"errors":d.get("errors")}
        if d.get("errors"): errors[p]=d.get("errors")
        sample=d.get("sample") or []
        if int((d.get("overall") or {}).get("n",0) or 0)>len(sample):
            raise RuntimeError(f"sample truncated {p}")
        for x in sample:
            if x.get("outcome") not in ("BOUNCE","BREAK") or x.get("fib_band") not in BANDS: continue
            t=datetime.fromisoformat(x["confirm_time"])
            if t.tzinfo is None:t=t.replace(tzinfo=timezone.utc)
            t=t.astimezone(timezone.utc)
            delta=(t-WINDOW_START).total_seconds()
            block=int(delta//(BLOCK_DAYS*86400))+1 if delta>=0 else 0
            events.append({"pair":p,"band":x.get("fib_band"),"side":x.get("side"),"t":t,"block":block,
                           "win":1 if x.get("outcome")=="BOUNCE" else 0})
    events.sort(key=lambda r:r["t"])

    # Compare the two most recent complete non-overlapping 120d blocks: 7 vs 8.
    b7=[r for r in events if r["block"]==7]
    b8=[r for r in events if r["block"]==8]
    b7_start=WINDOW_START+timedelta(days=BLOCK_DAYS*6); b7_end=b7_start+timedelta(days=BLOCK_DAYS)
    b8_start=b7_end; b8_end=b8_start+timedelta(days=BLOCK_DAYS)

    pair_band=[]
    for p in PAIRS:
        for band in BANDS:
            a=[r for r in b7 if r["pair"]==p and r["band"]==band]
            b=[r for r in b8 if r["pair"]==p and r["band"]==band]
            sa,sb=stat(a),stat(b)
            wrs=[x for x in (sa["wr_pct"],sb["wr_pct"]) if x is not None]
            pair_band.append({"pair":p,"band":band,"previous_120d":sa,"latest_120d":sb,
                              "combined":stat(a+b),"min_wr_pct":min(wrs) if len(wrs)==2 else None,
                              "wr_change_pp":round((sb["wr_pct"] or 0)-(sa["wr_pct"] or 0),2) if sa["n"] and sb["n"] else None})

    pair_side_band=[]
    for p in PAIRS:
        for side in ("DEMAND","SUPPLY"):
            for band in BANDS:
                a=[r for r in b7 if r["pair"]==p and r["side"]==side and r["band"]==band]
                b=[r for r in b8 if r["pair"]==p and r["side"]==side and r["band"]==band]
                sa,sb=stat(a),stat(b)
                wrs=[x for x in (sa["wr_pct"],sb["wr_pct"]) if x is not None]
                pair_side_band.append({"pair":p,"side":side,"band":band,"previous_120d":sa,"latest_120d":sb,
                                       "combined":stat(a+b),"min_wr_pct":min(wrs) if len(wrs)==2 else None})

    # Descriptive ranking only; criteria frozen before run and deliberately modest because cell n is small.
    stable_pair_band=[x for x in pair_band if x["previous_120d"]["n"]>=3 and x["latest_120d"]["n"]>=3 and x["min_wr_pct"] is not None and x["min_wr_pct"]>=55.0]
    stable_pair_band.sort(key=lambda x:(x["min_wr_pct"],x["combined"]["n"]),reverse=True)
    stable_pair_side_band=[x for x in pair_side_band if x["previous_120d"]["n"]>=2 and x["latest_120d"]["n"]>=2 and x["min_wr_pct"] is not None and x["min_wr_pct"]>=55.0]
    stable_pair_side_band.sort(key=lambda x:(x["min_wr_pct"],x["combined"]["n"]),reverse=True)

    # Best band per pair in previous block and how it transfers to latest block; min 3 train trades.
    transfer=[]
    for p in PAIRS:
        candidates=[x for x in pair_band if x["pair"]==p and x["previous_120d"]["n"]>=3]
        candidates.sort(key=lambda x:((x["previous_120d"]["wr_pct"] or -1),x["previous_120d"]["n"]),reverse=True)
        if candidates:
            x=candidates[0]
            transfer.append({"pair":p,"selected_band_from_previous":x["band"],"previous_120d":x["previous_120d"],"latest_120d":x["latest_120d"],"combined":x["combined"]})

    result={
        "phase":"V7-J","status":"ADJACENT_120D_VS_120D_PAIR_FIB_AUDIT",
        "definition":{"full_event_window_start":WINDOW_START.isoformat(),"full_event_window_end":WINDOW_END.isoformat(),
                      "previous_120d":{"start":b7_start.isoformat(),"end_exclusive":b7_end.isoformat()},
                      "latest_120d":{"start":b8_start.isoformat(),"end_exclusive":b8_end.isoformat()},
                      "rr":1.0,"confirm_bars":3,"event_stream":"single 971d reconstruction then bucketed","threshold_sweep":False,"tp_sl_sweep":False,"live_changes":False},
        "coverage":coverage,"errors":errors,
        "all_fib_events":{"previous_120d":stat(b7),"latest_120d":stat(b8)},
        "pair_band":pair_band,
        "stable_pair_band_cells":stable_pair_band,
        "pair_side_band":pair_side_band,
        "stable_pair_side_band_cells":stable_pair_side_band,
        "previous_best_band_transfer_to_latest":transfer,
        "source_pair_diagnostics":source,
    }
    print("V7_J_RESULT",json.dumps(result,separators=(",",":"),default=str))

if __name__=="__main__":main()
