#!/usr/bin/env python3
"""SUN1.2 — Sunday max-hold/exit geometry + all-hour executable surface.

Research only; live BBC untouched.

Two predeclared tracks:
A) Sunday 01:00 WIB BUY: sweep max hold x TP/SL to test whether the A1 4h
   close-direction edge can be converted into positive executable expectancy.
B) All 24 Sunday clock-hours: discovery-only selection of direction (BUY/SELL),
   max hold, TP and SL; validation is reported only after discovery ranking.

Causal/executable assumptions:
- Entry = exact clock-hour 5m open.
- Same 5m TP+SL ambiguity = adverse-first.
- $500 notional ($10 margin x50), 0.15% round-trip fee.
- Historical funding charged/credited for positions spanning settlements.
- Discovery first 83 Sundays, validation last 56; validation never selects a cell.
"""
from __future__ import annotations

import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50

OUT=Path(os.getenv('SUN12_OUT','sun12_out')); OUT.mkdir(parents=True,exist_ok=True)
NOTIONAL=500.0
FEE=0.0015*NOTIONAL
START=pd.Timestamp('2023-12-02',tz='UTC')
END=pd.Timestamp('2026-07-30',tz='UTC')
DISC_N=83
TP_GRID=np.round(np.arange(0.3,2.5001,0.1),1)
SL_GRID=np.round(np.arange(0.3,1.5001,0.1),1)
HOLDS_H=[1,2,4,6,8,12,18]
MAX_BARS=max(HOLDS_H)*12
INF=10_000


def metrics(x):
    a=np.asarray(x,float); wins=int((a>0).sum()); losses=int((a<=0).sum())
    gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float(np.max(peak[1:]-eq)) if len(eq) else 0.0
    return {'n':len(a),'wins':wins,'losses':losses,'wr':wins/len(a) if len(a) else np.nan,
            'pnl':float(a.sum()),'pf':gp/gl if gl>0 else (999.0 if gp>0 else 0.0),
            'dd':dd,'expectancy':float(a.mean()) if len(a) else np.nan}


def block_pnls(x,nblocks):
    a=np.asarray(x,float); return [float(z.sum()) for z in np.array_split(a,nblocks)]


def entries_for_hour(k,hour_wib):
    idx=k.index
    local=idx+pd.Timedelta(hours=7)
    mask=(idx>=START)&(idx<END)&(local.dayofweek==6)&(local.hour==hour_wib)&(local.minute==0)
    return list(idx[mask])


def funding_map(k,f):
    mp={}
    for r in f.itertuples(index=False):
        t=pd.Timestamp(r.ts)
        if t in k.index:
            px=float(k.loc[t,'open'])
            mp[t]=(float(r.rate),px)
    return mp


def prepare_hour(k,fmap,hour):
    entries=entries_for_hour(k,hour)
    if len(entries)!=139:
        raise RuntimeError(f'hour {hour} entry parity {len(entries)}')
    n=len(entries); highs=np.empty((n,MAX_BARS)); lows=np.empty_like(highs); closes=np.empty_like(highs)
    entry_px=np.empty(n); fund_cum=np.zeros((n,MAX_BARS))
    for i,t in enumerate(entries):
        bars=k[(k.index>=t)&(k.index<t+pd.Timedelta(hours=max(HOLDS_H)))].iloc[:MAX_BARS]
        if len(bars)!=MAX_BARS: raise RuntimeError(f'incomplete path {hour} {t} {len(bars)}')
        ep=float(k.loc[t,'open']); entry_px[i]=ep
        highs[i,:]=bars.high.to_numpy(float); lows[i,:]=bars.low.to_numpy(float); closes[i,:]=bars.close.to_numpy(float)
        fc=0.0
        for j,bt in enumerate(bars.index):
            # Settlement at bar open is paid if position is still alive entering this bar.
            if bt>t and bt in fmap:
                rate,px=fmap[bt]; fc += (NOTIONAL/ep)*px*rate
            fund_cum[i,j]=fc
    return entries,entry_px,highs,lows,closes,fund_cum


def first_idx(cond):
    anyhit=cond.any(axis=1); idx=cond.argmax(axis=1)
    return np.where(anyhit,idx,INF).astype(int)


def precompute_indices(entry,highs,lows,direction):
    n=len(entry)
    fav=np.empty((n,len(TP_GRID)),int); adv=np.empty((n,len(SL_GRID)),int)
    for j,tp in enumerate(TP_GRID):
        p=tp/100.0
        cond=(highs>=entry[:,None]*(1+p)) if direction==1 else (lows<=entry[:,None]*(1-p))
        fav[:,j]=first_idx(cond)
    for j,sl in enumerate(SL_GRID):
        p=sl/100.0
        cond=(lows<=entry[:,None]*(1-p)) if direction==1 else (highs>=entry[:,None]*(1+p))
        adv[:,j]=first_idx(cond)
    return fav,adv


def outcome(entry,closes,fund,fav_col,adv_col,tp,sl,hold_h,direction):
    hb=hold_h*12; timeout_idx=hb-1
    fi=np.where(fav_col<hb,fav_col,INF); ai=np.where(adv_col<hb,adv_col,INF)
    # adverse-first on equal 5m bar
    is_sl=(ai<=fi)&(ai<INF); is_tp=(fi<ai)&(fi<INF)
    ex_idx=np.where(is_sl,ai,np.where(is_tp,fi,timeout_idx)).astype(int)
    gross=np.empty(len(entry),float)
    gross[is_tp]=tp/100.0
    gross[is_sl]=-sl/100.0
    rem=~(is_tp|is_sl)
    gross[rem]=direction*(closes[rem,timeout_idx]/entry[rem]-1.0)
    fc=fund[np.arange(len(entry)),ex_idx]
    pnl=NOTIONAL*gross-FEE-direction*fc
    return pnl,is_tp,is_sl,rem


def evaluate_hour(hour,entry,highs,lows,closes,fund):
    rows=[]
    for direction in (1,-1):
        fav,adv=precompute_indices(entry,highs,lows,direction)
        for hh in HOLDS_H:
            for it,tp in enumerate(TP_GRID):
                for js,sl in enumerate(SL_GRID):
                    pnl,tp_mask,sl_mask,to_mask=outcome(entry,closes,fund,fav[:,it],adv[:,js],tp,sl,hh,direction)
                    d=pnl[:DISC_N]; v=pnl[DISC_N:]
                    dm=metrics(d); vm=metrics(v); fm=metrics(pnl)
                    db=block_pnls(d,5); fb=block_pnls(pnl,8)
                    rows.append({
                        'hour_wib':hour,'direction':'BUY' if direction==1 else 'SELL','direction_i':direction,
                        'hold_h':hh,'tp_pct':float(tp),'sl_pct':float(sl),'rr':float(tp/sl),
                        'D_pnl':dm['pnl'],'D_wr':dm['wr'],'D_pf':dm['pf'],'D_dd':dm['dd'],'D_exp':dm['expectancy'],'D_pos_blocks':sum(x>0 for x in db),
                        'V_pnl':vm['pnl'],'V_wr':vm['wr'],'V_pf':vm['pf'],'V_dd':vm['dd'],'V_exp':vm['expectancy'],
                        'full_pnl':fm['pnl'],'full_wr':fm['wr'],'full_pf':fm['pf'],'full_dd':fm['dd'],'full_exp':fm['expectancy'],'full_pos_blocks':sum(x>0 for x in fb),
                        'tp_n':int(tp_mask.sum()),'sl_n':int(sl_mask.sum()),'timeout_n':int(to_mask.sum())
                    })
    return rows


def pack(r):
    keys=['hour_wib','direction','hold_h','tp_pct','sl_pct','rr','D_pnl','D_wr','D_pf','D_dd','D_exp','D_pos_blocks',
          'V_pnl','V_wr','V_pf','V_dd','V_exp','full_pnl','full_wr','full_pf','full_dd','full_exp','full_pos_blocks','tp_n','sl_n','timeout_n']
    out={}
    for k in keys:
        v=r[k]
        if isinstance(v,(np.integer,)): v=int(v)
        elif isinstance(v,(np.floating,)): v=float(v)
        out[k]=v
    return out


def main():
    k=f517.load_klines(); f=s50.load_funding(); fmap=funding_map(k,f)
    allrows=[]
    for hour in range(24):
        entries,entry,highs,lows,closes,fund=prepare_hour(k,fmap,hour)
        allrows.extend(evaluate_hour(hour,entry,highs,lows,closes,fund))
        print(f'hour {hour:02d} complete',flush=True)
    df=pd.DataFrame(allrows)
    df['D_robust']=(df.D_pnl>0)&(df.D_pf>1.10)&(df.D_pos_blocks>=4)
    df['V_pass']=(df.V_pnl>0)&(df.V_pf>1.0)
    df.to_csv(OUT/'sun12_all_surface.csv',index=False)

    # Track A: Sunday 01:00 BUY only. Select from discovery only.
    s01=df[(df.hour_wib==1)&(df.direction=='BUY')].copy()
    elig01=s01[s01.D_robust].sort_values(['D_pnl','D_pf','D_wr'],ascending=False)
    raw01=s01.sort_values(['D_pnl','D_pf'],ascending=False).iloc[0]
    best01=(elig01.iloc[0] if len(elig01) else raw01)
    # Best cell per hold for anatomy; selected solely by D PnL within each hold.
    hold01=[]
    for hh in HOLDS_H:
        z=s01[s01.hold_h==hh].sort_values(['D_pnl','D_pf'],ascending=False).iloc[0]
        hold01.append(pack(z))

    # Track B: all hours/directions. Discovery-only robust champion.
    robust=df[df.D_robust].sort_values(['D_pnl','D_pf','D_wr'],ascending=False)
    rawall=df.sort_values(['D_pnl','D_pf'],ascending=False)
    champion=(robust.iloc[0] if len(robust) else rawall.iloc[0])

    # One discovery-selected candidate per hour to avoid one hour flooding the leaderboard.
    perhour=[]
    for hour in range(24):
        z=df[df.hour_wib==hour]
        rz=z[z.D_robust].sort_values(['D_pnl','D_pf','D_wr'],ascending=False)
        pick=(rz.iloc[0] if len(rz) else z.sort_values(['D_pnl','D_pf'],ascending=False).iloc[0])
        q=pack(pick); q['D_robust']=bool(pick.D_robust); q['V_pass']=bool(pick.V_pass); perhour.append(q)
    perhour_sorted=sorted(perhour,key=lambda x:(x['D_robust'],x['D_pnl'],x['D_pf']),reverse=True)

    # Discovery top-20 robust cells; validation shown but never used to reorder/select.
    top20=[{**pack(r),'V_pass':bool(r.V_pass)} for _,r in robust.head(20).iterrows()]
    robust_vpass=int((robust.V_pass).sum()) if len(robust) else 0

    out={
      'status':'COMPLETE_DISCOVERY_SELECTION_VALIDATION_REPORT','definition':{
        'day':'Sunday WIB','hours':list(range(24)),'directions_allhour':['BUY','SELL'],'track01_direction':'BUY',
        'holds_h':HOLDS_H,'tp_grid_pct':[0.3,2.5,0.1],'sl_grid_pct':[0.3,1.5,0.1],
        'discovery_n':83,'validation_n':56,'notional':500,'fee_rt_pct':0.15,'funding':'historical exact settlements','ambiguity':'adverse-first'},
      'surface_cells':int(len(df)),'D_robust_cells':int(df.D_robust.sum()),'D_robust_validation_pass_cells':robust_vpass,
      'sunday01_buy':{
        'D_robust_cells':int(s01.D_robust.sum()),'selected':pack(best01),'selection_is_robust':bool(best01.D_robust),
        'raw_D_champion':pack(raw01),'best_by_hold_discovery_only':hold01},
      'allhour_discovery_champion':{**pack(champion),'D_robust':bool(champion.D_robust),'V_pass':bool(champion.V_pass)},
      'per_hour_discovery_selected':perhour_sorted,
      'top20_discovery_robust_cells':top20,
      'guardrail':'All parameter/direction/hour selections use discovery only. Validation is reported after selection and must not be used to retune the chosen cell on this same sample.'}
    (OUT/'sun12_summary.json').write_text(json.dumps(out,indent=2,default=str))

    s=out['sunday01_buy']['selected']; c=out['allhour_discovery_champion']
    md=['# BTC Sunday — SUN1.2 Hold/Exit + All-Hour Executable Surface','',
        '**Status: COMPLETE — discovery-only selection, validation reported; live BBC untouched.**','',
        '## Definition',
        '- 139 Sundays; discovery 83 / validation 56.',
        '- Holds: 1h, 2h, 4h, 6h, 8h, 12h, 18h.',
        '- TP 0.3–2.5% step 0.1; SL 0.3–1.5% step 0.1.',
        '- $500 notional, 0.15% round-trip fee, historical funding, adverse-first same-5m ambiguity.','',
        '## Sunday 01:00 WIB BUY — hold/exit search',
        f"- discovery robust cells: **{int(s01.D_robust.sum())}**",
        f"- selected: **hold {int(s['hold_h'])}h / TP {s['tp_pct']:.1f}% / SL {s['sl_pct']:.1f}%**",
        f"- D: **${s['D_pnl']:+.3f}**, WR **{100*s['D_wr']:.2f}%**, PF **{s['D_pf']:.3f}**, DD **${s['D_dd']:.3f}**, blocks **{int(s['D_pos_blocks'])}/5**",
        f"- V: **${s['V_pnl']:+.3f}**, WR **{100*s['V_wr']:.2f}%**, PF **{s['V_pf']:.3f}**",
        f"- Full: **${s['full_pnl']:+.3f}**, WR **{100*s['full_wr']:.2f}%**, PF **{s['full_pf']:.3f}**, DD **${s['full_dd']:.3f}**",'',
        '### Best discovery cell by hold']
    for r in hold01:
        md.append(f"- {int(r['hold_h'])}h: TP {r['tp_pct']:.1f}/SL {r['sl_pct']:.1f} → D {r['D_pnl']:+.2f}, WR {100*r['D_wr']:.1f}%, PF {r['D_pf']:.2f}; V {r['V_pnl']:+.2f}")
    md += ['', '## All Sunday hours — discovery champion',
        f"- **{int(c['hour_wib']):02d}:00 WIB {c['direction']} / hold {int(c['hold_h'])}h / TP {c['tp_pct']:.1f}% / SL {c['sl_pct']:.1f}%**",
        f"- D: **${c['D_pnl']:+.3f}**, WR **{100*c['D_wr']:.2f}%**, PF **{c['D_pf']:.3f}**, blocks **{int(c['D_pos_blocks'])}/5**",
        f"- V: **${c['V_pnl']:+.3f}**, WR **{100*c['V_wr']:.2f}%**, PF **{c['V_pf']:.3f}**",
        f"- Full: **${c['full_pnl']:+.3f}**, WR **{100*c['full_wr']:.2f}%**, PF **{c['full_pf']:.3f}**, DD **${c['full_dd']:.3f}**",'',
        f"- total discovery-robust cells: **{int(df.D_robust.sum())}**; of those validation-positive/PF>1: **{robust_vpass}**",'',
        '## Best discovery-selected candidate per Sunday hour']
    for r in perhour_sorted:
        md.append(f"- {int(r['hour_wib']):02d}:00 {r['direction']} {int(r['hold_h'])}h TP{r['tp_pct']:.1f}/SL{r['sl_pct']:.1f}: D {r['D_pnl']:+.1f}, WR {100*r['D_wr']:.1f}%, PF {r['D_pf']:.2f}, blocks {int(r['D_pos_blocks'])}/5; V {r['V_pnl']:+.1f}, PF {r['V_pf']:.2f} — Drobust={r['D_robust']} Vpass={r['V_pass']}")
    md += ['', '## Guardrail','All selections above are based on discovery only. Validation is a test, not a tuning input.']
    (OUT/'SUN1.2_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
