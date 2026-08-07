"""Entry×Exit Matrix — 3 entries × 4 exits on V2 Mode B signal stream.

Entry: A=market@close, B=limit@EMA(next bar only), C=close if dist<threshold
Exit: 1=fixed TP/SL, 2=SL@protected_swing-ATR, 3=EMA cross exit, 4=trailing BE
First-touch: SL checked before TP within each bar.

GET /v2_gated/entry_exit?symbol=SOLUSDT&days=971
"""
import os, sqlite3, numpy as np, math
from fastapi import APIRouter, Query
from datetime import datetime, timezone
from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Switcher
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v2_gated", tags=["entry_exit"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

def _load(sym, tf, days):
    conn = sqlite3.connect(DB_PATH)
    now_ms = int(datetime.utcnow().timestamp()*1000)
    start = now_ms - (days*86400*1000)
    cur = conn.cursor()
    cur.execute("SELECT open_time,open,high,low,close,volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC", (sym, tf, start, now_ms))
    rows = cur.fetchall(); conn.close(); return rows

def _ema(c, p):
    e = np.zeros(len(c)); e[0]=c[0]; k=2.0/(p+1)
    for i in range(1, len(c)): e[i] = c[i]*k + e[i-1]*(1-k)
    return e

def _atr(H, L, C, period=14):
    n=len(H); atr=np.zeros(n)
    for i in range(1,n):
        tr=max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1]))
        if i<period: atr[i]=(atr[i-1]*(i-1)+tr)/i
        else: atr[i]=atr[i-1]+(tr-atr[i-1])/period
    return atr

def _va(H,L,C,V,w):
    n=len(H); vahs=[None]*n; vals=[None]*n; pocs=[None]*n
    for i in range(w,n):
        hs=H[i-w:i];ls=L[i-w:i];cs=C[i-w:i]
        vahs[i]=float(np.percentile(hs,85));vals[i]=float(np.percentile(ls,15))
        vs=V[i-w:i];tv=sum(vs) or 1
        tp=[(hs[j]+ls[j]+cs[j])/3 for j in range(w)]
        pocs[i]=sum(tp[j]*vs[j] for j in range(w))/tv
    return vahs,vals,pocs

class SignalCollector(Switcher):
    """Runs Full Switcher but just collects entry signals, gated by V2."""
    def __init__(self, config, det):
        super().__init__(config); self.det=det; self.signals=[]
    def _open_bull(self, bar_idx, entry_high, sl_level, entry_price, trigger='ema_reclaim'):
        if self.det.regime != "BULL": return
        self.signals.append({"bar":bar_idx,"side":"LONG","price":entry_price,"trigger":trigger})
        super()._open_bull(bar_idx, entry_high, sl_level, entry_price, trigger)
    def _open_bear(self, bar_idx, entry_high, entry_low, sl_level, entry_price):
        if self.det.regime != "BEAR": return
        self.signals.append({"bar":bar_idx,"side":"SHORT","price":entry_price})
        super()._open_bear(bar_idx, entry_high, entry_low, sl_level, entry_price)

def _sim_trade(entry_bar, entry_price, side, exit_mode, H, L, C, O, ef, es, atr_arr, n,
               tp_pct=0.013, sl_pct=0.013, prot_level=None, cost=0.0015, max_bars=100):
    """Simulate one trade with given entry and exit mode. Returns trade result."""
    # Exit params
    if exit_mode == 1:  # fixed TP/SL
        if side=="LONG": tp=entry_price*(1+tp_pct); sl=entry_price*(1-sl_pct)
        else: tp=entry_price*(1-tp_pct); sl=entry_price*(1+sl_pct)
    elif exit_mode == 2:  # SL at protected swing - ATR buffer
        atr_e = atr_arr[entry_bar] if atr_arr[entry_bar]>0 else 1
        if side=="LONG":
            sl = (prot_level - 0.5*atr_e) if prot_level else entry_price*(1-sl_pct)
            tp = entry_price*(1+tp_pct)
        else:
            sl = (prot_level + 0.5*atr_e) if prot_level else entry_price*(1+sl_pct)
            tp = entry_price*(1-tp_pct)
    elif exit_mode == 3:  # EMA cross exit (close through EMA)
        tp = None; sl = None  # no fixed TP/SL, exit on EMA cross
    elif exit_mode == 4:  # trailing BE after 0.5% profit
        if side=="LONG": tp=entry_price*(1+tp_pct); sl=entry_price*(1-sl_pct)
        else: tp=entry_price*(1-tp_pct); sl=entry_price*(1+sl_pct)
        be_triggered = False

    mfe=0; mae=0; mfe_bar=0; mae_bar=0
    atr_e = atr_arr[entry_bar] if atr_arr[entry_bar]>0 else 1

    end = min(entry_bar+max_bars+1, n)
    for j in range(entry_bar+1, end):
        bars_in = j - entry_bar
        if side=="LONG":
            fav = (H[j]-entry_price)/entry_price; adv = (entry_price-L[j])/entry_price
        else:
            fav = (entry_price-L[j])/entry_price; adv = (H[j]-entry_price)/entry_price
        if fav>mfe: mfe=fav; mfe_bar=bars_in
        if adv>mae: mae=adv; mae_bar=bars_in

        if exit_mode in (1, 2):
            # First touch: check SL first
            if side=="LONG":
                hit_sl = L[j] <= sl; hit_tp = H[j] >= tp
            else:
                hit_sl = H[j] >= sl; hit_tp = L[j] <= tp
            if hit_sl:
                pnl_pct = -abs(entry_price-sl)/entry_price - cost
                return {"exit":"SL","bars":bars_in,"pnl_pct":round(pnl_pct*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_bar":mfe_bar,"mae_bar":mae_bar}
            if hit_tp:
                pnl_pct = abs(tp-entry_price)/entry_price - cost
                return {"exit":"TP","bars":bars_in,"pnl_pct":round(pnl_pct*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_bar":mfe_bar,"mae_bar":mae_bar}

        elif exit_mode == 3:
            # Exit on close through EMA (EMA fast)
            if side=="LONG" and C[j] < ef[j]:
                pnl_pct = (C[j]-entry_price)/entry_price - cost
                return {"exit":"EMA_CROSS","bars":bars_in,"pnl_pct":round(pnl_pct*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_bar":mfe_bar,"mae_bar":mae_bar}
            elif side=="SHORT" and C[j] > ef[j]:
                pnl_pct = (entry_price-C[j])/entry_price - cost
                return {"exit":"EMA_CROSS","bars":bars_in,"pnl_pct":round(pnl_pct*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_bar":mfe_bar,"mae_bar":mae_bar}

        elif exit_mode == 4:
            # Trailing: move SL to BE after 0.5% profit
            if not be_triggered:
                if side=="LONG" and H[j] >= entry_price*(1+0.005):
                    sl = entry_price; be_triggered = True
                elif side=="SHORT" and L[j] <= entry_price*(1-0.005):
                    sl = entry_price; be_triggered = True
            if side=="LONG":
                hit_sl = L[j] <= sl; hit_tp = H[j] >= tp
            else:
                hit_sl = H[j] >= sl; hit_tp = L[j] <= tp
            if hit_sl:
                pnl_pct = (sl-entry_price)/entry_price if side=="LONG" else (entry_price-sl)/entry_price
                pnl_pct -= cost
                ex = "BE" if be_triggered and abs(sl-entry_price)<0.001*entry_price else "SL"
                return {"exit":ex,"bars":bars_in,"pnl_pct":round(pnl_pct*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_bar":mfe_bar,"mae_bar":mae_bar}
            if hit_tp:
                pnl_pct = abs(tp-entry_price)/entry_price - cost
                return {"exit":"TP","bars":bars_in,"pnl_pct":round(pnl_pct*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_bar":mfe_bar,"mae_bar":mae_bar}

    # Timeout
    pnl_pct = (C[end-1]-entry_price)/entry_price if side=="LONG" else (entry_price-C[end-1])/entry_price
    pnl_pct -= cost
    return {"exit":"TIMEOUT","bars":max_bars,"pnl_pct":round(pnl_pct*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_bar":mfe_bar,"mae_bar":mae_bar}


@router.get("/entry_exit")
def entry_exit_matrix(
    symbol: str = Query("SOLUSDT"), days: int = Query(971),
    ema_period: int = Query(7), ema_slow: int = Query(20),
    tp_pct: float = Query(0.013), sl_pct: float = Query(0.013),
    bull_body: float = Query(0.5), bear_body: float = Query(0.6),
    fee_pct: float = Query(0.001), slippage_pct: float = Query(0.0005),
    swing_lb: int = Query(10), swing_atr: float = Query(0.5),
    dist_threshold_pct: float = Query(0.3),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < max(ema_period, ema_slow)+60: return {"error": f"Not enough: {len(rows)}"}
    O=np.array([r[1] for r in rows],dtype=float); H=np.array([r[2] for r in rows],dtype=float)
    L=np.array([r[3] for r in rows],dtype=float); C=np.array([r[4] for r in rows],dtype=float)
    V=np.array([r[5] for r in rows],dtype=float); n=len(rows)
    ef=_ema(C,ema_period); es=_ema(C,ema_slow); atr_arr=_atr(H,L,C,14)
    vahs,vals,pocs = _va(H.tolist(),L.tolist(),C.tolist(),V.tolist(),50)
    cost = fee_pct + slippage_pct; notional = 500.0

    cfg = Mode3BBCConfig()
    cfg.ema_period=ema_period; cfg.tp_pct=tp_pct; cfg.sl_pct=sl_pct
    cfg.bull_body_ratio_min=bull_body; cfg.bear_body_ratio_min=bear_body
    cfg.bull_mtf_15m_enabled=False; cfg.bear_mtf_15m_enabled=False
    cfg.sideways_mtf_15m_enabled=False; cfg.enable_sideways_trades=False
    cfg.direct_transition_enabled=True
    cfg.fee_pct_roundtrip=fee_pct; cfg.slippage_pct=slippage_pct

    det = ContinuationDetectorV2(ema_period, ema_slow, swing_lb, swing_atr, 3, min_pb_bars=1)
    sc = SignalCollector(cfg, det)

    for i in range(n):
        det.process(i, O, H, L, C, ef, es, atr_arr)
        sc.process_candle(i, O[i], H[i], L[i], C[i], ef[i], vahs[i], vals[i], pocs[i])

    signals = sc.signals
    # Enrich signals with EMA/ATR/prot at signal bar
    for s in signals:
        i = s["bar"]
        s["ema"] = float(ef[i]); s["atr"] = float(atr_arr[i])
        s["dist_pct"] = round(100*abs(s["price"]-ef[i])/ef[i], 3)
        s["dist_atr"] = round(abs(s["price"]-ef[i])/atr_arr[i], 3) if atr_arr[i]>0 else 0
        # Protected level from detector
        s["prot"] = det.swing.protected_low if s["side"]=="LONG" else det.swing.protected_high

    # Split for walk-forward
    mid = n // 2
    train_sigs = [s for s in signals if s["bar"] < mid]
    test_sigs = [s for s in signals if s["bar"] >= mid]

    # Determine dist_threshold from train set (median dist)
    train_dists = [s["dist_pct"] for s in train_sigs]
    auto_threshold = round(float(np.median(train_dists)),2) if train_dists else dist_threshold_pct*100

    results = {}
    exit_labels = {1:"fixed_TP_SL", 2:"prot_swing_SL", 3:"EMA_cross_exit", 4:"trailing_BE"}

    for entry_mode in ["A","B","C"]:
        for exit_mode in [1, 2, 3, 4]:
            key = f"{entry_mode}_{exit_mode}"
            all_trades = []; filled = 0; skipped = 0

            for s in signals:
                i = s["bar"]; side = s["side"]
                # ENTRY
                if entry_mode == "A":
                    ep = s["price"]; fill = True
                elif entry_mode == "B":
                    # Limit at EMA, valid next bar only
                    if i+1 >= n: continue
                    ema_at = ef[i]
                    if side=="LONG":
                        fill = L[i+1] <= ema_at  # price dipped to EMA
                        ep = ema_at if fill else None
                    else:
                        fill = H[i+1] >= ema_at
                        ep = ema_at if fill else None
                    if not fill: skipped += 1; continue
                    i = i + 1  # entry on next bar
                elif entry_mode == "C":
                    if s["dist_pct"] > auto_threshold:
                        skipped += 1; continue
                    ep = s["price"]; fill = True

                if not fill: continue
                filled += 1

                # Get prot level for exit mode 2
                prot = s.get("prot")

                result = _sim_trade(i, ep, side, exit_mode, H, L, C, O, ef, es, atr_arr, n,
                                    tp_pct=tp_pct, sl_pct=sl_pct, prot_level=prot, cost=cost)
                result["side"] = side
                result["entry_bar"] = i
                all_trades.append(result)

            # Aggregate
            nt = len(all_trades)
            if nt == 0:
                results[key] = {"entry":entry_mode,"exit":exit_labels[exit_mode],"trades":0,"filled":filled,"skipped":skipped}
                continue
            wins = sum(1 for t in all_trades if t["pnl_pct"]>0)
            gross_pnl = sum((t["pnl_pct"]+cost*100)/100*notional for t in all_trades)
            net_pnl = sum(t["pnl_pct"]/100*notional for t in all_trades)
            avg_mfe = round(np.mean([t["mfe"] for t in all_trades]),3)
            avg_mae = round(np.mean([t["mae"] for t in all_trades]),3)

            # Walk-forward: train vs test
            train_t = [t for t in all_trades if t["entry_bar"] < mid]
            test_t = [t for t in all_trades if t["entry_bar"] >= mid]
            train_net = sum(t["pnl_pct"]/100*notional for t in train_t) if train_t else 0
            test_net = sum(t["pnl_pct"]/100*notional for t in test_t) if test_t else 0
            train_wr = round(100*sum(1 for t in train_t if t["pnl_pct"]>0)/len(train_t),1) if train_t else 0
            test_wr = round(100*sum(1 for t in test_t if t["pnl_pct"]>0)/len(test_t),1) if test_t else 0

            # Drawdown
            eq=0;pk=0;mdd=0
            for t in all_trades:
                eq+=t["pnl_pct"]/100*notional
                if eq>pk:pk=eq
                dd=pk-eq
                if dd>mdd:mdd=dd

            # Exit breakdown
            eb = {}
            for t in all_trades: eb[t["exit"]] = eb.get(t["exit"],0)+1

            # Per side
            long_t = [t for t in all_trades if t["side"]=="LONG"]
            short_t = [t for t in all_trades if t["side"]=="SHORT"]
            l_wr = round(100*sum(1 for t in long_t if t["pnl_pct"]>0)/len(long_t),1) if long_t else 0
            s_wr = round(100*sum(1 for t in short_t if t["pnl_pct"]>0)/len(short_t),1) if short_t else 0

            results[key] = {
                "entry":entry_mode, "exit":exit_labels[exit_mode],
                "trades":nt, "filled":filled, "skipped":skipped,
                "fill_rate": round(100*filled/(filled+skipped),1) if (filled+skipped)>0 else 0,
                "wr": round(100*wins/nt,1), "gross_pnl": round(gross_pnl,2), "net_pnl": round(net_pnl,2),
                "gross_exp": round(gross_pnl/nt,3), "net_exp": round(net_pnl/nt,3),
                "max_dd": round(mdd,2),
                "avg_mfe": avg_mfe, "avg_mae": avg_mae,
                "exit_breakdown": eb,
                "long": {"n":len(long_t),"wr":l_wr}, "short": {"n":len(short_t),"wr":s_wr},
                "walk_forward": {
                    "train": {"n":len(train_t),"wr":train_wr,"net":round(train_net,2)},
                    "test": {"n":len(test_t),"wr":test_wr,"net":round(test_net,2)},
                    "consistent": (train_net>0 and test_net>0) or (train_net<0 and test_net<0),
                },
            }

    # Entry distance stats
    dists = [s["dist_pct"] for s in signals]

    return {
        "symbol": symbol, "days": days, "candles": n,
        "total_signals": len(signals), "cost_pct": cost, "notional": notional,
        "auto_dist_threshold": auto_threshold,
        "entry_distance": {
            "mean_pct": round(np.mean(dists),3) if dists else 0,
            "median_pct": round(float(np.median(dists)),3) if dists else 0,
            "p25": round(float(np.percentile(dists,25)),3) if dists else 0,
            "p75": round(float(np.percentile(dists,75)),3) if dists else 0,
        },
        "results": results,
    }
