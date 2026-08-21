#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import numpy as np

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_crossover_cycle_entry_b23e as b23e

ROOT = Path(__file__).resolve().parent.parent
TRADES = ROOT / 'BTC_FIRST_GREEN_AFTER_CROSS_B23G_Trades.csv'
OUT_MD = ROOT / 'BTC_FIRST_GREEN_AFTER_CROSS_B23G_LossExitDistribution.md'
OUT_CSV = ROOT / 'BTC_FIRST_GREEN_AFTER_CROSS_B23G_LossExitDistribution.csv'

MAIN_PARTS = ['external','development','reference_validation']


def classify_zone(row):
    if pd.isna(row['ema20']) or pd.isna(row['ema50']) or pd.isna(row['close']):
        return 'UNKNOWN'
    if row['ema20'] < row['ema50']:
        return 'EMA20_BELOW_EMA50'
    if row['close'] < row['ema50']:
        return 'BELOW_EMA50'
    if row['close'] < row['ema20']:
        return 'BETWEEN_EMA20_EMA50'
    return 'ABOVE_EMA20'


def pct(n,d):
    return 100.0*n/d if d else np.nan


def main():
    trades = pd.read_csv(TRADES, parse_dates=['entry_ts','exit_ts'])
    losses = trades[trades['return'] <= 0].copy()

    x5, coverage = b21.load5()
    frames = {tf: b23e.add_cycles(b22b.enrich(b22b.resample_ohlc(x5, rule))) for tf,(rule,_) in b23e.TFS.items()}

    durations = {'5m': pd.Timedelta(minutes=5), '15m': pd.Timedelta(minutes=15), '1h': pd.Timedelta(hours=1), '4h': pd.Timedelta(hours=4)}
    enriched=[]
    for r in losses.itertuples(index=False):
        tf = r.timeframe
        frame = frames[tf]
        trigger_ts = pd.Timestamp(r.exit_ts) - durations[tf]
        if trigger_ts in frame.index:
            z = frame.loc[trigger_ts]
            close=float(z.close); e20=float(z.ema20); e50=float(z.ema50)
            zone=classify_zone({'close':close,'ema20':e20,'ema50':e50})
            state=str(z.state)
        else:
            close=e20=e50=np.nan; zone='UNKNOWN'; state='UNKNOWN'
        enriched.append({
            'partition':r.partition,'timeframe':tf,'entry_ts':r.entry_ts,'exit_ts':r.exit_ts,
            'return':r._asdict().get('return'), 'exit_reason':r.exit_reason,
            'trigger_ts':trigger_ts,'trigger_state':state,'trigger_zone':zone,
            'trigger_close':close,'trigger_ema20':e20,'trigger_ema50':e50,
        })
    e = pd.DataFrame(enriched)

    rows=[]
    for scope, parts in [('main_combined',MAIN_PARTS),('reference_validation',['reference_validation'])]:
        q=e[e.partition.isin(parts)]
        for tf in ['5m','15m','1h','4h']:
            g=q[q.timeframe==tf]
            total=len(g)
            for zone in ['ABOVE_EMA20','BETWEEN_EMA20_EMA50','BELOW_EMA50','EMA20_BELOW_EMA50','UNKNOWN']:
                n=int((g.trigger_zone==zone).sum())
                rows.append({'scope':scope,'timeframe':tf,'kind':'zone','bucket':zone,'n':n,'pct':pct(n,total),'total_losses':total})
            for reason in ['DYNAMIC_DETERIORATION_CUT','REVERSAL_CUT','BEAR_CROSS_CUT','PARTITION_FORCE_CLOSE']:
                n=int((g.exit_reason==reason).sum())
                rows.append({'scope':scope,'timeframe':tf,'kind':'reason','bucket':reason,'n':n,'pct':pct(n,total),'total_losses':total})
    out=pd.DataFrame(rows)
    out.to_csv(OUT_CSV,index=False)

    md=[
        '# B23G Losing-Trade Exit Distribution',
        '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.',
        '',
        'This is post-result forensic diagnostics only. It does not alter B23G rules. A losing trade is any trade with gross return <= 0. The trigger zone is measured on the completed same-timeframe candle that caused the next-open exit.',
        '',
        'Zone definitions: ABOVE_EMA20 = close >= EMA20 > EMA50; BETWEEN_EMA20_EMA50 = EMA20 > close >= EMA50; BELOW_EMA50 = EMA20 > EMA50 and close < EMA50; EMA20_BELOW_EMA50 = EMA20 < EMA50.',
        '',
        '## Main partitions combined (External + Development + Reference Validation)',
        '',
        '| TF | Losing trades | Above EMA20 | Between EMA20/50 | Below EMA50 | EMA20 below EMA50 |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for tf in ['5m','15m','1h','4h']:
        q=out[(out.scope=='main_combined')&(out.timeframe==tf)&(out.kind=='zone')]
        total=int(q.total_losses.iloc[0]) if len(q) else 0
        vals={r.bucket:r for r in q.itertuples()}
        def cell(k):
            r=vals[k]; return f'{r.n} ({r.pct:.2f}%)'
        md.append(f'| {tf} | {total} | {cell("ABOVE_EMA20")} | {cell("BETWEEN_EMA20_EMA50")} | {cell("BELOW_EMA50")} | {cell("EMA20_BELOW_EMA50")} |')

    md += ['', '## Reference Validation only', '', '| TF | Losing trades | Above EMA20 | Between EMA20/50 | Below EMA50 | EMA20 below EMA50 |', '|---|---:|---:|---:|---:|---:|']
    for tf in ['5m','15m','1h','4h']:
        q=out[(out.scope=='reference_validation')&(out.timeframe==tf)&(out.kind=='zone')]
        total=int(q.total_losses.iloc[0]) if len(q) else 0
        vals={r.bucket:r for r in q.itertuples()}
        def cell2(k):
            r=vals[k]; return f'{r.n} ({r.pct:.2f}%)'
        md.append(f'| {tf} | {total} | {cell2("ABOVE_EMA20")} | {cell2("BETWEEN_EMA20_EMA50")} | {cell2("BELOW_EMA50")} | {cell2("EMA20_BELOW_EMA50")} |')

    md += ['', '## Exit-reason distribution, main partitions combined', '', '| TF | Deterioration cut | Reversal cut | Bear-cross cut | Force close |', '|---|---:|---:|---:|---:|']
    for tf in ['5m','15m','1h','4h']:
        q=out[(out.scope=='main_combined')&(out.timeframe==tf)&(out.kind=='reason')]
        vals={r.bucket:r for r in q.itertuples()}
        def rc(k):
            r=vals[k]; return f'{r.n} ({r.pct:.2f}%)'
        md.append(f'| {tf} | {rc("DYNAMIC_DETERIORATION_CUT")} | {rc("REVERSAL_CUT")} | {rc("BEAR_CROSS_CUT")} | {rc("PARTITION_FORCE_CLOSE")} |')

    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__ == '__main__':
    main()
