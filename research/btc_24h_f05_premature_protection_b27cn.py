#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
BASE_SUM = ROOT / 'BTC_24H_F05_STATE_MACHINE_B27CL_Summary.csv'
OUT_MD = ROOT / 'BTC_24H_F05_PREMATURE_PROTECTION_B27CN_Result.md'
OUT_TRADES = ROOT / 'BTC_24H_F05_PREMATURE_PROTECTION_B27CN_Trades.csv'
OUT_SUM = ROOT / 'BTC_24H_F05_PREMATURE_PROTECTION_B27CN_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_F05_PREMATURE_PROTECTION_B27CN_Status.txt'
OUT_AUDIT = ROOT / 'BTC_24H_F05_PREMATURE_PROTECTION_B27CN_Audit.txt'

BAR5 = pd.Timedelta(minutes=5)
EXTRA = pd.Timedelta(hours=4)
MAJOR = ('external','development','reference_validation')
REUSED = ('external','reference_validation')
CLOCKS = ('00-04','04-08','08-12','12-16','16-20','20-00')
WIB = {'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
NOTIONAL = 500.0
FEE = 0.40
EPS = 1e-12


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a=int(x5.index.searchsorted(start,'left'))
    b=int(x5.index.searchsorted(end,'left'))
    return x5.iloc[a:b]


def boundary_open_or_close(x5: pd.DataFrame, q_before: pd.DataFrame, end: pd.Timestamp, label: str):
    pos=int(x5.index.searchsorted(end,'left'))
    if pos < len(x5) and x5.index[pos] == end:
        return end,float(x5.iloc[pos].open),label+'_OPEN'
    assert len(q_before)>0
    return q_before.index[-1]+BAR5,float(q_before.iloc[-1].close),label+'_FALLBACK_CLOSE'


def load_source() -> pd.DataFrame:
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','reclaim_complete_ts','terminal_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    d['eligible']=as_bool(d['eligible'])
    q=d[d.partition.isin(MAJOR)&d.eligible].copy()
    exp={'external':202,'development':333,'reference_validation':194}
    outcomes={
        'external':{'REBREAK_LOW':149,'HIGH_BREAK':9,'NO_BOUNDARY_BY_BLOCK_END':44},
        'development':{'REBREAK_LOW':237,'HIGH_BREAK':23,'NO_BOUNDARY_BY_BLOCK_END':73},
        'reference_validation':{'REBREAK_LOW':133,'HIGH_BREAK':9,'NO_BOUNDARY_BY_BLOCK_END':52},
    }
    assert len(q)==729
    for p,n in exp.items():
        z=q[q.partition.eq(p)]; assert len(z)==n,(p,len(z),n)
        got=z.terminal_type.value_counts().to_dict()
        for k,v in outcomes[p].items(): assert int(got.get(k,0))==v,(p,k,got.get(k,0),v)
    return q.sort_values(['obs_start','partition']).reset_index(drop=True)


def pnl(entry: float, exit_px: float):
    gross=(entry-exit_px)/entry
    return gross,gross*NOTIONAL-FEE


def eval_one(x5: pd.DataFrame, r) -> dict:
    start=pd.Timestamp(r.reclaim_complete_ts); obs_end=pd.Timestamp(r.obs_end); ext_end=obs_end+EXTRA
    H=float(r.H); L=float(r.L); R4=float(r.R4)
    assert R4>0 and abs(R4-(H-L))<1e-7*max(1.0,R4)
    F05=L+.05*R4; T5=L-.05*R4; T75=L-.075*R4; T10=L-.10*R4
    assert T10<T75<T5<L<F05<H

    q0=fast_slice(x5,start,obs_end)
    qall=fast_slice(x5,start,ext_end)
    assert len(q0)>=1 and q0.index[0]==start and len(qall)>=len(q0)

    base={'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
          'obs_start':pd.Timestamp(r.obs_start),'obs_end':obs_end,'reclaim_complete_ts':start,
          'source_terminal_type':str(r.terminal_type),'H':H,'L':L,'R4':R4,
          'F05':F05,'T5':T5,'T7p5':T75,'T10':T10}

    # Exact B27CL entry semantics; entries are allowed only inside original block.
    fill_idx=None; fill_ts=pd.NaT; entry=np.nan; cancel='NO_FILL_BEFORE_BLOCK_END'
    for i,b in enumerate(q0.itertuples()):
        o=float(b.open); h=float(b.high); c=float(b.close)
        if o>=H:
            cancel='HIGH_INVALIDATED_BEFORE_FILL'; break
        if h>=F05:
            fill_idx=i; fill_ts=q0.index[i]; entry=o if o>=F05 else F05
            if entry>=H:
                fill_idx=None; fill_ts=pd.NaT; entry=np.nan; cancel='HIGH_INVALIDATED_BEFORE_FILL'
            break
        if c<L:
            cancel='REBREAK_BEFORE_FILL'; break
        if c>H:
            cancel='HIGH_BREAK_BEFORE_FILL'; break

    if fill_idx is None:
        return {**base,'filled':False,'cancel_reason':cancel,'fill_ts':pd.NaT,'entry_px':np.nan,
                'rebreak_confirmed':False,'rebreak_complete_ts':pd.NaT,'t5_reached':False,'t75_reached':False,'t10_reached':False,
                'extension_used':False,'ratchets':0,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'NO_TRADE','exit_kind':'NONE',
                'gross_return':np.nan,'net_pnl_usd':np.nan,'hold_minutes':np.nan,'exit_ext_from_L_r4':np.nan,'peak_favorable_from_L_r4':np.nan}

    # fill_idx in q0 is also same index in qall because both start identically.
    active=np.nan; active_kind='NONE'; pending=np.nan; pending_kind='NONE'
    rebreak=False; rebreak_complete=pd.NaT; t5=t75=t10=False; ratchets=0
    extension_used=False; reason=None; exit_kind='NONE'; exit_ts=pd.NaT; exit_px=np.nan
    highs=qall.high.astype(float).to_numpy()

    fb=qall.iloc[fill_idx]; fb_ts=qall.index[fill_idx]; fb_c=float(fb.close)
    if fb_c>H:
        exit_ts=fb_ts+BAR5; exit_px=fb_c; reason='FULL_SL_HIGH_BREAK'; exit_kind='HIGH'
    elif fb_c<L:
        rebreak=True; rebreak_complete=fb_ts+BAR5

    for i in range(fill_idx+1,len(qall)):
        if reason is not None: break
        ts=qall.index[i]; b=qall.iloc[i]

        # At original block boundary: T10-complete trades preserve B27CL time exit.
        # Pre-T10 unresolved trades receive exactly one frozen +4h extension.
        if ts>=obs_end and not extension_used:
            if t10:
                exit_ts=obs_end; exit_px=float(b.open); reason='TIME_ORIGINAL_BLOCK_END_OPEN'; exit_kind='TIME_ORIGINAL'; break
            extension_used=True

        o=float(b.open); hi=float(b.high); lo=float(b.low); c=float(b.close)

        # Prior completed bar's protection becomes active now.
        if np.isfinite(pending):
            if (not np.isfinite(active)) or pending<active-EPS:
                active=float(pending); active_kind=str(pending_kind)
            pending=np.nan; pending_kind='NONE'

        # Existing resting ceiling has priority on same-bar ambiguity.
        if np.isfinite(active):
            if o>=active:
                exit_ts=ts; exit_px=o; reason='CEILING_OPEN_EXIT'; exit_kind=active_kind; break
            if hi>=active:
                exit_ts=ts+BAR5; exit_px=active; reason='CEILING_STOP'; exit_kind=active_kind; break

        # Without active protection, only a completed structural High break is a full loss.
        if not np.isfinite(active) and c>H:
            exit_ts=ts+BAR5; exit_px=c; reason='FULL_SL_HIGH_BREAK'; exit_kind='HIGH'; break

        if not rebreak:
            if c<L:
                rebreak=True; rebreak_complete=ts+BAR5
            continue

        # Milestones only from first raw bar after confirmation.
        if ts<rebreak_complete:
            continue

        milestone=np.nan; mkind='NONE'
        if lo<=T10:
            t5=t75=t10=True; milestone=T10; mkind='T10'
        elif lo<=T75:
            t5=t75=True; milestone=T5; mkind='T5'
        elif lo<=T5:
            t5=True; milestone=L; mkind='L'

        if np.isfinite(milestone):
            cur=active if np.isfinite(active) else math.inf
            pen=pending if np.isfinite(pending) else math.inf
            if milestone<min(cur,pen)-EPS:
                pending=milestone; pending_kind=mkind

        # Strict 3-bar pivot-high runner only after T10 has been reached.
        if t10 and i>=2 and qall.index[i-2]>=rebreak_complete:
            if highs[i-1]>highs[i-2] and highs[i-1]>highs[i]:
                piv=float(highs[i-1])
                cur=active if np.isfinite(active) else math.inf
                pen=pending if np.isfinite(pending) else math.inf
                if piv<min(cur,pen)-EPS:
                    pending=piv; pending_kind='STRUCTURAL'; ratchets+=1

    if reason is None:
        if extension_used:
            qend=fast_slice(x5,start,ext_end)
            exit_ts,exit_px,reason=boundary_open_or_close(x5,qend,ext_end,'TIME_EXTENDED_END')
            exit_kind='TIME_EXTENDED'
        else:
            # This occurs when data loop ended before obs_end unexpectedly; preserve original boundary exit.
            qend=fast_slice(x5,start,obs_end)
            exit_ts,exit_px,reason=boundary_open_or_close(x5,qend,obs_end,'TIME_ORIGINAL_BLOCK_END')
            exit_kind='TIME_ORIGINAL'

    gross,net=pnl(entry,float(exit_px))
    horizon_end=pd.Timestamp(exit_ts)
    aq=fast_slice(x5,fill_ts,horizon_end if horizon_end>fill_ts else fill_ts+BAR5)
    peak=float((L-float(aq.low.min()))/R4) if len(aq) else np.nan
    ext=float((L-float(exit_px))/R4)
    return {**base,'filled':True,'cancel_reason':'','fill_ts':fill_ts,'entry_px':entry,
            'rebreak_confirmed':bool(rebreak),'rebreak_complete_ts':rebreak_complete,
            't5_reached':bool(t5),'t75_reached':bool(t75),'t10_reached':bool(t10),
            'extension_used':bool(extension_used),'ratchets':int(ratchets),
            'exit_ts':exit_ts,'exit_px':float(exit_px),'exit_reason':reason,'exit_kind':exit_kind,
            'gross_return':gross,'net_pnl_usd':net,
            'hold_minutes':float((pd.Timestamp(exit_ts)-fill_ts)/pd.Timedelta(minutes=1)),
            'exit_ext_from_L_r4':ext,'peak_favorable_from_L_r4':peak}


def max_drawdown(net: pd.Series) -> float:
    x=pd.to_numeric(net,errors='coerce').dropna().to_numpy(float)
    if len(x)==0:return np.nan
    cum=np.concatenate([[0.0],np.cumsum(x)]); peak=np.maximum.accumulate(cum)
    return float(np.max(peak-cum))


def max_loss_streak(net: pd.Series) -> int:
    x=pd.to_numeric(net,errors='coerce').dropna().to_numpy(float); cur=best=0
    for v in x:
        if v<0: cur+=1; best=max(best,cur)
        else: cur=0
    return int(best)


def metrics(g: pd.DataFrame) -> dict:
    source_n=int(len(g)); t=g[g.filled].copy().sort_values(['fill_ts','obs_start']); n=int(len(t))
    if n==0:
        return {'source_n':source_n,'trades_n':0,'fill_rate':0.0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'total_net':0.0,
                'avg_win':np.nan,'avg_loss':np.nan,'max_dd':np.nan,'max_loss_streak':0,'median_hold_min':np.nan,
                'full_sl_n':0,'l_lock_n':0,'t5_lock_n':0,'t10_lock_n':0,'structural_n':0,'time_original_n':0,'time_extended_n':0,
                'extension_used_n':0,'rebreak_n':0,'t5_reach_n':0,'t75_reach_n':0,'t10_reach_n':0}
    net=pd.to_numeric(t.net_pnl_usd,errors='coerce'); pos=net[net>0]; neg=net[net<0]
    gp=float(pos.sum()); gl=float(-neg.sum()); pf=gp/gl if gl>0 else (math.inf if gp>0 else np.nan)
    kind=t.exit_kind.astype(str); reason=t.exit_reason.astype(str)
    full=int((reason=='FULL_SL_HIGH_BREAK').sum())
    lk=int(kind.eq('L').sum()); t5k=int(kind.eq('T5').sum()); t10k=int(kind.eq('T10').sum()); st=int(kind.eq('STRUCTURAL').sum())
    torig=int(kind.eq('TIME_ORIGINAL').sum()); text=int(kind.eq('TIME_EXTENDED').sum())
    ext_unresolved=int((kind.eq('TIME_EXTENDED') & ~t.t10_reached).sum())
    t10family=int((kind.isin(['T10','STRUCTURAL'])) .sum() + (kind.str.startswith('TIME') & t.t10_reached).sum())
    return {'source_n':source_n,'trades_n':n,'fill_rate':n/source_n if source_n else np.nan,
            'wr':float((net>0).mean()),'pf':pf,'expectancy':float(net.mean()),'total_net':float(net.sum()),
            'avg_win':float(pos.mean()) if len(pos) else np.nan,'avg_loss':float(neg.mean()) if len(neg) else np.nan,
            'max_dd':max_drawdown(net),'max_loss_streak':max_loss_streak(net),'median_hold_min':float(t.hold_minutes.median()),
            'full_sl_n':full,'full_sl_rate':full/n,'l_lock_n':lk,'t5_lock_n':t5k,'t10_lock_n':t10k,'structural_n':st,
            'time_original_n':torig,'time_extended_n':text,'extension_used_n':int(t.extension_used.sum()),
            'rebreak_n':int(t.rebreak_confirmed.sum()),'t5_reach_n':int(t.t5_reached.sum()),'t75_reach_n':int(t.t75_reached.sum()),'t10_reach_n':int(t.t10_reached.sum()),
            'per100_full_sl':100*full/n,'per100_intermediate':100*(lk+t5k)/n,'per100_t10_family':100*t10family/n,
            'per100_extended_unresolved':100*ext_unresolved/n,'per100_wins':100*float((net>0).mean())}


def summarize(d: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for p in MAJOR: rows.append({'scope':'PARTITION','name':p,**metrics(d[d.partition.eq(p)])})
    rows.append({'scope':'POOL','name':'POOLED_REUSED_EXTVAL',**metrics(d[d.partition.isin(REUSED)])})
    rows.append({'scope':'POOL','name':'POOLED_MAJOR',**metrics(d)})
    for cb in CLOCKS:
        rows.append({'scope':'CLOCK_REUSED','name':cb,**metrics(d[d.partition.isin(REUSED)&d.clock_block.eq(cb)])})
        rows.append({'scope':'CLOCK_MAJOR','name':cb,**metrics(d[d.clock_block.eq(cb)])})
    return pd.DataFrame(rows)


def getrow(s,scope,name):
    z=s[(s.scope==scope)&(s.name==name)]; assert len(z)==1,(scope,name,len(z)); return z.iloc[0]

def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x): return '-' if pd.isna(x) else f'{float(x):.2f}'
def money(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'
def pfmt(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def load_b27cl_baseline():
    b=pd.read_csv(BASE_SUM)
    return b


def baseline_row(b,scope,name):
    z=b[(b.scope==scope)&(b.name==name)]; assert len(z)==1,(scope,name); return z.iloc[0]


def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    d=pd.DataFrame([eval_one(x5,r) for r in src.itertuples(index=False)])
    assert len(d)==729
    expected={'external':183,'development':297,'reference_validation':172}
    for p,n in expected.items(): assert int(d[d.partition.eq(p)].filled.sum())==n,(p,int(d[d.partition.eq(p)].filled.sum()),n)
    assert int(d.filled.sum())==652
    d.to_csv(OUT_TRADES,index=False)
    s=summarize(d); s.to_csv(OUT_SUM,index=False)
    b=load_b27cl_baseline()

    ext=getrow(s,'PARTITION','external'); dev=getrow(s,'PARTITION','development'); val=getrow(s,'PARTITION','reference_validation'); major=getrow(s,'POOL','POOLED_MAJOR')
    econ=bool(dev.expectancy>0 and dev.pf>=1.10 and ext.expectancy>0 and ext.pf>1.0 and val.expectancy>0 and val.pf>1.0 and major.expectancy>0 and major.pf>=1.10)
    full=bool(ext.full_sl_rate<=.10 and dev.full_sl_rate<=.10 and val.full_sl_rate<=.10)
    candidate=econ and full
    hq70=bool(ext.wr>=.70 and dev.wr>=.70 and val.wr>=.70)
    verdict='B27CN_REUSED_DATA_ECON_CANDIDATE' if candidate else 'B27CN_REUSED_DATA_ECON_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text('\n'.join([
        'audit=PASS','raw_rows=698112','coverage=1.0','source_major=729',
        'fills_external=183','fills_development=297','fills_validation=172','fills_major=652',
        'data_reuse=external_and_reference_validation_seen_in_B27CM','untouched_holdout=NONE'])+'\n')

    lines=['# B27CN — BTC 24H F05 Delayed-Protection + 4H Rescue Economics — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CE source and B27CL executable fill identity reproduced: external 183 / development 297 / validation 172 / major 652.','',
           '**Validation caveat:** external/reference_validation were already inspected in B27CM and are reused-data confirmation, **not untouched OOS**.','',
           'Configuration: F05 entry; **no BE at L or rebreak**; first protection only after T5 (lock L); T7.5 -> lock T5; T10 -> lock T10 + strict 3-bar pivot-high runner; pre-T10 unresolved at block end gets exactly +4h. $500 notional, $0.40 fee.','',
           '## Six-clock reused external+validation economics — first','',
           '| UTC / WIB | N | WR | PF | Exp/trade | Net | Full SL | L/T5 locks | T10 family | Extension used | Extended unresolved |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=getrow(s,'CLOCK_REUSED',cb)
        t10fam=(r.t10_lock_n+r.structural_n)
        lines.append(f'| {cb} / {WIB[cb]} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {int(r.full_sl_n)} | {int(r.l_lock_n+r.t5_lock_n)} | {int(t10fam)} | {int(r.extension_used_n)} | {r.per100_extended_unresolved:.1f}/100 |')

    lines += ['', '## Major partitions / pools','',
              '| Scope | Source | Trades | Fill | WR | PF | Exp | Net | Avg win | Avg loss | Max DD | Streak | Full SL | L-lock | T5-lock | T10-lock | Runner | Time orig | Time ext | Ext used | Rebreak | T5 | T7.5 | T10 | Median hold |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_REUSED_EXTVAL'),('POOL','POOLED_MAJOR')]:
        r=getrow(s,scope,name)
        lines.append(f'| {name} | {int(r.source_n)} | {int(r.trades_n)} | {pct(r.fill_rate)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.avg_win)} | {money(r.avg_loss)} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.full_sl_n)} | {int(r.l_lock_n)} | {int(r.t5_lock_n)} | {int(r.t10_lock_n)} | {int(r.structural_n)} | {int(r.time_original_n)} | {int(r.time_extended_n)} | {int(r.extension_used_n)} | {int(r.rebreak_n)} | {int(r.t5_reach_n)} | {int(r.t75_reach_n)} | {int(r.t10_reach_n)} | {num(r.median_hold_min)}m |')

    lines += ['', '## Per 100 filled entries','',
              '| Scope | Economic wins | Full SL | L/T5 intermediate | T10-or-runner family | Extended unresolved |',
              '|---|---:|---:|---:|---:|---:|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_REUSED_EXTVAL'),('POOL','POOLED_MAJOR')]:
        r=getrow(s,scope,name)
        lines.append(f'| {name} | {r.per100_wins:.1f} | {r.per100_full_sl:.1f} | {r.per100_intermediate:.1f} | {r.per100_t10_family:.1f} | {r.per100_extended_unresolved:.1f} |')

    lines += ['', '## Direct comparison vs B27CL on identical reused cohorts','',
              '| Scope | WR B27CL -> B27CN | PF B27CL -> B27CN | Exp B27CL -> B27CN | Net B27CL -> B27CN | Full SL B27CL -> B27CN | T10 reached B27CL -> B27CN |',
              '|---|---|---|---|---|---|---|']
    for scope,name,b_scope,b_name in [('PARTITION','external','PARTITION','external'),('PARTITION','development','PARTITION','development'),('PARTITION','reference_validation','PARTITION','reference_validation'),('POOL','POOLED_MAJOR','POOL','POOLED_MAJOR')]:
        r=getrow(s,scope,name); old=baseline_row(b,b_scope,b_name)
        lines.append(f'| {name} | {100*old.wr:.1f}% -> {100*r.wr:.1f}% | {old.pf:.2f} -> {r.pf:.2f} | ${old.expectancy:+.2f} -> ${r.expectancy:+.2f} | ${old.total_net:+.2f} -> ${r.total_net:+.2f} | {int(old.full_sl_n)} -> {int(r.full_sl_n)} | {int(old.t10_reach_n)} -> {int(r.t10_reach_n)} |')

    lines += ['', '## Frozen gate','',
              f'- reused-data economics gate: **{"PASS" if econ else "FAIL"}**',
              f'- full structural SL <=10% in every major partition: **{"PASS" if full else "FAIL"}**',
              f'- HIGH_QUALITY_70: **{"PASS" if hq70 else "FAIL"}**','',
              f'**Frozen verdict: `{verdict}`.**','',
              'Even a PASS is only a reused-data candidate; no fresh holdout remains in this lineage. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
