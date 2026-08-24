#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_direct_break_retest_short_b27bz as b27bz
import btc_24h_clock_tp_sl_b27cs as b27cs
import btc_24h_full_loser_separability_b27cv as b27cv

ROOT=Path(__file__).resolve().parent.parent
BE=ROOT/'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Detail.csv'
CE=ROOT/'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
OUT=ROOT/'BTC_24H_FRESH_PIPELINE_PARITY_B27DB_Result.md'
OUT_AUDIT=ROOT/'BTC_24H_FRESH_PIPELINE_PARITY_B27DB_Audit.txt'
OUT_STATUS=ROOT/'BTC_24H_FRESH_PIPELINE_PARITY_B27DB_Status.txt'
OUT_SRC=ROOT/'BTC_24H_FRESH_PIPELINE_PARITY_B27DB_ReconstructedSources.csv'
OUT_TRADES=ROOT/'BTC_24H_FRESH_PIPELINE_PARITY_B27DB_ReconstructedTrades.csv'

MAJOR=('external','development','reference_validation')
EXP_SRC={'external':202,'development':333,'reference_validation':194}
EXP_FILL={'external':183,'development':297,'reference_validation':172}


def as_bool(s):
    if s.dtype==bool:return s.copy()
    return s.astype(str).str.lower().eq('true')


def dt(d,cols):
    for c in cols:
        if c in d.columns:d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    return d


def keyset(d, cols):
    q=d.copy()
    out=[]
    for c in cols:
        if c in q.columns and pd.api.types.is_datetime64_any_dtype(q[c]):
            q[c]=q[c].astype(str)
    return set(map(tuple,q[cols].astype(str).itertuples(index=False,name=None)))


def main():
    x5,cov=b21.load5()
    assert len(x5)==698112 and abs(float(cov)-1.0)<1e-12

    be=pd.read_csv(BE)
    be=dt(be,['obs_start','obs_end','k1_ts','k2_ts','k3_ts','regime_available_ts'])
    be['k1_opp0']=as_bool(be.k1_opp0)
    kb=be[be.partition.isin(MAJOR)&be.k1_opp0].copy().sort_values(['obs_start','partition']).reset_index(drop=True)
    assert len(kb)==2767,len(kb)

    ev=pd.DataFrame([b27bz.evaluate_one(x5,r) for r in kb.itertuples(index=False)])
    ev=dt(ev,['obs_start','obs_end','retest_complete_ts'])
    raw=ev[(ev.retest_class.eq('RETEST_RECLAIMED'))&ev.retest_complete_ts.notna()].copy()
    assert len(raw)==734,len(raw)
    rec=raw[raw.retest_complete_ts<raw.obs_end].copy()
    rec['reclaim_complete_ts']=rec.retest_complete_ts
    rec['R4']=pd.to_numeric(rec.H)-pd.to_numeric(rec.L)
    rec=rec.sort_values(['obs_start','partition']).reset_index(drop=True)
    rec['event_id']=np.arange(len(rec),dtype=int)
    assert len(rec)==729,len(rec)
    for p,n in EXP_SRC.items():assert len(rec[rec.partition.eq(p)])==n,(p,len(rec[rec.partition.eq(p)]),n)

    ce=pd.read_csv(CE)
    ce=dt(ce,['obs_start','obs_end','reclaim_complete_ts'])
    ce['eligible']=as_bool(ce.eligible)
    oldsrc=ce[ce.partition.isin(MAJOR)&ce.eligible].copy()
    assert len(oldsrc)==729
    src_cols=['partition','obs_start','obs_end','reclaim_complete_ts']
    src_identity=(keyset(rec,src_cols)==keyset(oldsrc,src_cols))
    missing_src=len(keyset(oldsrc,src_cols)-keyset(rec,src_cols))
    extra_src=len(keyset(rec,src_cols)-keyset(oldsrc,src_cols))

    b27cs.validate_cr_map()
    trades=pd.DataFrame([b27cs.eval_one(x5,r,'BASE_H') for r in rec.itertuples(index=False)])
    fills=trades[trades.filled.astype(bool)].copy()
    assert len(fills)==652,len(fills)
    for p,n in EXP_FILL.items():assert len(fills[fills.partition.eq(p)])==n,(p,len(fills[fills.partition.eq(p)]),n)

    parent=b27cv.load_trades()
    fill_cols=['partition','obs_start','reclaim_complete_ts','fill_ts']
    fills=dt(fills,['obs_start','reclaim_complete_ts','fill_ts'])
    parent=dt(parent,['obs_start','reclaim_complete_ts','fill_ts'])
    fill_identity=(keyset(fills,fill_cols)==keyset(parent,fill_cols))
    missing_fill=len(keyset(parent,fill_cols)-keyset(fills,fill_cols))
    extra_fill=len(keyset(fills,fill_cols)-keyset(parent,fill_cols))

    pass_all=bool(src_identity and fill_identity)
    status='B27DB_PIPELINE_PARITY_PASS' if pass_all else 'B27DB_PIPELINE_PARITY_FAIL'
    OUT_STATUS.write_text(status+'\n')
    rec.to_csv(OUT_SRC,index=False)
    fills.to_csv(OUT_TRADES,index=False)
    OUT_AUDIT.write_text(
        f'audit={"PASS" if pass_all else "FAIL"}\nraw_rows={len(x5)}\ncoverage={float(cov)}\n'
        f'k1_opp0={len(kb)}\nraw_reclaimed={len(raw)}\neligible_reclaimed={len(rec)}\n'
        f'sources_external={len(rec[rec.partition.eq("external")])}\nsources_development={len(rec[rec.partition.eq("development")])}\nsources_validation={len(rec[rec.partition.eq("reference_validation")])}\n'
        f'source_identity_exact={src_identity}\nmissing_sources={missing_src}\nextra_sources={extra_src}\n'
        f'f05_fills={len(fills)}\nfills_external={len(fills[fills.partition.eq("external")])}\nfills_development={len(fills[fills.partition.eq("development")])}\nfills_validation={len(fills[fills.partition.eq("reference_validation")])}\n'
        f'fill_identity_exact={fill_identity}\nmissing_fills={missing_fill}\nextra_fills={extra_fill}\n'
    )
    lines=[
        '# B27DB — Fresh Pipeline Historical Parity Audit','',
        f'**Audit: {"PASS" if pass_all else "FAIL"}.** Raw 5m: {len(x5):,}, coverage {100*float(cov):.4f}%.','',
        '## Source reconstruction','',
        f'- K1 OPP0 blocks: **{len(kb)}**',
        f'- Raw RETEST_RECLAIMED: **{len(raw)}**',
        f'- Eligible reclaimed sources: **{len(rec)}** = external {len(rec[rec.partition.eq("external")])} / development {len(rec[rec.partition.eq("development")])} / validation {len(rec[rec.partition.eq("reference_validation")])}',
        f'- Exact source identity vs persisted B27CE: **{src_identity}** (missing {missing_src}, extra {extra_src})','',
        '## F05 execution parity','',
        f'- F05 fills: **{len(fills)}** = external {len(fills[fills.partition.eq("external")])} / development {len(fills[fills.partition.eq("development")])} / validation {len(fills[fills.partition.eq("reference_validation")])}',
        f'- Exact fill identity vs persisted B27CV/B27CS: **{fill_identity}** (missing {missing_fill}, extra {extra_fill})','',
        f'**Frozen status: `{status}`.**','',
        'This is an implementation parity audit only; no strategy or live rule changed.'
    ]
    OUT.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()
