"""V7-E causal 1H-close control for legacy BBC trigger families.

Read-only research endpoint. The full 1H candle must be complete before entry;
legacy same-hour 15m MTF entry is disabled. Entry occurs at the completed 1H
close. The existing switcher only evaluates exits on subsequent 1H candles, so
there is no same-signal-candle exit. TP/SL/cost/state-machine rules otherwise
remain the legacy baseline.
"""
from datetime import datetime, timezone
import numpy as np
from fastapi import APIRouter, Query

from mode3_bbc import Mode3BBCConfig, Switcher, compute_ema_series, compute_va_at_bar
from mode3_bbc_endpoint import load_candles_from_db

router=APIRouter(prefix="/v7",tags=["v7_research"])
PAIRS=["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT"]
CANONICAL_END_MS=1785852000000


def _cfg():
    return Mode3BBCConfig(
        ema_period=7,tp_pct=0.013,sl_pct=0.013,bear_tp_pct=0.0,bear_sl_pct=0.0,
        enable_sideways_trades=False,direct_transition_enabled=True,use_wick_exit=True,
        entry_usd=10.0,leverage=50.0,fee_pct_roundtrip=0.001,slippage_pct=0.0005,
        bull_mtf_15m_enabled=False,bear_mtf_15m_enabled=False,sideways_mtf_15m_enabled=False,
        bull_body_ratio_min=0.5,bear_body_ratio_min=0.6,sideways_body_ratio_min=0.6,
        trailing_ema_enabled=False,bull_poc_entry_enabled=False,bull_wait_retest_enabled=False,
        bull_use_swing_break=False,bull_use_26_support=False,sideways_poc_breakout_enabled=False,
    )


def _label(pre,tool):
    if tool=="BULL": return {"BULL":"BULL_STAY_EMA_RECLAIM","SIDEWAYS":"DIRECT_SIDEWAYS_TO_BULL","WAIT_SEE_BEARISH":"DIRECT_WAIT_BEARISH_TO_BULL","BEAR":"DIRECT_BEAR_TO_BULL","STARTUP":"STARTUP_TO_BULL"}.get(pre,f"BULL_FROM_{pre}")
    if tool=="BEAR": return {"BEAR":"BEAR_STAY_EMA_REJECTION","SIDEWAYS":"DIRECT_SIDEWAYS_TO_BEAR","WAIT_SEE_BULLISH":"DIRECT_WAIT_BULLISH_TO_BEAR","BULL":"DIRECT_BULL_TO_BEAR","STARTUP":"STARTUP_TO_BEAR"}.get(pre,f"BEAR_FROM_{pre}")
    return f"{tool}_FROM_{pre}"


def _stat(xs):
    n=len(xs);w=sum(x["win"] for x in xs);p=sum(x["pnl_usd"] for x in xs)
    return {"trades":n,"wins":w,"losses":n-w,"wr_pct":round(100*w/n,2) if n else None,"pnl_usd":round(p,2),"expectancy_usd":round(p/n,4) if n else None}


def _pair(symbol,start,end):
    cfg=_cfg(); rows=load_candles_from_db(symbol,"1h",start,end)
    if len(rows)<cfg.startup_warmup_candles: raise RuntimeError(f"insufficient {len(rows)}")
    O=np.array([r[1] for r in rows],float);H=np.array([r[2] for r in rows],float);L=np.array([r[3] for r in rows],float);C=np.array([r[4] for r in rows],float);V=np.array([r[5] for r in rows],float)
    ema=compute_ema_series(C,7);vahs=[];vals=[];pocs=[]
    for i in range(len(rows)):
        a,b,c=compute_va_at_bar(H,L,C,V,i,cfg.va_window,cfg.va_percentile_high,cfg.va_percentile_low);vahs.append(a);vals.append(b);pocs.append(c)
    sw=Switcher(cfg);meta={};opened=0
    for i in range(len(rows)):
        pre=sw.state;had=sw.position is not None
        sw.process_candle(i,O[i],H[i],L[i],C[i],ema[i],vahs[i],vals[i],pocs[i])
        if not had and sw.position is not None:
            meta[i]={"trigger":_label(pre,sw.position.tool),"entry_time":int(rows[i][0])};opened+=1
    out=[];missing=0
    for t in sw.trades:
        m=meta.get(t.entry_bar)
        if not m: missing+=1;m={"trigger":"UNLABELED","entry_time":int(rows[t.entry_bar][0])}
        out.append({"symbol":symbol,"trigger":m["trigger"],"entry_time":m["entry_time"],"tool":t.tool,"side":t.side,"pnl_usd":float(t.pnl_usd),"win":bool(t.pnl_usd>0)})
    return out,{"bars_1h":len(rows),"opened":opened,"closed":len(out),"missing_meta":missing,"open_at_end":sw.position is not None}


@router.get("/close-trigger-forensic")
def close_trigger_forensic(days:int=Query(971,ge=30,le=1500),end_ts_ms:int=Query(CANONICAL_END_MS,ge=1)):
    start=end_ts_ms-days*86400000;allx=[];coverage={};errors={}
    for p in PAIRS:
        try:x,c=_pair(p,start,end);allx+=x;coverage[p]=c
        except Exception as e:errors[p]=str(e)
    gs=sorted(set(x["trigger"] for x in allx));overall=_stat(allx)
    by_pair={p:_stat([x for x in allx if x["symbol"]==p]) for p in PAIRS}
    by_trigger={g:_stat([x for x in allx if x["trigger"]==g]) for g in gs}
    by_trigger_pair={g:{p:_stat([x for x in allx if x["trigger"]==g and x["symbol"]==p]) for p in PAIRS} for g in gs}
    sdt=datetime.fromtimestamp(start/1000,tz=timezone.utc);edt=datetime.fromtimestamp(end_ts_ms/1000,tz=timezone.utc);span=edt-sdt;cuts=[sdt+span*k/4 for k in range(5)];names=["Q1_early","Q2","Q3","Q4_recent"]
    by_block={};by_trigger_block={g:{} for g in gs}
    for i,nm in enumerate(names):
        lo=int(cuts[i].timestamp()*1000);hi=int(cuts[i+1].timestamp()*1000);xx=[x for x in allx if lo<=x["entry_time"]<hi];by_block[nm]=_stat(xx)
        for g in gs:by_trigger_block[g][nm]=_stat([x for x in xx if x["trigger"]==g])
    robustness={}
    for g in gs:
        pp=sum(1 for p in PAIRS if by_trigger_pair[g][p]["trades"]>=20 and (by_trigger_pair[g][p]["expectancy_usd"] or 0)>0);bb=sum(1 for b in names if by_trigger_block[g][b]["trades"]>=20 and (by_trigger_block[g][b]["expectancy_usd"] or 0)>0)
        robustness[g]={"positive_pairs":pp,"positive_blocks":bb,"all_4_pairs_positive":pp==4,"all_4_blocks_positive":bb==4}
    return {"phase":"V7-E","status":"FROZEN_CAUSAL_1H_CLOSE_TRIGGER_FORENSIC","window":{"start":sdt.isoformat(),"end_exclusive":edt.isoformat(),"days":days},"frozen_definition":{"signal":"completed 1H candle + legacy state machine","entry":"same completed 1H close","same_candle_exit":False,"legacy_same_hour_15m_mtf":False,"tp_pct":0.013,"sl_pct":0.013,"total_cost_pct":0.0015,"sideways_trades":False,"threshold_sweep":False},"coverage":coverage,"errors":errors,"overall":overall,"by_pair":by_pair,"by_trigger":by_trigger,"by_trigger_pair":by_trigger_pair,"by_block":by_block,"by_trigger_block":by_trigger_block,"trigger_robustness":robustness}
