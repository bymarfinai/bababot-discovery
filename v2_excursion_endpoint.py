"""V2 Gated Excursion Audit — full price path analysis on Mode B entries.

For each Mode B entry, scan subsequent candles to compute:
- MFE/MAE in % and ATR
- % trades reaching various profit thresholds
- Whether target reached before SL
- Time to MFE, MAE, various levels
- Gross vs net PnL

GET /v2_gated/excursion?symbol=SOLUSDT&days=971
"""
import os, sqlite3, numpy as np, math
from fastapi import APIRouter, Query
from datetime import datetime, timezone
from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Switcher, Position
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v2_gated", tags=["v2_gated_excursion"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

def _load(symbol, tf, days):
    conn = sqlite3.connect(DB_PATH)
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    start = now_ms - (days * 86400 * 1000)
    cur = conn.cursor()
    cur.execute("SELECT open_time,open,high,low,close,volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC", (symbol, tf, start, now_ms))
    rows = cur.fetchall(); conn.close(); return rows

def _ema(c, p):
    e = np.zeros(len(c)); e[0] = c[0]; k = 2.0/(p+1)
    for i in range(1, len(c)): e[i] = c[i]*k + e[i-1]*(1-k)
    return e

def _atr(H, L, C, period=14):
    n = len(H); atr = np.zeros(n)
    for i in range(1, n):
        tr = max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1]))
        if i < period: atr[i] = (atr[i-1]*(i-1)+tr)/i if i>0 else tr
        else: atr[i] = atr[i-1]+(tr-atr[i-1])/period
    return atr

def _compute_va(H, L, C, V, w):
    n = len(H); vahs=[None]*n; vals=[None]*n; pocs=[None]*n
    for i in range(w, n):
        hs=H[i-w:i];ls=L[i-w:i];cs=C[i-w:i]
        vahs[i]=float(np.percentile(hs,85));vals[i]=float(np.percentile(ls,15))
        vs=V[i-w:i];tv=sum(vs) or 1
        tp=[(hs[j]+ls[j]+cs[j])/3 for j in range(w)]
        pocs[i]=sum(tp[j]*vs[j] for j in range(w))/tv
    return vahs, vals, pocs

class V2GatedSwitcher(Switcher):
    def __init__(self, config, detector):
        super().__init__(config)
        self.det = detector
    def _open_bull(self, bar_idx, entry_high, sl_level, entry_price, trigger='ema_reclaim'):
        if self.det.regime != "BULL": return
        super()._open_bull(bar_idx, entry_high, sl_level, entry_price, trigger)
    def _open_bear(self, bar_idx, entry_high, entry_low, sl_level, entry_price):
        if self.det.regime != "BEAR": return
        super()._open_bear(bar_idx, entry_high, entry_low, sl_level, entry_price)

def _excursion(entry_bar, entry_price, side, H, L, C, atr_arr, n, max_bars=50):
    """Track full price path after entry. Returns excursion data."""
    atr_e = atr_arr[entry_bar] if atr_arr[entry_bar] > 0 else 1.0
    mfe_pct = 0; mae_pct = 0; mfe_atr = 0; mae_atr = 0
    mfe_bar = 0; mae_bar = 0
    thresholds = [0.005, 0.008, 0.010, 0.013, 0.020, 0.030]
    reached = {t: False for t in thresholds}
    reached_bar = {t: None for t in thresholds}
    reached_before_sl = {t: {} for t in thresholds}  # {sl_level: bool}
    sl_levels = [0.010, 0.013, 0.015, 0.020]
    sl_hit_bar = {s: None for s in sl_levels}

    end = min(entry_bar + max_bars + 1, n)
    for j in range(entry_bar + 1, end):
        if side == "LONG":
            fav_pct = (H[j] - entry_price) / entry_price
            adv_pct = (entry_price - L[j]) / entry_price
        else:
            fav_pct = (entry_price - L[j]) / entry_price
            adv_pct = (H[j] - entry_price) / entry_price
        fav_atr = fav_pct * entry_price / atr_e
        adv_atr = adv_pct * entry_price / atr_e
        bars_in = j - entry_bar

        if fav_pct > mfe_pct: mfe_pct = fav_pct; mfe_bar = bars_in; mfe_atr = fav_atr
        if adv_pct > mae_pct: mae_pct = adv_pct; mae_bar = bars_in; mae_atr = adv_atr

        for t in thresholds:
            if not reached[t] and fav_pct >= t:
                reached[t] = True; reached_bar[t] = bars_in
        for s in sl_levels:
            if sl_hit_bar[s] is None and adv_pct >= s:
                sl_hit_bar[s] = bars_in

    # For each TP threshold × SL level: did TP hit before SL?
    for t in thresholds:
        for s in sl_levels:
            tp_bar = reached_bar[t]
            s_bar = sl_hit_bar[s]
            if tp_bar is not None and (s_bar is None or tp_bar <= s_bar):
                reached_before_sl[t][str(s)] = True
            else:
                reached_before_sl[t][str(s)] = False

    return {
        "mfe_pct": round(100*mfe_pct, 3), "mae_pct": round(100*mae_pct, 3),
        "mfe_atr": round(mfe_atr, 3), "mae_atr": round(mae_atr, 3),
        "mfe_bar": mfe_bar, "mae_bar": mae_bar,
        "reached": {f"{t*100:.1f}%": reached[t] for t in thresholds},
        "reached_bar": {f"{t*100:.1f}%": reached_bar[t] for t in thresholds},
        "reached_before_sl": {f"tp{t*100:.1f}_sl{s*100:.1f}": reached_before_sl[t][str(s)] for t in thresholds for s in sl_levels},
    }


@router.get("/excursion")
def v2_gated_excursion(
    symbol: str = Query("SOLUSDT"), days: int = Query(971),
    ema_period: int = Query(7), ema_slow: int = Query(20),
    tp_pct: float = Query(0.013), sl_pct: float = Query(0.013),
    bull_body: float = Query(0.5), bear_body: float = Query(0.6),
    fee_pct: float = Query(0.001), slippage_pct: float = Query(0.0005),
    swing_lb: int = Query(10), swing_atr: float = Query(0.5),
    mode: str = Query("B"),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < max(ema_period, ema_slow)+60: return {"error": f"Not enough: {len(rows)}"}
    O=np.array([r[1] for r in rows],dtype=float); H=np.array([r[2] for r in rows],dtype=float)
    L=np.array([r[3] for r in rows],dtype=float); C=np.array([r[4] for r in rows],dtype=float)
    V=np.array([r[5] for r in rows],dtype=float); n=len(rows)
    ef=_ema(C,ema_period); es=_ema(C,ema_slow); atr_arr=_atr(H,L,C,14)
    vahs,vals,pocs = _compute_va(H.tolist(),L.tolist(),C.tolist(),V.tolist(),50)

    cfg = Mode3BBCConfig()
    cfg.ema_period=ema_period; cfg.tp_pct=tp_pct; cfg.sl_pct=sl_pct
    cfg.bull_body_ratio_min=bull_body; cfg.bear_body_ratio_min=bear_body
    cfg.bull_mtf_15m_enabled=False; cfg.bear_mtf_15m_enabled=False
    cfg.sideways_mtf_15m_enabled=False; cfg.enable_sideways_trades=False
    cfg.direct_transition_enabled=True
    cfg.fee_pct_roundtrip=fee_pct; cfg.slippage_pct=slippage_pct

    det = ContinuationDetectorV2(ema_period, ema_slow, swing_lb, swing_atr, 3, min_pb_bars=1)

    if mode == "A":
        sw = Switcher(cfg)  # No gate
    else:
        sw = V2GatedSwitcher(cfg, detector=det)

    for i in range(n):
        det.process(i, O, H, L, C, ef, es, atr_arr)
        sw.process_candle(i, O[i], H[i], L[i], C[i], ef[i], vahs[i], vals[i], pocs[i])

    trades = sw.trades; nt = len(trades)
    cost = fee_pct + slippage_pct
    notional = 500.0

    # Per-trade excursion
    all_exc = []
    for t in trades:
        exc = _excursion(t.entry_bar, t.entry_price, t.side, H, L, C, atr_arr, n)
        exc["side"] = t.side; exc["tool"] = t.tool
        exc["gross_pnl_pct"] = round(t.pnl_pct*100 + cost*100, 3)  # add back cost
        exc["net_pnl_pct"] = round(t.pnl_pct*100, 3)
        exc["gross_pnl_usd"] = round((t.pnl_pct + cost) * notional, 2)
        exc["net_pnl_usd"] = round(t.pnl_pct * notional, 2)
        all_exc.append(exc)

    # Aggregates
    def _agg(excs, label="all"):
        if not excs: return {"n": 0}
        gross = sum(e["gross_pnl_usd"] for e in excs)
        net = sum(e["net_pnl_usd"] for e in excs)
        nn = len(excs)
        thresholds = ["0.5%","0.8%","1.0%","1.3%","2.0%","3.0%"]
        sl_levels = ["1.0%","1.3%","1.5%","2.0%"]
        reach_pct = {t: round(100*sum(1 for e in excs if e["reached"][t])/nn,1) for t in thresholds}
        avg_reach_bar = {}
        for t in thresholds:
            bars = [e["reached_bar"][t] for e in excs if e["reached_bar"][t] is not None]
            avg_reach_bar[t] = round(np.mean(bars),1) if bars else None
        # TP before SL matrix
        tp_before_sl = {}
        for t in thresholds:
            for s in sl_levels:
                key = f"tp{t[:-1]}_sl{s[:-1]}"
                tp_before_sl[f"{t}/{s}"] = round(100*sum(1 for e in excs if e["reached_before_sl"].get(key,False))/nn,1)
        return {
            "n": nn,
            "gross_pnl": round(gross,2), "net_pnl": round(net,2),
            "gross_exp": round(gross/nn,3), "net_exp": round(net/nn,3),
            "avg_mfe_pct": round(np.mean([e["mfe_pct"] for e in excs]),3),
            "avg_mae_pct": round(np.mean([e["mae_pct"] for e in excs]),3),
            "med_mfe_pct": round(float(np.median([e["mfe_pct"] for e in excs])),3),
            "med_mae_pct": round(float(np.median([e["mae_pct"] for e in excs])),3),
            "avg_mfe_atr": round(np.mean([e["mfe_atr"] for e in excs]),3),
            "avg_mae_atr": round(np.mean([e["mae_atr"] for e in excs]),3),
            "avg_mfe_bar": round(np.mean([e["mfe_bar"] for e in excs]),1),
            "avg_mae_bar": round(np.mean([e["mae_bar"] for e in excs]),1),
            "reached_pct": reach_pct,
            "avg_time_to_reach": avg_reach_bar,
            "tp_before_sl_pct": tp_before_sl,
        }

    result = {
        "symbol": symbol, "days": days, "candles": n, "mode": mode,
        "cost_pct": cost, "notional": notional,
        "all": _agg(all_exc),
    }

    # Per tool
    for tool in ["BULL","BEAR"]:
        te = [e for e in all_exc if e["tool"]==tool]
        if te: result[tool] = _agg(te)

    # Per side
    for side in ["LONG","SHORT"]:
        se = [e for e in all_exc if e["side"]==side]
        if se: result[side] = _agg(se)

    return result
