"""BTC Friday15 A6.9 — loss forensics for frozen A6.7 pullback candidate.

Population is NOT re-filtered or re-optimized:
- Friday exact 15:00 WIB BUY
- selected only when open<EMA7, open<EMA20, EMA7 15m slope<0, EMA20 15m slope<0
- indicators completed through i-1 only
- TP 2.0%, SL 0.7%, max hold 360m, fee 0.15%, $500 notional

Question: why do the selected executable trades lose?
This is taxonomy/diagnostic only. No management rule is promoted here.
"""
import json, statistics
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a724_preentry_wrongway_atlas as a724
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

TP=2.0; SL=.7; HOLD=360; FEE=.15
CHECKS=(15,30,60,120,240,360)


def mean(xs): return statistics.mean(xs) if xs else 0.0
def med(xs): return rnd(statistics.median(xs),4) if xs else None

def selected(px):
    return px['d7']<0 and px['d20']<0 and px['s7_15']<0 and px['s20_15']<0

def pct(px,e): return 100.0*(px-e)/e

def path_stats(rows,i,e):
    end=i+HOLD//5
    if end>=len(rows): return None
    if rows[end][0] != rows[i][0] + (HOLD//5)*TF: return None
    q=rows[i:end]
    mfe=max(100*(x[2]-e)/e for x in q)
    mae=max(100*(e-x[3])/e for x in q)
    # first chronological touch of useful levels, adverse-first inside the same bar.
    levels=(.3,.5,.8,1.0,1.5)
    first_up={str(z):None for z in levels}; first_dn={str(z):None for z in (.3,.5,.7)}
    peak=-1e9; peak_k=None; trough=1e9; trough_k=None
    for k,x in enumerate(q):
        hi=100*(x[2]-e)/e; lo=100*(x[3]-e)/e
        if hi>peak: peak=hi; peak_k=k
        if lo<trough: trough=lo; trough_k=k
        for z in levels:
            if first_up[str(z)] is None and hi>=z: first_up[str(z)]=k*5
        for z in (.3,.5,.7):
            if first_dn[str(z)] is None and lo<=-z: first_dn[str(z)]=k*5
    return {'mfe':mfe,'mae':mae,'peak_min':peak_k*5 if peak_k is not None else None,
            'trough_min':trough_k*5 if trough_k is not None else None,'first_up':first_up,'first_dn':first_dn,
            'close360':100*(q[-1][4]-e)/e}

def tax(r):
    m=r['path']['mfe']
    if m < .30: return 'A_WRONG_WAY_LT_03'
    if m < .50: return 'B_WEAK_POP_03_05'
    if m < 1.00: return 'C_GIVEBACK_05_10'
    return 'D_DEEP_GIVEBACK_GE_10'

def checkpoint(rows,r,e7,e20,h):
    i=r['i']; j=i+h//5
    if j>=len(rows) or rows[j][0]!=rows[i][0]+(h//5)*TF:return None
    e=r['entry']; op=rows[j][1]
    done=rows[i:j]
    if not done:return None
    mfe=max(100*(x[2]-e)/e for x in done); mae=max(100*(e-x[3])/e for x in done)
    taker=mean([(x[9]/x[6] if x[6] else .5) for x in done])-.5
    last=j-1; prev=max(0,last-3)
    return {'progress':100*(op-e)/e,'mfe':mfe,'mae':mae,'taker':taker,
            'd7':100*(op-e7[last])/e7[last],'d20':100*(op-e20[last])/e20[last],
            's7_15':100*(e7[last]-e7[prev])/e7[prev] if e7[prev] else 0,
            's20_15':100*(e20[last]-e20[prev])/e20[prev] if e20[prev] else 0}

def atlas(q):
    out={}
    labs=['WIN','A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10']
    for lab in labs:
        z=[r for r in q if r['label']==lab]
        d={'n':len(z)}
        if z:
            d.update({'mfe_med':med([r['path']['mfe'] for r in z]),'mae_med':med([r['path']['mae'] for r in z]),
                      'peak_min_med':med([r['path']['peak_min'] for r in z]),
                      'pre1_med':med([r['prex']['pre1'] for r in z]),'pre4_med':med([r['prex']['pre4'] for r in z]),
                      'd20_entry_med':med([r['prex']['d20'] for r in z]),'s20_15_entry_med':med([r['prex']['s20_15'] for r in z])})
            for h in CHECKS:
                zz=[r['checks'][str(h)] for r in z if r['checks'].get(str(h))]
                for f in ('progress','mfe','mae','taker','d7','d20','s7_15','s20_15'):
                    d[f'{h}_{f}_med']=med([x[f] for x in zz])
        out[lab]=d
    return out

def split_counts(q):
    labs=['WIN','A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10']
    return {lab:sum(r['label']==lab for r in q) for lab in labs}

def first_order_capacity(q):
    losses=[r for r in q if r['label']!='WIN']
    def before(a,b):
        x=r['path']['first_up'][str(a)]; y=r['path']['first_dn'][str(b)]
        return x is not None and (y is None or x<y)
    out={}
    for up in (.3,.5,.8,1.0):
        for dn in (.3,.5,.7):
            n=0
            for r in losses:
                x=r['path']['first_up'][str(up)]; y=r['path']['first_dn'][str(dn)]
                if x is not None and (y is None or x<y): n+=1
            out[f'up{up}_before_dn{dn}']=n
    return out

def recovery_after_exit(rows,r):
    if r['trade']['reason'] not in ('SL','AMB_SL'): return None
    i=r['i']; e=r['entry']; exit_bars=r['trade']['bars']; start=i+exit_bars
    end=i+HOLD//5
    q=rows[start:end]
    if not q:return {'nbar':0,'mfe_after_sl':None,'reaches_entry_netpositive':False,'reaches_tp':False}
    mfe=max(100*(x[2]-e)/e for x in q)
    return {'nbar':len(q),'mfe_after_sl':rnd(mfe,4),'reaches_entry_netpositive':mfe>=FEE,'reaches_05':mfe>=.5,'reaches_10':mfe>=1.0,'reaches_tp':mfe>=TP}

def recovery_summary(q):
    z=[r for r in q if r.get('recovery')]
    return {'sl_losses':len(z),
      'recover_netpositive':sum(x['recovery']['reaches_entry_netpositive'] for x in z),
      'recover_05':sum(x['recovery']['reaches_05'] for x in z),
      'recover_10':sum(x['recovery']['reaches_10'] for x in z),
      'recover_tp2':sum(x['recovery']['reaches_tp'] for x in z),
      'mfe_after_sl_med':med([x['recovery']['mfe_after_sl'] for x in z if x['recovery']['mfe_after_sl'] is not None])}

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; e7=a74.ema_series(rows,7); e20=a74.ema_series(rows,20)
    rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]]; px=a724.pre_features(rows,i,e7,e20)
        if px is None or not selected(px):continue
        t=a60.trade(rows,i,TP,SL,HOLD); p=path_stats(rows,i,x[1])
        if t is None or p is None:continue
        r={'i':i,'ts':x[0],'entry':x[1],'prex':px,'trade':t,'path':p}
        r['label']='WIN' if t['net_usd']>0 else tax(r)
        r['checks']={str(h):checkpoint(rows,r,e7,e20,h) for h in CHECKS}
        r['recovery']=recovery_after_exit(rows,r)
        rec.append(r)
    split=int(138*.60) # preserve original Friday chronology boundary: first 82 all-Friday occurrences
    # Selected rows need split by timestamp at the 83rd all-Friday occurrence, not 60% of selected.
    all_idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==4 and d.hour==15 and d.minute==0: all_idx.append(x[0])
    boundary=all_idx[82]
    disc=[r for r in rec if r['ts']<boundary]; val=[r for r in rec if r['ts']>=boundary]
    losses=[r for r in rec if r['label']!='WIN']
    out={'status':'FRIDAY15_A69_LOSS_FORENSICS','selected_n':len(rec),'wins':sum(r['label']=='WIN' for r in rec),'losses':len(losses),
      'discovery_n':len(disc),'validation_n':len(val),'counts':{'full':split_counts(rec),'discovery':split_counts(disc),'validation':split_counts(val)},
      'exit_reasons_full':{z:sum(r['trade']['reason']==z for r in rec) for z in ('TP','SL','AMB_SL','TIMEOUT')},
      'loss_exit_reasons':{z:sum(r['trade']['reason']==z for r in losses) for z in ('SL','AMB_SL','TIMEOUT')},
      'loss_capacity':{
        'mfe_ge_03':sum(r['path']['mfe']>=.3 for r in losses),'mfe_ge_05':sum(r['path']['mfe']>=.5 for r in losses),
        'mfe_ge_08':sum(r['path']['mfe']>=.8 for r in losses),'mfe_ge_10':sum(r['path']['mfe']>=1.0 for r in losses),
        'mfe_ge_15':sum(r['path']['mfe']>=1.5 for r in losses),
        'first_order':first_order_capacity(rec)},
      'recovery_after_sl':{'full':recovery_summary(rec),'discovery':recovery_summary(disc),'validation':recovery_summary(val)},
      'atlas':{'full':atlas(rec),'discovery':atlas(disc),'validation':atlas(val)},
      'loss_cases':[{'ts':r['ts'],'label':r['label'],'reason':r['trade']['reason'],'net':rnd(r['trade']['net_usd'],3),
                     'mfe':rnd(r['path']['mfe'],4),'mae':rnd(r['path']['mae'],4),'peak_min':r['path']['peak_min'],
                     'first_up':r['path']['first_up'],'first_dn':r['path']['first_dn'],'recovery':r['recovery']} for r in losses]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
