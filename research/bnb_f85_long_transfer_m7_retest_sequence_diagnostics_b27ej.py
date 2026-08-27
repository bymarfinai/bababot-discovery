#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import eth_f85_f15_transfer_m1_k1_opp0 as data_base

PFX = 'BNB_F85_LONG_TRANSFER_M7_RETEST_SEQUENCE_DIAGNOSTICS_B27EJ'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_PRE = ROOT / f'{PFX}_PreH2Summary.csv'
OUT_POST = ROOT / f'{PFX}_PostBreakoutSummary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET='BNBUSDT'
MAJOR=('external','development','reference_validation')
SOURCES=('ALT_0330','RAW_0530')
BAR5=pd.Timedelta(minutes=5)


def fs(x,a,z):
    return x.iloc[int(x.index.searchsorted(a,side='left')):int(x.index.searchsorted(z,side='left'))]


def bar_at(x,ts):
    p=int(x.index.searchsorted(ts,side='left'))
    if p>=len(x) or x.index[p]!=ts:
        raise AssertionError(f'missing raw5m bar {ts}')
    return x.iloc[p]


def open_at(x,ts):
    return float(bar_at(x,ts).open)


def episodes(mask: pd.Series) -> int:
    if len(mask)==0: return 0
    a=mask.astype(bool).to_numpy()
    return int(np.sum(a & np.r_[True, ~a[:-1]]))


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x,n=3): return '-' if pd.isna(x) else f'{float(x):.{n}f}'


def pre_sequence(r,x5):
    ets=pd.Timestamp(r.entry_ts); end=pd.Timestamp(r.execution_end)
    H=float(r.H); L=float(r.L); R=float(r.R); F85=float(r.entry_level)
    h2 = str(r.structural_outcome)=='H2' and pd.notna(r.structural_h2_ts)
    h2ts = pd.Timestamp(r.structural_h2_ts) if h2 else pd.NaT
    stop = h2ts if h2 else end
    q=fs(x5,ets,stop)  # strictly before H2 bar; no intrabar order assumptions
    if len(q) and q.index[0]!=ets: raise AssertionError(f'entry slice drift {r.candidate_id}')
    touch=(q.low.astype(float)<=F85) if len(q) else pd.Series(dtype=bool)
    nret=episodes(touch)
    first_ts=pd.NaT; first_hold=False; first_close_below=False
    deepest=np.nan
    first_below_ts=pd.NaT; second_reclaim_ts=pd.NaT; entry2_ts=pd.NaT; entry2_px=np.nan
    if len(q):
        deepest=(F85-float(q.low.min()))/R
        if bool(touch.any()):
            i=int(np.flatnonzero(touch.to_numpy())[0]); first_ts=pd.Timestamp(q.index[i]); b=q.iloc[i]
            first_hold=bool(float(b.close)>=F85); first_close_below=bool(float(b.close)<F85)
        below=q.close.astype(float)<F85
        if bool(below.any()):
            ib=int(np.flatnonzero(below.to_numpy())[0]); first_below_ts=pd.Timestamp(q.index[ib])
            after=q.iloc[ib+1:]
            rr=after.close.astype(float)>=F85
            if bool(rr.any()):
                ir=int(np.flatnonzero(rr.to_numpy())[0]); second_reclaim_ts=pd.Timestamp(after.index[ir])
        elif pd.notna(first_ts) and first_hold:
            second_reclaim_ts=first_ts
        if pd.notna(second_reclaim_ts):
            nts=second_reclaim_ts+BAR5
            if nts < (h2ts if h2 else end):
                entry2_ts=nts; entry2_px=open_at(x5,nts)
    if h2 and nret==0: path='DIRECT_H2_NO_RETEST'
    elif h2 and pd.notna(first_below_ts) and pd.notna(second_reclaim_ts): path='ACCEPT_BELOW_RERECLAIM_THEN_H2'
    elif h2 and nret>0: path='RETEST_THEN_H2'
    elif (not h2) and nret>0: path='RETEST_NO_H2'
    else: path='NO_RETEST_NO_H2'
    return {
        'pre_h2_retest_episodes':nret,
        'pre_h2_retest_bucket':'0' if nret==0 else ('1' if nret==1 else ('2' if nret==2 else '3+')),
        'first_f85_retest_ts':first_ts,
        'first_f85_retest_hold':first_hold,
        'first_f85_retest_close_below':first_close_below,
        'first_close_below_f85_ts':first_below_ts,
        'second_reclaim_ts':second_reclaim_ts,
        'entry2_exists':pd.notna(entry2_ts),
        'entry2_ts':entry2_ts,'entry2_px':entry2_px,
        'entry2_depth_R':((entry2_px-L)/R) if pd.notna(entry2_px) else np.nan,
        'entry2_reward_to_H_R':((H-entry2_px)/R) if pd.notna(entry2_px) else np.nan,
        'minutes_entry1_to_entry2':((entry2_ts-ets).total_seconds()/60) if pd.notna(entry2_ts) else np.nan,
        'deepest_below_f85_pre_h2_R':deepest,
        'pre_h2_path':path,
    }


def first_strict_breakout(r,x5):
    if str(r.structural_outcome)!='H2' or pd.isna(r.structural_h2_ts): return pd.NaT
    h2ts=pd.Timestamp(r.structural_h2_ts); end=pd.Timestamp(r.execution_end); H=float(r.H)
    q=fs(x5,h2ts,end)
    hit=q.close.astype(float)>H
    if not bool(hit.any()): return pd.NaT
    return pd.Timestamp(q.index[int(np.flatnonzero(hit.to_numpy())[0])])


def post_breakout(r,x5):
    H=float(r.H); R=float(r.R); end=pd.Timestamp(r.execution_end)
    h2 = str(r.structural_outcome)=='H2' and pd.notna(r.structural_h2_ts)
    if not h2:
        return {'h2_bar_close_above_H':False,'strict_H_breakout_ts':pd.NaT,'strict_H_breakout':False,
                'post_breakout_first_event':'NO_H2','h_retest_episodes_before_E10':np.nan,
                'h_retest_episodes_before_E20':np.nan,'hold_retest_then_E10':False,'hold_retest_then_E20':False}
    h2ts=pd.Timestamp(r.structural_h2_ts); h2bar=bar_at(x5,h2ts)
    bts=first_strict_breakout(r,x5)
    if pd.isna(bts):
        return {'h2_bar_close_above_H':bool(float(h2bar.close)>H),'strict_H_breakout_ts':pd.NaT,'strict_H_breakout':False,
                'post_breakout_first_event':'NO_STRICT_H_BREAKOUT','h_retest_episodes_before_E10':np.nan,
                'h_retest_episodes_before_E20':np.nan,'hold_retest_then_E10':False,'hold_retest_then_E20':False}
    start=bts+BAR5; q=fs(x5,start,end); E10=H+.10*R; E20=H+.20*R
    event='TIMEOUT'; event_ts=pd.NaT; first_hold_ts=pd.NaT
    for ts,b in q.iterrows():
        e10=float(b.high)>=E10; ret=float(b.low)<=H; fail=float(b.close)<H; hold=ret and float(b.close)>=H
        if e10 and (ret or fail):
            event='AMBIGUOUS_E10_H_INTERACTION'; event_ts=pd.Timestamp(ts); break
        if e10:
            event='E10_CONTINUATION'; event_ts=pd.Timestamp(ts); break
        if fail:
            event='H_FAIL_ACCEPT_BELOW'; event_ts=pd.Timestamp(ts); break
        if hold:
            event='H_HOLD_RETEST'; event_ts=pd.Timestamp(ts); first_hold_ts=pd.Timestamp(ts); break
    # retest episodes before first E10/E20, strict after breakout bar
    def ret_before(level):
        hit=q.high.astype(float)>=level
        z=q.iloc[:int(np.flatnonzero(hit.to_numpy())[0])] if bool(hit.any()) else q
        return episodes(z.low.astype(float)<=H)
    r10=ret_before(E10); r20=ret_before(E20)
    if pd.isna(first_hold_ts) and event=='H_HOLD_RETEST': first_hold_ts=event_ts
    e10_after=False; e20_after=False
    if pd.notna(first_hold_ts):
        z=fs(x5,first_hold_ts+BAR5,end)
        e10_after=bool((z.high.astype(float)>=E10).any()) if len(z) else False
        e20_after=bool((z.high.astype(float)>=E20).any()) if len(z) else False
    return {'h2_bar_close_above_H':bool(float(h2bar.close)>H),'strict_H_breakout_ts':bts,'strict_H_breakout':True,
            'post_breakout_first_event':event,'post_breakout_first_event_ts':event_ts,
            'h_retest_episodes_before_E10':r10,'h_retest_episodes_before_E20':r20,
            'hold_retest_then_E10':e10_after,'hold_retest_then_E20':e20_after}


def summarize_pre(q):
    return {
        'n':len(q),'h2_rate':float(q.structural_outcome.eq('H2').mean()) if len(q) else np.nan,
        'entry2_rate':float(q.entry2_exists.astype(bool).mean()) if len(q) else np.nan,
        'entry2_depth_median_R':float(q.entry2_depth_R.dropna().median()) if q.entry2_depth_R.notna().any() else np.nan,
        'entry2_reward_H_median_R':float(q.entry2_reward_to_H_R.dropna().median()) if q.entry2_reward_to_H_R.notna().any() else np.nan,
        'entry1_to_entry2_median_min':float(q.minutes_entry1_to_entry2.dropna().median()) if q.minutes_entry1_to_entry2.notna().any() else np.nan,
    }


def main():
    if (ROOT/'BNB_F85_LONG_TRANSFER_M6_ENTRY_DEPTH_DIAGNOSTICS_B27EI_Status.txt').read_text().strip()!='B27EI_BNB_ENTRY_DEPTH_DIAGNOSTICS_COMPLETE':
        raise AssertionError('B27EI prerequisite drift')
    x5,coverage=data_base.load5(TARGET)
    if coverage<.995: raise AssertionError(f'coverage below gate {coverage}')
    d=pd.read_csv(ROOT/'BNB_F85_F15_TRANSFER_M4_PATH_DIAGNOSTICS_B27EG_Detail.csv')
    for c in ('entry_ts','execution_end','confirmation_bar_start','structural_h2_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    q=d[d.accepted.astype(bool)&d.partition.isin(MAJOR)&d.side.eq('LONG')&d.source.isin(SOURCES)].copy().sort_values('entry_ts').reset_index(drop=True)
    if len(q)!=106 or q.source.value_counts().to_dict()!={'ALT_0330':55,'RAW_0530':51}: raise AssertionError('frozen LONG identity drift')
    # audit against B27EI IDs and entry geometry
    ei=pd.read_csv(ROOT/'BNB_F85_LONG_TRANSFER_M6_ENTRY_DEPTH_DIAGNOSTICS_B27EI_Detail.csv')
    if set(ei.candidate_id)!=set(q.candidate_id): raise AssertionError('B27EI candidate join drift')
    for r in q.itertuples(index=False):
        if abs(open_at(x5,pd.Timestamp(r.entry_ts))-float(r.entry_px))>max(1e-10,abs(float(r.entry_px))*1e-10): raise AssertionError(f'entry open drift {r.candidate_id}')
        c=bar_at(x5,pd.Timestamp(r.confirmation_bar_start))
        if float(c.close)<=float(r.entry_level): raise AssertionError(f'initial reclaim drift {r.candidate_id}')
    rows=[]
    for _,r in q.iterrows(): rows.append({**r.to_dict(),**pre_sequence(r,x5),**post_breakout(r,x5)})
    z=pd.DataFrame(rows); z.to_csv(OUT_DETAIL,index=False)

    pre=[]
    for scope in ('POOLED_LONG',*SOURCES):
        s=z if scope=='POOLED_LONG' else z[z.source.eq(scope)]
        for bucket in ('ALL','0','1','2','3+'):
            a=s if bucket=='ALL' else s[s.pre_h2_retest_bucket.eq(bucket)]
            pre.append({'scope':scope,'retest_bucket':bucket,**summarize_pre(a)})
        for beh in ('FIRST_HOLD','FIRST_CLOSE_BELOW'):
            a=s[s.first_f85_retest_hold.astype(bool)] if beh=='FIRST_HOLD' else s[s.first_f85_retest_close_below.astype(bool)]
            pre.append({'scope':scope,'retest_bucket':beh,**summarize_pre(a)})
    predf=pd.DataFrame(pre); predf.to_csv(OUT_PRE,index=False)

    post=[]
    for scope in ('POOLED_LONG',*SOURCES):
        s=z if scope=='POOLED_LONG' else z[z.source.eq(scope)]
        h=s[s.structural_outcome.eq('H2')]; b=h[h.strict_H_breakout.astype(bool)]
        for ev in ['ALL','E10_CONTINUATION','H_HOLD_RETEST','H_FAIL_ACCEPT_BELOW','AMBIGUOUS_E10_H_INTERACTION','TIMEOUT']:
            a=b if ev=='ALL' else b[b.post_breakout_first_event.eq(ev)]
            post.append({'scope':scope,'event':ev,'n':len(a),'rate_of_breakouts':len(a)/len(b) if len(b) else np.nan,
                         'median_H_retests_before_E10':float(a.h_retest_episodes_before_E10.dropna().median()) if len(a) and a.h_retest_episodes_before_E10.notna().any() else np.nan,
                         'median_H_retests_before_E20':float(a.h_retest_episodes_before_E20.dropna().median()) if len(a) and a.h_retest_episodes_before_E20.notna().any() else np.nan,
                         'hold_then_E10_rate':float(a.hold_retest_then_E10.astype(bool).mean()) if len(a) else np.nan,
                         'hold_then_E20_rate':float(a.hold_retest_then_E20.astype(bool).mean()) if len(a) else np.nan})
    postdf=pd.DataFrame(post); postdf.to_csv(OUT_POST,index=False)

    h=z[z.structural_outcome.eq('H2')]
    dist=h.pre_h2_retest_bucket.value_counts(normalize=True)
    if dist.get('0',0)>=.60: prelabel='DIRECT_CONTINUATION_DOMINANT'
    elif dist.get('1',0)>=.50: prelabel='ONE_RETEST_DOMINANT'
    elif dist.get('2',0)+dist.get('3+',0)>=.50: prelabel='MULTI_RETEST_DOMINANT'
    else: prelabel='MIXED_PRE_H2_SEQUENCE'
    b=h[h.strict_H_breakout.astype(bool)]
    rates=b.post_breakout_first_event.value_counts(normalize=True) if len(b) else pd.Series(dtype=float)
    if rates.get('E10_CONTINUATION',0)>=.50: postlabel='DIRECT_EXTENSION_DOMINANT'
    elif rates.get('H_HOLD_RETEST',0)>=.50: postlabel='H_RETEST_DOMINANT'
    elif rates.get('H_FAIL_ACCEPT_BELOW',0)>=.50: postlabel='FAILED_BREAKOUT_DOMINANT'
    else: postlabel='MIXED_POST_BREAKOUT_SEQUENCE'

    pathcounts=z.pre_h2_path.value_counts()
    entry2=z[z.entry2_exists.astype(bool)]
    lines=['# BNB F85 LONG Transfer — M7 Retest Sequence Diagnostics — B27EJ Result','',
           f'Raw BNB 5m coverage: **{coverage:.4%}**. Frozen accepted LONG identity: **PASS (106 = 55 ALT_0330 + 51 RAW_0530)**.','',
           'B27EJ is sequence diagnosis only; no ENTRY2 PnL or strategy change is executed.','',
           '## Where current entry sits','',
           '- Frozen current entry is **ENTRY1**: the next-open immediately after the first F85 reclaim. It is not ENTRY2.',
           f'- A causal descriptive ENTRY2 exists in **{len(entry2)}/{len(z)} ({pct(len(entry2)/len(z))})** signals after a retest/re-reclaim sequence.',
           f'- ENTRY2 median delay from ENTRY1: **{num(entry2.minutes_entry1_to_entry2.median(),1)} min**; median depth **{num(entry2.entry2_depth_R.median())}R**; median reward-to-H **{num(entry2.entry2_reward_to_H_R.median())}R**.','',
           '## Before H2: how many F85 retests?','',
           '| Retest episodes | H2 trades | Share of H2 trades |', '|---|---:|---:|']
    for k in ('0','1','2','3+'):
        n=int((h.pre_h2_retest_bucket==k).sum()); lines.append(f'| {k} | {n} | {pct(n/len(h) if len(h) else np.nan)} |')
    lines += ['',f'**Pre-H2 label: {prelabel}**','', '### Path counts','']
    for k,v in pathcounts.items(): lines.append(f'- {k}: **{int(v)}**')
    firstret=z[z.first_f85_retest_ts.notna()]
    lines += ['', '### First retest behavior','',
              f'- Signals with at least one pre-H2 F85 retest: **{len(firstret)}/{len(z)} ({pct(len(firstret)/len(z))})**.',
              f'- First retest holds F85 on close: **{int(firstret.first_f85_retest_hold.sum())}/{len(firstret)} ({pct(firstret.first_f85_retest_hold.mean() if len(firstret) else np.nan)})**.',
              f'- First retest closes below F85: **{int(firstret.first_f85_retest_close_below.sum())}/{len(firstret)} ({pct(firstret.first_f85_retest_close_below.mean() if len(firstret) else np.nan)})**.','',
              '## After H2 / strict H breakout','',
              f'- H2 trades: **{len(h)}**; strict completed-close breakout >H: **{len(b)} ({pct(len(b)/len(h) if len(h) else np.nan)})**.','',
              '| First event after strict H breakout | N | Rate |','|---|---:|---:|']
    for ev in ('E10_CONTINUATION','H_HOLD_RETEST','H_FAIL_ACCEPT_BELOW','AMBIGUOUS_E10_H_INTERACTION','TIMEOUT'):
        n=int((b.post_breakout_first_event==ev).sum()); lines.append(f'| {ev} | {n} | {pct(n/len(b) if len(b) else np.nan)} |')
    hold=b[b.post_breakout_first_event.eq('H_HOLD_RETEST')]
    lines += ['',f'**Post-breakout label: {postlabel}**','',
              f'- When the first post-breakout event is an H hold-retest, later E10 is reached in **{pct(hold.hold_retest_then_E10.mean() if len(hold) else np.nan)}**, E20 in **{pct(hold.hold_retest_then_E20.mean() if len(hold) else np.nan)}**.','',
              '**Status: B27EJ_BNB_RETEST_SEQUENCE_DIAGNOSTICS_COMPLETE**','',
              'B27EJ stops here. No ENTRY2 economics, filtering, or live integration is run automatically.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text('B27EJ_BNB_RETEST_SEQUENCE_DIAGNOSTICS_COMPLETE\n')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
