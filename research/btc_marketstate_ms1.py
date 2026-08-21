#!/usr/bin/env python3
"""BTC Market-State MS1 — frozen preregistered high-probability LONG/SHORT state search.
Research only. Live BBC untouched.
"""
from __future__ import annotations

import io, itertools, json, math, os, zipfile
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_MarketState_MS1_Result.md"
OUT_JSON = ROOT / "BTC_MarketState_MS1_Result.json"
OUT_CSV = ROOT / "BTC_MarketState_MS1_Candidates.csv"
OUT_AUG = ROOT / "BTC_MarketState_MS1_Aug19_20.csv"
CACHE = Path(os.getenv("MS1_CACHE", "/tmp/ms1_cache")); CACHE.mkdir(parents=True, exist_ok=True)
SESSION = requests.Session(); SESSION.headers.update({"User-Agent":"bababot-discovery-ms1/1.0"})
BASE = "https://data.binance.vision/data/futures/um"
SYMBOL = "BTCUSDT"
START = pd.Timestamp("2023-01-01", tz="UTC")
END = pd.Timestamp("2026-08-21", tz="UTC")
TP = 0.015; SL = 0.008; HOLD = 6; FEE = 0.0015


def get_bytes(url: str, name: str) -> Optional[bytes]:
    p = CACHE / name
    if p.exists(): return p.read_bytes()
    r = SESSION.get(url, timeout=60)
    if r.status_code == 404: return None
    r.raise_for_status(); p.write_bytes(r.content); return r.content


def month_iter(start, end):
    cur = pd.Timestamp(start.year, start.month, 1, tz="UTC")
    last = pd.Timestamp(end.year, end.month, 1, tz="UTC")
    while cur <= last:
        yield cur.year, cur.month
        cur += pd.offsets.MonthBegin(1)


def read_zip_csv(data: bytes, header=None):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        n = [x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f: return pd.read_csv(f, header=header)


def load_klines():
    fs=[]
    for y,m in month_iter(START-pd.Timedelta(days=3), END):
        ym=f"{y:04d}-{m:02d}"; name=f"{SYMBOL}-1h-{ym}.zip"
        data=get_bytes(f"{BASE}/monthly/klines/{SYMBOL}/1h/{name}", name)
        if data is None:
            # current month may not yet have monthly archive: use daily files
            d0=pd.Timestamp(y,m,1,tz='UTC'); d1=min(d0+pd.offsets.MonthBegin(1), END)
            for d in pd.date_range(d0,d1-pd.Timedelta(days=1),freq='D'):
                ds=d.strftime('%Y-%m-%d'); dn=f"{SYMBOL}-1h-{ds}.zip"
                dd=get_bytes(f"{BASE}/daily/klines/{SYMBOL}/1h/{dn}", dn)
                if dd is None: continue
                fs.append(read_zip_csv(dd, header=None))
            continue
        fs.append(read_zip_csv(data, header=None))
    if not fs: raise RuntimeError('no kline data')
    x=pd.concat(fs,ignore_index=True).iloc[:,:12]
    x.columns=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore']
    for c in ['open','high','low','close','quote_volume','taker_buy_quote']: x[c]=pd.to_numeric(x[c],errors='coerce')
    ot=pd.to_numeric(x.open_time,errors='coerce'); unit='us' if ot.dropna().median()>1e14 else 'ms'
    x['ts']=pd.to_datetime(ot,unit=unit,utc=True)
    x=x.dropna(subset=['ts','open','high','low','close']).drop_duplicates('ts').sort_values('ts')
    x=x[(x.ts>=START-pd.Timedelta(days=2))&(x.ts<END)].reset_index(drop=True)
    return x


def load_funding():
    # Binance futures funding endpoint paginated; if unavailable, fail rather than silently remove preregistered feature.
    url='https://fapi.binance.com/fapi/v1/fundingRate'; rows=[]
    cur=int((START-pd.Timedelta(days=20)).timestamp()*1000); end=int(END.timestamp()*1000)
    while cur<end:
        r=SESSION.get(url,params={'symbol':SYMBOL,'startTime':cur,'endTime':end,'limit':1000},timeout=30)
        r.raise_for_status(); a=r.json()
        if not a: break
        rows.extend(a); nxt=max(int(z['fundingTime']) for z in a)+1
        if nxt<=cur: break
        cur=nxt
        if len(a)<1000: break
    if not rows: raise RuntimeError('funding history unavailable')
    f=pd.DataFrame(rows); f['ts']=pd.to_datetime(pd.to_numeric(f.fundingTime),unit='ms',utc=True)
    f['funding_rate']=pd.to_numeric(f.fundingRate,errors='coerce'); f=f[['ts','funding_rate']].dropna().drop_duplicates('ts').sort_values('ts')
    f['funding_mean30']=f.funding_rate.rolling(30,min_periods=10).mean(); f['funding_sd30']=f.funding_rate.rolling(30,min_periods=10).std()
    f['funding_z_30']=(f.funding_rate-f.funding_mean30)/f.funding_sd30.replace(0,np.nan)
    return f


def fred(series):
    u=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
    r=SESSION.get(u,timeout=30); r.raise_for_status()
    z=pd.read_csv(io.StringIO(r.text)); z.columns=['date',series]
    z['date']=pd.to_datetime(z.date,utc=True); z[series]=pd.to_numeric(z[series],errors='coerce')
    return z.dropna().sort_values('date')


def load_macro():
    ids=['DGS10','DTWEXBGS','VIXCLS','SP500']; parts=[]
    for s in ids:
        z=fred(s).set_index('date')[[s]]; parts.append(z)
    m=pd.concat(parts,axis=1).sort_index().ffill()
    m['dgs10_chg']=m.DGS10.diff(); m['dollar_chg']=m.DTWEXBGS.pct_change(); m['vix_chg']=m.VIXCLS.pct_change(); m['sp500_ret']=m.SP500.pct_change()
    # mandatory one-day lag: a BTC row on calendar day D only sees macro changes through D-1.
    q=m[['dgs10_chg','dollar_chg','vix_chg','sp500_ret']].shift(1).copy(); q['macro_date']=q.index
    return q.reset_index(drop=True)


def build_frame(k,f,m):
    x=k.copy(); c=x.close
    x['ret_1h']=c.pct_change(); x['ret_4h']=c/c.shift(4)-1; x['ret_24h']=c/c.shift(24)-1
    hi6=x.high.rolling(6,min_periods=6).max(); lo6=x.low.rolling(6,min_periods=6).min(); hi24=x.high.rolling(24,min_periods=24).max(); lo24=x.low.rolling(24,min_periods=24).min()
    x['compression_6_24']=(hi6-lo6)/(hi24-lo24).replace(0,np.nan)
    x['breakout_pos_24']=(c-lo24)/(hi24-lo24).replace(0,np.nan)
    x['rv_24']=x.ret_1h.rolling(24,min_periods=24).std()
    medv=x.quote_volume.rolling(24,min_periods=12).median(); x['rel_quote_volume_24']=x.quote_volume/medv.replace(0,np.nan)
    buy=x.taker_buy_quote.rolling(3,min_periods=3).sum(); qv=x.quote_volume.rolling(3,min_periods=3).sum(); x['taker_imbalance_3h']=(2*buy-qv)/qv.replace(0,np.nan)
    x=pd.merge_asof(x.sort_values('ts'),f.sort_values('ts'),on='ts',direction='backward')
    x['macro_date']=x.ts.dt.floor('D'); x=x.merge(m,on='macro_date',how='left')
    for c0 in ['dgs10_chg','dollar_chg','vix_chg','sp500_ret']: x[c0]=x[c0].ffill()
    return x


def simulate(x):
    rows=[]
    for i in range(24,len(x)-HOLD-1):
        t=x.iloc[i]; entry=float(x.iloc[i+1].open)
        if not np.isfinite(entry) or entry<=0: continue
        fut=x.iloc[i+1:i+1+HOLD]
        def side_eval(side):
            if side=='LONG': tp=entry*(1+TP); sl=entry*(1-SL)
            else: tp=entry*(1-TP); sl=entry*(1+SL)
            reason='TIME'; gross=float((fut.iloc[-1].close/entry-1)*(1 if side=='LONG' else -1))
            for _,b in fut.iterrows():
                hit_sl=(b.low<=sl) if side=='LONG' else (b.high>=sl)
                hit_tp=(b.high>=tp) if side=='LONG' else (b.low<=tp)
                if hit_sl: reason='SL'; gross=-SL; break
                if hit_tp: reason='TP'; gross=TP; break
            pnl=gross-FEE; return reason, gross, pnl
        lr,lg,lp=side_eval('LONG'); sr,sg,sp=side_eval('SHORT')
        d=t.to_dict(); d.update({'entry_ts':x.iloc[i+1].ts,'entry':entry,'long_reason':lr,'long_win':lr=='TP','long_pnl':lp,'short_reason':sr,'short_win':sr=='TP','short_pnl':sp})
        rows.append(d)
    return pd.DataFrame(rows)


def qv(disc,col,p):
    v=pd.to_numeric(disc[col],errors='coerce').dropna(); return float(v.quantile(p))


def atoms_and_thresholds(df,split):
    d=df.iloc[:split]
    T={
      'compression_q30':qv(d,'compression_6_24',.30),'flow_q30':qv(d,'taker_imbalance_3h',.30),'flow_q70':qv(d,'taker_imbalance_3h',.70),
      'break_q20':qv(d,'breakout_pos_24',.20),'break_q80':qv(d,'breakout_pos_24',.80),'ret4_q30':qv(d,'ret_4h',.30),'ret4_q70':qv(d,'ret_4h',.70),
      'vol_q70':qv(d,'rel_quote_volume_24',.70),'fundz_q30':qv(d,'funding_z_30',.30),'fundz_q70':qv(d,'funding_z_30',.70),
      'yield_q30':qv(d,'dgs10_chg',.30),'yield_q70':qv(d,'dgs10_chg',.70),'dollar_q30':qv(d,'dollar_chg',.30),'dollar_q70':qv(d,'dollar_chg',.70),
      'vix_q30':qv(d,'vix_chg',.30),'vix_q70':qv(d,'vix_chg',.70),'spx_q30':qv(d,'sp500_ret',.30),'spx_q70':qv(d,'sp500_ret',.70),
    }
    A={}
    A['LONG']={
      'COMPRESSED':df.compression_6_24<=T['compression_q30'],'POS_FLOW':df.taker_imbalance_3h>=T['flow_q70'],'HIGH_BREAKOUT_POS':df.breakout_pos_24>=T['break_q80'],
      'POS_4H':df.ret_4h>=T['ret4_q70'],'HIGH_VOLUME':df.rel_quote_volume_24>=T['vol_q70'],'LOW_FUNDING':(df.funding_z_30<=T['fundz_q30'])|(df.funding_rate<=0),
      'YIELD_DOWN':df.dgs10_chg<=T['yield_q30'],'DOLLAR_DOWN':df.dollar_chg<=T['dollar_q30'],'VIX_DOWN':df.vix_chg<=T['vix_q30'],'SPX_UP':df.sp500_ret>=T['spx_q70']}
    A['SHORT']={
      'COMPRESSED':df.compression_6_24<=T['compression_q30'],'NEG_FLOW':df.taker_imbalance_3h<=T['flow_q30'],'LOW_BREAKOUT_POS':df.breakout_pos_24<=T['break_q20'],
      'NEG_4H':df.ret_4h<=T['ret4_q30'],'HIGH_VOLUME':df.rel_quote_volume_24>=T['vol_q70'],'HIGH_FUNDING':(df.funding_z_30>=T['fundz_q70'])|(df.funding_rate>=0),
      'YIELD_UP':df.dgs10_chg>=T['yield_q70'],'DOLLAR_UP':df.dollar_chg>=T['dollar_q70'],'VIX_UP':df.vix_chg>=T['vix_q70'],'SPX_DOWN':df.sp500_ret<=T['spx_q30']}
    return A,T


def stat(z,side):
    n=len(z); wins=int(z[f'{side.lower()}_win'].sum()) if n else 0; pnl=float(z[f'{side.lower()}_pnl'].sum()) if n else 0.0
    return {'n':n,'wins':wins,'wr':wins/n if n else None,'pnl':pnl,'exp':pnl/n if n else None}


def evaluate(df,A,split):
    out=[]
    for side in ['LONG','SHORT']:
        names=list(A[side])
        for r in [2,3]:
            for combo in itertools.combinations(names,r):
                mask=pd.Series(True,index=df.index)
                for a in combo: mask &= A[side][a].fillna(False)
                dz=df.iloc[:split][mask.iloc[:split]]; vz=df.iloc[split:][mask.iloc[split:]]; pz=df[mask]
                ds,vs,ps=stat(dz,side),stat(vz,side),stat(pz,side)
                # Validation chronological quartile coverage.
                if len(vz):
                    pos=np.flatnonzero(mask.iloc[split:].values); q=np.minimum(3,(pos*4/max(1,len(df)-split)).astype(int)); qcov=len(set(q.tolist()))
                else:qcov=0
                candidate=bool(ds['n']>=30 and ds['wr']>=.80 and vs['n']>=12 and vs['wr']>=.75 and ps['wr']>=.80 and ds['exp']>0 and vs['exp']>0 and qcov>=3)
                validated=bool(candidate and vs['wr']>=.80)
                out.append({'side':side,'atoms':' + '.join(combo),'k':r,'disc_n':ds['n'],'disc_wr':ds['wr'],'disc_exp':ds['exp'],'val_n':vs['n'],'val_wr':vs['wr'],'val_exp':vs['exp'],'pooled_n':ps['n'],'pooled_wr':ps['wr'],'pooled_exp':ps['exp'],'val_quartiles':qcov,'candidate80':candidate,'validated80':validated})
    return pd.DataFrame(out).sort_values(['validated80','candidate80','val_wr','val_n'],ascending=[False,False,False,False])


def august_audit(df,A,cands):
    z=df[(df.entry_ts>=pd.Timestamp('2026-08-19',tz='UTC'))&(df.entry_ts<pd.Timestamp('2026-08-21',tz='UTC'))].copy()
    if z.empty:return pd.DataFrame()
    # strongest realized next-6h favorable excursion based on the already computed first-hit outcome, plus 6h close return proxy
    z['fwd6_close_ret']=z.close.shift(-6)/z.close-1
    idx=z.fwd6_close_ret.idxmax() if z.fwd6_close_ret.notna().any() else z.index[0]
    row=df.loc[idx]
    records=[]
    for side in ['LONG','SHORT']:
        active=[n for n,s in A[side].items() if bool(s.loc[idx])]
        fired=[]
        top=cands[(cands.side==side)&(cands.disc_n>=30)&(cands.disc_wr>=.80)]
        for _,c in top.iterrows():
            req=c.atoms.split(' + ')
            if all(a in active for a in req): fired.append(c.atoms)
        records.append({'side':side,'feature_ts':str(row.ts),'entry_ts':str(row.entry_ts),'entry':float(row.entry),'ret_4h':row.ret_4h,'ret_24h':row.ret_24h,'compression_6_24':row.compression_6_24,'breakout_pos_24':row.breakout_pos_24,'rel_quote_volume_24':row.rel_quote_volume_24,'taker_imbalance_3h':row.taker_imbalance_3h,'funding_rate':row.funding_rate,'funding_z_30':row.funding_z_30,'dgs10_chg':row.dgs10_chg,'dollar_chg':row.dollar_chg,'vix_chg':row.vix_chg,'sp500_ret':row.sp500_ret,'active_atoms':';'.join(active),'discovery80_states_fired':';'.join(fired),'long_reason':row.long_reason,'short_reason':row.short_reason})
    return pd.DataFrame(records)


def main():
    k=load_klines(); f=load_funding(); m=load_macro(); x=build_frame(k,f,m)
    df=simulate(x).replace([np.inf,-np.inf],np.nan)
    needed=['compression_6_24','breakout_pos_24','ret_4h','rel_quote_volume_24','taker_imbalance_3h','funding_rate','funding_z_30','dgs10_chg','dollar_chg','vix_chg','sp500_ret']
    df=df.dropna(subset=needed).reset_index(drop=True)
    if len(df)<5000: raise RuntimeError(f'insufficient eligible rows {len(df)}')
    split=int(len(df)*.70); A,T=atoms_and_thresholds(df,split); c=evaluate(df,A,split); c.to_csv(OUT_CSV,index=False)
    aug=august_audit(df,A,c); aug.to_csv(OUT_AUG,index=False)
    val=c[c.validated80]; cand=c[c.candidate80]
    verdict='MS1_VALIDATED_80_STATE_FOUND' if len(val) else ('MS1_80_CANDIDATE_FOUND' if len(cand) else 'NO_80_STATE_FOUND_MS1')
    top=c.head(30).replace({np.nan:None}).to_dict('records')
    result={'protocol':'BTC_MARKETSTATE_MS1','rows':len(df),'discovery_rows':split,'validation_rows':len(df)-split,'thresholds':T,'verdict':verdict,'validated80_count':int(len(val)),'candidate80_count':int(len(cand)),'validated80':val.replace({np.nan:None}).to_dict('records'),'candidate80':cand.replace({np.nan:None}).to_dict('records'),'top30':top,'aug19_20':aug.replace({np.nan:None}).to_dict('records'),'guardrail':'Frozen MS1 search only; no threshold/session/TP-SL rescue.'}
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str)+'\n')
    def pct(v): return '-' if v is None or pd.isna(v) else f'{100*v:.2f}%'
    md=['# BTC Market-State MS1 — Result','',f'**Verdict: {verdict}**','',f'Eligible hourly opportunities: **{len(df):,}** (discovery {split:,}; validation {len(df)-split:,}).','', '## 80% states','']
    if len(cand)==0: md += ['No preregistered 2–3 atom state passed the frozen 80-candidate gates.','']
    else:
        md += ['| Side | State | Disc N/WR | Val N/WR | Pooled N/WR | Val Exp | Strict 80? |','|---|---|---:|---:|---:|---:|---|']
        for _,r in cand.head(20).iterrows(): md.append(f"| {r.side} | {r.atoms} | {int(r.disc_n)} / {pct(r.disc_wr)} | {int(r.val_n)} / {pct(r.val_wr)} | {int(r.pooled_n)} / {pct(r.pooled_wr)} | {r.val_exp:.4f} | {'YES' if r.validated80 else 'NO'} |")
        md.append('')
    md += ['## Best validation-ranked states (descriptive, not automatically promotable)','', '| Side | State | Disc N/WR | Val N/WR | Pooled WR |','|---|---|---:|---:|---:|']
    for _,r in c.head(15).iterrows(): md.append(f"| {r.side} | {r.atoms} | {int(r.disc_n)} / {pct(r.disc_wr)} | {int(r.val_n)} / {pct(r.val_wr)} | {pct(r.pooled_wr)} |")
    md += ['','## 19–20 Aug 2026 archetype audit','']
    if aug.empty: md.append('No eligible August archetype row found.')
    else:
        for _,r in aug.iterrows(): md += [f"**{r.side} snapshot — feature close {r.feature_ts}, next-hour entry {r.entry_ts}**",f"- Active atoms: `{r.active_atoms}`",f"- Discovery >=80% states firing: `{r.discovery80_states_fired or 'none'}`",f"- ret4h {r.ret_4h:.4f}; compression {r.compression_6_24:.3f}; breakout-pos {r.breakout_pos_24:.3f}; taker imbalance {r.taker_imbalance_3h:.3f}; funding z {r.funding_z_30:.3f}.",f"- lagged macro: 10Y change {r.dgs10_chg:.4f}; dollar change {r.dollar_chg:.4f}; VIX change {r.vix_chg:.4f}; SP500 return {r.sp500_ret:.4f}.",'']
    md += ['## Guardrail','', 'This is historical conditional performance, not a guarantee of future win probability. MS1 rules were frozen before results; 19–20 Aug is explanatory only and cannot change thresholds. Live BBC remains untouched.']
    OUT_MD.write_text('\n'.join(md)+'\n'); print(json.dumps(result,indent=2,default=str))

if __name__=='__main__': main()
