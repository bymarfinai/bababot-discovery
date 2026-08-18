#!/usr/bin/env python3
"""SUN1.8 — Sunday16 previous-day RUNNER + persistent failed-development management.

Research only; live BBC untouched.

Frozen parent:
- Sunday 16:00 WIB SELL
- TP 2.5%, SL 1.4%, max hold 18h
- $500 notional, 0.15% round-trip fee, historical funding

Predeclared architecture (no threshold sweep):
1) RUNNER iff Saturday calendar return < 0 AND Sunday 00:00->16:00 return < 0.
   RUNNER keeps frozen parent unchanged.
2) All other trades are WATCH.
3) WATCH at +4h decision open: arm FAILED_DEVELOPMENT iff completed path has
   progress <= 0 (SELL has not closed below entry) AND EMA7 >= EMA20.
4) At +6h decision open: if still alive and both conditions still hold, exit
   at actual +6h 5m open. Parent exits before/equal +6h have priority.
5) No alternative checkpoints, thresholds, EMA periods, or rescue tuning.

Also reports two diagnostics without promoting them:
- RUNNER-only / WATCH-skip capacity benchmark.
- Same +4->+6 persistent rule applied to ALL trades, to isolate whether the
  previous-day RUNNER exemption helps or hurts.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
from sun17b_sunday16_loss_prevday_forensics_exactfunding import base as sun17

OUT=Path(os.getenv('SUN18_OUT','sun18_out')); OUT.mkdir(parents=True,exist_ok=True)
NOTIONAL=500.0; FEE=0.0015*NOTIONAL; DISC_N=83


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0: return {'n':0,'wins':0,'wr':np.nan,'pnl':0.0,'pf':np.nan,'exp':np.nan,'dd':0.0,'loss_streak':0}
    wins=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    eq=np.cumsum(a); peaks=np.maximum.accumulate(np.r_[0.0,eq]); dd=float(np.max(peaks[1:]-eq))
    cur=best=0
    for x in a:
        if x<=0: cur+=1; best=max(best,cur)
        else: cur=0
    return {'n':int(len(a)),'wins':wins,'wr':float(wins/len(a)),'pnl':float(a.sum()),
            'pf':float(gp/gl) if gl>0 else 999.0,'exp':float(a.mean()),'dd':dd,'loss_streak':int(best)}


def slices(a):
    a=np.asarray(a,float)
    return {'D':metrics(a[:DISC_N]),'V':metrics(a[DISC_N:]),'full':metrics(a)}


def cut6_pnl(k,tr):
    cp=tr['entry_t']+pd.Timedelta(hours=6)
    if cp not in k.index: raise RuntimeError(f'missing +6h open {cp}')
    px=float(k.loc[cp,'open'])
    # Sunday16 WIB = 09 UTC; +6h = 15 UTC, before the next 16 UTC funding settlement.
    return float(NOTIONAL*(1.0-px/tr['entry'])-FEE),px


def signal(k,tr):
    c4=sun17.checkpoint(k,tr,240)
    arm=bool(c4 is not None and c4['progress']<=0.0 and c4['ema_spread']>=0.0)
    c6=sun17.checkpoint(k,tr,360)
    confirm=bool(arm and c6 is not None and c6['progress']<=0.0 and c6['ema_spread']>=0.0)
    return arm,confirm,c4,c6


def main():
    k=f517.load_klines(); f=s50.load_funding(); es=sun17.entries(k)
    trades=[sun17.simulate_parent(k,f,t) for t in es]
    parent=np.array([tr['pnl'] for tr in trades],float)
    base=slices(parent)
    # Exact parity gate to SUN1.6/SUN1.7 checkpoint.
    if not (len(parent)==139 and base['full']['wins']==66 and abs(base['full']['pnl']-63.599379132074105)<0.25):
        raise RuntimeError(f'parent parity failed {base}')

    rows=[]; adaptive=parent.copy(); allrule=parent.copy()
    for i,tr in enumerate(trades):
        ctx=sun17.pre_context(k,tr['entry_t'])
        runner=bool(ctx['sat_day_ret']<0 and ctx['sun_pre16_ret']<0)
        arm,confirm,c4,c6=signal(k,tr)
        action=False; all_action=False; cutp=np.nan; cutpx=np.nan
        if confirm:
            cutp,cutpx=cut6_pnl(k,tr)
            allrule[i]=cutp; all_action=True
            if not runner:
                adaptive[i]=cutp; action=True
        rows.append({
            'i':i,'entry_t':str(tr['entry_t']),'parent_reason':tr['reason'],'parent_pnl':tr['pnl'],'parent_win':tr['win'],
            'sat_day_ret':ctx['sat_day_ret'],'sun_pre16_ret':ctx['sun_pre16_ret'],'state':'RUNNER' if runner else 'WATCH',
            'arm4':arm,'confirm6':confirm,'action6':action,'allrule_action6':all_action,
            'p4_progress':np.nan if c4 is None else c4['progress'],'p4_ema_spread':np.nan if c4 is None else c4['ema_spread'],
            'p6_progress':np.nan if c6 is None else c6['progress'],'p6_ema_spread':np.nan if c6 is None else c6['ema_spread'],
            'cut6_px':cutpx,'cut6_pnl':cutp,'adaptive_pnl':adaptive[i],
        })
    df=pd.DataFrame(rows)

    runner_mask=(df.state=='RUNNER').to_numpy(); watch_mask=~runner_mask
    action_mask=df.action6.to_numpy(bool); all_action_mask=df.allrule_action6.to_numpy(bool)
    delta=adaptive-parent; all_delta=allrule-parent

    def cohort(mask,pnls=parent):
        mask=np.asarray(mask,bool); idx=np.flatnonzero(mask); a=np.asarray(pnls,float)[idx]
        d=idx[idx<DISC_N]; v=idx[idx>=DISC_N]
        return {'full':metrics(a),
                'D':metrics(np.asarray(pnls)[d]),'V':metrics(np.asarray(pnls)[v])}

    action_parent_w=int(df.loc[action_mask,'parent_win'].sum()); action_parent_l=int(action_mask.sum()-action_parent_w)
    action_detail={
        'n':int(action_mask.sum()),'D':int(action_mask[:DISC_N].sum()),'V':int(action_mask[DISC_N:].sum()),
        'parent_W':action_parent_w,'parent_L':action_parent_l,
        'delta':float(delta.sum()),'D_delta':float(delta[:DISC_N].sum()),'V_delta':float(delta[DISC_N:].sum()),
        'saved_parent_losses_delta':float(delta[action_mask & (~df.parent_win.to_numpy(bool))].sum()),
        'harmed_parent_winners_delta':float(delta[action_mask & df.parent_win.to_numpy(bool)].sum()),
        'parent_positive_to_nonpositive':int(((parent>0)&(adaptive<=0)).sum()),
        'parent_nonpositive_to_positive':int(((parent<=0)&(adaptive>0)).sum()),
    }

    summary={
      'status':'COMPLETE_FIXED_ARCHITECTURE',
      'definition':{
        'parent':'Sunday16 SELL TP2.5 SL1.4 hold18h',
        'runner':'sat_day_ret < 0 AND sun_pre16_ret < 0',
        'watch':'all other pre-entry states',
        'arm4':'alive at +4h AND SELL progress<=0 AND EMA7>=EMA20',
        'cut6':'armed at +4h AND alive at +6h AND SELL progress<=0 AND EMA7>=EMA20; exit actual +6h open',
        'selection':'no threshold/checkpoint/EMA sweep; exact predeclared architecture'
      },
      'baseline':base,
      'runner_parent':cohort(runner_mask,parent),
      'watch_parent':cohort(watch_mask,parent),
      'runner_counts':{'full':int(runner_mask.sum()),'D':int(runner_mask[:DISC_N].sum()),'V':int(runner_mask[DISC_N:].sum())},
      'arm4_counts':{'full':int(df.arm4.sum()),'D':int(df.arm4.iloc[:DISC_N].sum()),'V':int(df.arm4.iloc[DISC_N:].sum())},
      'confirm6_all_counts':{'full':int(all_action_mask.sum()),'D':int(all_action_mask[:DISC_N].sum()),'V':int(all_action_mask[DISC_N:].sum())},
      'adaptive_runner_exempt':slices(adaptive),
      'adaptive_action_detail':action_detail,
      'diagnostic_alltrade_faileddev':slices(allrule),
      'diagnostic_alltrade_delta':{'full':float(all_delta.sum()),'D':float(all_delta[:DISC_N].sum()),'V':float(all_delta[DISC_N:].sum())},
      'runner_only_skip_watch':cohort(runner_mask,parent),
      'guardrail':'Same-sample architecture test. Previous-day state came from SUN1.7 forensic inspection, so positive economics are diagnostic, not untouched OOS validation.'
    }

    df.to_csv(OUT/'sun18_trades.csv',index=False)
    (OUT/'sun18_summary.json').write_text(json.dumps(summary,indent=2,default=str))

    b=summary['baseline']['full']; r=summary['runner_parent']['full']; w=summary['watch_parent']['full']; a=summary['adaptive_runner_exempt']['full']; ad=action_detail
    md=['# SUN1.8 — Sunday16 Previous-Day RUNNER + Persistent Failed-Development','',
        '**Status: COMPLETE — fixed causal architecture; same-sample diagnostic; live BBC untouched.**','',
        '## Fixed architecture',
        '- RUNNER: Saturday return < 0 AND Sunday 00:00→16:00 return < 0. Frozen parent unchanged.',
        '- WATCH: every other state.',
        '- +4h arm only if completed path has SELL progress <= 0 AND EMA7 >= EMA20.',
        '- +6h cut only if the same failure persists; exit at actual +6h open. Parent exits first have priority.',
        '- No threshold/timing/EMA sweep.','',
        '## Baseline',
        f"- N {b['n']}, WR **{100*b['wr']:.2f}%**, PnL **${b['pnl']:+.2f}**, PF **{b['pf']:.2f}**, DD ${b['dd']:.2f}.",'',
        '## Pre-entry state decomposition',
        f"- RUNNER: N **{r['n']}**, WR **{100*r['wr']:.2f}%**, PnL **${r['pnl']:+.2f}**, PF **{r['pf']:.2f}**.",
        f"- WATCH: N **{w['n']}**, WR **{100*w['wr']:.2f}%**, PnL **${w['pnl']:+.2f}**, PF **{w['pf']:.2f}**.",
        f"- RUNNER D/V: N {summary['runner_counts']['D']}/{summary['runner_counts']['V']}; PnL ${summary['runner_parent']['D']['pnl']:+.2f}/${summary['runner_parent']['V']['pnl']:+.2f}; WR {100*summary['runner_parent']['D']['wr']:.1f}%/{100*summary['runner_parent']['V']['wr']:.1f}%.",'',
        '## +4h→+6h failed-development actions in WATCH',
        f"- +4h armed: {summary['arm4_counts']['full']} (D/V {summary['arm4_counts']['D']}/{summary['arm4_counts']['V']}).",
        f"- +6h actions: **{ad['n']}** (D/V {ad['D']}/{ad['V']}), parent W/L **{ad['parent_W']}/{ad['parent_L']}**.",
        f"- Incremental: **${ad['delta']:+.2f}** (D ${ad['D_delta']:+.2f}, V ${ad['V_delta']:+.2f}).",
        f"- Loss savings ${ad['saved_parent_losses_delta']:+.2f}; winner damage ${ad['harmed_parent_winners_delta']:+.2f}; positive→nonpositive {ad['parent_positive_to_nonpositive']}.",'',
        '## Combined adaptive result',
        f"- N {a['n']}, WR **{100*a['wr']:.2f}%**, PnL **${a['pnl']:+.2f}**, PF **{a['pf']:.2f}**, DD ${a['dd']:.2f}, loss streak {a['loss_streak']}.",
        f"- D: WR {100*summary['adaptive_runner_exempt']['D']['wr']:.2f}%, PnL ${summary['adaptive_runner_exempt']['D']['pnl']:+.2f}, PF {summary['adaptive_runner_exempt']['D']['pf']:.2f}.",
        f"- V: WR {100*summary['adaptive_runner_exempt']['V']['wr']:.2f}%, PnL ${summary['adaptive_runner_exempt']['V']['pnl']:+.2f}, PF {summary['adaptive_runner_exempt']['V']['pf']:.2f}.",'',
        '## Diagnostics',
        f"- If same +4→+6 rule were applied to ALL trades: full PnL ${summary['diagnostic_alltrade_faileddev']['full']['pnl']:+.2f}, delta ${summary['diagnostic_alltrade_delta']['full']:+.2f}.",
        '- RUNNER-only / WATCH-skip is capacity only, not recommended as final frequency architecture.','',
        '## Guardrail',summary['guardrail']]
    (OUT/'SUN1.8_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(summary,indent=2,default=str),flush=True)

if __name__=='__main__': main()
