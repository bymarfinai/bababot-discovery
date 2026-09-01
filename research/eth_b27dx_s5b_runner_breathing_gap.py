#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
S5A_PATH=HERE/'eth_b27dx_s5a_runner_arm_geometry.py'
spec=importlib.util.spec_from_file_location('eth_s5a',S5A_PATH); s=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(s)

PFX='ETH_B27DX_S5B_RUNNER_BREATHING_GAP'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_CAND=ROOT/f'{PFX}_Candidates.csv'; OUT_DEC=ROOT/f'{PFX}_Decisions.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
ARM_EXT=0.25; GAPS=(0.05,0.10,0.15,0.20,0.25)
BASE_N=478; BASE_EXP=0.81; BASE_NET=385.75
BTC_WR=0.719298; BTC_PF=2.223193; BTC_EXP=1.26

def g_label(v):return f'G{int(round(v*100)):02d}'
def build_candidates(x):
    rows=[]; cache={(p,ex):s.b.sessions_for(x,p,ex,s.REF_MIN,s.HORIZON_MIN,'LONG',s.ENTRY_F) for p in s.PARTS for ex in s.CLOCKS}
    original_gap=s.GAP
    try:
        for gap in GAPS:
            s.GAP=float(gap)
            for p in s.PARTS:
                for ex in s.CLOCKS:
                    for sess in cache[(p,ex)]:
                        d0=s.runner_exit(x,sess,ARM_EXT,0.0); d5=s.runner_exit(x,sess,ARM_EXT,5.0)
                        if d0 is None or d5 is None:continue
                        if d0['exit_ts']!=d5['exit_ts'] or d0['exit_reason']!=d5['exit_reason']:raise AssertionError('stress changed chronology')
                        r={'gap':gap,'gap_label':g_label(gap),'partition':p,'exec_min':ex,'execution_utc':s.clock_label(ex),'execution_start':pd.Timestamp(sess['es']),
                           'entry_bar_start':pd.Timestamp(sess['fill_ts']),'entry_px':float(sess['entry']),'exit_ts':d0['exit_ts'],'exit_reason':d0['exit_reason'],'pnl_0':d0['pnl'],'pnl_5':d5['pnl']}
                        for k in ('armed','scheduled_updates','activations','ratchet_updates','buffer_f20_exit','gap_exit','touch_exit','early_floor_violation'):r[k]=d0[k]
                        rows.append(r)
    finally:s.GAP=original_gap
    c=pd.DataFrame(rows)
    for col in ('execution_start','entry_bar_start','exit_ts'):
        if col in c:c[col]=pd.to_datetime(c[col],utc=True,errors='coerce')
    return c

def summarize(c):
    decs=[];rows=[];aud=[];major_weeks=sum(s.weeks_for(p) for p in s.PARTS)
    for gap in GAPS:
        label=g_label(gap); bypart=[]
        for p in s.PARTS:
            g=c[(c.gap==gap)&(c.partition==p)].copy();d=s.lock(g);bypart.append(d);decs.append(d);a=d[d.accepted].sort_values('entry_bar_start')
            aud.append({'gap':gap,'gap_label':label,'partition':p,'early_floor_violations':int(pd.to_numeric(g.early_floor_violation,errors='coerce').fillna(0).sum()),'same_entry_ties':int((g.groupby('entry_bar_start').size()>1).sum())})
            for stress,col in ((0,'pnl_0'),(5,'pnl_5')):
                m=s.metrics(a,col);rows.append({'gap':gap,'gap_label':label,'partition':p,'stress_bps':stress,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/s.weeks_for(p),
                    'armed':int(a.armed.sum()),'floor_exits':int(a.exit_reason.isin(['LIVE_FLOOR_GAP_OPEN','LIVE_FLOOR_TOUCH']).sum()),'buffer_f20_exits':int((a.exit_reason=='BUFFER_CLOSE_INVALIDATION_F20').sum()),**m})
        dm=pd.concat(bypart,ignore_index=True);am=dm[dm.accepted].sort_values('entry_bar_start')
        for stress,col in ((0,'pnl_0'),(5,'pnl_5')):
            m=s.metrics(am,col);rows.append({'gap':gap,'gap_label':label,'partition':'POOLED_MAJOR','stress_bps':stress,'candidates':len(dm),'accepted':len(am),'blocked':int((~dm.accepted).sum()),'trades_per_week':len(am)/major_weeks,
                'armed':int(am.armed.sum()),'floor_exits':int(am.exit_reason.isin(['LIVE_FLOOR_GAP_OPEN','LIVE_FLOOR_TOUCH']).sum()),'buffer_f20_exits':int((am.exit_reason=='BUFFER_CLOSE_INVALIDATION_F20').sum()),**m})
    return pd.concat(decs,ignore_index=True),pd.DataFrame(rows),pd.DataFrame(aud)
def flags(sumdf,audit):
    out=[]
    for gap in GAPS:
        label=g_label(gap);p0=sumdf[(sumdf.gap==gap)&(sumdf.partition=='POOLED_MAJOR')&(sumdf.stress_bps==0)].iloc[0];p5=sumdf[(sumdf.gap==gap)&(sumdf.partition=='POOLED_MAJOR')&(sumdf.stress_bps==5)].iloc[0]
        maj=sumdf[(sumdf.gap==gap)&sumdf.partition.isin(s.PARTS)&(sumdf.stress_bps==0)];causal=int(audit[audit.gap==gap].early_floor_violations.sum())==0;major=bool(((maj.net>0)&(maj.pf>1.0)).all());stress=bool(p5.pf>=1.0 and p5.net>=0)
        supported=bool(p0.net>BASE_NET and p0.pf>=1.80 and p0.wr>=0.70 and p0.expectancy>BASE_EXP and p0.accepted>=0.80*BASE_N and major and causal and stress)
        btc=bool(p0.wr>=BTC_WR and p0.pf>=BTC_PF and p0.expectancy>=BTC_EXP and major and causal and stress)
        out.append({'gap':gap,'gap_label':label,'supported':supported,'btc_quality':btc,'causal':causal,'major_positive':major,'stress_pass':stress})
    return pd.DataFrame(out)
def runs(f):
    vals=[float(r.gap) for r in f.sort_values('gap').itertuples(index=False) if bool(r.supported)]
    if not vals:return []
    out=[];cur=[vals[0]]
    for v in vals[1:]:
        if abs(v-cur[-1]-0.05)<1e-9:cur.append(v)
        else:out.append(cur);cur=[v]
    out.append(cur);return out

def main():
    x,cov=s.b.m.m.load5();c=build_candidates(x);c.to_csv(OUT_CAND,index=False);dec,sumdf,audit=summarize(c) if False else summarize(c);dec.to_csv(OUT_DEC,index=False);sumdf.to_csv(OUT_SUM,index=False);audit.to_csv(OUT_AUDIT,index=False);f=flags(sumdf,audit);rr=runs(f);causal=bool(f.causal.all())
    status='ETH_S5B_CAUSAL_AUDIT_FAILED' if not causal else ('ETH_S5B_NATIVE_GAP_FAMILY_SUPPORTED' if any(len(r)>=2 for r in rr) else ('ETH_S5B_SUPPORTED_GAP_ISOLATED' if bool(f.supported.any()) else 'ETH_S5B_NO_SUPPORTED_GAP'))
    lines=['# ETH B27DX — S5B Live-Executable Runner Breathing-Gap Geometry — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',
           'Frozen: **R300/X360 · F75 entry · F20 pre-arm invalidation · E25 arm · 0.10R ratchet step · four ETH-native clocks**. Only breathing gap varies.','',
           '## Pooled-major gap comparison','',
           '| Gap | Initial floor | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS | 5bps PF | 5bps Net | Support | BTC quality |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for z in f.sort_values('gap').itertuples(index=False):
        r=sumdf[(sumdf.gap==z.gap)&(sumdf.partition=='POOLED_MAJOR')&(sumdf.stress_bps==0)].iloc[0];q=sumdf[(sumdf.gap==z.gap)&(sumdf.partition=='POOLED_MAJOR')&(sumdf.stress_bps==5)].iloc[0];floor=ARM_EXT-z.gap
        lines.append(f'| {z.gap_label} | {s.e_label(floor)} | {int(r.accepted)} | {r.trades_per_week:.3f} | {s.pct(r.wr)} | {s.fmt(r.pf)} | {s.fmt(r.expectancy)} | {s.fmt(r.net)} | {int(r.max_ls)} | {s.fmt(q.pf)} | {s.fmt(q.net)} | {"YES" if z.supported else "NO"} | {"PASS" if z.btc_quality else "NO"} |')
    lines += ['','## Fixed S4 baseline','', '- Accepted **478**, frequency **1.393/wk**, WR **62.8%**, PF **1.42**, expectancy **+$0.81/trade**, net **+$385.75**, max LS **5**.','','## Supported gap-family runs','']
    if not rr:lines.append('None.')
    else:
        for i,r in enumerate(rr,1):lines.append(f'- Run {i}: **{" → ".join(g_label(v) for v in r)}** ({len(r)} adjacent gaps).')
    lines += ['','## Per-partition 0 bps','', '| Gap | Partition | Accepted | WR | PF | Exp | Net | Max LS |','|---:|---|---:|---:|---:|---:|---:|---:|']
    for gap in GAPS:
        for p in s.PARTS:
            r=sumdf[(sumdf.gap==gap)&(sumdf.partition==p)&(sumdf.stress_bps==0)].iloc[0];lines.append(f'| {g_label(gap)} | {p} | {int(r.accepted)} | {s.pct(r.wr)} | {s.fmt(r.pf)} | {s.fmt(r.expectancy)} | {s.fmt(r.net)} | {int(r.max_ls)} |')
    lines += ['','## Causal audit','',f'- Early floor activations: **{int(audit.early_floor_violations.sum())}**.',f'- All gap variants causal-audit pass: **{"YES" if causal else "NO"}**.','','## Decision','',f'**Status: {status}**','', '- No arm, ratchet-step, structure, entry, clock, leverage, fee, or live-code tuning was performed.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
