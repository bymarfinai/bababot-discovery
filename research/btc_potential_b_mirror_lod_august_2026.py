#!/usr/bin/env python3
"""Potential B mirror: pre-London LOD breakdown + seller dominance -> BUY.

Frozen H7 / W90 / CONFIRM2 mirror. Research-only, no live path, no 1m.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import btc_potential_b_august_2026_replay as base

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_PotentialB_Mirror_LOD_August2026_Result.md"
OUT_JSON = ROOT / "BTC_PotentialB_Mirror_LOD_August2026_Result.json"
OUT_CSV = ROOT / "BTC_PotentialB_Mirror_LOD_August2026_Events.csv"

OPEN_HOUR = 7
WINDOW_MIN = 90
FLOW_CUT = 0.50


def resolve_60m_buy(x: pd.DataFrame, entry_idx: int) -> dict | None:
    end_idx = entry_idx + 11
    if end_idx >= len(x):
        return None
    expected = x.ts.iloc[entry_idx] + pd.Timedelta(minutes=55)
    if x.ts.iloc[end_idx] != expected:
        return None
    ep = float(x.open.iloc[entry_idx])
    fc = float(x.close.iloc[end_idx])
    hs = x.high.iloc[entry_idx:end_idx + 1].to_numpy(float)
    ls = x.low.iloc[entry_idx:end_idx + 1].to_numpy(float)
    signed = (fc - ep) / ep
    return {
        "entry_price": ep,
        "close_60m": fc,
        "signed_ret_60m": signed,
        "dir_win_60m": int(signed > 0),
        "mfe_60m": (float(np.max(hs)) - ep) / ep,
        "mae_60m": (ep - float(np.min(ls))) / ep,
    }


def resolve_1pct_buy(x: pd.DataFrame, entry_idx: int) -> dict | None:
    bars = 72
    end_idx = entry_idx + bars - 1
    if end_idx >= len(x):
        return None
    if x.ts.iloc[end_idx] != x.ts.iloc[entry_idx] + pd.Timedelta(minutes=5 * (bars - 1)):
        return None
    ep = float(x.open.iloc[entry_idx])
    tp = ep * 1.01
    sl = ep * 0.99
    hs = x.high.iloc[entry_idx:end_idx + 1].to_numpy(float)
    ls = x.low.iloc[entry_idx:end_idx + 1].to_numpy(float)
    tp_hits = np.flatnonzero(hs >= tp)
    sl_hits = np.flatnonzero(ls <= sl)
    ti = int(tp_hits[0]) if tp_hits.size else 10**9
    si = int(sl_hits[0]) if sl_hits.size else 10**9
    if si <= ti:
        raw = -0.01
        reason = "SL_1PCT"
        win = 0
    elif ti < 10**9:
        raw = 0.01
        reason = "TP_1PCT"
        win = 1
    else:
        fc = float(x.close.iloc[end_idx])
        raw = (fc - ep) / ep
        reason = "TIME_6H"
        win = int(raw - base.FEE > 0)
    net = raw - base.FEE
    return {
        "onepct_reason": reason,
        "onepct_win": win,
        "onepct_raw_ret": raw,
        "onepct_net_ret": net,
        "onepct_pnl": net * base.NOTIONAL,
        "mfe_6h": (float(np.max(hs)) - ep) / ep,
        "mae_6h": (ep - float(np.min(ls))) / ep,
    }


def detect(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = []
    by_date = {d: g for d, g in x.groupby("utc_date", sort=False)}
    d = start.normalize()
    while d < end.normalize():
        if d.weekday() >= 5:
            d += pd.Timedelta(days=1)
            continue
        ds = d.strftime("%Y-%m-%d")
        g = by_date.get(ds)
        d += pd.Timedelta(days=1)
        if g is None or g.empty:
            continue
        open_ts = pd.Timestamp(f"{ds}T{OPEN_HOUR:02d}:00:00Z")
        end_ts = open_ts + pd.Timedelta(minutes=WINDOW_MIN)
        pre = g[(g.ts >= pd.Timestamp(f"{ds}T00:00:00Z")) & (g.ts < open_ts)]
        sess = g[(g.ts >= open_ts) & (g.ts < end_ts)]
        if pre.empty or len(sess) < 3:
            continue
        lod = float(pre.low.min())
        idxs = sess.index.to_numpy(int)
        confirm_idx = None
        for k in range(1, len(idxs)):
            a, b = int(idxs[k - 1]), int(idxs[k])
            if x.ts.iloc[b] - x.ts.iloc[a] != pd.Timedelta(minutes=5):
                continue
            if float(x.close.iloc[a]) < lod and float(x.close.iloc[b]) < lod:
                confirm_idx = b
                break
        if confirm_idx is None:
            continue
        entry_idx = base.next_15m_entry(x, confirm_idx)
        if entry_idx is None:
            continue
        r60 = resolve_60m_buy(x, entry_idx)
        r1 = resolve_1pct_buy(x, entry_idx)
        if r60 is None or r1 is None:
            continue
        taker_buy = float(x.taker_buy_share.iloc[confirm_idx])
        seller_aggr = taker_buy < FLOW_CUT
        rows.append({
            "utc_date": ds,
            "frozen_lod": lod,
            "confirm_ts": x.ts.iloc[confirm_idx],
            "entry_ts": x.ts.iloc[entry_idx],
            "entry_wib": x.ts.iloc[entry_idx] + pd.Timedelta(hours=7),
            "confirm_taker_buy_share": taker_buy,
            "aggressive_seller": bool(seller_aggr),
            **r60,
            **r1,
        })
    return pd.DataFrame(rows)


def stats60(z: pd.DataFrame) -> dict:
    if z is None or z.empty:
        return {"n":0,"wins":0,"wr":None,"avg_ret":None,"median_mfe":None,"median_mae":None}
    return {
        "n": int(len(z)),
        "wins": int(z.dir_win_60m.sum()),
        "wr": float(z.dir_win_60m.mean()),
        "avg_ret": float(z.signed_ret_60m.mean()),
        "median_mfe": float(z.mfe_60m.median()),
        "median_mae": float(z.mae_60m.median()),
    }


def stats1(z: pd.DataFrame) -> dict:
    if z is None or z.empty:
        return {"n":0,"wins":0,"wr":None,"pnl":0.0,"tp":0,"sl":0,"time":0}
    return {
        "n": int(len(z)),
        "wins": int(z.onepct_win.sum()),
        "wr": float(z.onepct_win.mean()),
        "pnl": float(z.onepct_pnl.sum()),
        "tp": int((z.onepct_reason=="TP_1PCT").sum()),
        "sl": int((z.onepct_reason=="SL_1PCT").sum()),
        "time": int((z.onepct_reason=="TIME_6H").sum()),
        "median_mfe_6h": float(z.mfe_6h.median()),
        "median_mae_6h": float(z.mae_6h.median()),
    }


def split70(z: pd.DataFrame):
    if z.empty:
        return z.copy(), z.copy()
    cut = int(np.floor(len(z)*0.70))
    cut = min(max(cut,1), len(z)-1) if len(z) > 1 else len(z)
    return z.iloc[:cut].copy(), z.iloc[cut:].copy()


def four_blocks(z: pd.DataFrame):
    if z.empty:
        return []
    blocks=[]
    for i, idx in enumerate(np.array_split(np.arange(len(z)),4), start=1):
        zz=z.iloc[idx] if len(idx) else z.iloc[0:0]
        s=stats60(zz)
        blocks.append({"block":i,**s})
    return blocks


def fmt(v):
    return "-" if v is None else f"{100*v:.2f}%"


def main():
    x=base.load_data()
    hist=detect(x, base.HIST_START, base.HIST_END)
    aug=detect(x, base.AUG_START, base.AUG_END)
    hist_ag=hist[hist.aggressive_seller] if not hist.empty else hist
    aug_ag=aug[aug.aggressive_seller] if not aug.empty else aug

    disc, val = split70(hist_ag)
    blocks=four_blocks(hist_ag)
    full_ag=stats60(hist_ag)
    disc_s=stats60(disc)
    val_s=stats60(val)
    gate=(full_ag["n"]>=25 and full_ag["wr"] is not None and full_ag["wr"]>=0.80 and
          val_s["n"]>=10 and val_s["wr"] is not None and val_s["wr"]>=0.80 and
          disc_s["wr"] is not None and disc_s["wr"]>=0.80 and
          sum(1 for b in blocks if b["n"]>=5 and b["wr"] is not None and b["wr"]>0.50)>=3)

    out={
        "protocol":"POTENTIAL_B_MIRROR_LOD_H7_W90_CONFIRM2_V1",
        "data":{"rows":int(len(x)),"first_ts":str(x.ts.min()),"last_ts":str(x.ts.max())},
        "rule":{"open_hour_utc":7,"window_minutes":90,"weekdays_only":True,"direction":"BUY","aggressive_seller":"taker_buy_share<0.50","entry":"next_15m_open"},
        "historical_base_60m":stats60(hist),
        "historical_aggressive_60m":full_ag,
        "historical_aggressive_discovery70":disc_s,
        "historical_aggressive_validation30":val_s,
        "historical_aggressive_blocks":blocks,
        "historical_base_1pct":stats1(hist),
        "historical_aggressive_1pct":stats1(hist_ag),
        "august_base_60m":stats60(aug),
        "august_aggressive_60m":stats60(aug_ag),
        "august_base_1pct":stats1(aug),
        "august_aggressive_1pct":stats1(aug_ag),
        "promotion_80_candidate":bool(gate),
        "integrity":{"one_event_max_per_day":bool(hist.utc_date.is_unique if not hist.empty else True),"one_minute_data_used":False,"august_used_for_rule_selection":False},
    }
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+"\n")
    if aug.empty:
        pd.DataFrame(columns=["utc_date"]).to_csv(OUT_CSV,index=False)
    else:
        aug.to_csv(OUT_CSV,index=False)

    hb=out["historical_base_60m"]; ha=full_ag; ab=out["august_base_60m"]; aa=out["august_aggressive_60m"]
    h1=out["historical_aggressive_1pct"]; a1=out["august_aggressive_1pct"]
    md=[
        "# BTC Potential B Mirror — LOD Breakdown / Seller Trap BUY Result","",
        f"**80% candidate gate: {'PASS' if gate else 'REJECT'}**","",
        "Frozen rule: weekdays; pre-07:00 UTC LOD; first two consecutive 5m closes below LOD during 07:00-08:30 UTC; BUY next causal 15m open; aggressive seller iff taker-buy share <50%.","",
        "## Historical 2023-12-02 to 2026-07-30","",
        "| Cohort | N | Wins | WR | Avg BUY ret | Median MFE | Median MAE |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Base | {hb['n']} | {hb['wins']} | {fmt(hb['wr'])} | {fmt(hb['avg_ret'])} | {fmt(hb['median_mfe'])} | {fmt(hb['median_mae'])} |",
        f"| Aggressive seller | {ha['n']} | {ha['wins']} | {fmt(ha['wr'])} | {fmt(ha['avg_ret'])} | {fmt(ha['median_mfe'])} | {fmt(ha['median_mae'])} |","",
        "### Aggressive-seller chronology","",
        "| Split | N | Wins | WR |",
        "|---|---:|---:|---:|",
        f"| Discovery first70% | {disc_s['n']} | {disc_s['wins']} | {fmt(disc_s['wr'])} |",
        f"| Validation last30% | {val_s['n']} | {val_s['wins']} | {fmt(val_s['wr'])} |","",
        "| Block | N | Wins | WR |","|---|---:|---:|---:|",
    ]
    for b in blocks:
        md.append(f"| B{b['block']} | {b['n']} | {b['wins']} | {fmt(b['wr'])} |")
    md += ["","## Historical >1% diagnostic — aggressive seller","",
           f"N **{h1['n']}**, wins **{h1['wins']}**, WR **{fmt(h1['wr'])}**, TP **{h1['tp']}**, SL **{h1['sl']}**, TIME **{h1['time']}**, PnL **${h1['pnl']:.2f}**.","",
           "## August 2026 true-OOS","",
           "| Cohort | N | Wins | 60m WR | Avg BUY ret |","|---|---:|---:|---:|---:|",
           f"| Base | {ab['n']} | {ab['wins']} | {fmt(ab['wr'])} | {fmt(ab['avg_ret'])} |",
           f"| Aggressive seller | {aa['n']} | {aa['wins']} | {fmt(aa['wr'])} | {fmt(aa['avg_ret'])} |","",
           f"August aggressive >1% diagnostic: N **{a1['n']}**, wins **{a1['wins']}**, WR **{fmt(a1['wr'])}**, TP **{a1['tp']}**, SL **{a1['sl']}**, TIME **{a1['time']}**, PnL **${a1['pnl']:.2f}**.","",
           "## August event ledger","" ]
    if aug.empty:
        md.append("No mirror event occurred in available completed August data.")
    else:
        md += ["| UTC date | Entry WIB | LOD | Taker buy | Seller aggressive | 60m | BUY ret | 1%/6h | MFE6h |",
               "|---|---|---:|---:|---|---|---:|---|---:|"]
        for _,r in aug.iterrows():
            md.append(f"| {r.utc_date} | {pd.Timestamp(r.entry_wib).strftime('%Y-%m-%d %H:%M')} | {r.frozen_lod:.2f} | {100*r.confirm_taker_buy_share:.1f}% | {'YES' if r.aggressive_seller else 'NO'} | {'WIN' if r.dir_win_60m else 'LOSS'} | {100*r.signed_ret_60m:.3f}% | {r.onepct_reason} | {100*r.mfe_6h:.3f}% |")
    md += ["","No clock/window/flow/TP-SL parameter was selected from the result. Live BBC untouched."]
    OUT_MD.write_text("\n".join(md)+"\n")
    print(json.dumps(out,indent=2,default=str))

if __name__ == "__main__":
    main()
