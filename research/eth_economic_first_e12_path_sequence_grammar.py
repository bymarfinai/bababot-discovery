#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e1_clock_drift as e1
import eth_economic_first_e3_drive_strength_fast as e3

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E12_PATH_SEQUENCE_GRAMMAR"
OUT_PANEL = ROOT / f"{PFX}_ClockPanel.csv"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SELECTED = ROOT / f"{PFX}_SelectedClockAtlas.csv"
OUT_HOLDOUT = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = tuple(range(0, 1440, 30))
HOLDS = (120, 240, 360, 720, 960)
YEARS = (2022, 2023, 2024)
NOTIONAL = 500.0
FEE = 0.75
BAR_MIN = 5

IRR_LBS = (60, 120, 240, 360)
CE_LBS = (120, 240, 360, 480)
ER_LBS = (60, 120, 240, 360)
IRR_BANDS = ((0.15, 0.40, "R1"), (0.40, 0.65, "R2"), (0.65, 0.90, "R3"))
IRR_Q = (0.25, 0.40, 0.55)
CE_A = (1.5, 2.0, 3.0)
CE_E = (0.35, 0.50, 0.65)
ER_E = (0.35, 0.50, 0.65)
ER_BANDS = ((0.20, 0.40, "R1"), (0.40, 0.60, "R2"), (0.60, 0.80, "R3"))


def hhmm(m): return e1.hhmm(int(m))
def wib(m): return e1.wib(int(m))
def pct(x): return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"
def money(x): return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def summarize(net, gross):
    net = np.asarray(net, float); gross = np.asarray(gross, float)
    if len(net) == 0:
        return {"trades":0,"win_rate":np.nan,"net_pnl":0.0,"expectancy":np.nan,"pf":np.nan,"max_dd":np.nan,"max_loss_streak":0,"max_win_streak":0}
    return e3.summarize(net, gross, 0)


def specs():
    out=[]
    for lb in IRR_LBS:
        for bi,(_,_,bl) in enumerate(IRR_BANDS):
            for qi,q in enumerate(IRR_Q):
                for mode,mult in (("CONTINUE",1.0),("REVERSE",-1.0)):
                    for h in HOLDS:
                        out.append(dict(family="IRR",lookback_min=lb,p1_idx=bi,p1_label=bl,p1_value=float(bi),p2_idx=qi,p2_label=f"Q{q:.2f}",p2_value=q,mode=mode,dir_mult=mult,hold_min=h))
    for lb in CE_LBS:
        for ai,a in enumerate(CE_A):
            for ei,ev in enumerate(CE_E):
                for mode,mult in (("CONTINUE",1.0),("REVERSE",-1.0)):
                    for h in HOLDS:
                        out.append(dict(family="CE",lookback_min=lb,p1_idx=ai,p1_label=f"A{a:.1f}",p1_value=a,p2_idx=ei,p2_label=f"E{ev:.2f}",p2_value=ev,mode=mode,dir_mult=mult,hold_min=h))
    for lb in ER_LBS:
        for ei,ev in enumerate(ER_E):
            for bi,(_,_,bl) in enumerate(ER_BANDS):
                for mode,mult in (("RESUME",1.0),("EXTEND_RECOVERY",-1.0)):
                    for h in HOLDS:
                        out.append(dict(family="ER",lookback_min=lb,p1_idx=ei,p1_label=f"E{ev:.2f}",p1_value=ev,p2_idx=bi,p2_label=bl,p2_value=float(bi),mode=mode,dir_mult=mult,hold_min=h))
    if len(out) != 1080:
        raise AssertionError(f"expected 1080 specs, got {len(out)}")
    return out

SPECS = specs()
IDCOLS = ["family","lookback_min","p1_idx","p1_label","p1_value","p2_idx","p2_label","p2_value","mode","hold_min"]


def sequence_frame(x5: pd.DataFrame, clock: int, lb: int) -> pd.DataFrame:
    S = e3.signal_frame(x5, clock, lb).copy()
    idx = x5.index
    op = x5.open.to_numpy(float)
    pi = idx.get_indexer(pd.DatetimeIndex(S.pre_ts))
    ei = S.entry_ix.to_numpy(int)
    nrow=len(S)
    cols={k:np.full(nrow,np.nan,float) for k in (
        "irr_r1","irr_r2","irr_r3","irr_final",
        "ce_activity_ratio","ce_eff","ce_dir",
        "er_r1","er_r2","er_eff","er_final")}
    for j,(a,b) in enumerate(zip(pi,ei)):
        if a < 0 or b <= a or (b-a) != lb//BAR_MIN:
            continue
        path=op[a:b+1]
        if np.any(path<=0):
            continue
        z=np.log(path)
        n=len(z)-1
        if n % 3 == 0:
            k=n//3
            r1=z[k]-z[0]; r2=z[2*k]-z[k]; r3=z[-1]-z[2*k]
            cols["irr_r1"][j]=r1; cols["irr_r2"][j]=r2; cols["irr_r3"][j]=r3; cols["irr_final"][j]=z[-1]-z[0]
            split=2*k
            dc=np.diff(z[:split+1]); de=np.diff(z[split:])
            ca=float(np.mean(np.abs(dc))) if len(dc) else np.nan
            ea=float(np.mean(np.abs(de))) if len(de) else np.nan
            cols["ce_activity_ratio"][j]=(ea/ca) if ca>0 else np.nan
            enet=float(z[-1]-z[split]); eden=float(np.abs(de).sum())
            cols["ce_eff"][j]=(abs(enet)/eden) if eden>0 else np.nan
            cols["ce_dir"][j]=float(np.sign(enet)) if enet!=0 else np.nan
        if n % 2 == 0:
            k=n//2
            r1=z[k]-z[0]; r2=z[-1]-z[k]
            d1=np.diff(z[:k+1]); den=float(np.abs(d1).sum())
            cols["er_r1"][j]=r1; cols["er_r2"][j]=r2
            cols["er_eff"][j]=(abs(r1)/den) if den>0 else np.nan
            cols["er_final"][j]=z[-1]-z[0]
    for k,v in cols.items(): S[k]=v
    return S


def between(x, lo, hi, last=False):
    x=np.asarray(x,float)
    return np.isfinite(x)&(x>=lo)&(x<=hi if last else x<hi)


def event_mask_dir(S: pd.DataFrame, sp: dict):
    fam=sp["family"]
    if fam=="IRR":
        r1=S.irr_r1.to_numpy(float); r2=S.irr_r2.to_numpy(float); r3=S.irr_r3.to_numpy(float); fin=S.irr_final.to_numpy(float)
        sd=np.sign(r1); rr=np.divide(np.abs(r2),np.abs(r1),out=np.full(len(r1),np.nan),where=np.abs(r1)>0)
        qa=np.divide(np.abs(r3),np.abs(r1),out=np.full(len(r1),np.nan),where=np.abs(r1)>0)
        lo,hi,_=IRR_BANDS[int(sp["p1_idx"])]
        m=np.isfinite(sd)&(sd!=0)&(np.sign(r2)==-sd)&(np.sign(r3)==sd)&between(rr,lo,hi,int(sp["p1_idx"])==2)&(qa>=float(sp["p2_value"]))&(fin*sd>0)
        return m, sd*float(sp["dir_mult"])
    if fam=="CE":
        ar=S.ce_activity_ratio.to_numpy(float); ef=S.ce_eff.to_numpy(float); sd=S.ce_dir.to_numpy(float)
        m=np.isfinite(sd)&(sd!=0)&(ar>=float(sp["p1_value"]))&(ef>=float(sp["p2_value"]))
        return m, sd*float(sp["dir_mult"])
    if fam=="ER":
        r1=S.er_r1.to_numpy(float); r2=S.er_r2.to_numpy(float); ef=S.er_eff.to_numpy(float); fin=S.er_final.to_numpy(float)
        sd=np.sign(r1); rr=np.divide(np.abs(r2),np.abs(r1),out=np.full(len(r1),np.nan),where=np.abs(r1)>0)
        lo,hi,_=ER_BANDS[int(sp["p2_idx"])]
        m=np.isfinite(sd)&(sd!=0)&(np.sign(r2)==-sd)&(ef>=float(sp["p1_value"]))&between(rr,lo,hi,int(sp["p2_idx"])==2)&(fin*sd>0)
        return m, sd*float(sp["dir_mult"])
    raise ValueError(fam)


def panel_rows(x5: pd.DataFrame) -> pd.DataFrame:
    pa,pz=base.PARTS["development"]
    rows=[]
    unique_lbs=sorted(set(IRR_LBS+CE_LBS+ER_LBS))
    for clock in CLOCKS:
        frames={lb:sequence_frame(x5,clock,lb) for lb in unique_lbs}
        hold_cache={}
        for lb,S in frames.items():
            for h in HOLDS:
                hold_cache[(lb,h)]=e3.hold_base(x5,S,h)
        for sp in SPECS:
            lb=int(sp["lookback_min"]); h=int(sp["hold_min"]); S=frames[lb]
            ent=pd.DatetimeIndex(S.entry_ts); pre=pd.DatetimeIndex(S.pre_ts)
            ex,valid,xp,delta,_=hold_cache[(lb,h)]
            ev, direction=event_mask_dir(S,sp)
            m=valid&ev&(pre>=pa)&(ent>=pa)&(ex<pz)
            gross_all=NOTIONAL*direction*delta; net_all=gross_all-FEE
            s=summarize(net_all[m],gross_all[m])
            row={k:sp[k] for k in IDCOLS}
            row.update({"clock_min_utc":clock,"clock_utc":hhmm(clock),"clock_wib":wib(clock),**s})
            for y in YEARS:
                ya=pd.Timestamp(f"{y}-01-01",tz="UTC"); yz=pd.Timestamp(f"{y+1}-01-01",tz="UTC")
                ym=m&(pre>=ya)&(ent>=ya)&(ex<yz)
                ys=summarize(net_all[ym],gross_all[ym])
                row.update({f"y{y}_trades":ys["trades"],f"y{y}_wr":ys["win_rate"],f"y{y}_net":ys["net_pnl"],f"y{y}_exp":ys["expectancy"],f"y{y}_pf":ys["pf"]})
            rows.append(row)
    P=pd.DataFrame(rows)
    expected=1080*48
    if len(P)!=expected: raise AssertionError(f"expected {expected} rows, got {len(P)}")
    return P


def aggregate_candidates(P: pd.DataFrame):
    rows=[]
    for vals,G in P.groupby(IDCOLS,sort=False,dropna=False):
        base_id=dict(zip(IDCOLS,vals))
        ev=G.trades>=45
        E=G[ev]
        supportive=ev&(G.win_rate>=.54)&(G.net_pnl>0)&(G.expectancy>=.50)&(G.pf>=1.15)&(G.max_dd<=100)&(G.max_loss_streak<=8)
        pexp=ev&(G.expectancy>0)
        block_ok=[]
        for bi in range(6):
            bg=G[(G.clock_min_utc//240)==bi]
            bev=bg.trades>=45
            bs=bev&(bg.win_rate>=.54)&(bg.net_pnl>0)&(bg.expectancy>=.50)&(bg.pf>=1.15)&(bg.max_dd<=100)&(bg.max_loss_streak<=8)
            block_ok.append(bool(bev.sum()>0 and bs.sum()/bev.sum()>=.50))
        row={**base_id,
            "evaluable_clocks":int(ev.sum()),"supportive_clocks":int(supportive.sum()),
            "supportive_fraction":float(supportive.sum()/ev.sum()) if ev.sum() else np.nan,
            "positive_exp_clocks":int(pexp.sum()),
            "median_wr":float(E.win_rate.median()) if len(E) else np.nan,
            "median_exp":float(E.expectancy.median()) if len(E) else np.nan,
            "median_pf":float(E.pf.median()) if len(E) else np.nan,
            "median_dd":float(E.max_dd.median()) if len(E) else np.nan,
            "median_loss_streak":float(E.max_loss_streak.median()) if len(E) else np.nan,
            "clock_blocks_ok":int(sum(block_ok))}
        era_ok=True; era_exps=[]
        for y in YEARS:
            yev=G[f"y{y}_trades"]>=12; YE=G[yev]
            medwr=float(YE[f"y{y}_wr"].median()) if len(YE) else np.nan
            medexp=float(YE[f"y{y}_exp"].median()) if len(YE) else np.nan
            pos=int((yev&(G[f"y{y}_exp"]>0)).sum()); frac=float(pos/yev.sum()) if yev.sum() else np.nan
            row.update({f"y{y}_evaluable":int(yev.sum()),f"y{y}_median_wr":medwr,f"y{y}_median_exp":medexp,f"y{y}_positive_exp_fraction":frac})
            yok=(yev.sum()>=20 and np.isfinite(medwr) and medwr>=.52 and np.isfinite(medexp) and medexp>=.25 and frac>=.55)
            era_ok &= bool(yok); era_exps.append(medexp if np.isfinite(medexp) else -np.inf)
        breadth=(row["evaluable_clocks"]>=24 and row["supportive_clocks"]>=14 and row["supportive_fraction"]>=.55 and row["positive_exp_clocks"]>=28)
        medgate=(row["median_wr"]>=.55 and row["median_exp"]>=.75 and row["median_pf"]>=1.20 and row["median_dd"]<=90)
        blockgate=row["clock_blocks_ok"]>=4
        row.update({"breadth_gate":breadth,"median_gate":medgate,"era_gate":era_ok,"block_gate":blockgate,"candidate_gate":breadth and medgate and era_ok and blockgate,"min_era_median_exp":float(min(era_exps))})
        fam=str(row["family"]); lb=int(row["lookback_min"]); h=int(row["hold_min"]); p1=int(row["p1_idx"]); p2=int(row["p2_idx"])
        lbs=IRR_LBS if fam=="IRR" else CE_LBS if fam=="CE" else ER_LBS
        row["boundary"]=(lb in (min(lbs),max(lbs)) or h in (min(HOLDS),max(HOLDS)) or p1 in (0,2) or p2 in (0,2))
        rows.append(row)
    D=pd.DataFrame(rows)
    if len(D)!=1080: raise AssertionError(f"expected 1080 candidates, got {len(D)}")
    C=D[D.candidate_gate].copy().sort_values(
        ["min_era_median_exp","supportive_fraction","median_exp","median_wr","median_pf","median_dd","hold_min","lookback_min","family","p1_idx","p2_idx","mode"],
        ascending=[False,False,False,False,False,True,True,True,True,True,True,True]).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def spec_from_row(r):
    return dict(family=str(r["family"]),lookback_min=int(r["lookback_min"]),p1_idx=int(r["p1_idx"]),p1_label=str(r["p1_label"]),p1_value=float(r["p1_value"]),p2_idx=int(r["p2_idx"]),p2_label=str(r["p2_label"]),p2_value=float(r["p2_value"]),mode=str(r["mode"]),dir_mult=(1.0 if str(r["mode"]) in ("CONTINUE","RESUME") else -1.0),hold_min=int(r["hold_min"]))


def selected_panel_part(x5, sel, part):
    sp=spec_from_row(sel); pa,pz=base.PARTS[part]; rows=[]
    for clock in CLOCKS:
        S=sequence_frame(x5,clock,int(sp["lookback_min"])); ent=pd.DatetimeIndex(S.entry_ts); pre=pd.DatetimeIndex(S.pre_ts)
        ex,valid,xp,delta,_=e3.hold_base(x5,S,int(sp["hold_min"])); ev,direction=event_mask_dir(S,sp)
        m=valid&ev&(pre>=pa)&(ent>=pa)&(ex<pz)
        gross=NOTIONAL*direction*delta; net=gross-FEE; s=summarize(net[m],gross[m])
        rows.append({"partition":part,"clock_min_utc":clock,"clock_utc":hhmm(clock),"clock_wib":wib(clock),**s})
    return pd.DataFrame(rows)


def holdout_summary(G):
    ev=G.trades>=25; E=G[ev]
    sup=ev&(G.win_rate>=.52)&(G.expectancy>0)&(G.pf>=1.05)
    pfrac=float((ev&(G.expectancy>0)).sum()/ev.sum()) if ev.sum() else np.nan
    blocks=[]
    for bi in range(6):
        bg=G[(G.clock_min_utc//240)==bi]; bev=bg.trades>=25; bs=bev&(bg.win_rate>=.52)&(bg.expectancy>0)&(bg.pf>=1.05)
        blocks.append(bool(bev.sum()>0 and bs.sum()/bev.sum()>=.50))
    out={"evaluable_clocks":int(ev.sum()),"supportive_clocks":int(sup.sum()),"median_wr":float(E.win_rate.median()) if len(E) else np.nan,"median_exp":float(E.expectancy.median()) if len(E) else np.nan,"median_pf":float(E.pf.median()) if len(E) else np.nan,"positive_exp_fraction":pfrac,"clock_blocks_ok":int(sum(blocks))}
    out["pass"]=(out["evaluable_clocks"]>=16 and out["median_wr"]>=.53 and out["median_exp"]>0 and out["median_pf"]>=1.08 and out["positive_exp_fraction"]>=.55 and out["clock_blocks_ok"]>=4)
    return out


def main():
    base.synthetic_tests(); x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    P=panel_rows(x5); D,C=aggregate_candidates(P)
    P.to_csv(OUT_PANEL,index=False); D.to_csv(OUT_GRID,index=False); C.to_csv(OUT_LEADER,index=False)
    lines=["# ETH Economic-First E12 — Path-Sequence Grammar Result","",f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.","Clock treatment: **48 half-hour UTC clocks are contexts, not candidate coordinates**.","Families: **IRR / CE / ER**. No H/L, breakout, EMA, Fibonacci, TP or SL.",f"Candidate identities: **{len(D)}**; full Development gate passers: **{len(C)}**.","","## Best Development sequence identities","","| # | Family | Shape | Mode | LB | Hold | Eval | Support | Med WR | Med Exp | PF | DD | Blocks | 2022 WR/Exp | 2023 | 2024 | Gate |","|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    top=D.sort_values(["min_era_median_exp","supportive_fraction","median_exp","median_wr"],ascending=[False,False,False,False]).head(20)
    for i,r in enumerate(top.itertuples(index=False),1):
        lines.append(f"| {i} | {r.family} | {r.p1_label}/{r.p2_label} | {r.mode} | {int(r.lookback_min)}m | {int(r.hold_min)}m | {int(r.evaluable_clocks)} | {int(r.supportive_clocks)}/{int(r.evaluable_clocks)} | {pct(r.median_wr)} | {money(r.median_exp)} | {r.median_pf:.3f} | {money(r.median_dd)} | {int(r.clock_blocks_ok)}/6 | {pct(r.y2022_median_wr)}/{money(r.y2022_median_exp)} | {pct(r.y2023_median_wr)}/{money(r.y2023_median_exp)} | {pct(r.y2024_median_wr)}/{money(r.y2024_median_exp)} | {'YES' if r.candidate_gate else 'NO'} |")
    if len(C)==0:
        status="ETH_ECONOMIC_FIRST_E12_NO_SEQUENCE_CANDIDATE"; OUT_STATUS.write_text(status+"\n")
        lines += ["",f"**Status: {status}**","","No IRR, CE or ER sequence identity passed breadth + median economics + all-era + clock-block gates. OOS remained closed. No gate relaxation or raw-top substitution.","","Research/shadow only; no live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return
    sel=C.iloc[0]; atlas=P[(P.family==sel.family)&(P.lookback_min==sel.lookback_min)&(P.p1_idx==sel.p1_idx)&(P.p2_idx==sel.p2_idx)&(P["mode"]==sel["mode"])&(P.hold_min==sel.hold_min)].copy(); atlas.to_csv(OUT_SELECTED,index=False)
    lines += ["","## Development-selected sequence","",f"**{sel.family} / {sel.p1_label}/{sel.p2_label} / {sel['mode']} / LB{int(sel.lookback_min)} / hold{int(sel.hold_min)}m**",f"Median WR **{pct(sel.median_wr)}**, median exp **{money(sel.median_exp)}/trade**, median PF **{sel.median_pf:.3f}**, supportive clocks **{int(sel.supportive_clocks)}/{int(sel.evaluable_clocks)}**, clock blocks **{int(sel.clock_blocks_ok)}/6**."]
    if bool(sel.boundary):
        status="ETH_ECONOMIC_FIRST_E12_BOUNDARY_OPEN"; OUT_STATUS.write_text(status+"\n")
        lines += ["","Selected Development winner touches a preregistered sequence-grid boundary. OOS remains closed.","",f"**Status: {status}**"]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return
    hrows=[]; allok=True
    for part in ("external","reference_validation"):
        G=selected_panel_part(x5,sel,part); s=holdout_summary(G); s["partition"]=part; hrows.append(s); allok &= bool(s["pass"])
        lines += ["",f"### {part}",f"Eval clocks **{s['evaluable_clocks']}**, support **{s['supportive_clocks']}**, median WR **{pct(s['median_wr'])}**, median exp **{money(s['median_exp'])}**, median PF **{s['median_pf']:.3f}**, positive-exp fraction **{pct(s['positive_exp_fraction'])}**, blocks **{s['clock_blocks_ok']}/6** — **{'PASS' if s['pass'] else 'FAIL'}**."]
    pd.DataFrame(hrows).to_csv(OUT_HOLDOUT,index=False)
    status="ETH_ECONOMIC_FIRST_E12_SUPPORTED" if allok else "ETH_ECONOMIC_FIRST_E12_NOT_REPLICATED"
    OUT_STATUS.write_text(status+"\n"); lines += ["",f"**Status: {status}**","","Research/shadow only; no live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__ == "__main__":
    main()
