#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_v5_batch2d_state_time_direction as b2d

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_V5_BATCH2F_STRUCTURAL_GRAMMAR"
TEST_YEARS = b2d.TEST_YEARS
PRIOR_N = 40.0
MIN_SUPPORT = 30
ROUNDTRIP_COST_PCT = b2d.ROUNDTRIP_COST_PCT
NOTIONAL = 500.0
SEQ_BARS = 24
MOTIF_LEN = 4


def pf(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    return math.inf if neg <= 0 and pos > 0 else (pos / neg if neg > 0 else np.nan)


def max_dd(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    if a.empty:
        return np.nan
    eq = a.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def max_ls(pnls) -> int:
    best = cur = 0
    for x in pd.Series(pnls, dtype=float).dropna():
        if x < 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return best


def token(prev_h: float, prev_l: float, h: float, l: float) -> str:
    if h > prev_h and l < prev_l:
        return "O"
    if h < prev_h and l > prev_l:
        return "I"
    if h >= prev_h and l >= prev_l and (h > prev_h or l > prev_l):
        return "U"
    if h <= prev_h and l <= prev_l and (h < prev_h or l < prev_l):
        return "D"
    return "F"


def grammar_for_entry(x5: pd.DataFrame, t: pd.Timestamp) -> str | None:
    q = x5[(x5.open_time >= t - pd.Timedelta(minutes=SEQ_BARS*5)) & (x5.open_time < t)].tail(SEQ_BARS)
    if len(q) != SEQ_BARS:
        return None
    hi = q.high.astype(float).to_numpy(); lo = q.low.astype(float).to_numpy()
    toks = [token(hi[i-1], lo[i-1], hi[i], lo[i]) for i in range(1, len(q))]
    if len(toks) < MOTIF_LEN:
        return None
    return "-".join(toks[-MOTIF_LEN:])


def build_episodes(x5: pd.DataFrame) -> pd.DataFrame:
    episodes, _ = b2d.build_episode_table(x5)
    episodes = episodes.copy()
    episodes["grammar"] = [grammar_for_entry(x5, t) for t in episodes.entry_time]
    episodes = episodes[episodes.grammar.notna()].copy()
    episodes["net60_pct"] = episodes.ret_60m_pct.astype(float) - ROUNDTRIP_COST_PCT
    episodes["pnl60_usd"] = episodes.net60_pct / 100.0 * NOTIONAL
    return episodes.sort_values("entry_time").reset_index(drop=True)


def train_motif_stats(tr: pd.DataFrame, test_year: int) -> pd.DataFrame:
    global_edge = float(tr.net60_pct.mean())
    global_up = float(tr.target_up_first.mean())
    rows = []
    for gname, g in tr.groupby("grammar"):
        n = int(len(g))
        edge = float(g.net60_pct.mean())
        up = float(g.target_up_first.mean())
        shr_edge = (n * edge + PRIOR_N * global_edge) / (n + PRIOR_N)
        shr_up = (n * up + PRIOR_N * global_up) / (n + PRIOR_N)
        rows.append({
            "test_year": test_year, "grammar": gname, "train_n": n,
            "train_up_first": up, "train_edge_pct": edge, "train_wr60": float((g.net60_pct > 0).mean()),
            "train_pf60": pf(g.pnl60_usd), "global_edge_pct": global_edge, "global_up_first": global_up,
            "shrunk_edge_pct": shr_edge, "shrunk_up_first": shr_up,
            "eligible": bool(n >= MIN_SUPPORT and shr_edge > 0 and shr_up > global_up),
        })
    return pd.DataFrame(rows).sort_values(["eligible","shrunk_edge_pct","train_n"], ascending=[False,False,False])


def walk_forward(ep: pd.DataFrame):
    assigns, dictionaries = [], []
    for y in TEST_YEARS:
        yrs = b2d.b2.train_years_for(y)
        tr = ep[ep.test_year.isin(yrs)].copy()
        te = ep[ep.test_year == y].copy()
        if tr.empty or te.empty:
            raise RuntimeError(f"bad split {y}")
        stats = train_motif_stats(tr, y)
        dictionaries.append(stats)
        elig = set(stats.loc[stats.eligible, "grammar"].astype(str))
        mp = stats.set_index("grammar")
        te["eligible_long"] = te.grammar.astype(str).isin(elig)
        te["train_support"] = te.grammar.map(mp.train_n).fillna(0).astype(int)
        te["train_shrunk_edge_pct"] = te.grammar.map(mp.shrunk_edge_pct)
        te["train_shrunk_up_first"] = te.grammar.map(mp.shrunk_up_first)
        assigns.append(te)
    return pd.concat(assigns, ignore_index=True).sort_values("entry_time"), pd.concat(dictionaries, ignore_index=True)


def econ(g: pd.DataFrame) -> dict:
    if g.empty:
        return {"n":0,"wr":np.nan,"exp":np.nan,"pf":np.nan,"pnl":0.0,"dd":np.nan,"ls":0,"up":np.nan}
    return {
        "n":len(g), "wr":float((g.net60_pct > 0).mean()), "exp":float(g.net60_pct.mean()),
        "pf":pf(g.pnl60_usd), "pnl":float(g.pnl60_usd.sum()), "dd":max_dd(g.pnl60_usd),
        "ls":max_ls(g.pnl60_usd), "up":float(g.target_up_first.mean()),
    }


def fmt(v, d=3):
    if pd.isna(v): return "n/a"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def main():
    b2d.b2.b1.v4.v3.v1.base.fetch_one = b2d.b2.b1.v4.v3.v1.fetch_one_with_volume
    x5, coverage = b2d.b2.b1.v4.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    ep = build_episodes(x5)
    pred, dct = walk_forward(ep)
    sel = pred[pred.eligible_long].copy().reset_index(drop=True)
    base = pred.copy()
    se, be = econ(sel), econ(base)
    base_up = be["up"]
    lift = se["up"] / base_up if np.isfinite(se["up"]) and base_up > 0 else np.nan

    yrs=[]
    for y in TEST_YEARS:
        g=pred[pred.test_year==y]; s=g[g.eligible_long]
        ee, bb=econ(s), econ(g)
        yrs.append({"test_year":y,"episodes":len(g),"base_up_first":bb["up"],"selected_n":len(s),
                    "selected_up_first":ee["up"],"lift":ee["up"]/bb["up"] if len(s) and bb["up"]>0 else np.nan,
                    "wr60":ee["wr"],"exp60":ee["exp"],"pf60":ee["pf"],"pnl60":ee["pnl"],
                    "distinct_traded_grammars":s.grammar.nunique()})
    yr=pd.DataFrame(yrs)
    positive_years=int((yr.pnl60>0).sum())
    distinct=int(sel.grammar.nunique())

    transfer=[]
    for (y,gr), g in pred.groupby(["test_year","grammar"]):
        st=dct[(dct.test_year==y)&(dct.grammar==gr)]
        if st.empty: continue
        r=st.iloc[0]
        transfer.append({"test_year":y,"grammar":gr,"eligible_train":bool(r.eligible),"train_n":int(r.train_n),
                         "train_shrunk_edge_pct":float(r.shrunk_edge_pct),"train_shrunk_up_first":float(r.shrunk_up_first),
                         "test_n":len(g),"test_up_first":float(g.target_up_first.mean()),"test_edge_pct":float(g.net60_pct.mean()),
                         "test_pf60":pf(g.pnl60_usd)})
    transfer=pd.DataFrame(transfer)

    freq=ep.groupby("grammar").agg(n=("grammar","size"),up_first=("target_up_first","mean"),edge_pct=("net60_pct","mean")).reset_index().sort_values("n",ascending=False)

    gates={
        "selected_oos_n_ge_100": se["n"] >= 100,
        "selected_up_first_lift_ge_1_20x": bool(np.isfinite(lift) and lift >= 1.20),
        "selected_expectancy_positive": bool(np.isfinite(se["exp"]) and se["exp"] > 0),
        "selected_pf_ge_1_10": bool(np.isfinite(se["pf"]) and se["pf"] >= 1.10),
        "positive_selected_pnl_years_ge_2_of_3": positive_years >= 2,
        "distinct_traded_grammars_ge_2": distinct >= 2,
        "selected_expectancy_beats_baseline": bool(np.isfinite(se["exp"]) and np.isfinite(be["exp"]) and se["exp"] > be["exp"]),
    }
    verdict="READY_FOR_BATCH3_RISK_ENVELOPE" if all(gates.values()) else "STRUCTURAL_GRAMMAR_NOT_READY"

    pred.to_csv(ROOT/f"{PFX}_Assignments.csv",index=False)
    dct.to_csv(ROOT/f"{PFX}_TrainingMotifDictionary.csv",index=False)
    dct[dct.eligible].to_csv(ROOT/f"{PFX}_EligibleMotifs.csv",index=False)
    sel.to_csv(ROOT/f"{PFX}_SelectedTrades.csv",index=False)
    yr.to_csv(ROOT/f"{PFX}_YearSummary.csv",index=False)
    transfer.to_csv(ROOT/f"{PFX}_TransferAudit.csv",index=False)
    freq.to_csv(ROOT/f"{PFX}_GrammarFrequency.csv",index=False)
    pd.DataFrame([{"gate":k,"pass":v} for k,v in gates.items()]).to_csv(ROOT/f"{PFX}_GateAudit.csv",index=False)

    lines=["# SOL V5 Batch 2F — Structural Transition Motif / Grammar Result","",
           f"- Data coverage: **{coverage*100:.6f}%**",f"- OOS HIGH_STATE episodes 2022-2024: **{len(pred)}**",
           f"- Selected LONG trades: **{se['n']}**",f"- Distinct traded grammars: **{distinct}**","- Grammar length: **4 tokens**",
           "- 2025+ reference_validation remained CLOSED.","","## Pooled economics","",
           f"- Baseline UP_FIRST: **{base_up*100:.2f}%**",f"- Selected UP_FIRST: **{se['up']*100:.2f}%**" if np.isfinite(se['up']) else "- Selected UP_FIRST: **n/a**",
           f"- UP_FIRST lift: **{fmt(lift)}x**",f"- Selected WR +60m: **{se['wr']*100:.2f}%**" if np.isfinite(se['wr']) else "- Selected WR +60m: **n/a**",
           f"- Selected expectancy: **{fmt(se['exp'],4)}%**",f"- Selected PF: **{fmt(se['pf'])}**",f"- Selected PnL: **${se['pnl']:.2f}**",
           f"- Baseline expectancy: **{fmt(be['exp'],4)}%**",f"- Baseline PF: **{fmt(be['pf'])}**","","## Year stability","",
           "| Year | Episodes | Base UP_FIRST | Selected | Sel UP_FIRST | Lift | WR60 | Exp60 | PF60 | PnL | Grammars |",
           "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in yr.iterrows():
        lines.append(f"| {int(r.test_year)} | {int(r.episodes)} | {float(r.base_up_first)*100:.2f}% | {int(r.selected_n)} | {float(r.selected_up_first)*100:.2f}% | {fmt(r.lift)}x | {float(r.wr60)*100:.2f}% | {fmt(r.exp60,4)}% | {fmt(r.pf60)} | ${float(r.pnl60):.2f} | {int(r.distinct_traded_grammars)} |" if r.selected_n>0 else f"| {int(r.test_year)} | {int(r.episodes)} | {float(r.base_up_first)*100:.2f}% | 0 | n/a | n/a | n/a | n/a | n/a | $0.00 | 0 |")
    lines += ["","## Eligible grammar transfer (training-qualified motifs)",""]
    q=transfer[transfer.eligible_train].sort_values(["test_year","train_shrunk_edge_pct"],ascending=[True,False]).head(30)
    for _,r in q.iterrows():
        lines.append(f"- {int(r.test_year)} `{r.grammar}` — train N{int(r.train_n)}, shr edge {r.train_shrunk_edge_pct:.4f}%, shr UP {r.train_shrunk_up_first*100:.2f}% → test N{int(r.test_n)}, edge {r.test_edge_pct:.4f}%, UP {r.test_up_first*100:.2f}%, PF {fmt(r.test_pf60)}")
    lines += ["","## Batch 2F gate audit",""]
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["",f"# BATCH 2F VERDICT: {verdict}","",
              "READY_FOR_BATCH3_RISK_ENVELOPE means exact terminal structural grammars transfer OOS with positive pre-exit-optimization LONG economics.",
              "STRUCTURAL_GRAMMAR_NOT_READY means do not rescue by sweeping motif length, support, prior, token definitions, hours, horizon, TP or SL on 2022-2024."]
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n",encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
