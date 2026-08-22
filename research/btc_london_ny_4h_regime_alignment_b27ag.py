#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
LONG_W = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Windows.csv'
LONG_E = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Entries.csv'
SHORT_W = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Windows.csv'
SHORT_T = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Trades.csv'
LONG_ECON = ROOT / 'BTC_LONDON_NY_E20_PROFIT_LOCK_RUNNER_B27AC_Trades.csv'

OUT_MD = ROOT / 'BTC_LONDON_NY_4H_REGIME_ALIGNMENT_B27AG_Result.md'
OUT_DETAIL = ROOT / 'BTC_LONDON_NY_4H_REGIME_ALIGNMENT_B27AG_Detail.csv'
OUT_STRUCT = ROOT / 'BTC_LONDON_NY_4H_REGIME_ALIGNMENT_B27AG_StructuralSummary.csv'
OUT_ECON = ROOT / 'BTC_LONDON_NY_4H_REGIME_ALIGNMENT_B27AG_EconomicSummary.csv'
OUT_REGIME = ROOT / 'BTC_LONDON_NY_4H_REGIME_ALIGNMENT_B27AG_RegimeBars.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_4H_REGIME_ALIGNMENT_B27AG_Status.txt'

PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
BAR5 = pd.Timedelta(minutes=5)
H4 = pd.Timedelta(hours=4)


def as_bool(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().eq('true')


def dt(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors='coerce')
    return df


def ema(c: np.ndarray, p: int) -> np.ndarray:
    # Exact existing v4h_regime_endpoint.py implementation.
    e = np.zeros(len(c), dtype=float)
    e[0] = c[0]
    k = 2.0 / (p + 1)
    for i in range(1, len(c)):
        e[i] = c[i] * k + e[i-1] * (1-k)
    return e


def atr(H: np.ndarray, L: np.ndarray, C: np.ndarray, p: int = 14) -> np.ndarray:
    # Exact existing v4h_regime_endpoint.py implementation.
    n = len(H)
    a = np.zeros(n, dtype=float)
    for i in range(1, n):
        t = max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1]))
        a[i] = a[i-1] + (t-a[i-1]) / min(i, p)
    return a


class SwingRegime:
    # Exact existing v4h_regime_endpoint.py semantics/defaults.
    def __init__(self, slb=5, sa=0.5):
        self.slb=slb; self.sa=sa
        self.hh=0; self.hl=0; self.lh=0; self.ll=0
        self.lsh=None; self.lsl=None; self.psh=None; self.psl=None

    def process(self, i, H, L, C, ef, es, at):
        if i < self.slb:
            return 'SIDEWAYS'
        mid = i - self.slb//2
        if mid < 0:
            return 'SIDEWAYS'
        wh = H[max(0, i-self.slb):i+1]
        wl = L[max(0, i-self.slb):i+1]
        am = self.sa * at[i] if at[i] > 0 else 0
        if H[mid] == max(wh) and (self.lsh is None or abs(H[mid]-self.lsh) >= am):
            self.psh=self.lsh; self.lsh=float(H[mid])
            if self.psh:
                if self.lsh > self.psh:
                    self.hh += 1
                else:
                    self.lh += 1; self.hh=max(0, self.hh-1)
        if L[mid] == min(wl) and (self.lsl is None or abs(L[mid]-self.lsl) >= am):
            self.psl=self.lsl; self.lsl=float(L[mid])
            if self.psl:
                if self.lsl > self.psl:
                    self.hl += 1; self.ll=max(0, self.ll-1)
                else:
                    self.ll += 1; self.hl=max(0, self.hl-1)
        if self.hh >= 2 and self.hl >= 2 and ef[i] > es[i] and C[i] > es[i]:
            return 'BULL'
        if self.lh >= 2 and self.ll >= 2 and ef[i] < es[i] and C[i] < es[i]:
            return 'BEAR'
        return 'SIDEWAYS'


def build_regime(x5: pd.DataFrame) -> pd.DataFrame:
    z = x5[['open','high','low','close']].copy()
    agg = z.resample('4h', origin='epoch', label='left', closed='left').agg(
        open=('open','first'), high=('high','max'), low=('low','min'), close=('close','last')
    )
    cnt = z.close.resample('4h', origin='epoch', label='left', closed='left').count()
    agg['n5'] = cnt
    # Exact complete 4H bars only; no partial/gappy constituent set can create a state.
    agg = agg[(agg.n5 == 48) & agg.open.notna() & agg.close.notna()].copy()
    if len(agg) < 1000:
        raise AssertionError('too few complete 4H bars')
    H = agg.high.to_numpy(float); L = agg.low.to_numpy(float); C = agg.close.to_numpy(float)
    ef = ema(C, 7); es = ema(C, 20); at = atr(H,L,C,14)
    det = SwingRegime(5,0.5)
    states=[]
    for i in range(len(agg)):
        states.append(det.process(i,H,L,C,ef,es,at))
    agg['ema7']=ef; agg['ema20']=es; agg['atr14']=at; agg['regime']=states
    agg['available_ts'] = agg.index + H4
    # Availability must be strictly monotonic.
    assert agg.available_ts.is_monotonic_increasing
    return agg


def state_at(reg: pd.DataFrame, ts: pd.Timestamp):
    av = reg.available_ts.array.asi8
    j = int(np.searchsorted(av, pd.Timestamp(ts).value, side='right')) - 1
    if j < 0:
        return 'SIDEWAYS', pd.NaT, pd.NaT
    r = reg.iloc[j]
    assert pd.Timestamp(r.available_ts) <= pd.Timestamp(ts)
    return str(r.regime), reg.index[j], pd.Timestamp(r.available_ts)


def fast_slice(x5, start, end):
    a=int(x5.index.searchsorted(start,side='left'))
    b=int(x5.index.searchsorted(end,side='left'))
    return x5.iloc[a:b]


def post_h2(x5, side, H, L, h2, end):
    R = H-L
    e20 = H + .20*R if side=='LONG' else L - .20*R
    q=fast_slice(x5,pd.Timestamp(h2),pd.Timestamp(end))
    if q.empty or q.index[0] != pd.Timestamp(h2):
        raise AssertionError('missing H2 bar in post-H2 scan')
    accepted=False; e20_hit=False
    for _,b in q.iterrows():
        if side=='LONG':
            accepted = accepted or float(b.close) > H
            e20_hit = e20_hit or float(b.high) >= e20
        else:
            accepted = accepted or float(b.close) < L
            e20_hit = e20_hit or float(b.low) <= e20
        if accepted and e20_hit:
            break
    return accepted,e20_hit


def alignment(side, regime):
    if regime=='SIDEWAYS': return 'SIDEWAYS'
    if (side=='LONG' and regime=='BULL') or (side=='SHORT' and regime=='BEAR'):
        return 'ALIGNED'
    return 'COUNTER'


def load_struct_side(side: str):
    sig=pd.read_csv(SIGNALS)
    sig=sig[(sig.transition=='LONDON_TO_NEWYORK') & (sig.side==side) &
            (pd.to_numeric(sig.k)==1) & (pd.to_numeric(sig.opp_visits_at_signal)==0)].copy()
    sig=dt(sig,['signal_ts','signal_bar_start','active_session_end'])
    if side=='LONG':
        w=dt(pd.read_csv(LONG_W),['signal_ts','eligible_start','h2_bar_start','session_end'])
        e=pd.read_csv(LONG_E); e=e[e.entry_name=='F85'].copy()
        e=dt(e,['signal_ts','entry_ts','h2_bar_start','eligible_start'])
        e['filled_b']=as_bool(e.filled); e['h2_b']=as_bool(e.target_hit)
        e['entry_time_norm']=e.entry_ts
        e['entry_px_norm']=pd.to_numeric(e.entry_px,errors='coerce')
        expected=pd.to_numeric(e.L)+.85*(pd.to_numeric(e.H)-pd.to_numeric(e.L))
    else:
        w=dt(pd.read_csv(SHORT_W),['signal_ts','eligible_start','h2_bar_start','session_end'])
        t=pd.read_csv(SHORT_T); e=t[t.rule=='BLIND_F15'].copy()
        e=dt(e,['signal_ts','blind_touch_bar_start','h2_bar_start','eligible_start'])
        e['filled_b']=as_bool(e.blind_filled); e['h2_b']=as_bool(e.h2_after_fill)
        e['entry_time_norm']=e.blind_touch_bar_start
        e['entry_px_norm']=pd.to_numeric(e.blind_entry_px,errors='coerce')
        expected=pd.to_numeric(e.L)+.15*(pd.to_numeric(e.H)-pd.to_numeric(e.L))
    keys=['partition','signal_ts']
    for d in (sig,w,e):
        d.sort_values(keys,inplace=True); d.reset_index(drop=True,inplace=True)
    assert len(sig)==len(w)==len(e), (side,len(sig),len(w),len(e))
    assert sig[keys].equals(w[keys]) and sig[keys].equals(e[keys]), f'{side} identity mismatch'
    f=e[e.filled_b]
    assert np.allclose(f.entry_px_norm.to_numpy(float),expected.loc[f.index].to_numpy(float),rtol=1e-12,atol=1e-9)
    return sig,w,e


def build_detail(x5,reg,side,sig,w,e):
    rows=[]
    for i in range(len(sig)):
        s=sig.iloc[i]; ww=w.iloc[i]; ee=e.iloc[i]
        regime,rb,rav=state_at(reg,pd.Timestamp(s.signal_ts))
        clean=pd.notna(ww.eligible_start)
        filled=bool(ee.filled_b)
        h2=bool(ee.h2_b) if filled else False
        entry_reg=''; entry_av=pd.NaT; entry_rb=pd.NaT; state_changed=False
        if filled:
            entry_reg,entry_rb,entry_av=state_at(reg,pd.Timestamp(ee.entry_time_norm))
            state_changed=entry_reg != regime
        accepted=False; e20=False
        if h2:
            accepted,e20=post_h2(x5,side,float(ee.H),float(ee.L),pd.Timestamp(ee.h2_bar_start),pd.Timestamp(ww.session_end))
        rows.append({
            'side':side,'partition':s.partition,'date_utc':s.date_utc,
            'signal_ts':pd.Timestamp(s.signal_ts),'regime_at_signal':regime,
            'regime_bar_start':rb,'regime_available_ts':rav,
            'alignment':alignment(side,regime),
            'target_break':str(s.structural_outcome)=='TARGET_BREAK',
            'clean_window':clean,'filled':filled,'h2':h2,'accepted_after_h2':accepted,'e20_after_h2':e20,
            'entry_ts':ee.entry_time_norm if filled else pd.NaT,
            'regime_at_entry':entry_reg if filled else '',
            'entry_regime_available_ts':entry_av,'state_changed_signal_to_entry':state_changed,
        })
    return pd.DataFrame(rows)


def pf(vals):
    x=pd.to_numeric(pd.Series(vals),errors='coerce').dropna()
    pos=float(x[x>0].sum()); neg=float(-x[x<0].sum())
    if neg==0 and pos>0:return float('inf')
    return pos/neg if neg>0 else np.nan


def structural_summary(d):
    out=[]
    groups=[]
    for part in PARTS:
        for side in ('LONG','SHORT'):
            for rg in ('BULL','BEAR','SIDEWAYS'):
                groups.append((part,side,rg,d[(d.partition==part)&(d.side==side)&(d.regime_at_signal==rg)]))
    for side in ('LONG','SHORT'):
        for rg in ('BULL','BEAR','SIDEWAYS'):
            g=d[(d.partition.isin(MAJOR))&(d.side==side)&(d.regime_at_signal==rg)]
            groups.append(('POOLED_MAJOR',side,rg,g))
    for part,side,rg,g in groups:
        n=len(g); clean=g[g.clean_window]; fill=g[g.filled]; h2=fill[fill.h2]
        out.append({
            'partition':part,'side':side,'regime':rg,'alignment':alignment(side,rg),'k1_n':n,
            'target_break_rate':float(g.target_break.mean()) if n else np.nan,
            'clean_rate':float(g.clean_window.mean()) if n else np.nan,
            'fill_given_clean':float(len(fill)/len(clean)) if len(clean) else np.nan,
            'fills':len(fill),'h2_n':int(fill.h2.sum()) if len(fill) else 0,
            'h2_given_fill':float(fill.h2.mean()) if len(fill) else np.nan,
            'accept_given_h2':float(h2.accepted_after_h2.mean()) if len(h2) else np.nan,
            'e20_given_h2':float(h2.e20_after_h2.mean()) if len(h2) else np.nan,
            'state_change_rate_filled':float(fill.state_changed_signal_to_entry.mean()) if len(fill) else np.nan,
        })
    return pd.DataFrame(out)


def econ_rows(reg):
    rows=[]
    # LONG existing B27AC: only executed rows are persisted.
    le=dt(pd.read_csv(LONG_ECON),['signal_ts','entry_start'])
    for rule in ('BLIND_F85','EARLY_RECLAIM'):
        g=le[le.rule==rule].copy()
        for r in g.itertuples(index=False):
            rg,_,av=state_at(reg,pd.Timestamp(r.signal_ts))
            rows.append({'side':'LONG','rule':rule,'partition':r.partition,'signal_ts':r.signal_ts,
                         'regime':rg,'alignment':alignment('LONG',rg),
                         'fixed_pnl':float(r.baseline_net_pnl_usd),'hybrid_pnl':float(r.hybrid_net_pnl_usd)})
    # SHORT existing B27AD: file contains no-trade rows, so executed only.
    se=dt(pd.read_csv(SHORT_T),['signal_ts','entry_start'])
    for rule in ('BLIND_F15','EARLY_REJECT'):
        g=se[(se.rule==rule)&as_bool(se.entry_executed)].copy()
        for r in g.itertuples(index=False):
            rg,_,av=state_at(reg,pd.Timestamp(r.signal_ts))
            rows.append({'side':'SHORT','rule':rule,'partition':r.partition,'signal_ts':r.signal_ts,
                         'regime':rg,'alignment':alignment('SHORT',rg),
                         'fixed_pnl':float(r.fixed_net_pnl_usd),'hybrid_pnl':float(r.hybrid_net_pnl_usd)})
    return pd.DataFrame(rows)


def econ_summary(e):
    out=[]
    groups=[]
    for side,rule in [('LONG','BLIND_F85'),('LONG','EARLY_RECLAIM'),('SHORT','BLIND_F15'),('SHORT','EARLY_REJECT')]:
        for part in PARTS:
            for rg in ('BULL','BEAR','SIDEWAYS'):
                groups.append((side,rule,part,rg,e[(e.side==side)&(e.rule==rule)&(e.partition==part)&(e.regime==rg)]))
        for rg in ('BULL','BEAR','SIDEWAYS'):
            groups.append((side,rule,'POOLED_MAJOR',rg,e[(e.side==side)&(e.rule==rule)&(e.partition.isin(MAJOR))&(e.regime==rg)]))
    # Combined alignment rows for confirmed entries only.
    conf=e[((e.side=='LONG')&(e.rule=='EARLY_RECLAIM'))|((e.side=='SHORT')&(e.rule=='EARLY_REJECT'))]
    for al in ('ALIGNED','COUNTER','SIDEWAYS'):
        groups.append(('COMBINED','CONFIRMED','POOLED_MAJOR',al,conf[(conf.partition.isin(MAJOR))&(conf.alignment==al)]))
    for side,rule,part,label,g in groups:
        n=len(g); fx=pd.to_numeric(g.fixed_pnl,errors='coerce'); hy=pd.to_numeric(g.hybrid_pnl,errors='coerce')
        out.append({'side':side,'rule':rule,'partition':part,'regime_or_alignment':label,'n':n,
                    'fixed_wr':float((fx>0).mean()) if n else np.nan,'fixed_pf':pf(fx),'fixed_exp':float(fx.mean()) if n else np.nan,'fixed_total':float(fx.sum()) if n else 0.0,
                    'hybrid_wr':float((hy>0).mean()) if n else np.nan,'hybrid_pf':pf(hy),'hybrid_exp':float(hy.mean()) if n else np.nan,'hybrid_total':float(hy.sum()) if n else 0.0})
    return pd.DataFrame(out)


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def money(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'
def pfn(x): return '-' if pd.isna(x) else ('inf' if math.isinf(float(x)) else f'{float(x):.2f}')


def main():
    x5,coverage=b21.load5()
    if abs(float(coverage)-1.0)>1e-12:
        raise AssertionError(f'coverage not 100%: {coverage}')
    reg=build_regime(x5)
    # Every persisted regime bar must be a full 48 x 5m bar set.
    assert (reg.n5==48).all()

    ls,lw,le=load_struct_side('LONG')
    ss,sw,se=load_struct_side('SHORT')
    dl=build_detail(x5,reg,'LONG',ls,lw,le)
    ds=build_detail(x5,reg,'SHORT',ss,sw,se)
    d=pd.concat([dl,ds],ignore_index=True)

    # Frozen cohort count reproduction.
    major=d[d.partition.isin(MAJOR)]
    assert int(major[(major.side=='LONG')].filled.sum())==149
    assert int(major[(major.side=='SHORT')].filled.sum())==163
    assert int(major[(major.side=='LONG') & major.filled].h2.sum())==121
    assert int(major[(major.side=='SHORT') & major.filled].h2.sum())==120
    assert (d.regime_available_ts.dropna() <= d.loc[d.regime_available_ts.notna(),'signal_ts']).all()
    ff=d[d.filled & d.entry_regime_available_ts.notna()]
    assert (ff.entry_regime_available_ts <= ff.entry_ts).all()

    sm=structural_summary(d)
    econ=econ_rows(reg)
    es=econ_summary(econ)

    # Existing economics must reproduce pooled major totals before regime interpretation.
    checks={
        ('LONG','BLIND_F85'):89.68,
        ('LONG','EARLY_RECLAIM'):76.51,
        ('SHORT','BLIND_F15'):-11.67,
        ('SHORT','EARLY_REJECT'):-7.68,
    }
    for (side,rule),want in checks.items():
        got=float(econ[(econ.side==side)&(econ.rule==rule)&(econ.partition.isin(MAJOR))].fixed_pnl.sum())
        if abs(got-want)>0.02:
            raise AssertionError((side,rule,got,want))

    reg.to_csv(OUT_REGIME,index=True,index_label='bar_start')
    d.to_csv(OUT_DETAIL,index=False)
    sm.to_csv(OUT_STRUCT,index=False)
    es.to_csv(OUT_ECON,index=False)

    lines=['# B27AG — BTC London -> New York 4H HH/HL Regime Alignment Audit — Result','',
           f'5m rows: **{len(x5):,}**; coverage: **{100*coverage:.4f}%**.','',
           '**Audit status: PASS.** Existing 4H SwingRegime semantics/defaults were reproduced, only fully completed 4H bars were available to each K1 signal, frozen F85/F15 cohorts reproduced, and existing fixed-E20 totals reproduced before regime attribution.','',
           '## Pooled-major structural funnel by pre-signal 4H state','',
           '| Side | 4H state | Alignment | K1 N | Target break | Clean | Fills | H2/fill | Accept/H2 | E20/H2 |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for side in ('LONG','SHORT'):
        for rg in ('BULL','BEAR','SIDEWAYS'):
            r=sm[(sm.partition=='POOLED_MAJOR')&(sm.side==side)&(sm.regime==rg)].iloc[0]
            lines.append(f"| {side} | {rg} | {r.alignment} | {int(r.k1_n)} | {pct(r.target_break_rate)} | {pct(r.clean_rate)} | {int(r.fills)} | {pct(r.h2_given_fill)} | {pct(r.accept_given_h2)} | {pct(r.e20_given_h2)} |")

    lines += ['', '## Confirmed-entry economics by pre-signal 4H state','',
              '| Side | Rule | State | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total |',
              '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for side,rule in [('LONG','EARLY_RECLAIM'),('SHORT','EARLY_REJECT')]:
        for rg in ('BULL','BEAR','SIDEWAYS'):
            r=es[(es.side==side)&(es.rule==rule)&(es.partition=='POOLED_MAJOR')&(es.regime_or_alignment==rg)].iloc[0]
            lines.append(f"| {side} | {rule} | {rg} | {int(r.n)} | {pct(r.fixed_wr)} | {pfn(r.fixed_pf)} | {money(r.fixed_exp)} | {money(r.fixed_total)} | {pct(r.hybrid_wr)} | {pfn(r.hybrid_pf)} | {money(r.hybrid_exp)} | {money(r.hybrid_total)} |")

    lines += ['', '## Combined confirmed-entry alignment','',
              '| Alignment | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    comb={}
    for al in ('ALIGNED','COUNTER','SIDEWAYS'):
        r=es[(es.side=='COMBINED')&(es.rule=='CONFIRMED')&(es.partition=='POOLED_MAJOR')&(es.regime_or_alignment==al)].iloc[0]
        comb[al]=r
        lines.append(f"| {al} | {int(r.n)} | {pct(r.fixed_wr)} | {pfn(r.fixed_pf)} | {money(r.fixed_exp)} | {money(r.fixed_total)} | {pct(r.hybrid_wr)} | {pfn(r.hybrid_pf)} | {money(r.hybrid_exp)} | {money(r.hybrid_total)} |")

    def srow(side,rg):
        return sm[(sm.partition=='POOLED_MAJOR')&(sm.side==side)&(sm.regime==rg)].iloc[0]
    sb=srow('SHORT','BEAR'); su=srow('SHORT','BULL'); lb=srow('LONG','BULL'); lbe=srow('LONG','BEAR')
    conds={
        'short_h2': (not pd.isna(sb.h2_given_fill) and not pd.isna(su.h2_given_fill) and sb.h2_given_fill > su.h2_given_fill),
        'short_e20': (not pd.isna(sb.e20_given_h2) and not pd.isna(su.e20_given_h2) and sb.e20_given_h2 > su.e20_given_h2),
        'long_h2': (not pd.isna(lb.h2_given_fill) and not pd.isna(lbe.h2_given_fill) and lb.h2_given_fill > lbe.h2_given_fill),
        'long_e20': (not pd.isna(lb.e20_given_h2) and not pd.isna(lbe.e20_given_h2) and lb.e20_given_h2 > lbe.e20_given_h2),
        'econ': (int(comb['ALIGNED'].n)>0 and int(comb['COUNTER'].n)>0 and float(comb['ALIGNED'].fixed_exp) > float(comb['COUNTER'].fixed_exp)),
    }
    support=all(conds.values())
    status='B27AG_REGIME_HYPOTHESIS_DIRECTIONALLY_SUPPORTED' if support else 'B27AG_REGIME_HYPOTHESIS_NOT_FULLY_SUPPORTED'
    lines += ['', '## Frozen hypothesis readout','']
    lines.append(f"- SHORT H2: BEAR {pct(sb.h2_given_fill)} vs BULL {pct(su.h2_given_fill)} -> {'PASS' if conds['short_h2'] else 'FAIL/INCONCLUSIVE'}")
    lines.append(f"- SHORT E20/H2: BEAR {pct(sb.e20_given_h2)} vs BULL {pct(su.e20_given_h2)} -> {'PASS' if conds['short_e20'] else 'FAIL/INCONCLUSIVE'}")
    lines.append(f"- LONG H2: BULL {pct(lb.h2_given_fill)} vs BEAR {pct(lbe.h2_given_fill)} -> {'PASS' if conds['long_h2'] else 'FAIL/INCONCLUSIVE'}")
    lines.append(f"- LONG E20/H2: BULL {pct(lb.e20_given_h2)} vs BEAR {pct(lbe.e20_given_h2)} -> {'PASS' if conds['long_e20'] else 'FAIL/INCONCLUSIVE'}")
    lines.append(f"- Confirmed fixed expectancy: ALIGNED {money(comb['ALIGNED'].fixed_exp)} (N={int(comb['ALIGNED'].n)}) vs COUNTER {money(comb['COUNTER'].fixed_exp)} (N={int(comb['COUNTER'].n)}) -> {'PASS' if conds['econ'] else 'FAIL/INCONCLUSIVE'}")
    lines += ['', f'**Overall: {status}.**','',
              'This audit attributes existing trades to a pre-existing causal 4H state. It does not authorize a new live regime filter. Small regime cells remain a limitation.',
              '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text(status+'\n')
    print(status)


if __name__=='__main__':
    main()
