#!/usr/bin/env python3
"""V7-H — frozen FIB + 24h directional-consensus temporal robustness.

Research only. This is a pseudo-forward robustness test, NOT a pristine OOS
claim, because the candidate was selected after reviewing the 971d V7-G2
forensic. No parameter is fit or swept here.

Frozen candidate:
- V4-B2 FIB band 61.8-70.5
- RR = 1.0, confirm_bars = 3
- own-pair signed 24h return in trade direction > 0
- >= 3 of 4 market pairs aligned with trade direction over completed 24h
  (market_alignment24h >= 0.75)
- all market-state inputs use completed 1h candles available by 5m confirm close

Window and block edges are exactly V7-F/G2: 971d ending
2026-08-15T15:11:15.831175Z, split into 8x120d + 11d remainder.
"""
import json
import os
from datetime import datetime, timezone

from research import v7_g_fib_regime_forensic as g
from research import v7_g2_fib_regime_forensic_warmup as g2


def stat(rows):
    n=len(rows); w=sum(int(r['win']) for r in rows)
    return {'n':n,'wins':w,'losses':n-w,'wr_pct':round(100.0*w/n,2) if n else None}


def grouped(rows,key,values):
    return {v:stat([r for r in rows if r.get(key)==v]) for v in values}


def main():
    coverage=g2.build_db_with_warmup()
    os.environ['DB_PATH']=g.DB

    import v4_context_fib_forensic_endpoint as fib
    import v4_market_state_forensic_endpoint as ms
    from v4_structural_zone_endpoint import _atr

    # Event generator remains pinned to the exact 971d V7-F window.
    fib._load=g.fixed_load
    all_series={p:g2.build_series_with_warmup(p,_atr) for p in g.PAIRS}

    events=[]; errors={}; source={}
    for p in g.PAIRS:
        d=fib.context_fib_forensic(symbols=p,days=g.DAYS,rr=1.0,confirm_bars=3,sample_limit=500)
        source[p]={'overall':d.get('overall'),'fib_bands':d.get('fib_bands'),'errors':d.get('errors')}
        if d.get('errors'): errors[p]=d.get('errors')
        sample=d.get('sample') or []
        if int((d.get('overall') or {}).get('n',0) or 0)>len(sample):
            raise RuntimeError(f'sample truncated {p}')
        for x in sample:
            if x.get('fib_band')!=g.BAND or x.get('outcome') not in ('BOUNCE','BREAK'):
                continue
            dt=datetime.fromisoformat(x['confirm_time'])
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            dt=dt.astimezone(timezone.utc)
            event_close_ms=int(dt.timestamp()*1000)+300_000
            oi=ms._latest_completed_index(all_series[p]['T'],event_close_ms)
            own=ms._pair_state(all_series[p],oi) if oi>=0 else None
            if not own: raise RuntimeError(f'missing state warmup for {p} {dt.isoformat()}')
            trade_dir=1 if x.get('side')=='DEMAND' else -1
            market=ms._market_state(all_series,event_close_ms,trade_dir)
            own_signed24=100.0*own['ret24h']*trade_dir if own.get('ret24h') is not None else None
            align24=market.get('market_alignment24h')
            delta=(dt-g.WINDOW_START).total_seconds()
            block=int(delta//(g.BLOCK_DAYS*86400))+1 if delta>=0 else 0
            events.append({
                'pair':p,'side':x.get('side'),'t':dt,'block':block,
                'win':1 if x.get('outcome')=='BOUNCE' else 0,
                'own_signed_ret24h_pct':own_signed24,
                'market_alignment24h':align24,
                'candidate':bool(own_signed24 is not None and own_signed24>0 and align24 is not None and align24>=0.75),
            })
    events.sort(key=lambda r:r['t'])

    full=[r for r in events if 1<=r['block']<=8]
    rem=[r for r in events if r['block']==9]
    selected=[r for r in full if r['candidate']]
    rejected=[r for r in full if not r['candidate']]
    selected_rem=[r for r in rem if r['candidate']]

    blocks=[]
    for b in range(1,9):
        base=[r for r in full if r['block']==b]
        sel=[r for r in base if r['candidate']]
        rej=[r for r in base if not r['candidate']]
        blocks.append({'block':b,'baseline':stat(base),'selected':stat(sel),'rejected':stat(rej),
                       'selection_rate_pct':round(100.0*len(sel)/len(base),2) if base else None})

    first_half=[r for r in selected if r['block']<=4]
    second_half=[r for r in selected if r['block']>=5]
    pairs=grouped(selected,'pair',g.PAIRS)
    sides=grouped(selected,'side',['DEMAND','SUPPLY'])
    pair_side={}
    for p in g.PAIRS:
        for side in ('DEMAND','SUPPLY'):
            pair_side[f'{p}:{side}']=stat([r for r in selected if r['pair']==p and r['side']==side])

    # Predeclared robustness gate before this run's results were inspected.
    # Low-frequency candidate, so block criterion accepts 50% as non-degrading.
    block_non_degrading=sum(1 for x in blocks if x['selected']['n']>=2 and x['selected']['wr_pct'] is not None and x['selected']['wr_pct']>=50.0)
    pair_eligible=[s for s in pairs.values() if s['n']>=5]
    side_eligible=[s for s in sides.values() if s['n']>=5]
    checks={
        'overall_n_ge25_and_wr_ge65': stat(selected)['n']>=25 and (stat(selected)['wr_pct'] or 0)>=65.0,
        'both_chronological_halves_n_ge8_and_wr_gt55': first_half and second_half and len(first_half)>=8 and len(second_half)>=8 and (stat(first_half)['wr_pct'] or 0)>55.0 and (stat(second_half)['wr_pct'] or 0)>55.0,
        'at_least_6_of_8_blocks_n_ge2_and_wr_ge50': block_non_degrading>=6,
        'at_least_3_pairs_n_ge5_and_wr_gt50': sum(1 for s in pair_eligible if (s['wr_pct'] or 0)>50.0)>=3,
        'both_sides_n_ge5_and_wr_gt50': len(side_eligible)==2 and all((s['wr_pct'] or 0)>50.0 for s in side_eligible),
    }

    result={
        'phase':'V7-H','status':'FROZEN_FIB_24H_CONSENSUS_PSEUDO_FORWARD_ROBUSTNESS',
        'definition':{
            'contamination_note':'candidate selected after reviewing full 971d V7-G2; robustness only, not pristine OOS',
            'window_start':g.WINDOW_START.isoformat(),'window_end':g.WINDOW_END.isoformat(),
            'fib_band':g.BAND,'rr':1.0,'confirm_bars':3,
            'own_24h_rule':'signed 24h return in trade direction > 0',
            'market_24h_rule':'market_alignment24h >= 0.75 (>=3/4 pairs)',
            'causal_state':'completed 1h candles only by 5m confirmation close',
            'threshold_sweep':False,'tp_sl_sweep':False,'live_changes':False,
        },
        'coverage':coverage,'errors':errors,
        'parity':{'all_events':stat(events),'full_8_blocks':stat(full),'remainder_11d':stat(rem),'v7_f_fingerprint':{'n':120,'wins':61,'losses':59,'wr_pct':50.83}},
        'candidate_overall':stat(selected),'candidate_rejected':stat(rejected),'candidate_remainder_11d':stat(selected_rem),
        'chronological_halves':{'blocks_1_4':stat(first_half),'blocks_5_8':stat(second_half)},
        'blocks_120d':blocks,'by_pair':pairs,'by_side':sides,'by_pair_side':pair_side,
        'robustness_gate':{'checks':checks,'passed':all(checks.values()),'block_non_degrading_count':block_non_degrading,'eligible_pairs_n_ge5':len(pair_eligible)},
        'verdict':'PASS_PSEUDO_FORWARD_ROBUSTNESS' if all(checks.values()) else 'FAIL_PSEUDO_FORWARD_ROBUSTNESS',
        'source_pair_diagnostics':source,
    }
    print('V7_H_RESULT',json.dumps(result,separators=(',',':'),default=str))

if __name__=='__main__': main()
