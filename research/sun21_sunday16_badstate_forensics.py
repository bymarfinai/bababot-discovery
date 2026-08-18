#!/usr/bin/env python3
"""SUN2.1 — forensic F-|S-|U+ Sunday16 state.
Research only; live BBC untouched. No threshold/timing/TP-SL sweeps.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sun17_sunday16_loss_prevday_forensics as sun17
import sun19_sunday16_dynamic_direction_engine as sun19

OUT=Path(os.getenv('SUN21_OUT','sun21_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83; TARGET='F-|S-|U+'

def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0: return {'n':0,'wins':0,'wr':None,'pnl':0.0,'pf':None,'exp':None}
    wins=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    return {'n':int(len(a)),'wins':wins,'wr':float(wins/len(a)),'pnl':float(a.sum()),
            'pf':float(gp/gl) if gl>0 else 999.0,'exp':float(a.mean())}

def close_before(k,t):
    x=k[k.index<t]
    return np.nan if x.empty else float(x.iloc[-1].close)

def extra_context(k,t,ctx):
    local=t+pd.Timedelta(hours=7); sun0=local.normalize()-pd.Timedelta(hours=7); sun12=t-pd.Timedelta(hours=4)
    p0=close_before(k,sun0); p12=close_before(k,sun12); pre=close_before(k,t)
    w4=k[(k.index>=sun12)&(k.index<t)]
    first12=p12/p0-1.0; last4=pre/p12-1.0
    taker4=float(np.nanmean(w4.taker_imb.to_numpy(float))) if len(w4) else np.nan
    return {
      'sun00_12_ret':first12,'sun12_16_ret2':last4,'last4_taker':taker4,
      'sustained_up':bool(first12>=0 and last4>=0),'late_rebound':bool(first12<0 and last4>=0),
      'fading_up':bool(first12>=0 and last4<0),'upper_half24':bool(ctx['prior24_close_loc']>=0.5),
      'above_ema7':bool(ctx['pre_close_vs_ema7']>=0),'above_ema20':bool(ctx['pre_close_vs_ema20']>=0),
      'ema_bull':bool(ctx['pre_ema_spread']>=0),'last4_buyflow':bool(taker4>=0),
      'thu_up':bool(ctx['thu_day_ret']>=0),'last4_up':bool(last4>=0),'first12_up':bool(first12>=0)
    }

def main():
    k=f517.load_klines(); f=s50.load_funding(); es=sun19.entries(k)
    rows=[]; sa=[]; ba=[]
    for i,t in enumerate(es):
        ctx=sun17.pre_context(k,t); st=sun19.state_key(ctx); s=sun19.simulate(k,f,t,-1); b=sun19.simulate(k,f,t,1)
        rows.append({'i':i,'entry_t':str(t),'state':st,'thu_day_ret':ctx['thu_day_ret'],
                     'prior24_close_loc':ctx['prior24_close_loc'],'pre_close_vs_ema7':ctx['pre_close_vs_ema7'],
                     'pre_close_vs_ema20':ctx['pre_close_vs_ema20'],'pre_ema_spread':ctx['pre_ema_spread'],
                     **extra_context(k,t,ctx),'sell_pnl':s['pnl'],'buy_pnl':b['pnl']})
        sa.append(s['pnl']); ba.append(b['pnl'])
    df0=pd.DataFrame(rows); sa=np.array(sa,float); ba=np.array(ba,float)
    idx=np.flatnonzero(df0.state.to_numpy()==TARGET)
    if len(idx)!=12: raise RuntimeError(f'target parity expected 12 got {len(idx)}')
    df=df0.iloc[idx].copy().reset_index(drop=True); sell=sa[idx]; buy=ba[idx]; gi=np.array(idx,int)
    d=gi<DISC_N; v=~d
    base={'SELL':{'D':metrics(sell[d]),'V':metrics(sell[v]),'full':metrics(sell)},
          'BUY':{'D':metrics(buy[d]),'V':metrics(buy[v]),'full':metrics(buy)}}

    bools=['thu_up','first12_up','last4_up','sustained_up','late_rebound','fading_up','upper_half24','above_ema7','above_ema20','ema_bull','last4_buyflow']
    anatomy=[]
    for feat in bools:
        m=df[feat].to_numpy(bool)
        anatomy.append({'feature':feat,'true_n':int(m.sum()),'D_true_n':int((m&d).sum()),'V_true_n':int((m&v).sum()),
                        'SELL_true':metrics(sell[m]),'SELL_false':metrics(sell[~m]),
                        'BUY_true':metrics(buy[m]),'BUY_false':metrics(buy[~m]),
                        'D_SELL_true':metrics(sell[m&d]),'V_SELL_true':metrics(sell[m&v]),
                        'D_SELL_false':metrics(sell[(~m)&d]),'V_SELL_false':metrics(sell[(~m)&v])})

    rules=['sustained_up','upper_half24','above_ema20','ema_bull','last4_buyflow','first12_up','last4_up']
    routers=[]
    for rule in rules:
        m=df[rule].to_numpy(bool); rp=np.where(m,buy,sell)
        routers.append({'rule':f'{rule}: true BUY / false SELL','D':metrics(rp[d]),'V':metrics(rp[v]),'full':metrics(rp)})
    agree=df.sustained_up.to_numpy(bool)&df.upper_half24.to_numpy(bool); rp=np.where(agree,buy,sell)
    routers.append({'rule':'sustained_up AND upper_half24: true BUY / false SELL','D':metrics(rp[d]),'V':metrics(rp[v]),'full':metrics(rp)})

    a=df.sustained_up.to_numpy(bool); b=df.upper_half24.to_numpy(bool)
    tb=a&b; ts=(~a)&(~b); take=tb|ts; cp=np.where(tb,buy,sell)
    conservative={'D':metrics(cp[take&d]),'V':metrics(cp[take&v]),'full':metrics(cp[take]),
                  'trade_n':int(take.sum()),'wait_n':int((~take).sum()),'buy_n':int(tb.sum()),'sell_n':int(ts.sum())}
    result={'status':'COMPLETE_BADSTATE_FORENSIC','state':TARGET,'n':12,'D_n':int(d.sum()),'V_n':int(v.sum()),
            'base':base,'anatomy':anatomy,'routers':routers,'conservative_agreement':conservative,
            'guardrail':'Forensic only. N=12 (D=5,V=7) is small and this history has been inspected before; no rule is promoted from this step.'}
    df.to_csv(OUT/'sun21_badstate_trades.csv',index=False); (OUT/'sun21_summary.json').write_text(json.dumps(result,indent=2))

    def fm(m):
        wr='-' if m['wr'] is None else f"{100*m['wr']:.1f}%"; pf='-' if m['pf'] is None else f"{m['pf']:.2f}"
        return f"N {m['n']}, WR {wr}, PnL ${m['pnl']:+.2f}, PF {pf}"
    md=['# SUN2.1 — F-/S-/U+ Reversal vs Retracement Forensic','',
        '**Status: COMPLETE — forensic only; live BBC untouched.**','',
        '## State baseline',f"- SELL: D {fm(base['SELL']['D'])}; V {fm(base['SELL']['V'])}; Full {fm(base['SELL']['full'])}.",
        f"- BUY: D {fm(base['BUY']['D'])}; V {fm(base['BUY']['V'])}; Full {fm(base['BUY']['full'])}.",'',
        '## Natural reversal routers','| Rule | D | V | Full |','|---|---|---|---|']
    for r in routers: md.append(f"| {r['rule']} | {fm(r['D'])} | {fm(r['V'])} | {fm(r['full'])} |")
    md += ['', '## Conservative agreement',
           f"- sustained_up + upper_half24: trades {conservative['trade_n']}/12 (BUY {conservative['buy_n']}, SELL {conservative['sell_n']}, WAIT {conservative['wait_n']}).",
           f"- D {fm(conservative['D'])}; V {fm(conservative['V'])}; Full {fm(conservative['full'])}.",'','## Guardrail',result['guardrail']]
    (OUT/'SUN2.1_CHECKPOINT.md').write_text('\n'.join(md)+'\n'); print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__': main()
