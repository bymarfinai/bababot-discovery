"""Friday T-Method F5.11 — hidden-state reversal forensics.

Purpose
-------
F5.7 proved large ex-post BUY->SHORT reversal capacity, while F5.8-F5.10 showed
that ordinary 5m price/volume/taker-flow rules could not identify the pivot
causally. F5.11 asks whether futures hidden-state variables change before a
future-good reversal while price can still look bullish.

This is FORENSICS ONLY. No trading rule or threshold is selected.

Frozen parent / oracle label
----------------------------
- Friday 15:00 WIB BUY
- TP2.0 / SL0.7 / hold360m
- candidate decision opens every 5m from +15m to +180m while BUY is alive
- diagnostic SHORT fixed TP0.7 / SL0.7 / hold180m
- GOOD_REVERSE label (future-only): SHORT net >= $1 and combined BUY-close+SHORT
  improves the frozen parent by >= $2

Causal features at every decision open use only information strictly before the
open. Official Binance USD-M daily metrics archives supply OI / top-trader /
global positioning / taker long-short snapshots. Completed 5m klines supply a
CVD-like taker-flow proxy and EMA state.

EMA is deliberately included as a comparator, not assumed to be useful.
"""
import json, math, statistics
from collections import defaultdict

from btc_temporal_a34_5m_events import load, ldt, rnd, TF
import btc_temporal_friday15_f57_reversal_pivot_atlas as F57
import btc_temporal_friday15_a645_positioning_attribution as POS
from btc_temporal_friday15_a60_money_geometry import trade

BUY_TP=2.0; BUY_SL=0.7; BUY_HOLD=360
WINDOWS=(5,15,30)


def mean(x): return statistics.mean(x) if x else None

def median(x): return statistics.median(x) if x else None

def pct(a,b): return 100*(a/b-1) if b else None

def safe_div(a,b,default=0.0): return a/b if b else default


def auc(vals, labels):
    q=[(v,int(y)) for v,y in zip(vals,labels) if v is not None]
    pos=[v for v,y in q if y]; neg=[v for v,y in q if not y]
    if not pos or not neg:return None
    # Mann-Whitney probability with ties=0.5; O(n^2) is fine for ~4k rows.
    s=0.0
    for a in pos:
        for b in neg:
            if a>b:s+=1
            elif a==b:s+=.5
    return s/(len(pos)*len(neg))


def stat(vals):
    vals=[v for v in vals if v is not None]
    if not vals:return {'n':0}
    return {'n':len(vals),'mean':rnd(mean(vals),5),'median':rnd(median(vals),5)}


def ema_series(rows,n):
    alpha=2/(n+1); out=[]; e=None
    for x in rows:
        c=x[4]; e=c if e is None else alpha*c+(1-alpha)*e; out.append(e)
    return out


def kline_window(rows,j,mins):
    n=mins//5
    if j-n<0:return None
    q=rows[j-n:j]  # completed strictly before decision open j
    if len(q)!=n:return None
    for k in range(1,len(q)):
        if q[k][0]!=q[k-1][0]+TF:return None
    p0=q[0][1]; pc=q[-1][4]
    ret=100*(pc/p0-1)
    quote=sum(x[6] for x in q)
    taker_buy_quote=sum(x[9] for x in q)
    taker_ratio=taker_buy_quote/quote if quote>0 else .5
    taker_imb=2*taker_ratio-1
    hi=max(x[2] for x in q);lo=min(x[3] for x in q)
    rng=100*(hi/lo-1) if lo>0 else 0
    bar_abs=sum(abs(100*(x[4]/x[1]-1)) for x in q)
    eff=abs(ret)/bar_abs if bar_abs else 0
    # Positive absorption_buy_fail means aggressive buying accompanies flat/down price.
    buy_fail=max(0,taker_imb)*max(0,-ret)
    sell_fail=max(0,-taker_imb)*max(0,ret)
    return {'ret':ret,'taker_imb':taker_imb,'range':rng,'eff':eff,
            'buy_fail':buy_fail,'sell_fail':sell_fail}


def metric_snapshot_features(metrics,ts):
    # Strictly before decision open.
    last=POS.nearest_at_or_before(metrics,ts-1)
    if last is None:return None
    out={
      'top_position':last['sum_toptrader_long_short_ratio'],
      'top_account':last['count_toptrader_long_short_ratio'],
      'global_account':last['count_long_short_ratio'],
      'taker_ls':last['sum_taker_long_short_vol_ratio'],
      'oi_value':last['sum_open_interest_value'],
    }
    out['top_vs_global']=safe_div(out['top_position'],out['global_account'],1.0)-1
    out['top_pos_vs_account']=safe_div(out['top_position'],out['top_account'],1.0)-1
    out['snapshot_age_min']=(ts-last['ts'])/60000
    for w in WINDOWS:
        old=POS.nearest_at_or_before(metrics,ts-w*60000-1)
        if old is None:
            for k in ('oi','top_position','top_account','global_account','taker_ls'):
                out[f'{k}_chg_{w}']=None
            continue
        out[f'oi_chg_{w}']=pct(last['sum_open_interest_value'],old['sum_open_interest_value'])
        out[f'top_position_chg_{w}']=pct(last['sum_toptrader_long_short_ratio'],old['sum_toptrader_long_short_ratio'])
        out[f'top_account_chg_{w}']=pct(last['count_toptrader_long_short_ratio'],old['count_toptrader_long_short_ratio'])
        out[f'global_account_chg_{w}']=pct(last['count_long_short_ratio'],old['count_long_short_ratio'])
        out[f'taker_ls_chg_{w}']=pct(last['sum_taker_long_short_vol_ratio'],old['sum_taker_long_short_vol_ratio'])
    return out


def event_features(rows,j,entry_i,metrics,e7,e20):
    ts=rows[j][0]
    m=metric_snapshot_features(metrics,ts)
    if m is None:return None
    out=dict(m)
    for w in WINDOWS:
        z=kline_window(rows,j,w)
        if z is None:continue
        for k,v in z.items():out[f'{k}_{w}']=v
        oi=out.get(f'oi_chg_{w}')
        if oi is not None:
            out[f'price_x_oi_{w}']=z['ret']*oi
            out[f'up_oi_down_{w}']=max(0,z['ret'])*max(0,-oi)
            out[f'up_oi_up_{w}']=max(0,z['ret'])*max(0,oi)
            out[f'down_oi_up_{w}']=max(0,-z['ret'])*max(0,oi)
    # 5m EMA state based on the last completed bar j-1.
    if j>=4:
        px=rows[j-1][4]
        out['ema7_dist']=100*(px/e7[j-1]-1)
        out['ema20_dist']=100*(px/e20[j-1]-1)
        out['ema_spread']=100*(e7[j-1]/e20[j-1]-1)
        out['ema7_slope15']=100*(e7[j-1]/e7[j-4]-1)
        out['ema20_slope15']=100*(e20[j-1]/e20[j-4]-1)
        out['ema_spread_chg15']=100*((e7[j-1]/e20[j-1])/(e7[j-4]/e20[j-4])-1)
    # Path state relative to Friday BUY entry, known causally at this time.
    st=F57.path_state(rows,entry_i,j)
    if st:
        for k,v in st.items():out[f'path_{k}']=v
    return out


def split_event(ev,cut_ts):return ev['entry_ts']<cut_ts


def build_events():
    rows=load(); e7=ema_series(rows,7); e20=ema_series(rows,20)
    entries=F57.indices(rows); cache={}; events=[]; occ=[]
    for i in entries:
        p=trade(rows,i,BUY_TP,BUY_SL,BUY_HOLD)
        if p is None:continue
        date=ldt(rows[i][0]).strftime('%Y-%m-%d')
        if date not in cache:
            cache[date]=POS.load_day(date)
            print('METRICS_DAY',date,'ROWS',len(cache[date]),flush=True)
        metrics=cache[date]
        candidates=[]
        for minute in range(F57.START_MIN,F57.END_MIN+1,F57.STEP_MIN):
            j=i+minute//5
            if j>=len(rows) or rows[j][0]!=rows[i][0]+(j-i)*TF:continue
            if not F57.parent_alive_before(rows,i,j):continue
            s=F57.short_trade(rows,j)
            if s is None:continue
            buy=F57.buy_close_pnl(rows[i][1],rows[j][1]); combined=buy+s['net_usd']; delta=combined-p['net_usd']
            feat=event_features(rows,j,i,metrics,e7,e20)
            if feat is None:continue
            good=(s['net_usd']>=1.0 and delta>=2.0)
            rec={'entry_ts':rows[i][0],'ts':rows[j][0],'date':date,'minute':minute,
                 'parent':p['net_usd'],'parent_reason':p['reason'],'short':s['net_usd'],
                 'delta':delta,'good':good,'feat':feat,'j':j,'i':i}
            events.append(rec);candidates.append(rec)
        if candidates:
            best=max(candidates,key=lambda r:r['delta'] if r['short']>=1.0 else -1e9)
            strong=bool(best['short']>=1.0 and best['delta']>=2.0)
            occ.append({'date':date,'entry_ts':rows[i][0],'strong':strong,'best':best if strong else None,
                        'parent':p['net_usd'],'parent_reason':p['reason']})
    return rows,e7,e20,cache,events,occ


def feature_stability(events):
    # Same 60/40 chronological split by occurrence timestamp as prior T-Method.
    unique=sorted(set(e['entry_ts'] for e in events)); cut=unique[int(len(unique)*.60)]
    names=sorted(set(k for e in events for k in e['feat'].keys()))
    out=[]
    for name in names:
        disc=[e for e in events if e['entry_ts']<cut and e['feat'].get(name) is not None]
        val=[e for e in events if e['entry_ts']>=cut and e['feat'].get(name) is not None]
        da=auc([e['feat'][name] for e in disc],[e['good'] for e in disc]); va=auc([e['feat'][name] for e in val],[e['good'] for e in val])
        if da is None or va is None:continue
        dd=da-.5;vd=va-.5;same=(dd==0 or vd==0 or dd*vd>0)
        out.append({'feature':name,'disc_auc':rnd(da,4),'val_auc':rnd(va,4),'same_direction':same,
                    'disc_strength':rnd(abs(dd),4),'val_strength':rnd(abs(vd),4),'min_strength':rnd(min(abs(dd),abs(vd)),4)})
    return sorted(out,key=lambda z:(z['same_direction'],z['min_strength']),reverse=True),cut


def paired_pre_pivot(rows,e7,e20,cache,occ):
    # Strong oracle best pivot vs 5/10/15/20/30 minutes earlier in the SAME occurrence.
    results={w:defaultdict(list) for w in WINDOWS+(20,)}
    n={w:0 for w in WINDOWS+(20,)}
    for o in occ:
        if not o['strong']:continue
        b=o['best']; j=b['j'];i=b['i']; metrics=cache[o['date']]
        now=b['feat']
        for lag in WINDOWS+(20,):
            jj=j-lag//5
            if jj<=i or not F57.parent_alive_before(rows,i,jj):continue
            old=event_features(rows,jj,i,metrics,e7,e20)
            if old is None:continue
            common=set(now).intersection(old); n[lag]+=1
            for k in common:
                a=now.get(k);z=old.get(k)
                if isinstance(a,(int,float)) and isinstance(z,(int,float)):
                    results[lag][k].append(a-z)
    out={}
    for lag,d in results.items():
        ranked=[]
        for k,v in d.items():
            if not v:continue
            ranked.append({'feature':k,'n':len(v),'median_change':rnd(median(v),5),'mean_change':rnd(mean(v),5),
                           'positive_share':rnd(sum(x>0 for x in v)/len(v),3)})
        ranked.sort(key=lambda z:abs(z['median_change']),reverse=True)
        out[str(lag)]={'pairs':n[lag],'changes':ranked[:30]}
    return out


def group_summary(events,names):
    good=[e for e in events if e['good']];bad=[e for e in events if not e['good']]
    out={}
    for name in names:
        out[name]={'good':stat([e['feat'].get(name) for e in good]),'other':stat([e['feat'].get(name) for e in bad])}
    return out


def main():
    rows,e7,e20,cache,events,occ=build_events()
    ranked,cut=feature_stability(events)
    # Report compact spotlight on hidden-state + EMA, not thousands of features.
    spotlight=['oi_chg_5','oi_chg_15','oi_chg_30','top_position','top_position_chg_5','top_position_chg_15','top_position_chg_30',
               'top_account_chg_15','global_account_chg_15','taker_ls','taker_ls_chg_5','taker_ls_chg_15','taker_ls_chg_30',
               'top_vs_global','ret_5','ret_15','ret_30','taker_imb_5','taker_imb_15','taker_imb_30',
               'up_oi_down_5','up_oi_down_15','up_oi_down_30','buy_fail_5','buy_fail_15','buy_fail_30',
               'ema7_dist','ema20_dist','ema_spread','ema7_slope15','ema20_slope15','ema_spread_chg15']
    stable_hidden=[r for r in ranked if r['feature'] in spotlight]
    out={'status':'FRIDAY_TMETHOD_F511_HIDDEN_STATE_REVERSAL_FORENSICS',
         'design':{'forensics_only':True,'events':len(events),'occurrences':len(occ),'strong_occurrences':sum(o['strong'] for o in occ),
                   'good_event_rate':rnd(sum(e['good'] for e in events)/len(events),4) if events else None,
                   'split_cut_date':ldt(cut).strftime('%Y-%m-%d') if cut else None,
                   'metrics_source':'Binance USD-M daily metrics; snapshots strictly before decision open',
                   'ema_role':'comparator only; 5m EMA7/EMA20 from completed bars'},
         'feature_stability_all_top30':ranked[:30],
         'feature_stability_spotlight':stable_hidden,
         'group_summary_spotlight':group_summary(events,spotlight),
         'paired_hidden_transition_before_strong_oracle_pivot':paired_pre_pivot(rows,e7,e20,cache,occ),
         'notes':'Future GOOD_REVERSE labels are diagnostic only. No threshold or trading rule is selected in F5.11. F5.12 is allowed only if a hidden-state transition is directionally stable enough to justify it.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
