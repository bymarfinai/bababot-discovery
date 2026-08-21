#!/usr/bin/env python3
from __future__ import annotations
import io,itertools,json,zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests
import btc_marketstate_ms1 as ms1
import ms1_funding_source as fs

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_MarketState_MS2_Positioning_Result.md'
OUT_JSON=ROOT/'BTC_MarketState_MS2_Positioning_Result.json'
OUT_CSV=ROOT/'BTC_MarketState_MS2_Positioning_Candidates.csv'
OUT_AUG=ROOT/'BTC_MarketState_MS2_Positioning_Aug19_20.csv'
START=pd.Timestamp('2024-01-01',tz='UTC'); END=pd.Timestamp('2026-08-21',tz='UTC')
TP=.015;SL=.008;HOLD=6;FEE=.0015

def load_funding():
    f=pd.concat([fs.load_archived_funding(),fs.load_recent_funding()],ignore_index=True).dropna().drop_duplicates('ts').sort_values('ts').reset_index(drop=True)
    f['funding_mean30']=f.funding_rate.rolling(30,min_periods=10).mean();f['funding_sd30']=f.funding_rate.rolling(30,min_periods=10).std();f['funding_z_30']=(f.funding_rate-f.funding_mean30)/f.funding_sd30.replace(0,np.nan)
    return f

def parse_metric_date(d):
    ds=pd.Timestamp(d).strftime('%Y-%m-%d')
    url=f'{ms1.BASE}/daily/metrics/{ms1.SYMBOL}/{ms1.SYMBOL}-metrics-{ds}.zip'
    try:
        r=requests.get(url,timeout=45,headers={'User-Agent':'bababot-discovery-ms2/1.0'})
        if r.status_code==404:return None
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
            with z.open(n) as f:df=pd.read_csv(f)
        df.columns=[str(c).strip().lower() for c in df.columns]
        tc='create_time' if 'create_time' in df.columns else ('timestamp' if 'timestamp' in df.columns else 'time')
        vals=pd.to_numeric(df[tc],errors='coerce')
        if vals.notna().mean()>.9:
            unit='us' if vals.dropna().median()>1e14 else 'ms';ts=pd.to_datetime(vals,unit=unit,utc=True)
        else:ts=pd.to_datetime(df[tc],utc=True,errors='coerce')
        def col(*names):
            for x in names:
                if x in df.columns:return pd.to_numeric(df[x],errors='coerce')
            return pd.Series(np.nan,index=df.index)
        out=pd.DataFrame({'ts':ts,'oi_value':col('sum_open_interest_value'),'global_ls':col('count_long_short_ratio'),'top_pos_ls':col('sum_toptrader_long_short_ratio'),'top_account_ls':col('count_toptrader_long_short_ratio'),'taker_ls_metric':col('sum_taker_long_short_vol_ratio')})
        return out.dropna(subset=['ts','oi_value','global_ls','top_pos_ls']).drop_duplicates('ts').sort_values('ts')
    except Exception as e:
        return ('ERR',ds,type(e).__name__,str(e)[:120])

def load_metrics():
    days=list(pd.date_range(START-pd.Timedelta(days=1),END-pd.Timedelta(days=1),freq='D'))
    frames=[];errs=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs={ex.submit(parse_metric_date,d):d for d in days}
        for f in as_completed(futs):
            z=f.result()
            if isinstance(z,tuple):errs.append(z)
            elif z is not None and len(z):frames.append(z)
    if errs:print('metric download warnings',errs[:10])
    if not frames:raise RuntimeError('no metrics')
    m=pd.concat(frames,ignore_index=True).drop_duplicates('ts').sort_values('ts').reset_index(drop=True)
    return m

def prep():
    old_start,old_end=ms1.START,ms1.END
    ms1.START,ms1.END=START,END
    try:k=ms1.load_klines()
    finally:ms1.START,ms1.END=old_start,old_end
    x=k.copy();c=x.close
    x['ret_4h']=c/c.shift(4)-1
    hi6=x.high.rolling(6).max();lo6=x.low.rolling(6).min();hi24=x.high.rolling(24).max();lo24=x.low.rolling(24).min()
    x['compression_6_24']=(hi6-lo6)/(hi24-lo24).replace(0,np.nan);x['breakout_pos_24']=(c-lo24)/(hi24-lo24).replace(0,np.nan)
    med=x.quote_volume.rolling(24,min_periods=12).median();x['rel_quote_volume_24']=x.quote_volume/med.replace(0,np.nan)
    buy=x.taker_buy_quote.rolling(3).sum();qv=x.quote_volume.rolling(3).sum();x['taker_imbalance_3h']=(2*buy-qv)/qv.replace(0,np.nan)
    f=load_funding();x=pd.merge_asof(x.sort_values('ts'),f[['ts','funding_rate','funding_z_30']].sort_values('ts'),on='ts',direction='backward')
    m=load_metrics().sort_values('ts').reset_index(drop=True)
    m['top_vs_global']=m.top_pos_ls/m.global_ls-1
    for lag,name in [(12,'1h'),(48,'4h')]:
        m[f'oi_value_chg_{name}']=m.oi_value/m.oi_value.shift(lag)-1
    m['global_ls_chg_1h']=m.global_ls/m.global_ls.shift(12)-1;m['top_pos_ls_chg_1h']=m.top_pos_ls/m.top_pos_ls.shift(12)-1
    cols=['ts','oi_value_chg_1h','oi_value_chg_4h','global_ls','global_ls_chg_1h','top_pos_ls','top_pos_ls_chg_1h','top_account_ls','top_vs_global','taker_ls_metric']
    x=pd.merge_asof(x.sort_values('ts'),m[cols].sort_values('ts'),on='ts',direction='backward',tolerance=pd.Timedelta(minutes=15))
    return x

def simulate(x):
    rows=[]
    for i in range(24,len(x)-HOLD-1):
        t=x.iloc[i];entry=float(x.iloc[i+1].open);fut=x.iloc[i+1:i+1+HOLD]
        def ev(side):
            tp=entry*(1+TP) if side=='LONG' else entry*(1-TP);sl=entry*(1-SL) if side=='LONG' else entry*(1+SL);reason='TIME';gross=float((fut.iloc[-1].close/entry-1)*(1 if side=='LONG' else -1))
            for _,b in fut.iterrows():
                hs=(b.low<=sl) if side=='LONG' else (b.high>=sl);ht=(b.high>=tp) if side=='LONG' else (b.low<=tp)
                if hs:reason='SL';gross=-SL;break
                if ht:reason='TP';gross=TP;break
            return reason,gross-FEE
        lr,lp=ev('LONG');sr,sp=ev('SHORT');d=t.to_dict();d.update({'entry_ts':x.iloc[i+1].ts,'entry':entry,'long_reason':lr,'long_win':lr=='TP','long_pnl':lp,'short_reason':sr,'short_win':sr=='TP','short_pnl':sp});rows.append(d)
    return pd.DataFrame(rows)

def q(d,c,p):return float(pd.to_numeric(d[c],errors='coerce').dropna().quantile(p))
def atoms(df,split):
    d=df.iloc[:split];T={}
    specs={'comp':('compression_6_24',.30),'oi1l':('oi_value_chg_1h',.30),'oi1h':('oi_value_chg_1h',.70),'oi4l':('oi_value_chg_4h',.30),'oi4h':('oi_value_chg_4h',.70),'glob_l':('global_ls',.30),'glob_h':('global_ls',.70),'top_l':('top_pos_ls',.30),'top_h':('top_pos_ls',.70),'tvg_l':('top_vs_global',.30),'tvg_h':('top_vs_global',.70),'gchg_l':('global_ls_chg_1h',.30),'gchg_h':('global_ls_chg_1h',.70),'tchg_l':('top_pos_ls_chg_1h',.30),'tchg_h':('top_pos_ls_chg_1h',.70),'flow_l':('taker_imbalance_3h',.30),'flow_h':('taker_imbalance_3h',.70),'mt_l':('taker_ls_metric',.30),'mt_h':('taker_ls_metric',.70),'br_l':('breakout_pos_24',.20),'br_h':('breakout_pos_24',.80),'vol_h':('rel_quote_volume_24',.70),'fund_l':('funding_z_30',.30),'fund_h':('funding_z_30',.70)}
    for n,(c,p) in specs.items():T[n]=q(d,c,p)
    A={'LONG':{},'SHORT':{}}
    A['LONG']={'COMPRESSED':df.compression_6_24<=T['comp'],'OI_BUILD_1H':df.oi_value_chg_1h>=T['oi1h'],'OI_BUILD_4H':df.oi_value_chg_4h>=T['oi4h'],'GLOBAL_SHORT':df.global_ls<=T['glob_l'],'TOP_SHORT':df.top_pos_ls<=T['top_l'],'TOP_MORE_SHORT':df.top_vs_global<=T['tvg_l'],'GLOBAL_SHORTING':df.global_ls_chg_1h<=T['gchg_l'],'TOP_SHORTING':df.top_pos_ls_chg_1h<=T['tchg_l'],'AGG_BUY':df.taker_imbalance_3h>=T['flow_h'],'METRIC_BUY':df.taker_ls_metric>=T['mt_h'],'HIGH_BREAKOUT_POS':df.breakout_pos_24>=T['br_h'],'HIGH_VOLUME':df.rel_quote_volume_24>=T['vol_h'],'LOW_FUNDING':df.funding_z_30<=T['fund_l']}
    A['SHORT']={'COMPRESSED':df.compression_6_24<=T['comp'],'OI_BUILD_1H':df.oi_value_chg_1h>=T['oi1h'],'OI_BUILD_4H':df.oi_value_chg_4h>=T['oi4h'],'GLOBAL_LONG':df.global_ls>=T['glob_h'],'TOP_LONG':df.top_pos_ls>=T['top_h'],'TOP_MORE_LONG':df.top_vs_global>=T['tvg_h'],'GLOBAL_LONGING':df.global_ls_chg_1h>=T['gchg_h'],'TOP_LONGING':df.top_pos_ls_chg_1h>=T['tchg_h'],'AGG_SELL':df.taker_imbalance_3h<=T['flow_l'],'METRIC_SELL':df.taker_ls_metric<=T['mt_l'],'LOW_BREAKOUT_POS':df.breakout_pos_24<=T['br_l'],'HIGH_VOLUME':df.rel_quote_volume_24>=T['vol_h'],'HIGH_FUNDING':df.funding_z_30>=T['fund_h']}
    return A,T

def st(z,side):
    n=len(z);w=int(z[f'{side.lower()}_win'].sum()) if n else 0;p=float(z[f'{side.lower()}_pnl'].sum()) if n else 0
    return n,w,w/n if n else None,p/n if n else None

def evaluate(df,A,split):
    out=[]
    for side in ['LONG','SHORT']:
        names=list(A[side])
        for kk in [3,4]:
            for combo in itertools.combinations(names,kk):
                mask=pd.Series(True,index=df.index)
                for a in combo:mask&=A[side][a].fillna(False)
                dz=df.iloc[:split][mask.iloc[:split]];vz=df.iloc[split:][mask.iloc[split:]];pz=df[mask]
                dn,dw,dwr,dexp=st(dz,side);vn,vw,vwr,vexp=st(vz,side);pn,pw,pwr,pexp=st(pz,side)
                pos=np.flatnonzero(mask.iloc[split:].values);qcov=len(set(np.minimum(3,(pos*4/max(1,len(df)-split)).astype(int)).tolist())) if len(pos) else 0
                cand=bool(dn>=40 and dwr>=.8 and vn>=15 and vwr>=.75 and pwr>=.8 and dexp>0 and vexp>0 and qcov>=3);val=bool(cand and vwr>=.8)
                out.append({'side':side,'atoms':' + '.join(combo),'k':kk,'disc_n':dn,'disc_wr':dwr,'disc_exp':dexp,'val_n':vn,'val_wr':vwr,'val_exp':vexp,'pooled_n':pn,'pooled_wr':pwr,'pooled_exp':pexp,'val_quartiles':qcov,'candidate80':cand,'validated80':val})
    return pd.DataFrame(out).sort_values(['validated80','candidate80','val_wr','val_n'],ascending=[False,False,False,False])

def august(df,A,c):
    z=df[(df.entry_ts>=pd.Timestamp('2026-08-19',tz='UTC'))&(df.entry_ts<pd.Timestamp('2026-08-21',tz='UTC'))].copy()
    if z.empty:return pd.DataFrame()
    z['f6']=z.close.shift(-6)/z.close-1;idx=z.f6.idxmax() if z.f6.notna().any() else z.index[0];r=df.loc[idx];rows=[]
    for side in ['LONG','SHORT']:
        active=[n for n,s in A[side].items() if bool(s.loc[idx])];fired=[]
        for _,x in c[(c.side==side)&(c.disc_n>=40)&(c.disc_wr>=.8)].iterrows():
            req=x.atoms.split(' + ')
            if all(a in active for a in req):fired.append(x.atoms)
        rows.append({'side':side,'feature_ts':r.ts,'entry_ts':r.entry_ts,'active_atoms':';'.join(active),'discovery80_states_fired':';'.join(fired),'oi_value_chg_1h':r.oi_value_chg_1h,'oi_value_chg_4h':r.oi_value_chg_4h,'global_ls':r.global_ls,'top_pos_ls':r.top_pos_ls,'top_vs_global':r.top_vs_global,'global_ls_chg_1h':r.global_ls_chg_1h,'top_pos_ls_chg_1h':r.top_pos_ls_chg_1h,'taker_ls_metric':r.taker_ls_metric,'taker_imbalance_3h':r.taker_imbalance_3h,'compression_6_24':r.compression_6_24,'breakout_pos_24':r.breakout_pos_24,'funding_z_30':r.funding_z_30,'long_reason':r.long_reason,'short_reason':r.short_reason})
    return pd.DataFrame(rows)

def main():
    x=prep();df=simulate(x).replace([np.inf,-np.inf],np.nan)
    need=['compression_6_24','oi_value_chg_1h','oi_value_chg_4h','global_ls','global_ls_chg_1h','top_pos_ls','top_pos_ls_chg_1h','top_vs_global','taker_imbalance_3h','taker_ls_metric','breakout_pos_24','rel_quote_volume_24','funding_z_30']
    df=df.dropna(subset=need).reset_index(drop=True)
    if len(df)<10000:raise RuntimeError(f'insufficient rows {len(df)}')
    split=int(len(df)*.7);A,T=atoms(df,split);c=evaluate(df,A,split);c.to_csv(OUT_CSV,index=False);aug=august(df,A,c);aug.to_csv(OUT_AUG,index=False)
    val=c[c.validated80];cand=c[c.candidate80];verdict='MS2_VALIDATED_80' if len(val) else ('MS2_80_CANDIDATE' if len(cand) else 'NO_80_POSITIONING_STATE_MS2')
    out={'protocol':'BTC_MARKETSTATE_MS2_POSITIONING','rows':len(df),'split':split,'thresholds':T,'verdict':verdict,'validated80':val.replace({np.nan:None}).to_dict('records'),'candidate80':cand.replace({np.nan:None}).to_dict('records'),'top30':c.head(30).replace({np.nan:None}).to_dict('records'),'aug19_20':aug.replace({np.nan:None}).to_dict('records')};OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    def p(v):return '-' if v is None or pd.isna(v) else f'{100*v:.2f}%'
    md=['# BTC Market-State MS2 Positioning — Result','',f'**Verdict: {verdict}**','',f'Eligible opportunities: **{len(df):,}**; discovery {split:,}; validation {len(df)-split:,}.','']
    if len(cand):
        md+=['## 80% candidates','','|Side|State|Disc N/WR|Val N/WR|Pooled N/WR|Strict 80?|','|---|---|---:|---:|---:|---|']
        for _,r in cand.head(20).iterrows():md.append(f"|{r.side}|{r.atoms}|{int(r.disc_n)} / {p(r.disc_wr)}|{int(r.val_n)} / {p(r.val_wr)}|{int(r.pooled_n)} / {p(r.pooled_wr)}|{'YES' if r.validated80 else 'NO'}|")
    else:md+=['No preregistered positioning state passed the 80-candidate gates.','']
    md+=['','## Best validation-ranked states','','|Side|State|Disc N/WR|Val N/WR|Pooled WR|','|---|---|---:|---:|---:|']
    for _,r in c.head(15).iterrows():md.append(f"|{r.side}|{r.atoms}|{int(r.disc_n)} / {p(r.disc_wr)}|{int(r.val_n)} / {p(r.val_wr)}|{p(r.pooled_wr)}|")
    md+=['','## 19–20 Aug positioning snapshot','']
    for _,r in aug.iterrows():md += [f"**{r.side} — {r.feature_ts} -> entry {r.entry_ts}**",f"- active: `{r.active_atoms}`",f"- discovery >=80 states firing: `{r.discovery80_states_fired or 'none'}`",f"- OI 1h {r.oi_value_chg_1h:.4f}, OI 4h {r.oi_value_chg_4h:.4f}, global LS {r.global_ls:.3f}, top-pos LS {r.top_pos_ls:.3f}, top-vs-global {r.top_vs_global:.3f}.",f"- global LS 1h {r.global_ls_chg_1h:.4f}, top-pos LS 1h {r.top_pos_ls_chg_1h:.4f}, metric taker LS {r.taker_ls_metric:.3f}, kline taker imbalance {r.taker_imbalance_3h:.3f}.",'']
    md+=['Live BBC untouched. No MS2 threshold/session/TP-SL rescue is authorized.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
