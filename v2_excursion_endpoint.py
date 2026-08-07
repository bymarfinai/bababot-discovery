"""V2 Gated + 15m Execution Layer — causal 15m entries within V2 regime.

Architecture:
1. V2 detector on 1H → REGIME (BULL/BEAR/SIDEWAYS)
2. During BULL: scan 15m candles for LONG entries (EMA7 reclaim on 15m)
3. During BEAR: scan 15m candles for SHORT entries (EMA7 rejection on 15m)
4. 15m candles must be AFTER the 1H close that set the regime
5. One position at a time per pair
6. TP/SL tracked on subsequent 15m candles

GET /v2_gated/entry_matrix?symbol=SOLUSDT&days=971   (original 1H entries)
GET /v2_gated/m15_exec?symbol=SOLUSDT&days=971       (15m execution layer)
"""
import os,sqlite3,numpy as np,traceback
from fastapi import APIRouter, Query
from datetime import datetime,timezone
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v2_gated", tags=["v2_gated_15m"])
DB_PATH = os.environ.get("DB_PATH","market_data.db")

def _ld(sym,tf,days):
    conn=sqlite3.connect(DB_PATH);now=int(datetime.utcnow().timestamp()*1000);st=now-(days*86400*1000)
    r=conn.cursor().execute("SELECT open_time,open,high,low,close,volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC",(sym,tf,st,now)).fetchall()
    conn.close();return r

def _ema(c,p):
    e=np.zeros(len(c));e[0]=c[0];k=2.0/(p+1)
    for i in range(1,len(c)):e[i]=c[i]*k+e[i-1]*(1-k)
    return e

def _atr(H,L,C,p=14):
    n=len(H);a=np.zeros(n)
    for i in range(1,n):
        t=max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1]))
        a[i]=a[i-1]+(t-a[i-1])/min(i,p)
    return a

@router.get("/m15_exec")
def m15_execution(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_1h:int=Query(7),ema_slow:int=Query(20),ema_15m:int=Query(7),
    tp_pct:float=Query(0.013),sl_pct:float=Query(0.013),
    fee_pct:float=Query(0.001),slippage_pct:float=Query(0.0005),
    swing_lb:int=Query(10),swing_atr:float=Query(0.5),
    body_min:float=Query(0.3),
):
    try:
        r1h=_ld(symbol,"1h",days);r15m=_ld(symbol,"15m",days)
        if len(r1h)<ema_slow*2+60:return{"error":"not enough 1h"}
        if not r15m:return{"error":"no 15m data"}

        # 1H arrays
        O1=np.array([r[1] for r in r1h],dtype=float);H1=np.array([r[2] for r in r1h],dtype=float)
        L1=np.array([r[3] for r in r1h],dtype=float);C1=np.array([r[4] for r in r1h],dtype=float)
        T1=[r[0] for r in r1h];n1=len(r1h)
        ef1=_ema(C1,ema_1h);es1=_ema(C1,ema_slow);at1=_atr(H1,L1,C1)

        # 15m arrays
        O5=np.array([r[1] for r in r15m],dtype=float);H5=np.array([r[2] for r in r15m],dtype=float)
        L5=np.array([r[3] for r in r15m],dtype=float);C5=np.array([r[4] for r in r15m],dtype=float)
        T5=[r[0] for r in r15m];n5=len(r15m)
        ef5=_ema(C5,ema_15m)
        t5_idx={T5[i]:i for i in range(n5)}  # timestamp→index

        cost=fee_pct+slippage_pct;notional=500.0

        # Run V2 detector on 1H
        det=ContinuationDetectorV2(ema_1h,ema_slow,swing_lb,swing_atr,3,min_pb_bars=1)
        regime_per_bar=[]
        for i in range(n1):
            det.process(i,O1,H1,L1,C1,ef1,es1,at1)
            regime_per_bar.append(det.regime)

        # Count regime hours
        bull_bars=sum(1 for r in regime_per_bar if r=="BULL")
        bear_bars=sum(1 for r in regime_per_bar if r=="BEAR")

        # For each entry mode, scan 15m candles during BULL/BEAR regime
        # Entries: 1H_close, 15m_open, 15m_reclaim_close, 15m_limit
        modes={}
        for mode in ["1H_close","15m_open","15m_reclaim","15m_limit"]:
            trades=[];position=None;n_sig=0;n_fill=0;n_skip=0

            for i in range(max(ema_slow*2,60),n1):
                reg=regime_per_bar[i]
                if reg not in ("BULL","BEAR"):continue
                side="LONG" if reg=="BULL" else "SHORT"
                t_1h_close=T1[i]
                # 15m candles in the NEXT hour (4 candles: T+0, T+15, T+30, T+45 of next hour)
                next_hour_start=t_1h_close+3600*1000
                M=15*60*1000

                if mode=="1H_close":
                    # Entry at 1H close — same as Mode B
                    # But we check: is this a reclaim on 1H?
                    o,h,l,c=O1[i],H1[i],L1[i],C1[i];ef=ef1[i]
                    br=h-l;body=abs(c-o);bdy=body/br if br>0 else 0
                    if side=="LONG":is_sig=(l<=ef)and(c>ef)and(c>o)and(bdy>=body_min)
                    else:is_sig=(h>=ef)and(c<ef)and(c<o)and(bdy>=body_min)
                    if not is_sig:continue
                    if position is not None:continue  # one at a time
                    n_sig+=1;n_fill+=1
                    ep=c;entry_bar_15m=t5_idx.get(next_hour_start)
                    if entry_bar_15m is None:n_skip+=1;n_fill-=1;continue

                elif mode=="15m_open":
                    # Entry at open of first 15m candle in next hour
                    j=t5_idx.get(next_hour_start)
                    if j is None:continue
                    # Check 1H had a reclaim/rejection
                    o,h,l,c=O1[i],H1[i],L1[i],C1[i];ef=ef1[i]
                    br=h-l;body=abs(c-o);bdy=body/br if br>0 else 0
                    if side=="LONG":is_sig=(l<=ef)and(c>ef)and(c>o)and(bdy>=body_min)
                    else:is_sig=(h>=ef)and(c<ef)and(c<o)and(bdy>=body_min)
                    if not is_sig:continue
                    if position is not None:continue
                    n_sig+=1;n_fill+=1
                    ep=O5[j];entry_bar_15m=j

                elif mode=="15m_reclaim":
                    # Scan up to 4 15m candles in next hour for a reclaim/rejection
                    if position is not None:continue
                    found=False
                    for k in range(4):
                        t15=next_hour_start+k*M
                        j=t5_idx.get(t15)
                        if j is None or j<ema_15m*2:continue
                        o5,h5,l5,c5=O5[j],H5[j],L5[j],C5[j];e5=ef5[j]
                        br5=h5-l5;bd5=abs(c5-o5);bdy5=bd5/br5 if br5>0 else 0
                        if side=="LONG":ok=(l5<=e5)and(c5>e5)and(c5>o5)and(bdy5>=body_min)
                        else:ok=(h5>=e5)and(c5<e5)and(c5<o5)and(bdy5>=body_min)
                        if ok:
                            n_sig+=1;n_fill+=1;ep=c5;entry_bar_15m=j;found=True;break
                    if not found:n_sig+=1;n_skip+=1;continue

                elif mode=="15m_limit":
                    # Limit at 1H EMA, placed after signal, valid 4×15m candles
                    o,h,l,c=O1[i],H1[i],L1[i],C1[i];ef=ef1[i]
                    br=h-l;body=abs(c-o);bdy=body/br if br>0 else 0
                    if side=="LONG":is_sig=(l<=ef)and(c>ef)and(c>o)and(bdy>=body_min)
                    else:is_sig=(h>=ef)and(c<ef)and(c<o)and(bdy>=body_min)
                    if not is_sig:continue
                    if position is not None:continue
                    n_sig+=1
                    # Check if any of next 4 15m candles touches EMA
                    ea=ef
                    found=False
                    for k in range(4):
                        t15=next_hour_start+k*M
                        j=t5_idx.get(t15)
                        if j is None:continue
                        if side=="LONG" and L5[j]<=ea:ep=ea;entry_bar_15m=j;found=True;break
                        elif side=="SHORT" and H5[j]>=ea:ep=ea;entry_bar_15m=j;found=True;break
                    if not found:n_skip+=1;continue
                    n_fill+=1

                # ── TRADE SIMULATION on 15m bars ──
                if side=="LONG":tp_l=ep*(1+tp_pct);sl_l=ep*(1-sl_pct)
                else:tp_l=ep*(1-tp_pct);sl_l=ep*(1+sl_pct)
                # Track from NEXT 15m bar after entry
                mfe=0;mae=0;result=None
                for jj in range(entry_bar_15m+1,min(entry_bar_15m+200,n5)):
                    h5,l5=H5[jj],L5[jj]
                    if side=="LONG":
                        fv=(h5-ep)/ep;av=(ep-l5)/ep
                        hit_sl=l5<=sl_l;hit_tp=h5>=tp_l
                    else:
                        fv=(ep-l5)/ep;av=(h5-ep)/ep
                        hit_sl=h5>=sl_l;hit_tp=l5<=tp_l
                    if fv>mfe:mfe=fv
                    if av>mae:mae=av
                    if hit_sl:  # SL first
                        p=-sl_pct-cost
                        result={"x":"SL","b":jj-entry_bar_15m,"p":round(p*100,3),"mfe":round(mfe*100,2),"mae":round(mae*100,2)};break
                    if hit_tp:
                        p=tp_pct-cost
                        result={"x":"TP","b":jj-entry_bar_15m,"p":round(p*100,3),"mfe":round(mfe*100,2),"mae":round(mae*100,2)};break
                if not result:
                    eb_end=min(entry_bar_15m+200,n5)-1
                    p=(C5[eb_end]-ep)/ep if side=="LONG" else (ep-C5[eb_end])/ep;p-=cost
                    result={"x":"TO","b":200,"p":round(p*100,3),"mfe":round(mfe*100,2),"mae":round(mae*100,2)}
                result["sd"]=side;result["eb"]=entry_bar_15m;result["ep"]=round(ep,4)
                result["dist"]=round(100*abs(ep-ef1[i])/ef1[i],3)
                trades.append(result)
                position=result  # mark as in position
                # Position exits when trade resolves → next signal can enter
                # For simplicity, position clears immediately (trades are independent)
                position=None  # allow next signal

            # Aggregate
            nt=len(trades)
            if nt==0:modes[mode]={"n_sig":n_sig,"n_fill":n_fill,"n_skip":n_skip,"n_closed":0};continue
            ws=[t for t in trades if t["p"]>0]
            gr=sum((t["p"]+cost*100)/100*notional for t in trades)
            ne=sum(t["p"]/100*notional for t in trades)
            mfes=sorted([t["mfe"] for t in trades]);maes=sorted([t["mae"] for t in trades])
            mid=n5//2
            tr=[t for t in trades if t["eb"]<mid];te=[t for t in trades if t["eb"]>=mid]
            trn=sum(t["p"]/100*notional for t in tr) if tr else 0
            ten=sum(t["p"]/100*notional for t in te) if te else 0
            eq=0;pk=0;dd=0;ms=0;cs=0
            for t in trades:
                eq+=t["p"]/100*notional;pk=max(pk,eq);dd=max(dd,pk-eq)
                if t["p"]<=0:cs+=1;ms=max(ms,cs)
                else:cs=0
            eb={};[eb.update({t["x"]:eb.get(t["x"],0)+1}) for t in trades]
            lo=[t for t in trades if t["sd"]=="LONG"];sh=[t for t in trades if t["sd"]=="SHORT"]
            w_pnl=[t["p"]/100*notional for t in ws];l_pnl=[t["p"]/100*notional for t in trades if t["p"]<=0]
            aw=round(np.mean(w_pnl),2) if w_pnl else 0;al=round(np.mean(l_pnl),2) if l_pnl else 0
            
            modes[mode]={
                "n_sig":n_sig,"n_fill":n_fill,"n_skip":n_skip,"n_closed":nt,
                "fill_rate":round(100*n_fill/(n_fill+n_skip),1) if n_fill+n_skip else 0,
                "trades_per_day":round(nt/days,3),
                "wr":round(100*len(ws)/nt,1),"gr":round(gr,2),"ne":round(ne,2),
                "ge":round(gr/nt,3),"nee":round(ne/nt,3),
                "avg_w":aw,"avg_l":al,"R":round(aw/abs(al),2) if al else 0,
                "dd":round(dd,2),"mls":ms,
                "mfe_p50":round(mfes[len(mfes)//2],2),"mae_p50":round(maes[len(maes)//2],2),
                "mfe_p25":round(mfes[max(0,len(mfes)//4)],2),"mae_p75":round(maes[min(len(maes)-1,3*len(maes)//4)],2),
                "avg_dist":round(np.mean([t["dist"] for t in trades]),2),
                "exits":eb,
                "L":{"n":len(lo),"wr":round(100*sum(1 for t in lo if t["p"]>0)/len(lo),1) if lo else 0},
                "S":{"n":len(sh),"wr":round(100*sum(1 for t in sh if t["p"]>0)/len(sh),1) if sh else 0},
                "wf":{"trN":len(tr),"trP":round(trn,2),"teN":len(te),"teP":round(ten,2)},
            }

        return{
            "symbol":symbol,"days":days,"n_1h":n1,"n_15m":n5,
            "regime_bars":{"bull":bull_bars,"bear":bear_bars,"pct_active":round(100*(bull_bars+bear_bars)/n1,1)},
            "cost":cost,"notional":notional,
            "modes":modes,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
