#!/usr/bin/env python3
"""F6.10 — Friday15 frozen true-OOS extension for F6.9 + F6.5 layered management.

Research only; live BBC untouched.

Frozen research cutoff: parent research scored Fridays through 2026-07-24.
True-OOS Friday entries scored here: 2026-07-31, 2026-08-07, 2026-08-14.

NO RETUNING. Exact frozen actions:
A) F6.9 EARLY10 at +10m actual open iff:
   - first 5m close < entry
   - alive at +10m
   - second 5m high < entry (no trade reclaim)
   - second 5m close < EMA7
   - second 5m body ratio < 50%
B) If A did not act, F6.5 at +60m actual open iff:
   - FAILURE_60 (alive, progress<=0, taker<0, close<=EMA20)
   - final completed 5m upper wick >=50% candle range

Historical candles are warmup only; only the three dates above are scored.
"""
from __future__ import annotations

import json, os, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f69_friday_early_sink_candidate_robustness as f69

OUT=Path(os.getenv('F610_OUT','f610_out')); OUT.mkdir(parents=True,exist_ok=True)
OOS_DATES=['2026-07-31','2026-08-07','2026-08-14']


def normalize_daily(df: pd.DataFrame, cache_name: str) -> pd.DataFrame:
    # Binance daily kline archives may be headerless; mirror F5.17 normalization.
    if len(df.columns)==12 and str(df.columns[0]).isdigit():
        p=f517.CACHE/cache_name
        with zipfile.ZipFile(p) as zf:
            name=[n for n in zf.namelist() if n.lower().endswith('.csv')][0]
            with zf.open(name) as fh:
                df=pd.read_csv(fh,header=None)
    if len(df.columns)<12:
        raise RuntimeError(f'unexpected daily columns {df.columns.tolist()}')
    df=df.iloc[:,:12].copy()
    df.columns=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore']
    for c in ['open','high','low','close','volume','quote_volume','taker_buy_base','taker_buy_quote']:
        df[c]=pd.to_numeric(df[c],errors='coerce')
    ot=pd.to_numeric(df.open_time,errors='coerce')
    unit='us' if ot.dropna().median()>1e14 else 'ms'
    df['ts']=pd.to_datetime(ot,unit=unit,utc=True)
    return df[['ts','open','high','low','close','volume','quote_volume','taker_buy_quote']]


def load_extended() -> pd.DataFrame:
    # Historical monthly loader includes complete July 2026 and provides EMA warmup.
    k=f517.load_klines().reset_index(drop=True)
    frames=[k[['ts','open','high','low','close','volume','quote_volume','taker_buy_quote']].copy()]
    for d in pd.date_range('2026-08-01','2026-08-14',freq='D'):
        ds=d.strftime('%Y-%m-%d'); cache=f'BTCUSDT-5m-daily-{ds}.zip'
        url=f'{f517.BASE}/daily/klines/{f517.SYMBOL}/5m/{f517.SYMBOL}-5m-{ds}.zip'
        raw=f517.get_zip_csv(url,cache)
        if raw is None: raise RuntimeError(f'missing Binance daily kline {ds}')
        frames.append(normalize_daily(raw,cache))
    out=pd.concat(frames,ignore_index=True).dropna(subset=['ts','open','high','low','close'])
    out=out.drop_duplicates('ts',keep='last').sort_values('ts').reset_index(drop=True)
    out['ema7']=out.close.ewm(span=7,adjust=False).mean()
    out['ema20']=out.close.ewm(span=20,adjust=False).mean()
    out['ema_spread']=out.ema7/out.ema20-1.0
    out['ret5']=out.close.pct_change()
    out['taker_imb']=np.where(out.quote_volume>0,2*out.taker_buy_quote/out.quote_volume-1.0,np.nan)
    return out.set_index('ts',drop=False)


def diag10(k,t,tr):
    b1=k.loc[t]; b2=k.loc[t+pd.Timedelta(minutes=5)]
    rg=float(b2.high)-float(b2.low)
    body=abs(float(b2.close)-float(b2.open))/rg if rg>0 else 0.0
    return {
      'first5_red':bool(float(b1.close)<tr.entry),
      'alive10':bool(tr.exit_t>t+pd.Timedelta(minutes=10)),
      'bar2_high_reclaims_entry':bool(float(b2.high)>=tr.entry),
      'bar2_close_below_ema7':bool(float(b2.close)<float(b2.ema7)),
      'bar2_body_ratio':body,
      'progress10_pct':100*(float(k.loc[t+pd.Timedelta(minutes=10),'open'])/tr.entry-1.0),
    }


def main():
    k=load_extended(); rows=[]
    for ds in OOS_DATES:
        t=pd.Timestamp(ds,tz='UTC')+pd.Timedelta(hours=8)  # 15:00 WIB
        tr=f517.simulate_parent(k,t)
        early=f69.early_state(k,t,tr)
        later=f69.f65_state(k,t,tr)
        parent=float(tr.pnl); managed=parent; layer='PARENT'; exit_px=np.nan
        if early:
            exit_px=float(k.loc[t+pd.Timedelta(minutes=10),'open'])
            managed=f517.NOTIONAL*(exit_px/tr.entry-1.0)-f517.ROUND_TRIP_FEE
            layer='EARLY10'
        elif later:
            exit_px=float(k.loc[t+pd.Timedelta(minutes=60),'open'])
            managed=f517.NOTIONAL*(exit_px/tr.entry-1.0)-f517.ROUND_TRIP_FEE
            layer='F65_60'
        rows.append({'date':ds,'entry':tr.entry,'parent_reason':tr.reason,'parent_pnl':parent,
                     'mfe_pct':100*tr.mfe,'mae_pct':-100*tr.mae,'early10_trigger':early,'f65_trigger':later,
                     'layer':layer,'managed_pnl':managed,'delta':managed-parent,**diag10(k,t,tr)})
    df=pd.DataFrame(rows); df.to_csv(OUT/'f610_oos_rows.csv',index=False)
    out={
      'cutoff_last_scored_friday':'2026-07-24',
      'oos_dates':OOS_DATES,'n':len(df),
      'parent_pnl':float(df.parent_pnl.sum()),'parent_wins':int((df.parent_pnl>0).sum()),
      'early10_actions':int(df.early10_trigger.sum()),
      'f65_actions_after_priority':int((df.layer=='F65_60').sum()),
      'layered_pnl':float(df.managed_pnl.sum()),'layered_delta':float(df.delta.sum()),
      'rows':df.to_dict('records')
    }
    (OUT/'f610_summary.json').write_text(json.dumps(out,indent=2,default=float))
    md=['# Friday15 F6.10 — Frozen True-OOS Extension','',
        '**Status:** COMPLETE — TRUE-OOS OBSERVATION ONLY','**No thresholds or rule definitions changed. Live BBC untouched.**','',
        '## Protocol','- Historical last scored Friday: **2026-07-24**.',
        '- True-OOS Fridays: **2026-07-31, 2026-08-07, 2026-08-14**.',
        '- Exact frozen F6.9 +10m candidate, then frozen F6.5 +60m rule if early rule did not act.','',
        '## Aggregate',f"- N **{len(df)}**; parent wins **{out['parent_wins']}**; parent PnL **{out['parent_pnl']:+.3f}**",
        f"- EARLY10 actions **{out['early10_actions']}**; later F6.5 actions **{out['f65_actions_after_priority']}**",
        f"- Layered PnL **{out['layered_pnl']:+.3f}**; delta **{out['layered_delta']:+.3f}**",'',
        '## Trade by trade']
    for r in out['rows']:
        md.append(f"- {r['date']}: parent {r['parent_pnl']:+.3f} ({r['parent_reason']}), early10={r['early10_trigger']}, F6.5={r['f65_trigger']}, action={r['layer']}, managed {r['managed_pnl']:+.3f}, delta {r['delta']:+.3f}; first5red={r['first5_red']}, bar2_reclaim={r['bar2_high_reclaims_entry']}, close<EMA7={r['bar2_close_below_ema7']}, body2={r['bar2_body_ratio']:.3f}")
    md += ['','## Guardrail','N=3 is an observation, not enough to retune or statistically validate the rule. If no frozen trigger occurs, this is not evidence that the action rule failed; it means the branch was not exercised. If a trigger occurs, report its result exactly and keep the rule frozen.']
    (OUT/'F6.10_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=float),flush=True)

if __name__=='__main__': main()
