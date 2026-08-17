"""Friday T-Method F5.0 — static-parent forensics, mirroring Tuesday A5.0 process.

NO strategy optimization and NO A6.x management layers.
Frozen diagnostic parent:
- Friday 15:00 WIB exact open
- BUY
- TP 2.00%, SL 0.70%, max hold 6h
- $500 notional, 0.15% round-trip fee

Questions only:
1) WRONG_DIRECTION capacity
2) EARLY_ENTRY / delayed-entry capacity
3) FAILED_THESIS early path separation
4) BAD_EXIT / giveback capacity
"""
import json, statistics
from btc_temporal_a34_5m_events import load, ldt, context, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_friday15_a60_money_geometry import trade, FEE_PCT, NOTIONAL

TP=2.00
SL=0.70
HOLD=360
CHECKPOINTS=(5,10,15,30,60,90,120)


def med(xs): return rnd(statistics.median(xs),4) if xs else None

def contiguous(rows,i,nb):
    return i+nb <= len(rows) and all(rows[j][0]==rows[i][0]+(j-i)*TF for j in range(i,i+nb))

def path(rows,i,mins=HOLD):
    nb=mins//5
    if not contiguous(rows,i,nb): return None
    e=rows[i][1]; q=rows[i:i+nb]
    lows=[x[3] for x in q]; highs=[x[2] for x in q]
    mfe=100*(max(highs)-e)/e
    mae=100*(e-min(lows))/e
    tm={}
    for z in (0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,1.00,1.20,1.50,2.00):
        tfav=tadv=None
        for k,x in enumerate(q):
            if tfav is None and x[2] >= e*(1+z/100): tfav=(k+1)*5
            if tadv is None and x[3] <= e*(1-z/100): tadv=(k+1)*5
            if tfav is not None and tadv is not None: break
        tm[f'fav_{z:.2f}']=tfav; tm[f'adv_{z:.2f}']=tadv
    return {'mfe':mfe,'mae':mae,'times':tm}

def state(rows,i,cp):
    nb=cp//5
    if nb<=0 or not contiguous(rows,i,nb+1): return None
    e=rows[i][1]; obs=rows[i:i+nb]
    tp=e*(1+TP/100); sl=e*(1-SL/100)
    for x in obs:
        if x[2]>=tp or x[3]<=sl: return None
    dec=rows[i+nb][1]
    hi=max(x[2] for x in obs); lo=min(x[3] for x in obs)
    mfe=100*(hi-e)/e; mae=100*(e-lo)/e; net=100*(dec-e)/e
    tbr=[(x[9]/x[6] if x[6] else 0.5) for x in obs]
    taker=statistics.mean(tbr)-0.5
    rng=max(hi-lo,1e-9); close_pos=(dec-lo)/rng
    up=sum(x[4]>x[1] for x in obs)/len(obs)
    return {'net':net,'mfe':mfe,'mae':mae,'taker':taker,'close_pos':close_pos,'up_frac':up}

def short_from(rows,j,end_i,tp=0.7,sl=0.7):
    if j>=end_i or j>=len(rows): return None
    e=rows[j][1]; tp_px=e*(1-tp/100); sl_px=e*(1+sl/100)
    ex=None; reason='TIMEOUT'
    for k in range(j,min(end_i,len(rows))):
        if rows[k][0] != rows[j][0]+(k-j)*TF: return None
        hit_tp=rows[k][3]<=tp_px; hit_sl=rows[k][2]>=sl_px
        if hit_tp and hit_sl: ex=sl_px; reason='AMB_SL'; break
        if hit_sl: ex=sl_px; reason='SL'; break
        if hit_tp: ex=tp_px; reason='TP'; break
    if ex is None: ex=rows[min(end_i,len(rows))-1][4]
    gross=100*(e-ex)/e
    return {'net_usd':NOTIONAL*(gross-FEE_PCT)/100,'reason':reason}

def parent_exit_index(rows,i):
    e=rows[i][1]; tp=e*(1+TP/100); sl=e*(1-SL/100); end=min(len(rows),i+HOLD//5)
    for j in range(i,end):
        x=rows[j]
        if x[0]!=rows[i][0]+(j-i)*TF: return None
        hit_tp=x[2]>=tp; hit_sl=x[3]<=sl
        if hit_tp and hit_sl:return j,'AMB_SL'
        if hit_sl:return j,'SL'
        if hit_tp:return j,'TP'
    return end-1,'TIMEOUT'

def prectx(rows,i):
    c=context(rows,i)
    if c is None:return None
    e=rows[i][1]
    return {'day_pos':c['day_pos'],'pre1':c['pre1'],'pre4':c['pre4'],'pre24':c['pre24'],
            'vs_dopen':100*(e-c['daily_open'])/e,
            'to_hod':100*(c['hod']-e)/e,'to_lod':100*(e-c['lod'])/e}

def summarize_state(recs,cp,positive):
    z=[r['states'].get(cp) for r in recs if (r['base']>0)==positive and r['states'].get(cp) is not None]
    if not z:return None
    return {'n':len(z),'net_med':med([x['net'] for x in z]),'mfe_med':med([x['mfe'] for x in z]),
            'mae_med':med([x['mae'] for x in z]),'taker_med':med([x['taker'] for x in z]),
            'close_pos_med':med([x['close_pos'] for x in z]),'up_frac_med':med([x['up_frac'] for x in z])}
def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==4 and dt.hour==15 and dt.minute==0: idx.append(im[x[0]])
    recs=[]
    for i in idx:
        b=trade(rows,i,TP,SL,HOLD); p=path(rows,i); ex=parent_exit_index(rows,i)
        if b is None or p is None or ex is None: continue
        recs.append({'i':i,'ts':rows[i][0],'base':b['net_usd'],'reason':b['reason'],'mfe':p['mfe'],'mae':p['mae'],
                     'times':p['times'],'states':{cp:state(rows,i,cp) for cp in CHECKPOINTS},'pre':prectx(rows,i),'exit_i':ex[0]})
    pos=[r for r in recs if r['base']>0]; neg=[r for r in recs if r['base']<=0]
    bad_exit={}
    for q in (0.20,0.30,0.40,0.50,0.60,0.80,1.00,1.20,1.50):
        a=[r for r in neg if r['mfe']>=q]; before=[]
        for r in a:
            ft=r['times'].get(f'fav_{q:.2f}'); at=r['times'].get('adv_0.70')
            if ft is not None and (at is None or ft<at): before.append(r)
        bad_exit[str(q)]={'negative_with_mfe':len(a),'mfe_before_sl':len(before)}
    early=[]
    for r in neg:
        if r['reason'] not in ('SL','AMB_SL'): continue
        e=rows[r['i']][1]; target=e*(1+TP/100); end=min(len(rows),r['i']+HOLD//5)
        if any(rows[j][2]>=target for j in range(r['exit_i']+1,end)): early.append(r)
    flip_capacity={}
    for cp in CHECKPOINTS:
        nopen=can07=can20=0
        for r in neg:
            if r['states'].get(cp) is None: continue
            nopen+=1; j=r['i']+cp//5; end=min(len(rows),r['i']+HOLD//5)
            e=rows[r['i']][1]; px=rows[j][1]
            buy=NOTIONAL*((100*(px-e)/e)-FEE_PCT)/100
            q=short_from(rows,j,end,0.7,0.7); z=short_from(rows,j,end,2.0,0.7)
            if q and buy+q['net_usd']>0: can07+=1
            if z and buy+z['net_usd']>0: can20+=1
        flip_capacity[str(cp)]={'negative_still_open':nopen,'flip_short_07_07_total_positive':can07,'flip_short_20_07_total_positive':can20}
    keys=('day_pos','pre1','pre4','pre24','vs_dopen','to_hod','to_lod'); pre={}
    for k in keys:
        pre[k]={'winner_med':med([r['pre'][k] for r in pos if r['pre']]),'loser_med':med([r['pre'][k] for r in neg if r['pre']])}
    out={'status':'FRIDAY_TMETHOD_F50_PARENT_FORENSICS','parent':{'tp':TP,'sl':SL,'hold_min':HOLD,'trades':len(recs),
        'net_wins':len(pos),'net_losses':len(neg),'net_wr':rnd(100*len(pos)/len(recs),2),'net_pnl_usd':rnd(sum(r['base'] for r in recs),3)},
        'exit_reasons':{q:sum(r['reason']==q for r in recs) for q in ('TP','SL','AMB_SL','TIMEOUT')},
        'path_medians':{'winner_mfe':med([r['mfe'] for r in pos]),'winner_mae':med([r['mae'] for r in pos]),
                        'loser_mfe':med([r['mfe'] for r in neg]),'loser_mae':med([r['mae'] for r in neg])},
        'checkpoint_atlas':{str(cp):{'winners':summarize_state(recs,cp,True),'losers':summarize_state(recs,cp,False)} for cp in CHECKPOINTS},
        'bad_exit_capacity':bad_exit,'early_entry_capacity':{'sl_losses_later_reach_original_tp':len(early)},
        'flip_capacity':flip_capacity,'pre_entry_medians':pre,
        'notes':'Diagnostic only. No rule selected and no A6.x layer used.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__': main()
