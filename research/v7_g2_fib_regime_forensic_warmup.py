#!/usr/bin/env python3
"""V7-G2 parity fix: add 10d pre-window context warmup for market-state features.

The FIB event window remains exactly V7-F's frozen 971d window. Only the 1H/5m
archive DB receives 10 extra prior days so every early FIB event has the full
192h state lookback required by the pre-existing V4-B6 feature calculation.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from research import v7_g_fib_regime_forensic as g

WARMUP_DAYS=10
DATA_START=g.WINDOW_START-timedelta(days=WARMUP_DAYS)


def build_db_with_warmup():
    if os.path.exists(g.DB): os.unlink(g.DB)
    conn=sqlite3.connect(g.DB)
    conn.execute("""CREATE TABLE klines(
        symbol TEXT,timeframe TEXT,open_time INTEGER,
        open REAL,high REAL,low REAL,close REAL,volume REAL,
        close_time INTEGER,quote_volume REAL,trades INTEGER,
        taker_buy_volume REAL,taker_buy_quote_volume REAL,
        PRIMARY KEY(symbol,timeframe,open_time))""")
    coverage={}
    for p in g.PAIRS:
        coverage[p]={}
        for tf in ("1h","5m"):
            rows=g.archive.load_series(p,tf,DATA_START,g.WINDOW_END)
            conn.executemany("INSERT OR REPLACE INTO klines VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)
            conn.commit()
            coverage[p][tf]={
                "rows":len(rows),
                "first":datetime.fromtimestamp(rows[0][2]/1000,tz=timezone.utc).isoformat() if rows else None,
                "last":datetime.fromtimestamp(rows[-1][2]/1000,tz=timezone.utc).isoformat() if rows else None,
            }
    conn.close()
    coverage["_state_warmup_days"]=WARMUP_DAYS
    return coverage


def build_series_with_warmup(symbol, atr_func):
    conn=sqlite3.connect(g.DB)
    try:
        rows=conn.execute("""
            SELECT open_time,open,high,low,close,volume
            FROM klines
            WHERE symbol=? AND timeframe='1h' AND open_time>=? AND open_time<?
            ORDER BY open_time ASC""",
            (symbol,int(DATA_START.timestamp()*1000),int(g.WINDOW_END.timestamp()*1000))).fetchall()
    finally:
        conn.close()
    import numpy as np
    T=[int(r[0]) for r in rows]
    H=np.asarray([r[2] for r in rows],dtype=float)
    L=np.asarray([r[3] for r in rows],dtype=float)
    C=np.asarray([r[4] for r in rows],dtype=float)
    ATR=atr_func(H,L,C,14)
    atr_pct=np.asarray([(100.0*ATR[i]/C[i]) if C[i]>0 else 0.0 for i in range(len(C))],dtype=float)
    return {"T":T,"C":C,"ATR_PCT":atr_pct}


g.build_db=build_db_with_warmup
g.build_series=build_series_with_warmup

if __name__=="__main__":
    g.main()
