#!/usr/bin/env python3
"""SUN1.4 — Sunday 09:00 SELL -> reverse BUY after +0.4% short TP.

Research only; live BBC untouched.

Frozen first leg from SUN1.3:
- Sunday 09:00 WIB SELL
- TP 0.4%, SL 1.5%, max hold 18h
- $500 notional, 0.15% round-trip fee, historical funding
- adverse-first same-5m ambiguity

Reverse rule:
- Only when the first leg exits by TP 0.4%.
- Reverse BUY enters at the NEXT 5m candle open after the TP-touch bar.
  This avoids assuming an executable reversal at an intrabar wick price.
- Reverse BUY TP/SL and max-hold are swept on discovery only.
- Validation is reported after discovery selection and never used to tune.
"""
from __future__ import annotations

import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50

OUT = Path(os.getenv('SUN14_OUT','sun14_out')); OUT.mkdir(parents=True, exist_ok=True)
NOTIONAL = 500.0
FEE = 0.0015 * NOTIONAL
START = pd.Timestamp('2023-12-02', tz='UTC')
END = pd.Timestamp('2026-07-30', tz='UTC')
DISC_N = 83
FIRST_TP = 0.004
FIRST_SL = 0.015
FIRST_HOLD_H = 18
REV_TP_GRID = np.round(np.arange(0.3, 2.5001, 0.1), 1)
REV_SL_GRID = np.round(np.arange(0.3, 1.5001, 0.1), 1)
REV_HOLDS_H = [1,2,4,6,8,12]


def metrics(x):
    a=np.asarray(x,float)
    if len(a)==0: return {'n':0,'wins':0,'wr':np.nan,'pnl':0.0,'pf':np.nan,'dd':0.0,'exp':np.nan}
    wins=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    eq=np.cumsum(a); peaks=np.maximum.accumulate(np.r_[0.0,eq]); dd=float(np.max(peaks[1:]-eq))
    return {'n':len(a),'wins':wins,'wr':wins/len(a),'pnl':float(a.sum()),'pf':gp/gl if gl>0 else 999.0,'dd':dd,'exp':float(a.mean())}


def entries(k):
    idx=k.index; local=idx+pd.Timedelta(hours=7)
    mask=(idx>=START)&(idx<END)&(local.dayofweek==6)&(local.hour==9)&(local.minute==0)
    out=list(idx[mask])
    if len(out)!=139: raise RuntimeError(f'entry parity {len(out)}')
    return out


def funding_cost(k, f, entry_t, exit_t, entry_px, direction):
    rows=f[(f.ts>entry_t)&(f.ts<=exit_t)]
    qty=NOTIONAL/entry_px; total=0.0
    for r in rows.itertuples(index=False):
        px=float(k.loc[r.ts,'open']) if r.ts in k.index else entry_px
        total += direction * qty * px * float(r.rate)  # long pays +rate; short receives +rate
    return total


def first_leg(k,f,t):
    ep=float(k.loc[t,'open']); tp=ep*(1-FIRST_TP); sl=ep*(1+FIRST_SL)
    bars=k[(k.index>=t)&(k.index<t+pd.Timedelta(hours=FIRST_HOLD_H))]
    if len(bars)!=FIRST_HOLD_H*12: raise RuntimeError(f'first bars {t} {len(bars)}')
    reason='TIMEOUT'; ex_t=t+pd.Timedelta(hours=FIRST_HOLD_H); ex_px=float(bars.iloc[-1].close); touch_bar=None
    for b in bars.itertuples(index=False):
        hit_sl=float(b.high)>=sl; hit_tp=float(b.low)<=tp
        if hit_sl: # adverse-first if both on same 5m
            reason='SL'; ex_t=b.ts+pd.Timedelta(minutes=5); ex_px=sl; touch_bar=b.ts; break
        if hit_tp:
            reason='TP'; ex_t=b.ts+pd.Timedelta(minutes=5); ex_px=tp; touch_bar=b.ts; break
    gross=1.0-ex_px/ep
    fund=funding_cost(k,f,t,ex_t,ep,-1)
    pnl=NOTIONAL*gross-FEE-fund
    rev_t=ex_t if reason=='TP' else None  # next 5m open after touch bar
    return {'entry_t':t,'entry_px':ep,'exit_t':ex_t,'exit_px':ex_px,'reason':reason,'pnl':pnl,'rev_t':rev_t,
            'trigger_min':(ex_t-t).total_seconds()/60 if reason=='TP' else np.nan}


def reverse_leg(k,f,rev_t,tp_pct,sl_pct,hold_h):
    if rev_t not in k.index: return None
    ep=float(k.loc[rev_t,'open']); tp=ep*(1+tp_pct/100); sl=ep*(1-sl_pct/100)
    bars=k[(k.index>=rev_t)&(k.index<rev_t+pd.Timedelta(hours=hold_h))]
    if len(bars)!=hold_h*12: return None
    reason='TIMEOUT'; ex_t=rev_t+pd.Timedelta(hours=hold_h); ex_px=float(bars.iloc[-1].close)
    for b in bars.itertuples(index=False):
        hit_sl=float(b.low)<=sl; hit_tp=float(b.high)>=tp
        if hit_sl:
            reason='SL'; ex_t=b.ts+pd.Timedelta(minutes=5); ex_px=sl; break
        if hit_tp:
            reason='TP'; ex_t=b.ts+pd.Timedelta(minutes=5); ex_px=tp; break
    gross=ex_px/ep-1.0
    fund=funding_cost(k,f,rev_t,ex_t,ep,1)
    pnl=NOTIONAL*gross-FEE-fund
    return pnl,reason,ex_t


def pack_row(r):
    out={}
    for k,v in r.items():
        if isinstance(v,(np.integer,)): v=int(v)
        elif isinstance(v,(np.floating,)): v=float(v)
        out[k]=v
    return out


def main():
    k=f517.load_klines(); f=s50.load_funding(); es=entries(k)
    first=[first_leg(k,f,t) for t in es]
    first_pnl=np.array([x['pnl'] for x in first],float)
    first_reason=[x['reason'] for x in first]
    trig=np.array([r=='TP' for r in first_reason])
    trigger_idx=np.flatnonzero(trig)
    dtrig=trigger_idx[trigger_idx<DISC_N]; vtrig=trigger_idx[trigger_idx>=DISC_N]
    trigger_mins=np.array([first[i]['trigger_min'] for i in trigger_idx],float)

    rows=[]
    for hh in REV_HOLDS_H:
        for tp in REV_TP_GRID:
            for sl in REV_SL_GRID:
                rev_pnl=np.full(len(first),np.nan); rev_reason=['NO_TRIGGER']*len(first)
                chain=first_pnl.copy()
                for i in trigger_idx:
                    res=reverse_leg(k,f,first[i]['rev_t'],float(tp),float(sl),hh)
                    if res is None: continue
                    rp,rr,_=res; rev_pnl[i]=rp; rev_reason[i]=rr; chain[i]+=rp
                d_rev=rev_pnl[dtrig]; v_rev=rev_pnl[vtrig]
                d_rev=d_rev[np.isfinite(d_rev)]; v_rev=v_rev[np.isfinite(v_rev)]
                dm=metrics(d_rev); vm=metrics(v_rev); fm=metrics(rev_pnl[np.isfinite(rev_pnl)])
                dcm=metrics(chain[:DISC_N]); vcm=metrics(chain[DISC_N:]); fcm=metrics(chain)
                rows.append({
                    'hold_h':hh,'tp_pct':float(tp),'sl_pct':float(sl),'rr':float(tp/sl),
                    'D_rev_n':dm['n'],'D_rev_wr':dm['wr'],'D_rev_pnl':dm['pnl'],'D_rev_pf':dm['pf'],
                    'V_rev_n':vm['n'],'V_rev_wr':vm['wr'],'V_rev_pnl':vm['pnl'],'V_rev_pf':vm['pf'],
                    'full_rev_wr':fm['wr'],'full_rev_pnl':fm['pnl'],'full_rev_pf':fm['pf'],
                    'D_chain_pnl':dcm['pnl'],'D_chain_wr':dcm['wr'],'D_chain_pf':dcm['pf'],
                    'V_chain_pnl':vcm['pnl'],'V_chain_wr':vcm['wr'],'V_chain_pf':vcm['pf'],
                    'full_chain_pnl':fcm['pnl'],'full_chain_wr':fcm['wr'],'full_chain_pf':fcm['pf'],
                })
    df=pd.DataFrame(rows)
    # discovery selection requires reverse leg itself positive and PF>1, then maximize discovery chain PnL
    elig=df[(df.D_rev_pnl>0)&(df.D_rev_pf>1.0)].copy()
    champ=(elig.sort_values(['D_chain_pnl','D_rev_pnl','D_rev_pf'],ascending=False).iloc[0]
           if len(elig) else df.sort_values(['D_chain_pnl','D_rev_pnl'],ascending=False).iloc[0])
    raw=df.sort_values(['D_chain_pnl','D_rev_pnl'],ascending=False).iloc[0]
    eq04={}
    z=df[(df.tp_pct==0.4)&(df.sl_pct==0.4)]
    for _,r in z.sort_values('hold_h').iterrows(): eq04[str(int(r.hold_h))]=pack_row(r)
    top20=[pack_row(r) for _,r in df.sort_values(['D_chain_pnl','D_rev_pnl'],ascending=False).head(20).iterrows()]

    firstD=metrics(first_pnl[:DISC_N]); firstV=metrics(first_pnl[DISC_N:]); firstF=metrics(first_pnl)
    summary={
      'status':'COMPLETE_REVERSE_AFTER_04_CAUSAL',
      'definition':{'first_leg':'Sunday 09:00 WIB SELL TP0.4 SL1.5 hold18h','reverse':'BUY next 5m open after first-leg TP','discovery_n':83,'validation_n':56,
                    'reverse_holds_h':REV_HOLDS_H,'reverse_tp_grid':[0.3,2.5,0.1],'reverse_sl_grid':[0.3,1.5,0.1],'fee_rt_pct_each_leg':0.15,'notional_each_leg':500,'funding':'historical'},
      'first_leg':{'full_reason_counts':{x:first_reason.count(x) for x in ['TP','SL','TIMEOUT']},'D':firstD,'V':firstV,'full':firstF,
                   'reverse_triggers_full':int(len(trigger_idx)),'reverse_triggers_D':int(len(dtrig)),'reverse_triggers_V':int(len(vtrig)),
                   'trigger_time_min_median':float(np.nanmedian(trigger_mins)),'trigger_time_min_p25':float(np.nanpercentile(trigger_mins,25)),'trigger_time_min_p75':float(np.nanpercentile(trigger_mins,75))},
      'discovery_selected':pack_row(champ),'raw_discovery_chain_champion':pack_row(raw),'equal_04_04_by_hold':eq04,'top20_discovery_chain':top20,
      'guardrail':'Reverse parameters were selected using discovery only. Validation is report-only. Reverse entry is next 5m open, not the intrabar TP wick.'
    }
    (OUT/'sun14_summary.json').write_text(json.dumps(summary,indent=2,default=str))
    df.to_csv(OUT/'sun14_surface.csv',index=False)

    c=summary['discovery_selected']; fr=summary['first_leg']
    md=['# Sunday 09:00 WIB — SUN1.4 Reverse BUY after SELL +0.4%','',
        '**Status: COMPLETE — causal next-5m reversal, discovery-only parameter selection; live BBC untouched.**','',
        '## Frozen first leg',
        '- SELL Sunday 09:00 WIB; TP 0.4%, SL 1.5%, max hold 18h.',
        f"- Full reasons: TP **{fr['full_reason_counts']['TP']}**, SL **{fr['full_reason_counts']['SL']}**, timeout **{fr['full_reason_counts']['TIMEOUT']}**.",
        f"- Reverse triggers: D **{fr['reverse_triggers_D']}**, V **{fr['reverse_triggers_V']}**, full **{fr['reverse_triggers_full']}**.",
        f"- TP0.4 trigger timing median **{fr['trigger_time_min_median']:.0f}m** (P25 {fr['trigger_time_min_p25']:.0f}m, P75 {fr['trigger_time_min_p75']:.0f}m).",'',
        '## Reverse execution',
        '- When SELL TP0.4 is touched, SELL closes at its TP.',
        '- BUY opens at the **next completed 5m boundary/open**, not at the wick touch price.',
        '- Each leg pays its own 0.15% round-trip fee; historical funding included.','',
        '## Discovery-selected reverse BUY',
        f"- BUY hold **{int(c['hold_h'])}h**, TP **{c['tp_pct']:.1f}%**, SL **{c['sl_pct']:.1f}%** (RR {c['rr']:.2f}).",
        f"- Reverse D: N {int(c['D_rev_n'])}, WR **{100*c['D_rev_wr']:.2f}%**, PnL **${c['D_rev_pnl']:+.2f}**, PF **{c['D_rev_pf']:.2f}**.",
        f"- Reverse V: N {int(c['V_rev_n'])}, WR **{100*c['V_rev_wr']:.2f}%**, PnL **${c['V_rev_pnl']:+.2f}**, PF **{c['V_rev_pf']:.2f}**.",
        f"- Reverse full: WR **{100*c['full_rev_wr']:.2f}%**, PnL **${c['full_rev_pnl']:+.2f}**, PF **{c['full_rev_pf']:.2f}**.",'',
        '## Combined SELL -> BUY chain',
        f"- D chain PnL **${c['D_chain_pnl']:+.2f}**, WR **{100*c['D_chain_wr']:.2f}%**, PF **{c['D_chain_pf']:.2f}**.",
        f"- V chain PnL **${c['V_chain_pnl']:+.2f}**, WR **{100*c['V_chain_wr']:.2f}%**, PF **{c['V_chain_pf']:.2f}**.",
        f"- Full chain PnL **${c['full_chain_pnl']:+.2f}**, WR **{100*c['full_chain_wr']:.2f}%**, PF **{c['full_chain_pf']:.2f}**.",'',
        '## Equal reverse 0.4/0.4 reference']
    for hh,r in eq04.items():
        md.append(f"- {hh}h: reverse D {r['D_rev_pnl']:+.2f}, V {r['V_rev_pnl']:+.2f}, full {r['full_rev_pnl']:+.2f}; full reverse WR {100*r['full_rev_wr']:.1f}%; chain full {r['full_chain_pnl']:+.2f}")
    md += ['', '## Guardrail', summary['guardrail']]
    (OUT/'SUN1.4_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(summary,indent=2,default=str),flush=True)

if __name__=='__main__': main()
