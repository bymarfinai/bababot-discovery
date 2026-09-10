#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e3_drive_strength_fast as e3

ROOT=Path(__file__).resolve().parent.parent
PFX="ETH_ECONOMIC_FIRST_E6_LOWDRIVE_MANAGEMENT"
OUT_GRID=ROOT/f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER=ROOT/f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SUMMARY=ROOT/f"{PFX}_HoldoutSummary.csv"
OUT_TRADES=ROOT/f"{PFX}_SelectedTrades.csv"
OUT_RESULT=ROOT/f"{PFX}_Result.md"
OUT_STATUS=ROOT/f"{PFX}_Status.txt"

CLOCK=17*60
LOOKBACK=360
NOTIONAL=500.0
FEE=0.75
TPS=(0.002,0.003,0.004,0.006,0.008,0.010,0.015,0.020)
SLS=(None,0.005,0.0075,0.010,0.015,0.020,0.030)
HOLDS=(120,240,360,480,720,960)
BAR_MIN=5


def money(x): return f"${float(x):+.2f}"
def pct(x): return f"{100*float(x):.2f}%"
def sl_label(sl): return "NONE" if sl is None else f"{100*sl:.2f}%"

def first_true(mask):
    n=mask.shape[1]
    any_=mask.any(axis=1)
    out=np.argmax(mask,axis=1).astype(int)
    out[~any_]=n
    return out


def eligible_signal_frame(x5,part,hold):
    S=e3.signal_frame(x5,CLOCK,LOOKBACK)
    ent=pd.DatetimeIndex(S.entry_ts); pre=pd.DatetimeIndex(S.pre_ts)
    strength=S.strength_pct.to_numpy(float)
    ex=ent+pd.Timedelta(minutes=hold)
    ei=S.entry_ix.to_numpy(int)
    xi=x5.index.get_indexer(ex)
    pa,pz=base.PARTS[part]
    valid=(xi>=0)&((xi-ei)==hold//BAR_MIN)&(pre>=pa)&(ent>=pa)&(ex<pz)&np.isfinite(strength)&(strength>=0.0)&(strength<0.20)
    return S,ent,ex,ei,xi,valid


def simulate(x5,part,tp,sl,hold,return_trades=False):
    S,ent,ex,ei,xi,m=eligible_signal_frame(x5,part,hold)
    idx=np.where(m)[0]
    if len(idx)==0:
        return ({},pd.DataFrame()) if return_trades else ({},None)
    eix=ei[idx]
    nbar=hold//BAR_MIN
    path_ix=eix[:,None]+np.arange(nbar)[None,:]
    h=x5.high.to_numpy(float)[path_ix]
    l=x5.low.to_numpy(float)[path_ix]
    entry=S.entry_price.to_numpy(float)[idx]
    drive=S.drive_return.to_numpy(float)[idx]
    direction=np.where(drive>0,1.0,-1.0)

    tp_long=entry*(1+tp); tp_short=entry*(1-tp)
    tp_hit=np.where(direction[:,None]>0,h>=tp_long[:,None],l<=tp_short[:,None])
    itp=first_true(tp_hit)

    if sl is None:
        isl=np.full(len(idx),nbar,dtype=int)
        sl_first=np.zeros(len(idx),dtype=bool)
    else:
        sl_long=entry*(1-sl); sl_short=entry*(1+sl)
        sl_hit=np.where(direction[:,None]>0,l<=sl_long[:,None],h>=sl_short[:,None])
        isl=first_true(sl_hit)
        sl_first=(isl<=itp)&(isl<nbar)

    tp_first=(itp<isl)&(itp<nbar)
    timed=~(tp_first|sl_first)
    gross_ret=np.empty(len(idx),float)
    gross_ret[tp_first]=tp
    if sl is not None:
        gross_ret[sl_first]=-sl
    exit_open=x5.open.to_numpy(float)[xi[idx]]
    gross_ret[timed]=direction[timed]*(exit_open[timed]-entry[timed])/entry[timed]
    gross=NOTIONAL*gross_ret
    net=gross-FEE
    s=e3.summarize(net,gross,4 if part=="development" else 0)
    s.update({
        "tp_exit_rate":float(tp_first.mean()),
        "sl_exit_rate":float(sl_first.mean()),
        "time_exit_rate":float(timed.mean()),
    })
    if not return_trades:
        return s,None

    exit_reason=np.full(len(idx),"TIME",dtype=object)
    exit_reason[tp_first]="TP"; exit_reason[sl_first]="SL"
    exit_ts=np.array(ex[idx],dtype="datetime64[ns]")
    pidx=np.where(tp_first)[0]
    if len(pidx):
        exit_ts[pidx]=np.array([x5.index[eix[j]+itp[j]] for j in pidx],dtype="datetime64[ns]")
    sidx=np.where(sl_first)[0]
    if len(sidx):
        exit_ts[sidx]=np.array([x5.index[eix[j]+isl[j]] for j in sidx],dtype="datetime64[ns]")
    T=pd.DataFrame({
        "partition":part,"clock_utc":"17:00","clock_wib":"00:00","lookback_min":LOOKBACK,
        "strength_band":"B0_20","mode":"MOMENTUM","tp_pct":tp,"sl_pct":np.nan if sl is None else sl,"sl_mode":sl_label(sl),"hold_min":hold,
        "entry_ts":ent[idx],"entry_price":entry,"drive_return":drive,"strength_pct":S.strength_pct.to_numpy(float)[idx],
        "side":np.where(direction>0,"LONG","SHORT"),"exit_reason":exit_reason,"exit_ts":pd.to_datetime(exit_ts,utc=True),
        "gross_return":gross_ret,"gross_pnl":gross,"fee":FEE,"net_pnl":net,"net_positive":net>0,
    })
    return s,T


def dev_scan(x5):
    rows=[]
    for tp in TPS:
        for sl in SLS:
            for hold in HOLDS:
                s,_=simulate(x5,"development",tp,sl,hold,False)
                rows.append({"tp_pct":tp,"sl_pct":np.nan if sl is None else sl,"sl_mode":sl_label(sl),"hold_min":hold,**s})
    D=pd.DataFrame(rows)
    if len(D)!=336: raise AssertionError(f"expected 336 candidates, got {len(D)}")
    D["quality_gate"]=(
        (D.trades>=120)&(D.win_rate>=.55)&(D.net_pnl>0)&(D.expectancy>=.75)&
        (D.pf>=1.20)&(D.max_dd<=100)&(D.max_loss_streak<=8)&(D.positive_blocks>=3)
    )
    return D


def key(tp,sl_mode,hold): return (round(float(tp),6),str(sl_mode),int(hold))

def neighbor_keys(r):
    tp=float(r.tp_pct); hold=int(r.hold_min); sm=str(r.sl_mode)
    ti=TPS.index(tp); hi=HOLDS.index(hold); ks=[]
    if ti>0: ks.append(key(TPS[ti-1],sm,hold))
    if ti+1<len(TPS): ks.append(key(TPS[ti+1],sm,hold))
    if hi>0: ks.append(key(tp,sm,HOLDS[hi-1]))
    if hi+1<len(HOLDS): ks.append(key(tp,sm,HOLDS[hi+1]))
    if sm!="NONE":
        nums=[x for x in SLS if x is not None]
        sl=float(str(sm).rstrip('%'))/100.0
        si=min(range(len(nums)),key=lambda i:abs(nums[i]-sl))
        if si>0: ks.append(key(tp,sl_label(nums[si-1]),hold))
        if si+1<len(nums): ks.append(key(tp,sl_label(nums[si+1]),hold))
    return ks


def build(D):
    D=D.copy(); lookup={key(r.tp_pct,r.sl_mode,r.hold_min):r for r in D.itertuples(index=False)}
    nav=[]; ns=[]; stable=[]
    for r in D.itertuples(index=False):
        ks=neighbor_keys(r); sup=0
        for k in ks:
            x=lookup[k]
            sup += int(int(x.trades)>=120 and float(x.win_rate)>=.52 and float(x.net_pnl)>0 and float(x.expectancy)>0 and float(x.pf)>=1.05 and int(x.positive_blocks)>=2)
        need=2 if len(ks)>=3 else 1
        nav.append(len(ks)); ns.append(sup); stable.append(sup>=need)
    D["neighbors_available"]=nav; D["neighbors_supportive"]=ns; D["local_stable"]=stable
    D["candidate_eligible"]=D.quality_gate&D.local_stable
    numeric=D.sl_mode!="NONE"
    D["boundary"]=(D.tp_pct.isin((min(TPS),max(TPS)))|D.hold_min.isin((min(HOLDS),max(HOLDS)))|(numeric&D.sl_pct.isin((min(x for x in SLS if x is not None),max(x for x in SLS if x is not None)))))
    D["sl_tie"]=np.where(D.sl_mode=="NONE",0,1)
    C=D[D.candidate_eligible].copy().sort_values(
        ["win_rate","expectancy","pf","max_dd","max_loss_streak","hold_min","tp_pct","sl_tie"],
        ascending=[False,False,False,True,True,True,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def parse_sl(row):
    return None if str(row["sl_mode"])=="NONE" else float(row["sl_pct"])


def main():
    base.synthetic_tests()
    x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    D0=dev_scan(x5); D,C=build(D0)
    D.to_csv(OUT_GRID,index=False); C.to_csv(OUT_LEADER,index=False)
    lines=["# ETH Economic-First E6 — Low-Drive MOMENTUM Management Result","",
           f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
           "Frozen signal: **17:00 UTC / LB360 / causal B0_20 / MOMENTUM / exact-open entry**.",
           "Fixed economics: **$500 notional / $0.75 round-trip fee**.",
           f"Development management candidates: **{len(D)}**.",
           f"Quality-gate passers: **{int(D.quality_gate.sum())}**; quality + local-stability passers: **{len(C)}**.",""]
    top=D.sort_values(["win_rate","expectancy","pf","max_dd"],ascending=[False,False,False,True]).head(15)
    lines += ["## Top Development management cells","",
              "| # | TP | SL | Hold | N | WR | Net | Exp | PF | DD | L-streak | TP/SL/Time | Blocks | Gate | Neigh | Eligible |",
              "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|"]
    for i,r in enumerate(top.itertuples(index=False),1):
        lines.append(f"| {i} | {100*r.tp_pct:.2f}% | {r.sl_mode} | {int(r.hold_min)}m | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.tp_exit_rate)}/{pct(r.sl_exit_rate)}/{pct(r.time_exit_rate)} | {int(r.positive_blocks)}/4 | {'YES' if r.quality_gate else 'NO'} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {'YES' if r.candidate_eligible else 'NO'} |")
    if len(C)==0:
        status="ETH_ECONOMIC_FIRST_E6_NO_DEV_CANDIDATE"; OUT_STATUS.write_text(status+"\n")
        lines += ["",f"**Status: {status}**","","No management cell met the preregistered WR + economics + stability gate.","","Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return
    sel=C.iloc[0]; sl=parse_sl(sel)
    lines += ["","## Development-selected management","",
              f"**TP {100*float(sel['tp_pct']):.2f}% / SL {sel['sl_mode']} / hold {int(sel['hold_min'])}m**","",
              f"N **{int(sel['trades'])}**, WR **{pct(sel['win_rate'])}**, net **{money(sel['net_pnl'])}**, exp **{money(sel['expectancy'])}/trade**, PF **{float(sel['pf']):.3f}**, DD **{money(sel['max_dd'])}**, loss streak **{int(sel['max_loss_streak'])}**, blocks **{int(sel['positive_blocks'])}/4**, neighbors **{int(sel['neighbors_supportive'])}/{int(sel['neighbors_available'])}**."]
    _,Tdev=simulate(x5,"development",float(sel["tp_pct"]),sl,int(sel["hold_min"]),True)
    if bool(sel["boundary"]):
        status="ETH_ECONOMIC_FIRST_E6_BOUNDARY_OPEN"; OUT_STATUS.write_text(status+"\n"); Tdev.to_csv(OUT_TRADES,index=False)
        lines += ["","Winner touches a preregistered management sentinel; holdouts remain closed.","",f"**Status: {status}**"]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return
    hrows=[]; tlist=[Tdev]; allok=True
    for part in ("external","reference_validation"):
        s,T=simulate(x5,part,float(sel["tp_pct"]),sl,int(sel["hold_min"]),True)
        ok=(s.get("trades",0)>=50 and s.get("win_rate",0)>=.52 and s.get("net_pnl",-1)>0 and s.get("expectancy",-1)>0 and s.get("pf",0)>=1.05 and s.get("max_loss_streak",99)<=10)
        hrows.append({"partition":part,**s,"replication_pass":bool(ok)}); allok &= bool(ok); tlist.append(T)
    H=pd.DataFrame(hrows); H.to_csv(OUT_SUMMARY,index=False); pd.concat(tlist,ignore_index=True).to_csv(OUT_TRADES,index=False)
    status="ETH_ECONOMIC_FIRST_E6_SUPPORTED" if allok else "ETH_ECONOMIC_FIRST_E6_CANDIDATE_NOT_REPLICATED"; OUT_STATUS.write_text(status+"\n")
    lines += ["","## Historical replication","","| Partition | N | WR | Net | Exp | PF | DD | L-streak | TP/SL/Time | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.tp_exit_rate)}/{pct(r.sl_exit_rate)}/{pct(r.time_exit_rate)} | {'PASS' if r.replication_pass else 'FAIL'} |")
    allT=pd.concat(tlist,ignore_index=True).sort_values("entry_ts")
    sa=e3.summarize(allT.net_pnl.to_numpy(float),allT.gross_pnl.to_numpy(float),0)
    lines += ["","## Combined historical — descriptive","",
              f"N **{sa['trades']}**, WR **{pct(sa['win_rate'])}**, net **{money(sa['net_pnl'])}**, exp **{money(sa['expectancy'])}/trade**, PF **{sa['pf']:.3f}**, DD **{money(sa['max_dd'])}**, loss streak **{sa['max_loss_streak']}**.","",
              "BTC A3.9 context: WR56.83%, exp+$0.6887/trade, PF1.431, DD$31.636, loss streak4.","",f"**Status: {status}**","","Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__": main()
