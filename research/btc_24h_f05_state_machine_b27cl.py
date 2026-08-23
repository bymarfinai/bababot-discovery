#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
OUT_MD = ROOT / 'BTC_24H_F05_STATE_MACHINE_B27CL_Result.md'
OUT_TRADES = ROOT / 'BTC_24H_F05_STATE_MACHINE_B27CL_Trades.csv'
OUT_SUM = ROOT / 'BTC_24H_F05_STATE_MACHINE_B27CL_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_F05_STATE_MACHINE_B27CL_Status.txt'
OUT_AUDIT = ROOT / 'BTC_24H_F05_STATE_MACHINE_B27CL_Audit.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
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
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_source() -> pd.DataFrame:
    d = pd.read_csv(SRC)
    for c in ('obs_start','obs_end','reclaim_complete_ts','terminal_ts'):
        d[c] = pd.to_datetime(d[c], utc=True, errors='coerce')
    d['eligible'] = as_bool(d['eligible'])
    q = d[d.partition.isin(MAJOR) & d.eligible].copy()
    exp = {'external':202,'development':333,'reference_validation':194}
    outcomes = {
        'external': {'REBREAK_LOW':149,'HIGH_BREAK':9,'NO_BOUNDARY_BY_BLOCK_END':44},
        'development': {'REBREAK_LOW':237,'HIGH_BREAK':23,'NO_BOUNDARY_BY_BLOCK_END':73},
        'reference_validation': {'REBREAK_LOW':133,'HIGH_BREAK':9,'NO_BOUNDARY_BY_BLOCK_END':52},
    }
    assert len(q) == 729
    for p,n in exp.items():
        z=q[q.partition.eq(p)]
        assert len(z)==n,(p,len(z),n)
        got=z.terminal_type.value_counts().to_dict()
        for k,v in outcomes[p].items(): assert int(got.get(k,0))==v,(p,k,got.get(k,0),v)
    assert len(q[q.partition.isin(OOS)]) == 396
    return q.sort_values(['obs_start','partition']).reset_index(drop=True)


def pnl(entry: float, exit_px: float) -> tuple[float,float]:
    gross = (entry-exit_px)/entry
    return gross, gross*NOTIONAL-FEE


def block_end_exit(x5: pd.DataFrame, q: pd.DataFrame, end: pd.Timestamp) -> tuple[pd.Timestamp,float,str]:
    pos=int(x5.index.searchsorted(end,side='left'))
    if pos < len(x5) and x5.index[pos] == end:
        return end,float(x5.iloc[pos].open),'TIME_BLOCK_END_OPEN'
    assert len(q)>0
    ts=q.index[-1]+BAR5
    return ts,float(q.iloc[-1].close),'TIME_FALLBACK_CLOSE'


def eval_one(x5: pd.DataFrame, r) -> dict:
    start=pd.Timestamp(r.reclaim_complete_ts); end=pd.Timestamp(r.obs_end)
    H=float(r.H); L=float(r.L); R4=float(r.R4)
    assert R4>0 and abs(R4-(H-L))<1e-7*max(1.0,R4)
    F05=L+.05*R4; T5=L-.05*R4; T75=L-.075*R4; T10=L-.10*R4
    assert T10<T75<T5<L<F05<H
    q=fast_slice(x5,start,end)
    assert len(q)>=1 and q.index[0]==start

    base={
        'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
        'obs_start':pd.Timestamp(r.obs_start),'obs_end':end,'reclaim_complete_ts':start,
        'source_terminal_type':str(r.terminal_type),'H':H,'L':L,'R4':R4,
        'F05':F05,'T5':T5,'T7p5':T75,'T10':T10,
    }

    fill_idx=None; fill_ts=pd.NaT; entry=np.nan; cancel='NO_FILL_BEFORE_BLOCK_END'
    for i,b in enumerate(q.itertuples()):
        o=float(b.open); h=float(b.high); c=float(b.close)
        if o>=H:
            cancel='HIGH_INVALIDATED_BEFORE_FILL'; break
        if h>=F05:
            fill_idx=i; fill_ts=q.index[i]
            entry=o if o>=F05 else F05
            if entry>=H:
                fill_idx=None; fill_ts=pd.NaT; entry=np.nan; cancel='HIGH_INVALIDATED_BEFORE_FILL'; break
            break
        if c<L:
            cancel='REBREAK_BEFORE_FILL'; break
        if c>H:
            cancel='HIGH_BREAK_BEFORE_FILL'; break

    if fill_idx is None:
        return {**base,'filled':False,'cancel_reason':cancel,'fill_ts':pd.NaT,'entry_px':np.nan,
                'l_touch_after_fill':False,'rebreak_confirmed':False,'rebreak_complete_ts':pd.NaT,
                't5_reached':False,'t75_reached':False,'t10_reached':False,'ratchets':0,
                'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'NO_TRADE','exit_ceiling_kind':'NONE',
                'gross_return':np.nan,'net_pnl_usd':np.nan,'hold_minutes':np.nan,
                'exit_ext_from_L_r4':np.nan,'peak_favorable_from_L_r4':np.nan}

    active_ceiling=np.nan; active_kind='NONE'
    pending_ceiling=np.nan; pending_kind='NONE'
    l_touch=False; rebreak=False; rebreak_complete=pd.NaT
    t5=False; t75=False; t10=False; ratchets=0
    exit_ts=pd.NaT; exit_px=np.nan; reason=None; exit_kind='NONE'

    highs=q.high.astype(float).to_numpy()

    # Fill-bar completed-close logic. Same-fill-bar favorable low is deliberately not used for BE.
    fb=q.iloc[fill_idx]; fb_ts=q.index[fill_idx]; fb_c=float(fb.close)
    if fb_c>H:
        exit_ts=fb_ts+BAR5; exit_px=fb_c; reason='FULL_SL_HIGH_BREAK'; exit_kind='HIGH'
    elif fb_c<L:
        rebreak=True; rebreak_complete=fb_ts+BAR5
        pending_ceiling=entry; pending_kind='BE'

    for i in range(fill_idx+1,len(q)):
        if reason is not None: break
        ts=q.index[i]; b=q.iloc[i]
        o=float(b.open); hi=float(b.high); lo=float(b.low); c=float(b.close)

        # Any ceiling created by the prior completed bar becomes active now.
        if np.isfinite(pending_ceiling):
            if (not np.isfinite(active_ceiling)) or pending_ceiling<active_ceiling-EPS:
                active_ceiling=float(pending_ceiling); active_kind=str(pending_kind)
            pending_ceiling=np.nan; pending_kind='NONE'

        # Existing resting protection wins same-bar ambiguity conservatively.
        if np.isfinite(active_ceiling):
            if o>=active_ceiling:
                exit_ts=ts; exit_px=o; reason='CEILING_OPEN_EXIT'; exit_kind=active_kind; break
            if hi>=active_ceiling:
                exit_ts=ts+BAR5; exit_px=active_ceiling; reason='CEILING_STOP'; exit_kind=active_kind; break

        # Before rebreak, only a genuine completed close >H is a full structural loss.
        if not rebreak:
            if c>H:
                exit_ts=ts+BAR5; exit_px=c; reason='FULL_SL_HIGH_BREAK'; exit_kind='HIGH'; break
            if lo<=L:
                l_touch=True
                if (not np.isfinite(active_ceiling)) or entry<active_ceiling-EPS:
                    pending_ceiling=entry; pending_kind='BE'
            if c<L:
                rebreak=True; rebreak_complete=ts+BAR5
                if (not np.isfinite(active_ceiling)) or entry<active_ceiling-EPS:
                    if (not np.isfinite(pending_ceiling)) or entry<pending_ceiling-EPS:
                        pending_ceiling=entry; pending_kind='BE'
            continue

        # Milestones only begin on the next raw 5m bar after rebreak confirmation.
        if ts < rebreak_complete:
            continue

        # Deepest crossed milestone on this completed bar controls next-bar lock.
        milestone_ceiling=np.nan; milestone_kind='NONE'
        if lo<=T10:
            t5=t75=t10=True
            milestone_ceiling=T10; milestone_kind='T10'
        elif lo<=T75:
            t5=t75=True
            milestone_ceiling=T5; milestone_kind='T5'
        elif lo<=T5:
            t5=True
            milestone_ceiling=L; milestone_kind='L'

        if np.isfinite(milestone_ceiling):
            current_min = active_ceiling if np.isfinite(active_ceiling) else math.inf
            pending_min = pending_ceiling if np.isfinite(pending_ceiling) else math.inf
            if milestone_ceiling < min(current_min,pending_min)-EPS:
                pending_ceiling=milestone_ceiling; pending_kind=milestone_kind

        # F85/B27AC-style strict pivot-high runner is allowed only once T10 is reached.
        if t10 and i>=2:
            # all three bars must be at/after rebreak followthrough start
            if q.index[i-2] >= rebreak_complete:
                if highs[i-1]>highs[i-2] and highs[i-1]>highs[i]:
                    piv=float(highs[i-1])
                    current_min = active_ceiling if np.isfinite(active_ceiling) else math.inf
                    pending_min = pending_ceiling if np.isfinite(pending_ceiling) else math.inf
                    if piv < min(current_min,pending_min)-EPS:
                        pending_ceiling=piv; pending_kind='STRUCTURAL'; ratchets+=1

    if reason is None:
        exit_ts,exit_px,reason=block_end_exit(x5,q,end)
        exit_kind='TIME'

    gross,net=pnl(entry,float(exit_px))
    aq=q.iloc[fill_idx:]
    peak=float((L-float(aq.low.min()))/R4) if len(aq) else np.nan
    ext=float((L-float(exit_px))/R4)
    return {**base,'filled':True,'cancel_reason':'','fill_ts':fill_ts,'entry_px':entry,
            'l_touch_after_fill':bool(l_touch),'rebreak_confirmed':bool(rebreak),'rebreak_complete_ts':rebreak_complete,
            't5_reached':bool(t5),'t75_reached':bool(t75),'t10_reached':bool(t10),'ratchets':int(ratchets),
            'exit_ts':exit_ts,'exit_px':float(exit_px),'exit_reason':reason,'exit_ceiling_kind':exit_kind,
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
        if v<0:cur+=1;best=max(best,cur)
        else:cur=0
    return int(best)


def metrics(g: pd.DataFrame) -> dict:
    source_n=int(len(g)); t=g[g.filled].copy().sort_values(['fill_ts','obs_start']); n=int(len(t))
    if n==0:
        keys=['wr','pf','expectancy','total_net','avg_win','avg_loss','max_dd','median_hold_min']
        out={k:np.nan for k in keys}; out.update({'source_n':source_n,'trades_n':0,'fill_rate':0.0,'max_loss_streak':0})
        for k in ['full_sl_n','be_n','l_lock_n','t5_lock_n','t10_lock_n','structural_n','time_n','rebreak_n','t5_reach_n','t75_reach_n','t10_reach_n']:out[k]=0
        return out
    net=pd.to_numeric(t.net_pnl_usd,errors='coerce'); pos=net[net>0]; neg=net[net<0]
    gp=float(pos.sum()); gl=float(-neg.sum()); pf=gp/gl if gl>0 else (math.inf if gp>0 else np.nan)
    kind=t.exit_ceiling_kind.astype(str); reason=t.exit_reason.astype(str)
    full=int((reason=='FULL_SL_HIGH_BREAK').sum())
    be=int(kind.eq('BE').sum()); lk=int(kind.eq('L').sum()); t5k=int(kind.eq('T5').sum()); t10k=int(kind.eq('T10').sum()); st=int(kind.eq('STRUCTURAL').sum()); tim=int(kind.eq('TIME').sum())
    return {
        'source_n':source_n,'trades_n':n,'fill_rate':n/source_n if source_n else np.nan,
        'wr':float((net>0).mean()),'pf':pf,'expectancy':float(net.mean()),'total_net':float(net.sum()),
        'avg_win':float(pos.mean()) if len(pos) else np.nan,'avg_loss':float(neg.mean()) if len(neg) else np.nan,
        'max_dd':max_drawdown(net),'max_loss_streak':max_loss_streak(net),'median_hold_min':float(t.hold_minutes.median()),
        'full_sl_n':full,'be_n':be,'l_lock_n':lk,'t5_lock_n':t5k,'t10_lock_n':t10k,'structural_n':st,'time_n':tim,
        'rebreak_n':int(t.rebreak_confirmed.sum()),'t5_reach_n':int(t.t5_reached.sum()),'t75_reach_n':int(t.t75_reached.sum()),'t10_reach_n':int(t.t10_reached.sum()),
        'full_sl_rate':full/n,'non_full_loss_rate':1-full/n,
        'per100_full_sl':100*full/n,'per100_be':100*be/n,'per100_intermediate':100*(lk+t5k)/n,
        'per100_t10_or_runner':100*(t10k+st+int((kind.eq('TIME') & t.t10_reached).sum()))/n,
        'per100_time_other':100*int((kind.eq('TIME') & ~t.t10_reached).sum())/n,
    }


def summarize(d:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for p in MAJOR: rows.append({'scope':'PARTITION','name':p,**metrics(d[d.partition.eq(p)])})
    rows.append({'scope':'POOL','name':'POOLED_OOS',**metrics(d[d.partition.isin(OOS)])})
    rows.append({'scope':'POOL','name':'POOLED_MAJOR',**metrics(d)})
    for cb in CLOCKS:
        rows.append({'scope':'CLOCK_OOS','name':cb,**metrics(d[d.partition.isin(OOS)&d.clock_block.eq(cb)])})
        rows.append({'scope':'CLOCK_MAJOR','name':cb,**metrics(d[d.clock_block.eq(cb)])})
    return pd.DataFrame(rows)


def getrow(s,scope,name):
    z=s[(s.scope==scope)&(s.name==name)]; assert len(z)==1; return z.iloc[0]
def pct(x):return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def pfmt(x):
    if pd.isna(x):return '-'
    if math.isinf(float(x)):return 'inf'
    return f'{float(x):.2f}'
def money(x):return '-' if pd.isna(x) else f'${float(x):+.2f}'
def num(x):return '-' if pd.isna(x) else f'{float(x):.1f}'


def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1.0)<1e-12
    d=pd.DataFrame([eval_one(x5,r) for r in src.itertuples(index=False)])
    assert len(d)==729
    d.to_csv(OUT_TRADES,index=False)
    s=summarize(d); s.to_csv(OUT_SUM,index=False)

    ext=getrow(s,'PARTITION','external'); dev=getrow(s,'PARTITION','development'); val=getrow(s,'PARTITION','reference_validation'); oos=getrow(s,'POOL','POOLED_OOS')
    econ=all(float(r.expectancy)>0 and float(r.pf)>=1.10 for r in (ext,dev,val)) and float(oos.expectancy)>0 and float(oos.pf)>=1.20
    full=bool(float(oos.full_sl_rate)<=.10)
    supported=bool(econ and full)
    high70=all(float(r.wr)>=.70 for r in (ext,dev,val))
    verdict='B27CL_STATE_MACHINE_ECON_SUPPORTED' if supported else 'B27CL_STATE_MACHINE_ECON_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(f'audit=PASS\nrows={len(x5)}\ncoverage={float(cov):.12f}\nsource={len(src)}\nfills={int(d.filled.sum())}\nverdict={verdict}\nhigh_quality_70={high70}\n')

    lines=['# B27CL — BTC 24H F05 State-Machine Trade Management — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact eligible B27CE source identity/outcomes reproduced. One preregistered state machine only; no clock/regime exclusion.','',
           'Configuration: F05 entry; favorable L touch -> next-bar BE; genuine close>H -> full structural SL; confirmed rebreak -> T5/T7.5/T10 staircase; T10 -> F85-style strict 3-bar pivot-high runner. $500 notional, $0.40 fee.','',
           '## Six-clock untouched OOS economics — first','',
           '| UTC / WIB | N | WR | PF | Exp/trade | Net | Full SL | BE | Intermediate | T10+runner | Time |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=getrow(s,'CLOCK_OOS',cb)
        lines.append(f'| {cb} / {WIB[cb]} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {int(r.full_sl_n)} | {int(r.be_n)} | {int(r.l_lock_n+r.t5_lock_n)} | {int(r.t10_lock_n+r.structural_n)} | {int(r.time_n)} |')

    lines += ['', '## Major partitions and pools','',
              '| Scope | Source | Trades | Fill | WR | PF | Exp | Net | Avg win | Avg loss | Max DD | Streak | Full SL | BE | L-lock | T5-lock | T10-lock | Runner | Time | Rebreak | T5 | T7.5 | T10 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_OOS'),('POOL','POOLED_MAJOR')]:
        r=getrow(s,scope,name)
        lines.append(f'| {name} | {int(r.source_n)} | {int(r.trades_n)} | {pct(r.fill_rate)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.avg_win)} | {money(r.avg_loss)} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.full_sl_n)} | {int(r.be_n)} | {int(r.l_lock_n)} | {int(r.t5_lock_n)} | {int(r.t10_lock_n)} | {int(r.structural_n)} | {int(r.time_n)} | {int(r.rebreak_n)} | {int(r.t5_reach_n)} | {int(r.t75_reach_n)} | {int(r.t10_reach_n)} |')

    lines += ['', '## Per 100 filled entries','',
              '| Scope | Full SL | Scratch/BE | Intermediate lock | T10-or-runner family | Other time exit | Non-full-SL |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_OOS'),('POOL','POOLED_MAJOR')]:
        r=getrow(s,scope,name)
        lines.append(f'| {name} | {num(r.per100_full_sl)} | {num(r.per100_be)} | {num(r.per100_intermediate)} | {num(r.per100_t10_or_runner)} | {num(r.per100_time_other)} | {pct(r.non_full_loss_rate)} |')

    lines += ['', '## Frozen gate','',
              f'- positive economics/PF gate across all major partitions + OOS: **{"PASS" if econ else "FAIL"}**',
              f'- OOS full structural SL share <=10%: **{"PASS" if full else "FAIL"}**',
              f'- HIGH_QUALITY_70 economic WR: **{"PASS" if high70 else "FAIL"}**','',
              f'**Frozen verdict: `{verdict}`.**','',
              'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
