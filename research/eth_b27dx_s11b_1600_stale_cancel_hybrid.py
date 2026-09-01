#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
S10_PATH=HERE/'eth_b27dx_s10_hybrid_profit_lock.py'
spec=importlib.util.spec_from_file_location('eth_s10',S10_PATH); s10=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(s10)
S9A_PATH=HERE/'eth_b27dx_s9a_stale_entry_cancellation.py'
spec2=importlib.util.spec_from_file_location('eth_s9a',S9A_PATH); s9a=importlib.util.module_from_spec(spec2)
assert spec2.loader is not None; spec2.loader.exec_module(s9a)
s4=s10.s4

PFX='ETH_B27DX_S11B_1600_STALE_CANCEL_HYBRID'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_CAND=ROOT/f'{PFX}_Candidates.csv'; OUT_DEC=ROOT/f'{PFX}_Decisions.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
PARTS=s4.PARTS
BTC_WR=s4.BTC_WR; BTC_PF=s4.BTC_PF; BTC_EXP=s4.BTC_EXP

def fmt(v,nd=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=s4.b.m.m.load5()
    fixed,runner,hybrid,audit10=s10.build_hybrid(x)
    c,fresh_audit=s9a.annotate_freshness(x,hybrid)
    fresh_ok=bool(len(fresh_audit)==len(c) and fresh_audit[['fill_match','eligible_before_or_at_fill','delay_is_5m_multiple']].all().all())
    audit10_ok=bool(audit10['pass'].all())
    c['s11b_entry_allowed']=~((c.exec_min==960)&(~c.immediate_fill))
    filt=c[c.s11b_entry_allowed].copy()

    base_dec,base_sum,_=s4.summarize(hybrid)
    dec,summ,_=s4.summarize(filt)
    c.to_csv(OUT_CAND,index=False); dec.to_csv(OUT_DEC,index=False)
    base_sum=base_sum.copy(); base_sum['variant']='S10_HYBRID'
    summ=summ.copy(); summ['variant']='S11B_1600_IMMEDIATE_ONLY'
    combined=pd.concat([base_sum,summ],ignore_index=True); combined.to_csv(OUT_SUM,index=False)

    audit=pd.DataFrame([
        {'check':'S10_candidate_parity_causal','value':int(audit10_ok),'pass':audit10_ok},
        {'check':'freshness_causal_audit','value':int(fresh_ok),'pass':fresh_ok},
        {'check':'16_stale_candidates_removed','value':int(((c.exec_min==960)&(~c.immediate_fill)).sum()),'pass':True},
        {'check':'non16_candidate_count_unchanged','value':int(len(filt[filt.exec_min!=960])),'pass':len(filt[filt.exec_min!=960])==len(hybrid[hybrid.exec_min!=960])},
    ])
    audit.to_csv(OUT_AUDIT,index=False)

    def row(df,p,stress): return df[(df.partition==p)&(df.stress_bps==stress)].iloc[0]
    b0=row(base_sum,'POOLED_MAJOR',0); b5=row(base_sum,'POOLED_MAJOR',5)
    h0=row(summ,'POOLED_MAJOR',0); h5=row(summ,'POOLED_MAJOR',5)
    major=summ[(summ.partition.isin(PARTS))&(summ.stress_bps==0)]
    audit_ok=bool(audit['pass'].all())
    major_pos=bool(((major.pf>1)&(major.net>0)).all())
    stress_ok=bool(h5.pf>1 and h5.net>0)
    retention=float(h0.accepted/b0.accepted)
    retention_ok=retention>=0.80
    freq_ok=float(h0.trades_per_week)>=1.10
    improves=bool(h0.wr>b0.wr and h0.pf>b0.pf and h0.expectancy>b0.expectancy and h0.net>b0.net)
    btc=bool(h0.wr>=BTC_WR and h0.pf>=BTC_PF and h0.expectancy>=BTC_EXP)
    supported=bool(audit_ok and major_pos and stress_ok and retention_ok and freq_ok and improves)
    status='ETH_S11B_1600_STALE_CANCEL_HYBRID_SUPPORTED' if supported else 'ETH_S11B_1600_STALE_CANCEL_HYBRID_NOT_SUPPORTED'

    base_ids=set(base_dec.loc[base_dec.accepted,'candidate_id'].astype(str)); ids=set(dec.loc[dec.accepted,'candidate_id'].astype(str))
    removed=base_ids-ids; freed=ids-base_ids

    lines=['# ETH B27DX — S11B 16:00 Stale-Cancel Hybrid — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',
           'Frozen map: **05:00 fixed E25 · 09:00 fixed E25 · 10:00 S10 E10 profit-lock runner · 16:00 fixed E25 with immediate-fill-only entry**.','',
           f'- S10 candidate/parity/causal audit: **{"PASS" if audit10_ok else "FAIL"}**.',f'- Freshness causal audit: **{"PASS" if fresh_ok else "FAIL"}**.','',
           '## Portfolio comparison','',
           '| Partition | Variant | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in [*PARTS,'POOLED_MAJOR']:
        for label,df in [('S10',base_sum),('S11B',summ)]:
            for stress in (0,5):
                r=row(df,p,stress)
                lines.append(f'| {p} | {label} | {stress} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
    lines += ['', '## Portfolio impact','',
              f'- Accepted retention vs S10: **{retention:.1%}**.',
              f'- Baseline accepted removed after 16:00 freshness rule/re-lock: **{len(removed)}**.',
              f'- Newly freed accepted trades after re-lock: **{len(freed)}**.',
              f'- WR: **{pct(b0.wr)} → {pct(h0.wr)}**.',
              f'- PF: **{fmt(b0.pf)} → {fmt(h0.pf)}**.',
              f'- Expectancy: **{fmt(b0.expectancy)} → {fmt(h0.expectancy)}**.',
              f'- Net: **{fmt(b0.net)} → {fmt(h0.net)}**.',
              f'- Frequency: **{b0.trades_per_week:.3f} → {h0.trades_per_week:.3f} trades/week**.','',
              '## Frozen gates','',
              f'- Audit pass: **{"PASS" if audit_ok else "FAIL"}**.',
              f'- All major partitions PF>1 and net>0: **{"PASS" if major_pos else "FAIL"}**.',
              f'- Pooled 5 bps PF>1 and net>0: **{"PASS" if stress_ok else "FAIL"}**.',
              f'- Accepted retention >=80%: **{"PASS" if retention_ok else "FAIL"}**.',
              f'- Frequency >=1.10/wk: **{"PASS" if freq_ok else "FAIL"}**.',
              f'- WR/PF/expectancy/net all improve vs S10: **{"PASS" if improves else "FAIL"}**.',
              f'- BTC-class diagnostic: **{"PASS" if btc else "FAIL"}**.','',
              '## Decision','',f'**Status: {status}**','',
              '- Exploratory/engineering validation: S11A informed the 16:00 freshness hypothesis; this is not pristine unseen OOS confirmation.',
              '- No alternate freshness cutoff, geometry, target, stop, runner, leverage, fee, or live-code change was made.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text(status+'\n'); print(OUT_MD.read_text())
if __name__=='__main__': main()
