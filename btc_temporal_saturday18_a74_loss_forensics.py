"""Saturday18 A7.4 — loss-path forensic atlas for the frozen research parent.

Frozen parent (DO NOT retune here):
- Saturday 18:00 WIB exact 5m open
- BUY
- TP 2.60%, SL 1.20%, max hold 18h
- $500 fixed notional, 0.15% round-trip fee
- historical BTCUSDT funding charged per trade using the same A7.3 approximation

Goal: explain the 139 parent trades before changing management.
We quantify four non-exclusive loss mechanisms:
1) WRONG_DIRECTION: a causal early flip to SHORT had oracle capacity.
2) EARLY_ENTRY: BUY direction later worked, but exact 18:00 entry was too early.
3) FAILED_THESIS: early path/flow/EMA state separates eventual losses.
4) GOOD_TRADE_BAD_EXIT: trade achieved useful BUY MFE, then gave it back.

No intervention is optimized in this file. It is an atlas + oracle-capacity study only.
"""
import json, statistics
from btc_temporal_a34_5m_events import load, ldt, context, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade, FEE_PCT, NOTIONAL
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.60
SL=1.20
HOLD=1080
CHECKPOINTS=(15,30,60,120,180,240,360)
MFE_LEVELS=(0.30,0.50,0.80,1.00,1.20,1.50,2.00,2.60)


def med(xs): return rnd(statistics.median(xs),4) if xs else None
def mean(xs): return rnd(statistics.mean(xs),4) if xs else None

def ema_series(rows, period):
    a=2.0/(period+1.0); out=[]; v=None
    for x in rows:
        c=x[4]; v=c if v is None else a*c+(1-a)*v; out.append(v)
    return out

def pct(a,b): return 100.0*(a-b)/b if b else 0.0

def contiguous(rows,i,nb):
    return i+nb<=len(rows) and all(rows[j][0]==rows[i][0]+(j-i)*TF for j in range(i,i+nb))

def funding_adjust(rows,t,funding,tsmap):
    """Return funding-adjusted parent PnL using the A7.3 methodology."""
    exit_ts=t['ts']+(t['bars']-1)*TF
    qty=NOTIONAL/t['entry']; fpay=0.0; events=0
    for ft,rate in funding:
        if ft<=t['ts']: continue
        if ft>exit_ts: break
        px=(tsmap.get(ft) or [None,t['entry']])[1]
        fpay += -qty*px*rate; events += 1
    return t['net_usd']+fpay, fpay, events

def path(rows,i):
    nb=HOLD//5
    if not contiguous(rows,i,nb): return None
    e=rows[i][1]; q=rows[i:i+nb]
    hi=max(x[2] for x in q); lo=min(x[3] for x in q)
    mfe=100*(hi-e)/e; mae=100*(e-lo)/e
    tm={}
    for z in MFE_LEVELS:
        fav=adv=None
        for k,x in enumerate(q):
            if fav is None and x[2]>=e*(1+z/100): fav=(k+1)*5
            if adv is None and x[3]<=e*(1-z/100): adv=(k+1)*5
            if fav is not None and adv is not None: break
        tm[f'fav_{z:.2f}']=fav; tm[f'adv_{z:.2f}']=adv
    return {'mfe':mfe,'mae':mae,'times':tm}

def parent_exit_index(rows,i):
    e=rows[i][1]; tp=e*(1+TP/100); sl=e*(1-SL/100); end=min(len(rows),i+HOLD//5)
    for j in range(i,end):
        x=rows[j]
        if x[0]!=rows[i][0]+(j-i)*TF: return None
        ht=x[2]>=tp; hs=x[3]<=sl
        if ht and hs:return j,'AMB_SL'
        if hs:return j,'SL'
        if ht:return j,'TP'
    return end-1,'TIMEOUT'

def state(rows,i,cp,e7,e20):
    nb=cp//5
    if nb<=0 or not contiguous(rows,i,nb+1): return None
    e=rows[i][1]; obs=rows[i:i+nb]; tp=e*(1+TP/100); sl=e*(1-SL/100)
    for x in obs:
        if x[2]>=tp or x[3]<=sl:return None
    j=i+nb; dec=rows[j][1]; hi=max(x[2] for x in obs); lo=min(x[3] for x in obs)
    tbr=[(x[9]/x[6] if x[6] else 0.5) for x in obs]
    prev=max(0,j-1); p3=max(0,j-3)
    return {
        'progress':100*(dec-e)/e,
        'mfe':100*(hi-e)/e,'mae':100*(e-lo)/e,
        'taker':statistics.mean(tbr)-0.5,
        'up_frac':sum(x[4]>x[1] for x in obs)/len(obs),
        'd7':pct(dec,e7[j]),'d20':pct(dec,e20[j]),
        's7_1':pct(e7[j],e7[prev]),'s7_3':pct(e7[j],e7[p3]),
        's20_1':pct(e20[j],e20[prev]),'s20_3':pct(e20[j],e20[p3]),
        'above7':dec>e7[j],'above20':dec>e20[j],
    }

def prectx(rows,i,e7,e20):
    c=context(rows,i)
    if c is None:return None
    e=rows[i][1]; p=max(0,i-1); p3=max(0,i-3)
    return {
      'day_pos':c['day_pos'],'pre1':c['pre1'],'pre4':c['pre4'],'pre24':c['pre24'],
      'vs_dopen':100*(e-c['daily_open'])/e,'to_hod':100*(c['hod']-e)/e,'to_lod':100*(e-c['lod'])/e,
      'd7':pct(e,e7[i]),'d20':pct(e,e20[i]),'s7_3':pct(e7[i],e7[p3]),'s20_3':pct(e20[i],e20[p3]),
      'above7':e>e7[i],'above20':e>e20[i]
    }

def simulate_buy_from(rows,j,end_i,tp=TP,sl=SL):
    if j>=end_i:return None
    e=rows[j][1]; tp_px=e*(1+tp/100); sl_px=e*(1-sl/100); ex=None; reason='TIMEOUT'
    for k in range(j,min(end_i,len(rows))):
        if rows[k][0]!=rows[j][0]+(k-j)*TF:return None
        ht=rows[k][2]>=tp_px; hs=rows[k][3]<=sl_px
        if ht and hs:ex=sl_px;reason='AMB_SL';break
        if hs:ex=sl_px;reason='SL';break
        if ht:ex=tp_px;reason='TP';break
    if ex is None: ex=rows[min(end_i,len(rows))-1][4]
    gross=100*(ex-e)/e
    return NOTIONAL*(gross-FEE_PCT)/100,reason

def simulate_short_from(rows,j,end_i,tp=1.2,sl=1.2):
    if j>=end_i:return None
    e=rows[j][1]; tp_px=e*(1-tp/100); sl_px=e*(1+sl/100); ex=None; reason='TIMEOUT'
    for k in range(j,min(end_i,len(rows))):
        if rows[k][0]!=rows[j][0]+(k-j)*TF:return None
        ht=rows[k][3]<=tp_px; hs=rows[k][2]>=sl_px
        if ht and hs:ex=sl_px;reason='AMB_SL';break
        if hs:ex=sl_px;reason='SL';break
        if ht:ex=tp_px;reason='TP';break
    if ex is None: ex=rows[min(end_i,len(rows))-1][4]
    gross=100*(e-ex)/e
    return NOTIONAL*(gross-FEE_PCT)/100,reason

def grp_state(recs,cp,win):
    z=[r['states'].get(cp) for r in recs if (r['base']>0)==win and r['states'].get(cp)]
    if not z:return None
    fields=('progress','mfe','mae','taker','up_frac','d7','d20','s7_1','s7_3','s20_1','s20_3')
    out={'n':len(z)}
    for f in fields:out[f+'_med']=med([x[f] for x in z])
    out['above7_pct']=rnd(100*sum(x['above7'] for x in z)/len(z),2)
    out['above20_pct']=rnd(100*sum(x['above20'] for x in z)/len(z),2)
    return out

def split_counts(recs,pred):
    d=recs[:83]; v=recs[83:]
    return {'full':sum(pred(r) for r in recs),'discovery':sum(pred(r) for r in d),'validation':sum(pred(r) for r in v)}

def main():
    rows=load(); tsmap={x[0]:x for x in rows}; im={x[0]:i for i,x in enumerate(rows)}
    e7=ema_series(rows,7); e20=ema_series(rows,20); funding,headers,misses=load_funding()
    idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==5 and dt.hour==18 and dt.minute==0:idx.append(im[x[0]])
    recs=[]
    for i in idx:
        t=trade(rows,i,TP,SL,HOLD); p=path(rows,i); ex=parent_exit_index(rows,i)
        if t is None or p is None or ex is None:continue
        base,fpay,fev=funding_adjust(rows,t,funding,tsmap)
        recs.append({'i':i,'ts':rows[i][0],'base':base,'raw_base':t['net_usd'],'funding':fpay,'funding_events':fev,
          'reason':t['reason'],'exit_i':ex[0],'mfe':p['mfe'],'mae':p['mae'],'times':p['times'],
          'states':{cp:state(rows,i,cp,e7,e20) for cp in CHECKPOINTS},'pre':prectx(rows,i,e7,e20)})
    pos=[r for r in recs if r['base']>0]; neg=[r for r in recs if r['base']<=0]

    # GOOD TRADE / BAD EXIT capacity.
    giveback={}
    for q in MFE_LEVELS[:-1]:
        key=f'fav_{q:.2f}'
        z=[r for r in neg if r['mfe']>=q]
        before=[r for r in z if r['times'].get(key) is not None and (r['times'].get('adv_1.20') is None or r['times'][key]<r['times']['adv_1.20'])]
        giveback[str(q)]={'losses_reached_mfe':len(z),'mfe_before_full_sl':len(before),
          'split':split_counts(recs,lambda r,q=q,key=key: r['base']<=0 and r['mfe']>=q and r['times'].get(key) is not None)}

    # EARLY ENTRY type A: SL hit but original BUY TP later occurs inside the original 18h window.
    later_tp=[]
    for r in neg:
        if r['reason'] not in ('SL','AMB_SL'):continue
        e=rows[r['i']][1]; target=e*(1+TP/100); end=min(len(rows),r['i']+HOLD//5)
        if any(rows[j][2]>=target for j in range(r['exit_i']+1,end)):later_tp.append(r)

    # EARLY ENTRY type B: delayed BUY with same geometry and remaining original horizon becomes net-positive.
    delayed={}; flip={}
    for cp in CHECKPOINTS:
        still=buypos=short12=short26=0
        for r in neg:
            if not r['states'].get(cp):continue
            still+=1; j=r['i']+cp//5; end=min(len(rows),r['i']+HOLD//5)
            b=simulate_buy_from(rows,j,end,TP,SL)
            if b and b[0]>0:buypos+=1
            s=simulate_short_from(rows,j,end,1.2,1.2)
            if s and s[0]>0:short12+=1
            s2=simulate_short_from(rows,j,end,2.6,1.2)
            if s2 and s2[0]>0:short26+=1
        delayed[str(cp)]={'losses_still_open':still,'delayed_same_buy_positive':buypos}
        flip[str(cp)]={'losses_still_open':still,'short_1.2_1.2_positive':short12,'short_2.6_1.2_positive':short26}

    # Pre-entry descriptive atlas.
    pre={}; prekeys=('day_pos','pre1','pre4','pre24','vs_dopen','to_hod','to_lod','d7','d20','s7_3','s20_3')
    for k in prekeys:
        pre[k]={'winner_med':med([r['pre'][k] for r in pos if r['pre']]),'loser_med':med([r['pre'][k] for r in neg if r['pre']])}
    pre['above7_pct']={'winner':rnd(100*sum(r['pre']['above7'] for r in pos if r['pre'])/len(pos),2),'loser':rnd(100*sum(r['pre']['above7'] for r in neg if r['pre'])/len(neg),2)}
    pre['above20_pct']={'winner':rnd(100*sum(r['pre']['above20'] for r in pos if r['pre'])/len(pos),2),'loser':rnd(100*sum(r['pre']['above20'] for r in neg if r['pre'])/len(neg),2)}

    out={
      'status':'SATURDAY18_A74_LOSS_FORENSICS',
      'parent':{'entry':'Saturday 18:00 WIB BUY','tp':TP,'sl':SL,'hold_min':HOLD,'trades':len(recs),'wins':len(pos),'losses':len(neg),
        'wr':rnd(100*len(pos)/len(recs),2),'net_pnl_funding_adj':rnd(sum(r['base'] for r in recs),3),'funding_usd':rnd(sum(r['funding'] for r in recs),3)},
      'funding':{'records':len(funding),'missing_months':misses},
      'exit_reasons':{q:sum(r['reason']==q for r in recs) for q in ('TP','SL','AMB_SL','TIMEOUT')},
      'path_medians':{'winner_mfe':med([r['mfe'] for r in pos]),'winner_mae':med([r['mae'] for r in pos]),'loser_mfe':med([r['mfe'] for r in neg]),'loser_mae':med([r['mae'] for r in neg])},
      'giveback_capacity':giveback,
      'early_entry_capacity':{'sl_losses_later_reach_original_tp':len(later_tp),'split':split_counts(recs,lambda r: r in later_tp)},
      'delayed_buy_capacity':delayed,
      'wrong_direction_short_capacity':flip,
      'checkpoint_atlas':{str(cp):{'winners':grp_state(recs,cp,True),'losers':grp_state(recs,cp,False)} for cp in CHECKPOINTS},
      'pre_entry_medians':pre
    }
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
