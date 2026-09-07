#!/usr/bin/env python3
from __future__ import annotations

import io
import importlib.util
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
A45_PATH = Path(__file__).resolve().parent / "sol_long_15utc_parent_prerange_anatomy_a45.py"
spec = importlib.util.spec_from_file_location("sol_a45", A45_PATH)
a45 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a45)

INFILE = ROOT / "SOL_LONG_15UTC_PREFILL_PATH_A47B_TRADES.csv"
OUT_TRADES = ROOT / "SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_TRADES.csv"
OUT_FEATURES = ROOT / "SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_FEATURES.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_Status.txt"

BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
FETCH_START = pd.Timestamp("2020-08-01T00:00:00Z")
END = pd.Timestamp("2026-08-01T00:00:00Z")
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
PARTS = ["development", "external", "reference_validation"]
EXPECTED_COUNTS = {"development": 601, "external": 281, "reference_validation": 337}
BAR = pd.Timedelta(minutes=5)
EPS = 1e-12

FEATURE_FAMILY = {
    "btc_ref6_return_pct":"REF6","eth_ref6_return_pct":"REF6",
    "btc_ref6_range_pct":"REF6","eth_ref6_range_pct":"REF6",
    "btc_ref6_close_location":"REF6","eth_ref6_close_location":"REF6",
    "market_ref6_mean_return_pct":"REF6","market_ref6_breadth":"REF6",
    "btc_last60_return_pct":"LATE","eth_last60_return_pct":"LATE",
    "btc_last120_return_pct":"LATE","eth_last120_return_pct":"LATE",
    "market_last60_mean_return_pct":"LATE","market_last120_mean_return_pct":"LATE",
    "market_last60_breadth":"LATE","market_last120_breadth":"LATE",
    "btc_prefill_return_pct":"PREFILL","eth_prefill_return_pct":"PREFILL",
    "market_prefill_mean_return_pct":"PREFILL","market_prefill_breadth":"PREFILL",
    "btc_prefill_close_vs_refH_pct":"PREFILL","eth_prefill_close_vs_refH_pct":"PREFILL",
}
FEATURES = list(FEATURE_FAMILY)


def month_urls(symbol):
    out=[]
    cur=pd.Timestamp(FETCH_START.year,FETCH_START.month,1,tz="UTC")
    end=pd.Timestamp(END.year,END.month,1,tz="UTC")
    while cur<end:
        ym=cur.strftime("%Y-%m")
        out.append((symbol,f"{BASE}/{symbol}/5m/{symbol}-5m-{ym}.zip"))
        cur += pd.offsets.MonthBegin(1)
    return out


def fetch_one(item):
    symbol,url=item
    r=requests.get(url,timeout=90,headers={"User-Agent":"bababot-sol-a49/1.0"})
    if r.status_code==404:return symbol,None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names=[n for n in zf.namelist() if n.lower().endswith('.csv')]
        if not names:return symbol,None
        with zf.open(names[0]) as fh:
            z=pd.read_csv(fh,header=None,usecols=[0,1,2,3,4],names=['ts','open','high','low','close'])
            return symbol,z


def load_symbol(symbol):
    frames=[]
    items=month_urls(symbol)
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs=[ex.submit(fetch_one,it) for it in items]
        for fut in as_completed(futs):
            sym,z=fut.result()
            if sym==symbol and z is not None and len(z):frames.append(z)
    if not frames:raise RuntimeError(f"no data {symbol}")
    x=pd.concat(frames,ignore_index=True)
    t=pd.to_numeric(x.ts,errors='coerce')
    t=np.where(t>100_000_000_000_000,t/1000.0,t)
    x['ts']=pd.to_datetime(t,unit='ms',utc=True,errors='coerce')
    for c in ['open','high','low','close']:x[c]=pd.to_numeric(x[c],errors='coerce')
    x=x.dropna().drop_duplicates('ts').sort_values('ts')
    x=x[(x.ts>=FETCH_START)&(x.ts<END)].set_index('ts')
    expected=int((x.index[-1]-x.index[0])/BAR)+1
    coverage=len(x)/expected
    if coverage<0.995:raise RuntimeError(f"{symbol} coverage {coverage:.6f}")
    return x,coverage


def exact_window(x,start,end,n):
    q=x[(x.index>=start)&(x.index<end)].copy()
    if len(q)!=n or q.index[0]!=start or q.index[-1]!=end-BAR:
        raise ValueError(f"incomplete window {start} {end} {len(q)}/{n}")
    return q


def ret(q):
    o=float(q.open.iloc[0]); c=float(q.close.iloc[-1])
    return c/o-1.0 if abs(o)>EPS else np.nan


def range_pct(q):
    c=float(q.close.iloc[-1]); rr=float(q.high.max()-q.low.min())
    return rr/c if abs(c)>EPS else np.nan


def close_loc(q):
    h=float(q.high.max());l=float(q.low.min());r=h-l
    return (float(q.close.iloc[-1])-l)/r if r>EPS else np.nan


def enrich(markets,r):
    es=pd.Timestamp(r.execution_start);et=pd.Timestamp(r.entry_ts);rs=es-pd.Timedelta(hours=6)
    out={}; refret={}; late60={}; late120={}; prefillret={}
    for symbol,prefix in [('BTCUSDT','btc'),('ETHUSDT','eth')]:
        x=markets[symbol]
        ref=exact_window(x,rs,es,72)
        r6=ret(ref); r60=ret(ref.iloc[-12:]); r120=ret(ref.iloc[-24:])
        out[f'{prefix}_ref6_return_pct']=r6
        out[f'{prefix}_ref6_range_pct']=range_pct(ref)
        out[f'{prefix}_ref6_close_location']=close_loc(ref)
        out[f'{prefix}_last60_return_pct']=r60
        out[f'{prefix}_last120_return_pct']=r120
        refret[prefix]=r6;late60[prefix]=r60;late120[prefix]=r120
        pre=x[(x.index>=es)&(x.index<et)].copy()
        if len(pre):
            pr=ret(pre)
            out[f'{prefix}_prefill_return_pct']=pr
            out[f'{prefix}_prefill_close_vs_refH_pct']=float(pre.close.iloc[-1])/float(ref.high.max())-1.0
            prefillret[prefix]=pr
        else:
            out[f'{prefix}_prefill_return_pct']=np.nan
            out[f'{prefix}_prefill_close_vs_refH_pct']=np.nan
            prefillret[prefix]=np.nan
    out['market_ref6_mean_return_pct']=float(np.mean([refret['btc'],refret['eth']]))
    out['market_ref6_breadth']=float((refret['btc']>0)+(refret['eth']>0))
    out['market_last60_mean_return_pct']=float(np.mean([late60['btc'],late60['eth']]))
    out['market_last120_mean_return_pct']=float(np.mean([late120['btc'],late120['eth']]))
    out['market_last60_breadth']=float((late60['btc']>0)+(late60['eth']>0))
    out['market_last120_breadth']=float((late120['btc']>0)+(late120['eth']>0))
    if pd.notna(prefillret['btc']) and pd.notna(prefillret['eth']):
        out['market_prefill_mean_return_pct']=float(np.mean([prefillret['btc'],prefillret['eth']]))
        out['market_prefill_breadth']=float((prefillret['btc']>0)+(prefillret['eth']>0))
    else:
        out['market_prefill_mean_return_pct']=np.nan
        out['market_prefill_breadth']=np.nan
    return out


def main():
    parent=pd.read_csv(INFILE)
    for c in ['execution_start','entry_ts','exit_ts']:parent[c]=pd.to_datetime(parent[c],utc=True,errors='coerce')
    for c in ['pnl','pnl_5bps','dev_block']:parent[c]=pd.to_numeric(parent[c],errors='coerce')
    counts=parent.groupby('partition').size().to_dict();count_ok=all(int(counts.get(k,0))==v for k,v in EXPECTED_COUNTS.items())
    markets={};cov={}
    for symbol in SYMBOLS:
        markets[symbol],cov[symbol]=load_symbol(symbol)
    enriched=[];errors=[]
    for idx,r in parent.iterrows():
        try:
            z=r.to_dict();z.update(enrich(markets,r));z['stress_outcome']='WIN' if float(r.pnl_5bps)>0 else 'FAIL';enriched.append(z)
        except Exception as exc:errors.append((int(idx),str(exc)))
    trades=pd.DataFrame(enriched);full=bool(count_ok and not errors and len(trades)==sum(EXPECTED_COUNTS.values()))
    rows=[]
    if full:
        for feature in FEATURES:
            dev=a45.effect_stats(trades[trades.partition=='development'],feature)
            ext=a45.effect_stats(trades[trades.partition=='external'],feature)
            refv=a45.effect_stats(trades[trades.partition=='reference_validation'],feature)
            sign=int(np.sign(dev['gap'])) if pd.notna(dev['gap']) else 0
            adequate=same=0;row={'family':FEATURE_FAMILY[feature],'feature':feature}
            for bi in range(6):
                b=trades[(trades.partition=='development')&(pd.to_numeric(trades.dev_block,errors='coerce')==bi)]
                bs=a45.effect_stats(b,feature);ok=bool(bs['win_n']>=20 and bs['fail_n']>=20)
                if ok:
                    adequate+=1
                    if sign!=0 and pd.notna(bs['gap']) and int(np.sign(bs['gap']))==sign:same+=1
                row[f'b{bi+1}_gap']=bs['gap'];row[f'b{bi+1}_effect_IQR']=bs['effect']
            counts_ok=bool(dev['win_n']>=100 and dev['fail_n']>=100 and ext['win_n']>=50 and ext['fail_n']>=50 and refv['win_n']>=50 and refv['fail_n']>=50)
            rep=bool(counts_ok and pd.notna(dev['effect']) and dev['effect']>=0.25 and adequate>=4 and same>=4 and sign!=0 and pd.notna(ext['gap']) and int(np.sign(ext['gap']))==sign and pd.notna(refv['gap']) and int(np.sign(refv['gap']))==sign and pd.notna(ext['effect']) and ext['effect']>=0.10 and pd.notna(refv['effect']) and refv['effect']>=0.10)
            strong=bool(rep and dev['effect']>=0.35 and same>=5)
            row.update({'dev_win_n':dev['win_n'],'dev_fail_n':dev['fail_n'],'dev_win_median':dev['win_median'],'dev_fail_median':dev['fail_median'],'dev_gap':dev['gap'],'dev_effect_IQR':dev['effect'],'adequate_dev_blocks':adequate,'same_sign_dev_blocks':same,'external_gap':ext['gap'],'external_effect_IQR':ext['effect'],'reference_gap':refv['gap'],'reference_effect_IQR':refv['effect'],'replicated_directional':rep,'strong_replicated':strong})
            rows.append(row)
    features=pd.DataFrame(rows)
    if len(features):features=features.sort_values(['strong_replicated','replicated_directional','dev_effect_IQR'],ascending=[False,False,False],na_position='last').reset_index(drop=True)
    trades.to_csv(OUT_TRADES,index=False);features.to_csv(OUT_FEATURES,index=False)
    if not full:status='SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_RECONCILIATION_FAIL'
    elif bool(features.replicated_directional.any()):status='SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_SUPPORTED_FOR_A50'
    else:status='SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_INCONCLUSIVE'
    OUT_STATUS.write_text(status+'\n',encoding='utf-8')
    lines=['# SOL LONG 15UTC Market Alignment Anatomy — A49 Result','', 'A49 keeps the SOL parent frozen and studies only BTC/ETH state available before the SOL H fill.','',f"BTC coverage **{100*cov['BTCUSDT']:.4f}%**; ETH coverage **{100*cov['ETHUSDT']:.4f}%**. Count reconciliation: **{count_ok}**. Enriched **{len(trades)}/{sum(EXPECTED_COUNTS.values())}**; errors **{len(errors)}**.",'','## Replicated market separators','', '| Family | Feature | Dev WIN med | Dev FAIL med | Dev effect | Dev sign blocks | Ext effect | RefVal effect | Strong |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    if len(features) and bool(features.replicated_directional.any()):
        for _,r in features[features.replicated_directional==True].iterrows():lines.append(f"| {r.family} | {r.feature} | {a45.fmt(r.dev_win_median,5)} | {a45.fmt(r.dev_fail_median,5)} | {a45.fmt(r.dev_effect_IQR)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | {a45.fmt(r.external_effect_IQR)} | {a45.fmt(r.reference_effect_IQR)} | {'YES' if bool(r.strong_replicated) else 'NO'} |")
    else:lines.append('| - | none | - | - | - | - | - | - | - |')
    lines += ['','## Strongest diagnostics','', '| Family | Feature | Dev effect | Dev sign blocks | Ext gap/effect | RefVal gap/effect | Replicated |','|---|---|---:|---:|---|---|---:|']
    if len(features):
        for _,r in features.head(12).iterrows():lines.append(f"| {r.family} | {r.feature} | {a45.fmt(r.dev_effect_IQR)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | {a45.fmt(r.external_gap,5)}/{a45.fmt(r.external_effect_IQR)} | {a45.fmt(r.reference_gap,5)}/{a45.fmt(r.reference_effect_IQR)} | {'YES' if bool(r.replicated_directional) else 'NO'} |")
    repn=int(features.replicated_directional.sum()) if len(features) else 0;strongn=int(features.strong_replicated.sum()) if len(features) else 0
    lines += ['','## Decision','',f'Replicated features: **{repn}**. Strong replicated: **{strongn}**.','',f'**Status: {status}**','','Research only. Live Baba Bot remains unchanged.']
    if errors:lines += ['','First errors:']+[f'- {i}: {e}' for i,e in errors[:10]]
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(status)


if __name__=='__main__':main()
