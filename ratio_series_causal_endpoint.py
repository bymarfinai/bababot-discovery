"""Ratio-Series Causal Test — faithful causal audit of DERET STATISTIK JADI.xlsx.

The uploaded workbook's core idea is:
    ratio_t = close_t / close_{t-1}
    forecast_ratio_{t+1} = arithmetic mean of recent observed ratios
    forecast_close_{t+1} = close_t * forecast_ratio_{t+1}

This endpoint tests ONLY the workbook-native lookbacks (4 and 5 ratios), one
bar ahead, with strict causality.  A deliberately contaminated diagnostic is
also reported to quantify the inflation caused by including the target ratio
inside its own averaging window.  The contaminated variant is NEVER a
strategy candidate.

No thresholds, EMA, Fibonacci, regime, orderflow, TP/SL tuning, or live logic.
"""

import math
import os
import sqlite3
import statistics
from datetime import datetime, timezone

from fastapi import APIRouter, Query

router = APIRouter(prefix="/research/ratio-series", tags=["ratio_series_research"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")
DAY_MS = 86_400_000


def _ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def _load(symbol, timeframe, days):
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    start_ms = now_ms - int(days) * DAY_MS
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            """
            SELECT open_time, close
            FROM klines
            WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?
            ORDER BY open_time ASC
            """,
            (symbol, timeframe, start_ms, now_ms),
        ).fetchall()
    finally:
        conn.close()


def _pearson(xs, ys):
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = statistics.fmean(xs); my = statistics.fmean(ys)
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    dx = sum((x-mx)**2 for x in xs); dy = sum((y-my)**2 for y in ys)
    if dx <= 0 or dy <= 0:
        return None
    return num / math.sqrt(dx*dy)


def _direction_stat(rows, pred_key="pred_ret"):
    usable=[r for r in rows if r.get("actual_ret") != 0 and r.get(pred_key) != 0]
    n=len(usable)
    w=sum((r[pred_key] > 0) == (r["actual_ret"] > 0) for r in usable)
    return {"n":n,"correct":w,"wrong":n-w,"wr_pct":round(100*w/n,2) if n else None}


def _summary(rows, pred_key="pred_ret", pred_close_key="pred_close"):
    d=_direction_stat(rows,pred_key)
    if not rows:
        return {**d,"mean_actual_ret_bps":None,"mean_signed_strategy_bps":None,
                "mean_net_bps_after_15bps_fee":None,"price_mape_pct":None,
                "median_pred_over_actual_pct":None,"pred_actual_return_corr":None,
                "pred_up_pct":None}
    gross=[]; mape=[]; pct_metric=[]; px=[]; py=[]
    for r in rows:
        pr=float(r[pred_key]); ar=float(r["actual_ret"])
        side=1 if pr>0 else -1 if pr<0 else 0
        gross.append(side*ar*10000)
        if r.get(pred_close_key) is not None and r.get("actual_close"):
            pc=float(r[pred_close_key]); ac=float(r["actual_close"])
            mape.append(abs(pc-ac)/ac*100)
            pct_metric.append(pc/ac*100)
        px.append(pr); py.append(ar)
    up=sum(float(r[pred_key])>0 for r in rows)
    return {
        **d,
        "mean_actual_ret_bps":round(statistics.fmean([r["actual_ret"]*10000 for r in rows]),4),
        "mean_signed_strategy_bps":round(statistics.fmean(gross),4),
        "mean_net_bps_after_15bps_fee":round(statistics.fmean(gross)-15.0,4),
        "price_mape_pct":round(statistics.fmean(mape),6) if mape else None,
        # Reproduces the spreadsheet-style ratio metric.  Around 100% merely
        # means predicted price is numerically near actual price; it is NOT WR.
        "median_pred_over_actual_pct":round(statistics.median(pct_metric),6) if pct_metric else None,
        "pred_actual_return_corr":round(_pearson(px,py),6) if _pearson(px,py) is not None else None,
        "pred_up_pct":round(100*up/len(rows),2),
    }


def _baseline(rows):
    if not rows:
        return {}
    actual=[r["actual_ret"] for r in rows]
    up=sum(x>0 for x in actual); down=sum(x<0 for x in actual); n=up+down
    always=max(up,down)
    persist=[]
    for r in rows:
        if r.get("last_observed_ret") == 0 or r["actual_ret"] == 0:
            continue
        persist.append((r["last_observed_ret"]>0)==(r["actual_ret"]>0))
    return {
        "actual_up_pct":round(100*up/n,2) if n else None,
        "majority_direction_accuracy_pct":round(100*always/n,2) if n else None,
        "last_return_persistence_accuracy_pct":round(100*sum(persist)/len(persist),2) if persist else None,
    }


def _blocks(rows, nblocks=8):
    if not rows:
        return []
    out=[]; n=len(rows)
    for k in range(nblocks):
        a=(n*k)//nblocks; b=(n*(k+1))//nblocks
        xs=rows[a:b]
        s=_direction_stat(xs)
        s["start"]=_ts(xs[0]["target_time"]) if xs else None
        s["end"]=_ts(xs[-1]["target_time"]) if xs else None
        out.append(s)
    return out


def _evaluate(close_rows, lookback):
    T=[int(r[0]) for r in close_rows]
    C=[float(r[1]) for r in close_rows]
    ratios=[None]+[C[i]/C[i-1] for i in range(1,len(C))]
    rows=[]
    # At bar t, ratios through ratio_t are known. Predict t+1.
    for t in range(lookback, len(C)-1):
        hist=ratios[t-lookback+1:t+1]
        if len(hist)!=lookback or any(x is None for x in hist):
            continue
        fr=statistics.fmean(hist)
        actual_ratio=ratios[t+1]
        actual_ret=actual_ratio-1.0
        pred_ret=fr-1.0
        pred_close=C[t]*fr

        # Contaminated spreadsheet-like diagnostic: target ratio participates
        # in the mean used to "predict" itself.  Keep the window length equal
        # to the faithful lookback by replacing the oldest known ratio with the
        # future target ratio.
        leak_hist=hist[1:]+[actual_ratio] if lookback>1 else [actual_ratio]
        leak_ratio=statistics.fmean(leak_hist)
        leak_ret=leak_ratio-1.0
        leak_close=C[t]*leak_ratio

        rows.append({
            "target_time":T[t+1],
            "current_close":C[t],"actual_close":C[t+1],
            "forecast_ratio":fr,"pred_ret":pred_ret,"pred_close":pred_close,
            "actual_ratio":actual_ratio,"actual_ret":actual_ret,
            "last_observed_ret":ratios[t]-1.0,
            "leaky_ratio":leak_ratio,"leaky_ret":leak_ret,"leaky_close":leak_close,
        })
    return rows


@router.get("")
def ratio_series_causal(
    symbols:str=Query("BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT"),
    timeframe:str=Query("1d"),
    days:int=Query(971,ge=60,le=1500),
    sample_limit:int=Query(0,ge=0,le=100),
):
    if timeframe not in {"1h","1d"}:
        return {"error":"timeframe must be 1h or 1d"}
    syms=[s.strip().upper() for s in symbols.split(',') if s.strip()]
    result={}; errors={}
    aggregate={4:[],5:[]}
    for symbol in syms:
        raw=_load(symbol,timeframe,days)
        min_rows=80 if timeframe=="1d" else 500
        if len(raw)<min_rows:
            errors[symbol]=f"not enough {timeframe} data: {len(raw)}"
            continue
        per={}
        for lb in (4,5):
            ev=_evaluate(raw,lb)
            aggregate[lb].extend(ev)
            per[str(lb)]={
                "causal":_summary(ev,"pred_ret","pred_close"),
                "leakage_control":_summary(ev,"leaky_ret","leaky_close"),
                "baselines":_baseline(ev),
                "chronological_8_blocks":_blocks(ev,8),
                "sample":[{
                    "target_time":_ts(r["target_time"]),
                    "actual_ret_bps":round(r["actual_ret"]*10000,4),
                    "pred_ret_bps":round(r["pred_ret"]*10000,4),
                    "actual_close":round(r["actual_close"],8),
                    "pred_close":round(r["pred_close"],8),
                } for r in ev[-sample_limit:]] if sample_limit else [],
            }
        result[symbol]={
            "rows":len(raw),"data_start":_ts(raw[0][0]),"data_end":_ts(raw[-1][0]),
            "lookbacks":per,
        }

    agg={}
    for lb in (4,5):
        ev=sorted(aggregate[lb],key=lambda r:r["target_time"])
        agg[str(lb)]={
            "causal":_summary(ev,"pred_ret","pred_close"),
            "leakage_control":_summary(ev,"leaky_ret","leaky_close"),
            "baselines":_baseline(ev),
            "chronological_8_blocks":_blocks(ev,8),
        }

    return {
        "phase":"RATIO-SERIES-CAUSAL-1",
        "status":"CAUSAL_WORKBOOK_IDEA_AUDIT",
        "definition":{
            "source_idea":"DERET STATISTIK JADI.xlsx",
            "ratio":"close_t / close_t-1",
            "causal_forecast":"arithmetic mean of last N fully observed ratios; N frozen to workbook-native 4 and 5",
            "target":"next bar close and direction",
            "leakage_control":"diagnostic only: future target ratio deliberately inserted into its own averaging window",
            "spreadsheet_percent_correctness_warning":"predicted_close/actual_close*100 is closeness-to-100, not directional win rate",
            "round_trip_fee_diagnostic_bps":15.0,
            "no_threshold_tuning":True,
        },
        "requested":{"symbols":syms,"timeframe":timeframe,"days":days},
        "aggregate":agg,
        "by_pair":result,
        "errors":errors,
    }
