#!/usr/bin/env python3
"""C3: BTC Friday 15m multi-candle sequence + local range context."""
from __future__ import annotations
import json,math
from pathlib import Path
import numpy as np
import pandas as pd
import btc_friday_all15m_candle_c1 as c1

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_15m_Sequence_C3_Result.md';OUT_JSON=ROOT/'BTC_Friday_15m_Sequence_C3_Result.json';OUT_ROWS=ROOT/'BTC_Friday_15m_Sequence_C3_Rows.csv';OUT_DISC=ROOT/'BTC_Friday_15m_Sequence_C3_Discovery_Archetypes.csv'

def sequence_key(df,i):
    if i<4:return None
    r=df.iloc[i];p=df.iloc[i-1]
    so,sc=float(r.open),float(r.close);po,pc=float(p.open),float(p.close)
    if so==sc or po==pc:return None
    scol='G' if sc>so else 'R';pcol='G' if pc>po else 'R';two=pcol+scol
    b,u,l,cp,ro=c1.geom(so,float(r.high),float(r.low),sc)
    bb='SMALL' if b<=1/3 else ('LARGE' if b>=2/3 else 'MEDIUM')
    dom='UPPER' if u>l and u>b else ('LOWER' if l>u and l>b else 'BODY_BALANCED')
    prs=[]
    for j in range(i-3,i):
        q=df.iloc[j];*_,qr=c1.geom(float(q.open),float(q.high),float(q.low),float(q.close));prs.append(qr)
    rs='EXPANDED' if ro>float(np.median(prs)) else 'NORMAL'
    prior4=df.iloc[i-4:i];base_open=float(prior4.iloc[0].open);last_close=float(prior4.iloc[-1].close)
    trend='UP' if last_close>base_open else ('DOWN' if last_close<base_open else 'FLAT')
    prev_hi=float(prior4.high.max());prev_lo=float(prior4.low.min())
    loc='BREAK_HIGH' if sc>prev_hi else ('BREAK_LOW' if sc<prev_lo else 'INSIDE')
    if trend=='FLAT':rel='FLAT'
    else:rel='WITH' if ((scol=='G')==(trend=='UP')) else 'AGAINST'
    key='|'.join([two,bb,dom,rs,trend,loc,rel])
    return {'archetype':key,'two_color':two,'signal_body':bb,'signal_dominance':dom,'range_state':rs,'prior4_trend':trend,'range_location':loc,'trend_relation':rel,'signal_color':scol}

def build(df):
    rows=[]
    for i in range(4,len(df)-c1.HOLD_BARS-1):
        r=df.iloc[i];wib=r.ts+pd.Timedelta(hours=7)
        if wib.weekday()!=4:continue
        a=sequence_key(df,i)
        if a is None:continue
        side=1 if a['signal_color']=='G' else -1;cont=c1.trade(df,i,side);rev=c1.trade(df,i,-side)
        if not cont or not rev:continue
        rows.append({'signal_ts':str(r.ts),'friday_wib':str(wib.date()),'entry_ts':str(df.iloc[i+1].ts),**a,'cont_pnl':cont['pnl'],'cont_win':cont['win'],'cont_reason':cont['reason'],'rev_pnl':rev['pnl'],'rev_win':rev['win'],'rev_reason':rev['reason']})
    return pd.DataFrame(rows)
def blocks(df,mode,key):
    dates=sorted(df.friday_wib.unique());out={}
    for i,ch in enumerate(np.array_split(np.array(dates,dtype=object),4)):out[f'B{i+1}']=c1.stats(df[df.friday_wib.isin(set(ch))&(df.archetype==key)],f'{mode}_pnl')
    return out

def main():
    px=c1.load_15m();df=build(px);dates=sorted(df.friday_wib.unique());cut=int(math.floor(.70*len(dates)));dd=set(dates[:cut]);vd=set(dates[cut:]);df['period']=np.where(df.friday_wib.isin(dd),'discovery','validation');disc=df[df.period=='discovery'];val=df[df.period=='validation']
    baseline={m:{'discovery':c1.stats(disc,f'{m}_pnl'),'validation':c1.stats(val,f'{m}_pnl'),'full':c1.stats(df,f'{m}_pnl')} for m in ('cont','rev')};reports=[];eligible=[]
    for mode in ('cont','rev'):
        for key,z in disc.groupby('archetype'):
            s=c1.stats(z,f'{mode}_pnl');q={'mode':mode,'archetype':key,**s};reports.append(q)
            if s['n']>=30 and s['wr'] is not None and s['wr']>=.80 and s['pnl']>0 and s['pf'] is not None and s['pf']>1:eligible.append(q)
    pd.DataFrame(reports).to_csv(OUT_DISC,index=False);eligible.sort(key=lambda q:(-q['wr'],-q['n'],-q['pf'],q['mode'],q['archetype']))
    out={'protocol':'C3','friday_dates':len(dates),'discovery_dates':len(dd),'validation_dates':len(vd),'signal_rows':len(df),'discovery_archetypes':len(set(disc.archetype)),'discovery_eligible_80':len(eligible),'baseline':baseline,'top_discovery_support30':{}}
    for mode in ('cont','rev'):
        top=[q for q in reports if q['mode']==mode and q['n']>=30];top.sort(key=lambda q:(-q['wr'],-q['n'],q['archetype']));out['top_discovery_support30'][mode]=top[:12]
    if not eligible:out.update({'selected':None,'verdict':'REJECT_C3_80_SEQUENCE_IDENTIFIER','reason':'No frozen 15m sequence/context archetype achieved discovery N>=30 and WR>=80%.'})
    else:
        q=eligible[0];m=q['mode'];k=q['archetype'];sd=c1.stats(disc[disc.archetype==k],f'{m}_pnl');sv=c1.stats(val[val.archetype==k],f'{m}_pnl');sf=c1.stats(df[df.archetype==k],f'{m}_pnl');bl=blocks(df,m,k);pos=sum(z['n']>0 and z['pnl']>0 for z in bl.values())
        ok=sd['n']>=30 and sd['wr']>=.80 and sv['n']>=15 and sv['wr'] is not None and sv['wr']>=.80 and sf['n']>=55 and sf['wr'] is not None and sf['wr']>=.80 and sv['exp'] is not None and sv['exp']>0 and sv['pf'] is not None and sv['pf']>1 and sv['wr']>baseline[m]['validation']['wr'] and pos>=3
        out['selected']={'mode':m,'archetype':k,'discovery':sd,'validation':sv,'full':sf,'blocks':bl,'positive_blocks':pos};out['verdict']='BTC_FRIDAY_15M_SEQUENCE_80_CANDIDATE' if ok else 'REJECT_C3_80_SEQUENCE_IDENTIFIER'
    df.to_csv(OUT_ROWS,index=False);OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n');F=lambda v,d=2:'-' if v is None else f'{v:.{d}f}';md=['# BTC Friday 15m Sequence + Context C3 — Result','',f"Friday dates **{len(dates)}**, signal rows **{len(df)}**, discovery archetypes **{out['discovery_archetypes']}**",f"Discovery archetypes passing 80% screen: **{len(eligible)}**",'']
    for mode in ('cont','rev'):
        md += [f'## {mode.upper()} best discovery archetypes N>=30','', '| Archetype | N | Wins | WR | PnL | PF |','|---|---:|---:|---:|---:|---:|']
        for q in out['top_discovery_support30'][mode]:md.append(f"| `{q['archetype']}` | {q['n']} | {q['wins']} | {F(100*q['wr'])}% | ${F(q['pnl'])} | {F(q['pf'],3)} |")
        md.append('')
    if out.get('selected') is None:md += ['## Verdict','',f"**{out['verdict']}**",'',out['reason']]
    else:
        s=out['selected'];md += ['## Selected sequence','',f"Mode **{s['mode'].upper()}**",f"`{s['archetype']}`",'', '| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
        for name,z in [('Discovery',s['discovery']),('Validation',s['validation']),('Full',s['full'])]:md.append(f"| {name} | {z['n']} | {z['wins']} | {F(100*z['wr'])}% | ${F(z['pnl'])} | ${F(z['exp'],3)} | {F(z['pf'],3)} |")
        md += ['','## Verdict','',f"**{out['verdict']}**"]
    md += ['','Observed historical WR is not a guaranteed future probability. No post-result key simplification or runner-up validation.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
