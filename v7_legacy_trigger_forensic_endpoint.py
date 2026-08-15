"""Read-only V7 forensic endpoint for the canonical 971d skip-SIDEWAYS BBC baseline.

No trading/order code. Uses the existing Mode3BBC Switcher and Railway historical DB,
with external instrumentation only, to label the state path that opened each trade.
"""
from collections import Counter
from datetime import datetime, timezone, timedelta

import numpy as np
from fastapi import APIRouter, Query

from mode3_bbc import Mode3BBCConfig, Switcher, compute_ema_series, compute_va_at_bar
from mode3_bbc_endpoint import load_candles_from_db, compute_mtf_bull_entry, compute_mtf_bear_entry

router = APIRouter(prefix="/v7", tags=["v7_research"])
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
CANONICAL_END_MS = 1785852000000  # 2026-08-04 14:00:00 UTC, exclusive


def _cfg():
    return Mode3BBCConfig(
        ema_period=7, tp_pct=0.013, sl_pct=0.013,
        bear_tp_pct=0.0, bear_sl_pct=0.0,
        enable_sideways_trades=False, direct_transition_enabled=True,
        use_wick_exit=True, entry_usd=10.0, leverage=50.0,
        fee_pct_roundtrip=0.001, slippage_pct=0.0005,
        bull_mtf_15m_enabled=True, bull_body_ratio_min=0.5,
        bear_mtf_15m_enabled=True, bear_body_ratio_min=0.6,
        sideways_mtf_15m_enabled=True, sideways_body_ratio_min=0.6,
        trailing_ema_enabled=False, bull_poc_entry_enabled=False,
        bull_wait_retest_enabled=False, bull_use_swing_break=False,
        bull_use_26_support=False, sideways_poc_breakout_enabled=False,
    )


def _label(pre_state, tool):
    if tool == "BULL":
        return {
            "BULL": "BULL_STAY_EMA_RECLAIM",
            "SIDEWAYS": "DIRECT_SIDEWAYS_TO_BULL",
            "WAIT_SEE_BEARISH": "DIRECT_WAIT_BEARISH_TO_BULL",
            "BEAR": "DIRECT_BEAR_TO_BULL",
            "STARTUP": "STARTUP_TO_BULL",
        }.get(pre_state, f"BULL_FROM_{pre_state}")
    if tool == "BEAR":
        return {
            "BEAR": "BEAR_STAY_EMA_REJECTION",
            "SIDEWAYS": "DIRECT_SIDEWAYS_TO_BEAR",
            "WAIT_SEE_BULLISH": "DIRECT_WAIT_BULLISH_TO_BEAR",
            "BULL": "DIRECT_BULL_TO_BEAR",
            "STARTUP": "STARTUP_TO_BEAR",
        }.get(pre_state, f"BEAR_FROM_{pre_state}")
    return f"{tool}_FROM_{pre_state}"


def _stat(rows):
    n = len(rows); w = sum(r["win"] for r in rows); pnl = sum(r["pnl_usd"] for r in rows)
    return {
        "trades": n, "wins": w, "losses": n-w,
        "wr_pct": round(100.0*w/n, 2) if n else None,
        "pnl_usd": round(pnl, 2),
        "expectancy_usd": round(pnl/n, 4) if n else None,
    }


def _run_pair(symbol, start_ts, end_ts):
    cfg = _cfg()
    rows = load_candles_from_db(symbol, "1h", start_ts, end_ts)
    rows15 = load_candles_from_db(symbol, "15m", start_ts, end_ts)
    if len(rows) < cfg.startup_warmup_candles:
        raise RuntimeError(f"{symbol}: insufficient 1h candles {len(rows)}")

    O=np.array([r[1] for r in rows],dtype=float); H=np.array([r[2] for r in rows],dtype=float)
    L=np.array([r[3] for r in rows],dtype=float); C=np.array([r[4] for r in rows],dtype=float)
    V=np.array([r[5] for r in rows],dtype=float); ema=compute_ema_series(C,cfg.ema_period)
    vahs=[]; vals=[]; pocs=[]
    for i in range(len(rows)):
        vah,val,poc=compute_va_at_bar(H,L,C,V,i,cfg.va_window,cfg.va_percentile_high,cfg.va_percentile_low)
        vahs.append(vah); vals.append(val); pocs.append(poc)

    sw=Switcher(cfg)
    bec,bel=compute_mtf_bull_entry(rows,rows15); sec,seh=compute_mtf_bear_entry(rows,rows15)
    sw.mtf_bull_entry_close=bec; sw.mtf_bull_entry_low=bel
    sw.mtf_bear_entry_close=sec; sw.mtf_bear_entry_high=seh

    meta={}; opened=Counter()
    for i in range(len(rows)):
        pre=sw.state; had=sw.position is not None
        sw.process_candle(i,O[i],H[i],L[i],C[i],ema[i],vahs[i],vals[i],pocs[i])
        if not had and sw.position is not None:
            lab=_label(pre,sw.position.tool); opened[lab]+=1
            meta[i]={"trigger":lab,"pre_state":pre,"entry_time_ms":rows[i][0],"tool":sw.position.tool,"side":sw.position.side}

    out=[]; missing=0
    for t in sw.trades:
        m=meta.get(t.entry_bar)
        if not m:
            missing+=1
            m={"trigger":"UNLABELED","pre_state":None,"entry_time_ms":rows[t.entry_bar][0],"tool":t.tool,"side":t.side}
        out.append({"symbol":symbol,"trigger":m["trigger"],"pre_state":m["pre_state"],"tool":t.tool,"side":t.side,
                    "entry_time_ms":m["entry_time_ms"],"pnl_usd":float(t.pnl_usd),"win":bool(t.pnl_usd>0)})
    return out,{"bars_1h":len(rows),"bars_15m":len(rows15),"entries_opened":sum(opened.values()),
                "closed_trades":len(out),"open_position_at_end":sw.position is not None,
                "missing_meta":missing,"entry_counts":dict(opened)}


@router.get("/legacy-trigger-forensic")
def legacy_trigger_forensic(
    days:int=Query(971,ge=30,le=1500),
    end_ts_ms:int=Query(CANONICAL_END_MS,ge=1),
):
    start_ts=end_ts_ms-days*86400000
    all_rows=[]; coverage={}; errors={}
    for p in PAIRS:
        try:
            rr,cov=_run_pair(p,start_ts,end_ts_ms); all_rows.extend(rr); coverage[p]=cov
        except Exception as e:
            errors[p]=str(e)

    overall=_stat(all_rows)
    by_pair={p:_stat([r for r in all_rows if r["symbol"]==p]) for p in PAIRS}
    by_tool={x:_stat([r for r in all_rows if r["tool"]==x]) for x in ("BULL","BEAR")}
    triggers=sorted(set(r["trigger"] for r in all_rows))
    by_trigger={g:_stat([r for r in all_rows if r["trigger"]==g]) for g in triggers}
    by_trigger_pair={g:{p:_stat([r for r in all_rows if r["trigger"]==g and r["symbol"]==p]) for p in PAIRS} for g in triggers}

    start_dt=datetime.fromtimestamp(start_ts/1000,tz=timezone.utc); end_dt=datetime.fromtimestamp(end_ts_ms/1000,tz=timezone.utc)
    span=end_dt-start_dt; cuts=[start_dt+span*k/4 for k in range(5)]; names=["Q1_early","Q2","Q3","Q4_recent"]
    by_block={}; by_trigger_block={g:{} for g in triggers}
    for i,name in enumerate(names):
        lo=int(cuts[i].timestamp()*1000); hi=int(cuts[i+1].timestamp()*1000)
        xs=[r for r in all_rows if lo<=r["entry_time_ms"]<hi]
        by_block[name]={**_stat(xs),"start":cuts[i].isoformat(),"end":cuts[i+1].isoformat()}
        for g in triggers: by_trigger_block[g][name]=_stat([r for r in xs if r["trigger"]==g])

    robustness={}
    for g in triggers:
        pair_pos=sum(1 for p in PAIRS if by_trigger_pair[g][p]["trades"]>=20 and (by_trigger_pair[g][p]["expectancy_usd"] or 0)>0)
        block_pos=sum(1 for b in names if by_trigger_block[g][b]["trades"]>=20 and (by_trigger_block[g][b]["expectancy_usd"] or 0)>0)
        robustness[g]={"positive_pairs":pair_pos,"positive_blocks":block_pos,"all_4_pairs_positive":pair_pos==4,"all_4_blocks_positive":block_pos==4}

    target={"trades":4945,"wins":3237,"losses":1708,"pnl_usd":6229.75,
            "per_pair_pnl":{"BTCUSDT":826.0,"ETHUSDT":1847.5,"SOLUSDT":2258.25,"BNBUSDT":1298.0}}
    delta={"trades":overall["trades"]-target["trades"],"wins":overall["wins"]-target["wins"],"losses":overall["losses"]-target["losses"],
           "pnl_usd":round(overall["pnl_usd"]-target["pnl_usd"],2),
           "per_pair_pnl":{p:round(by_pair[p]["pnl_usd"]-target["per_pair_pnl"][p],2) for p in PAIRS}}
    parity=(delta["trades"]==0 and delta["wins"]==0 and delta["losses"]==0 and abs(delta["pnl_usd"])<0.01 and all(abs(v)<0.01 for v in delta["per_pair_pnl"].values()))

    return {"phase":"V7-C","status":"RAILWAY_DB_CANONICAL_TRIGGER_FORENSIC",
            "window":{"start":start_dt.isoformat(),"end_exclusive":end_dt.isoformat(),"days":days},
            "config":{"ema":7,"tp":0.013,"sl":0.013,"entry_usd":10,"leverage":50,"total_cost_pct":0.0015,"sideways_trades":False,"legacy_15m_mtf":True},
            "target":target,"parity":{"pass":parity,"delta":delta},"coverage":coverage,"errors":errors,
            "overall":overall,"by_pair":by_pair,"by_tool":by_tool,"by_trigger":by_trigger,
            "by_trigger_pair":by_trigger_pair,"by_block":by_block,"by_trigger_block":by_trigger_block,
            "trigger_robustness":robustness}
