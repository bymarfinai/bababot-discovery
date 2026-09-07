#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A56=Path(__file__).resolve().parent/'sol_long_15utc_loss_confirmation_guard_a56.py'
spec=importlib.util.spec_from_file_location('a56',A56); a56=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a56)
OUT=ROOT/'SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_IDENTITY_AUDIT.csv'
OUTMD=ROOT/'SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_IDENTITY_AUDIT.md'

def main():
    x,_=a56.a2.a1.load5(); m=a56.a2.make_market_with_open(x)
    t=a56.replay(m)
    t53=a56.a53.replay(m)
    a=t[(t.partition=='development')&(t.variant=='A56_M0_L25')].sort_values('entry_ts').reset_index(drop=True)
    g=t53[(t53.partition=='development')&(t53.guard=='G1_PRE_L25')].sort_values('entry_ts').reset_index(drop=True)
    rows=[]
    for i in range(len(a)):
        ar=a.iloc[i]; gr=g.iloc[i]
        if str(ar.warning_ts)!=str(gr.warning_ts) or str(ar.exit_ts)!=str(gr.exit_ts) or abs(float(ar.pnl)-float(gr.pnl))>1e-8:
            # Inspect both warning candles relative to H/L/R.
            p=a56.parent(m,'development'); pr=p[p.entry_ts==ar.entry_ts].iloc[0]
            H,L,R=float(pr.H),float(pr.L),float(pr.R)
            rec={'entry_ts':ar.entry_ts,'H':H,'L':L,'R':R,
                 'a56_warning_ts':ar.warning_ts,'a53_warning_ts':gr.warning_ts,
                 'a56_exit_ts':ar.exit_ts,'a53_exit_ts':gr.exit_ts,
                 'a56_pnl':float(ar.pnl),'a53_pnl':float(gr.pnl)}
            idx=m['idx']; cl=m['close']
            for tag,ts in [('a56',ar.warning_ts),('a53',gr.warning_ts)]:
                if pd.notna(ts):
                    j=a56.bar_pos(idx,ts); c=float(cl[j])
                    rec[f'{tag}_warning_close']=c; rec[f'{tag}_close_minus_L_R']=(c-L)/R; rec[f'{tag}_close_minus_H_R']=(c-H)/R
                    rec[f'{tag}_below_L']=bool(c<L-a56.EPS); rec[f'{tag}_in_literal_L25']=bool(c>=L-a56.EPS and c<=L+0.25*R+a56.EPS)
            rows.append(rec)
    z=pd.DataFrame(rows); z.to_csv(OUT,index=False)
    lines=['# A56 Identity Mismatch Technical Audit','',f'Development differing rows: **{len(z)}**.','']
    if len(z):
        lines += ['| Entry | A53 warning | A53 close-L | A53 below L | A56 warning | A56 close-L | A56 literal L25 | A53 PnL | A56 PnL |','|---|---|---:|---:|---|---:|---:|---:|---:|']
        for _,r in z.iterrows():
            lines.append(f"| {r.entry_ts} | {r.a53_warning_ts} | {r.a53_close_minus_L_R:.3f}R | {bool(r.a53_below_L)} | {r.a56_warning_ts} | {r.a56_close_minus_L_R:.3f}R | {bool(r.a56_in_literal_L25)} | ${r.a53_pnl:.2f} | ${r.a56_pnl:.2f} |")
    lines += ['','This file is a technical audit only. It does not change A56 preregistration, thresholds, gates, or economics.']
    OUTMD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'A56 identity audit differences={len(z)}')

if __name__=='__main__': main()
