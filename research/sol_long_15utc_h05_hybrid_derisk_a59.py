#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A53_PATH = Path(__file__).resolve().parent / 'sol_long_15utc_executable_guard_a53.py'
spec = importlib.util.spec_from_file_location('a53', A53_PATH)
a53 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a53)
a17, a3, a2 = a53.a17, a53.a3, a53.a2

OUT_TRADES = ROOT / 'SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_TRADES.csv'
OUT_METRICS = ROOT / 'SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_METRICS.csv'
OUT_BLOCKS = ROOT / 'SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_BLOCKS.csv'
OUT_DIAG = ROOT / 'SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_DIAGNOSTICS.csv'
OUT_MD = ROOT / 'SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_Result.md'
OUT_STATUS = ROOT / 'SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_Status.txt'

REF_MIN, HOUR, NOTIONAL, STRESS, CUT = 360, 15, 500.0, 0.0005, 0.50
PARTS = ('development','external','reference_validation')
EXPECTED_N = {'development':601,'external':281,'reference_validation':337}
EXPECTED_WIN = {'development':244,'external':115,'reference_validation':150}
EPS = 1e-12


def fmt(v,d=2):
    if pd.isna(v): return '-'
    if np.isinf(v): return 'inf'
    return f'{float(v):.{d}f}'

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def pf(vals):
    x=pd.to_numeric(vals,errors='coerce').dropna(); gp=float(x[x>0].sum()); gl=float(-x[x<=0].sum())
    if gl==0: return np.inf if gp>0 else np.nan
    return gp/gl

def max_dd(vals):
    x=pd.to_numeric(vals,errors='coerce').fillna(0).to_numpy(float); eq=np.r_[0.0,np.cumsum(x)]; peak=np.maximum.accumulate(eq)
    return float(np.max(peak-eq))

def max_loss_streak(vals):
    best=cur=0
    for v in pd.to_numeric(vals,errors='coerce').fillna(0):
        if float(v)<=0: cur+=1; best=max(best,cur)
        else: cur=0
    return best

def bar_pos(idx,ts):
    i=int(idx.searchsorted(pd.Timestamp(ts),'left'))
    if i>=len(idx) or idx[i]!=pd.Timestamp(ts): raise RuntimeError(f'timestamp parity {ts}')
    return i

def parent(m,part):
    q=a17.simulate_cell(m,part,REF_MIN,HOUR,'A59','CENTRAL').copy()
    q['loss_class']=[a3.loss_class(r) for _,r in q.iterrows()]
    return q.sort_values('entry_ts').reset_index(drop=True)

def hybrid_row(m,r):
    base=a53.simulate(m,r,'BASELINE')
    hard=a53.simulate(m,r,'G2_POST_H05')
    if abs(float(base['pnl'])-float(r.pnl))>1e-7 or abs(float(base['pnl_5bps'])-float(r.pnl_5bps))>1e-7:
        raise RuntimeError(f'parent pnl parity {r.partition} {r.entry_ts}')
    if pd.Timestamp(base['exit_ts'])!=pd.Timestamp(r.exit_ts):
        raise RuntimeError(f'parent exit-ts parity {r.partition} {r.entry_ts}')

    entry=float(r.entry_price); parent_pnl=float(r.pnl); parent_pnl5=float(r.pnl_5bps)
    final_price=entry*(1.0+parent_pnl/NOTIONAL)
    derisk=bool(hard['guard_exit']); rearm=False
    cut_ts=pd.NaT; cut_price=np.nan; rearm_warning_ts=pd.NaT; rearm_ts=pd.NaT; rearm_price=np.nan

    if not derisk:
        pnl=parent_pnl; pnl5=parent_pnl5
    else:
        cut_ts=pd.Timestamp(hard['exit_ts']); cut_price=float(hard['exit_price'])
        idx,cl=m['idx'],m['close']; cut_i=bar_pos(idx,cut_ts); parent_exit_i=bar_pos(idx,r.exit_ts)
        H,R=float(r.H),float(r.R)
        for i in range(cut_i,parent_exit_i):
            if str(r.exit_reason)=='TARGET' and idx[i]==pd.Timestamp(r.exit_ts): break
            if float(cl[i])>H+0.10*R+EPS:
                ni=i+1
                if ni<len(idx) and ni<=parent_exit_i:
                    rearm=True; rearm_warning_ts=idx[i]; rearm_ts=idx[ni]; rearm_price=float(m['open'][ni])
                break
        pnl_cut=CUT*NOTIONAL*(cut_price/entry-1.0)
        pnl_keep=(1.0-CUT)*NOTIONAL*(final_price/entry-1.0)
        pnl_rearm=CUT*NOTIONAL*(final_price/rearm_price-1.0) if rearm else 0.0
        pnl=pnl_cut+pnl_keep+pnl_rearm
        pnl5=pnl-STRESS*NOTIONAL*(1.0+(CUT if rearm else 0.0))

    return {
        'variant':'HYB50_H05_H10_REARM','partition':r.partition,'dev_block':r.dev_block,'execution_start':r.execution_start,
        'entry_ts':r.entry_ts,'parent_exit_ts':r.exit_ts,'parent_exit_reason':r.exit_reason,'parent_pnl':parent_pnl,
        'parent_pnl_5bps':parent_pnl5,'parent_won':bool(parent_pnl>0),'parent_loss_class':r.loss_class,
        'pnl':pnl,'pnl_5bps':pnl5,'won':bool(pnl>0),'won_5bps':bool(pnl5>0),'derisked':derisk,
        'warning_ts':hard['warning_ts'] if derisk else pd.NaT,'cut_ts':cut_ts,'cut_price':cut_price,'rearmed':rearm,
        'rearm_warning_ts':rearm_warning_ts,'rearm_ts':rearm_ts,'rearm_price':rearm_price,
        'delta_pnl':pnl-parent_pnl,'delta_pnl_5bps':pnl5-parent_pnl5,
    }

def baseline_row(m,r):
    b=a53.simulate(m,r,'BASELINE')
    if abs(float(b['pnl'])-float(r.pnl))>1e-7 or abs(float(b['pnl_5bps'])-float(r.pnl_5bps))>1e-7:
        raise RuntimeError(f'baseline parity {r.partition} {r.entry_ts}')
    if pd.Timestamp(b['exit_ts'])!=pd.Timestamp(r.exit_ts): raise RuntimeError(f'baseline timestamp parity {r.partition} {r.entry_ts}')
    return {
        'variant':'BASELINE','partition':r.partition,'dev_block':r.dev_block,'execution_start':r.execution_start,
        'entry_ts':r.entry_ts,'parent_exit_ts':r.exit_ts,'parent_exit_reason':r.exit_reason,'parent_pnl':float(r.pnl),
        'parent_pnl_5bps':float(r.pnl_5bps),'parent_won':bool(float(r.pnl)>0),'parent_loss_class':r.loss_class,
        'pnl':float(r.pnl),'pnl_5bps':float(r.pnl_5bps),'won':bool(float(r.pnl)>0),'won_5bps':bool(float(r.pnl_5bps)>0),
        'derisked':False,'warning_ts':pd.NaT,'cut_ts':pd.NaT,'cut_price':np.nan,'rearmed':False,
        'rearm_warning_ts':pd.NaT,'rearm_ts':pd.NaT,'rearm_price':np.nan,'delta_pnl':0.0,'delta_pnl_5bps':0.0,
    }

def simulate_partition(m,part):
    q=parent(m,part)
    if len(q)!=EXPECTED_N[part]: raise RuntimeError(f'{part} N {len(q)}')
    if int((pd.to_numeric(q.pnl,errors='coerce')>0).sum())!=EXPECTED_WIN[part]: raise RuntimeError(f'{part} winners mismatch')
    rows=[]
    for _,r in q.iterrows(): rows.extend([baseline_row(m,r),hybrid_row(m,r)])
    return pd.DataFrame(rows).sort_values(['partition','variant','entry_ts']).reset_index(drop=True)

def one_metrics(q):
    q=q.sort_values('entry_ts'); p=pd.to_numeric(q.pnl,errors='coerce'); p5=pd.to_numeric(q.pnl_5bps,errors='coerce')
    pw=q.parent_won.astype(bool); d=q.derisked.astype(bool); rr=q.rearmed.astype(bool)
    return {'n':len(q),'wr':float((p>0).mean()),'pf':pf(p),'expectancy':float(p.mean()),'net':float(p.sum()),
            'max_dd':max_dd(p),'max_loss_streak':max_loss_streak(p),'wr_5bps':float((p5>0).mean()),'pf_5bps':pf(p5),
            'expectancy_5bps':float(p5.mean()),'net_5bps':float(p5.sum()),'max_dd_5bps':max_dd(p5),
            'max_loss_streak_5bps':max_loss_streak(p5),'derisk_count':int(d.sum()),'rearm_count':int(rr.sum()),
            'rearm_rate':float(rr.sum()/d.sum()) if d.sum() else np.nan,'derisk_no_rearm':int((d&~rr).sum()),
            'parent_winners_derisked':int((d&pw).sum()),'parent_losers_derisked':int((d&~pw).sum()),
            'parent_winners_rearmed':int((rr&pw).sum()),'parent_losers_rearmed':int((rr&~pw).sum()),
            'winner_pnl_delta':float(q.loc[pw,'delta_pnl'].sum()),'loss_pnl_delta':float(q.loc[~pw,'delta_pnl'].sum()),
            'delta_net':float(q.delta_pnl.sum()),'delta_net_5bps':float(q.delta_pnl_5bps.sum())}

def build_metrics(t):
    return pd.DataFrame([{'partition':p,'variant':v,**one_metrics(q)} for (p,v),q in t.groupby(['partition','variant'],sort=False)])

def build_blocks(t):
    q=t[t.partition=='development']; b=q[q.variant=='BASELINE'][['entry_ts','dev_block','pnl','pnl_5bps']].rename(columns={'pnl':'bp','pnl_5bps':'bp5'})
    h=q[q.variant!='BASELINE'][['entry_ts','dev_block','pnl','pnl_5bps']].merge(b,on=['entry_ts','dev_block'])
    rows=[]
    for bi in range(6):
        z=h[pd.to_numeric(h.dev_block,errors='coerce')==bi]
        rows.append({'dev_block':bi,'n':len(z),'delta_net':float((z.pnl-z.bp).sum()),'delta_net_5bps':float((z.pnl_5bps-z.bp5).sum())})
    return pd.DataFrame(rows)

def dev_gate(metrics,blocks):
    b=metrics[(metrics.partition=='development')&(metrics.variant=='BASELINE')].iloc[0]; h=metrics[(metrics.partition=='development')&(metrics.variant!='BASELINE')].iloc[0]
    pr=int((blocks.delta_net>0).sum()); p5=int((blocks.delta_net_5bps>0).sum())
    ok=bool(h.net>b.net+EPS and h.net_5bps>b.net_5bps+EPS and h.pf>b.pf+EPS and h.pf_5bps>b.pf_5bps+EPS and h.wr_5bps+EPS>=b.wr_5bps and h.max_dd<=b.max_dd+EPS and pr>=4 and p5>=4)
    return ok,pr,p5

def oos_gate(metrics,part):
    b=metrics[(metrics.partition==part)&(metrics.variant=='BASELINE')].iloc[0]; h=metrics[(metrics.partition==part)&(metrics.variant!='BASELINE')].iloc[0]
    return bool(h.net>b.net+EPS and h.net_5bps>b.net_5bps+EPS and h.pf>b.pf+EPS and h.pf_5bps>b.pf_5bps+EPS and h.wr_5bps+EPS>=b.wr_5bps and h.max_dd<=b.max_dd+EPS)

def diagnostics(t):
    rows=[]
    for part,q in t[t.variant!='BASELINE'].groupby('partition',sort=False):
        d=q[q.derisked.astype(bool)]
        masks={'DERISKED_ALL':pd.Series(True,index=d.index),'DERISKED_PARENT_WIN':d.parent_won.astype(bool),'DERISKED_PARENT_NONWIN':~d.parent_won.astype(bool),
               'REARMED_ALL':d.rearmed.astype(bool),'REARMED_PARENT_WIN':d.rearmed.astype(bool)&d.parent_won.astype(bool),'REARMED_PARENT_NONWIN':d.rearmed.astype(bool)&~d.parent_won.astype(bool)}
        for name,mask in masks.items():
            z=d[mask]; rows.append({'partition':part,'cohort':name,'n':len(z),'sum_delta_pnl':float(z.delta_pnl.sum()),'sum_delta_pnl_5bps':float(z.delta_pnl_5bps.sum())})
    return pd.DataFrame(rows)

def write_result(t,metrics,blocks,coverage,dev_ok,pr,p5,status,oos):
    lines=['# SOL LONG 15:00 UTC H05 Hybrid De-risk + H10 Re-arm — A59 Result','',f'Frozen SOLUSDT 5m coverage: **{100*coverage:.4f}%**.','',
           'A59 tests one preregistered nonlinear response only: first live H05 warning -> cut 50% next open -> restore that 50% only after a later completed close > H+0.10R, executed next open. One cut / one re-arm maximum. No fraction or threshold sweep.','',
           '## Parent reconciliation','',f"Development parent replay: **{EXPECTED_N['development']}/{EXPECTED_N['development']} exact PnL/timestamp parity**; winner count **{EXPECTED_WIN['development']}**.",'']
    if set(PARTS).issubset(set(t.partition.unique())): lines += [f"External / Reference Validation opened only after Development passed: **{EXPECTED_N['external']} / {EXPECTED_N['reference_validation']}** rows reconciled.",'']
    lines += ['## Economics','', '| Partition | Variant | WR | PF | Net | Exp | DD | Streak | 5bps WR | 5bps PF | 5bps Net | De-risk | Re-arm | Re-arm rate | Winner de-risk | Loser de-risk | Winner Δ | Loser Δ | ΔNet | 5bps ΔNet |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for part in PARTS:
        q=metrics[metrics.partition==part]
        if q.empty: continue
        q=q.assign(ord=q.variant.map({'BASELINE':0,'HYB50_H05_H10_REARM':1})).sort_values('ord')
        for _,r in q.iterrows():
            lines.append(f'| {part} | {r.variant} | {pct(r.wr)} | {fmt(r.pf)} | ${fmt(r.net)} | ${fmt(r.expectancy)} | ${fmt(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.wr_5bps)} | {fmt(r.pf_5bps)} | ${fmt(r.net_5bps)} | {int(r.derisk_count)} | {int(r.rearm_count)} | {pct(r.rearm_rate)} | {int(r.parent_winners_derisked)} | {int(r.parent_losers_derisked)} | ${fmt(r.winner_pnl_delta)} | ${fmt(r.loss_pnl_delta)} | ${fmt(r.delta_net)} | ${fmt(r.delta_net_5bps)} |')
    lines += ['','## Development six-block deltas','', '| Block | N | Raw ΔNet | 5bps ΔNet |','|---:|---:|---:|---:|']
    for _,r in blocks.sort_values('dev_block').iterrows(): lines.append(f'| {int(r.dev_block)+1} | {int(r.n)} | ${fmt(r.delta_net)} | ${fmt(r.delta_net_5bps)} |')
    lines += ['',f'Positive Development blocks: **{pr}/6 raw**, **{p5}/6 stress**.','',f"Development gate: **{'PASS' if dev_ok else 'FAIL'}**.",'']
    if dev_ok:
        lines += ['## OOS confirmation','', '| Partition | Gate |','|---|---:|',f"| External | {'PASS' if oos.get('external') else 'FAIL'} |",f"| Reference Validation | {'PASS' if oos.get('reference_validation') else 'FAIL'} |",'']
    else:
        lines += ['## OOS protocol','','Development failed the frozen gate, therefore A59 **did not compute/open hybrid External or Reference Validation results**.','']
    lines += ['## Decision','',f'**Status: {status}**','','A59 judges economics, not WR aesthetics. Rejection does not authorize a posthoc size-fraction sweep or H05/H10 retuning.','','Research only. Live Baba Bot remains unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8'); OUT_STATUS.write_text(status+'\n',encoding='utf-8')

def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    dev=simulate_partition(m,'development'); metrics=build_metrics(dev); blocks=build_blocks(dev); dev_ok,pr,p5=dev_gate(metrics,blocks)
    frames=[dev]; oos={}
    if dev_ok:
        for part in ('external','reference_validation'): frames.append(simulate_partition(m,part))
        t=pd.concat(frames,ignore_index=True); metrics=build_metrics(t)
        for part in ('external','reference_validation'): oos[part]=oos_gate(metrics,part)
        status='SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_SUPPORTED' if all(oos.values()) else 'SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_REJECTED_OOS'
    else:
        t=dev; status='SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_REJECTED_DEVELOPMENT'
    diag=diagnostics(t); t.to_csv(OUT_TRADES,index=False); metrics.to_csv(OUT_METRICS,index=False); blocks.to_csv(OUT_BLOCKS,index=False); diag.to_csv(OUT_DIAG,index=False)
    write_result(t,metrics,blocks,coverage,dev_ok,pr,p5,status,oos); print(status)

if __name__=='__main__': main()
