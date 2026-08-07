"""V2-Gated Switcher — diagnostic integration.

Mode A: Full Switcher baseline (no gate)
Mode B: V2 regime gate (LONG only if V2=BULL, SHORT only if V2=BEAR)
Mode C: V2 regime + pullback context (must be in/just-exited PULLBACK phase)

GET /v2_gated/backtest?symbol=SOLUSDT&days=971&mode=B
"""
import os, sqlite3, numpy as np, math
from fastapi import APIRouter, Query
from datetime import datetime, timezone
from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Switcher, Position
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v2_gated", tags=["v2_gated"])
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

def _compute_va(H, L, C, V, window):
    n = len(H); vahs=[None]*n; vals=[None]*n; pocs=[None]*n
    for i in range(window, n):
        hs=H[i-window:i]; ls=L[i-window:i]; cs=C[i-window:i]
        vahs[i]=float(np.percentile(hs,85)); vals[i]=float(np.percentile(ls,15))
        vs=V[i-window:i]; tv=sum(vs) or 1
        tp=[(hs[j]+ls[j]+cs[j])/3 for j in range(window)]
        pocs[i]=sum(tp[j]*vs[j] for j in range(window))/tv
    return vahs, vals, pocs


class V2GatedSwitcher(Switcher):
    def __init__(self, config, mode="A", detector=None):
        super().__init__(config)
        self.mode = mode
        self.det = detector
        self.gate_stats = {"attempts": 0, "allowed": 0, "blocked_regime": 0, "blocked_phase": 0}

    def _open_bull(self, bar_idx, entry_high, sl_level, entry_price, trigger='ema_reclaim'):
        self.gate_stats["attempts"] += 1
        if self.mode != "A" and self.det:
            if self.det.regime != "BULL":
                self.gate_stats["blocked_regime"] += 1; return
            if self.mode == "C":
                # Must be in PULLBACK phase or just fired continuation event
                if self.det.phase not in ("PULLBACK", "TREND") or not self.det.events:
                    if self.det.phase != "PULLBACK":
                        self.gate_stats["blocked_phase"] += 1; return
        self.gate_stats["allowed"] += 1
        super()._open_bull(bar_idx, entry_high, sl_level, entry_price, trigger)

    def _open_bear(self, bar_idx, entry_high, entry_low, sl_level, entry_price):
        self.gate_stats["attempts"] += 1
        if self.mode != "A" and self.det:
            if self.det.regime != "BEAR":
                self.gate_stats["blocked_regime"] += 1; return
            if self.mode == "C":
                if self.det.phase not in ("PULLBACK", "TREND") or not self.det.events:
                    if self.det.phase != "PULLBACK":
                        self.gate_stats["blocked_phase"] += 1; return
        self.gate_stats["allowed"] += 1
        super()._open_bear(bar_idx, entry_high, entry_low, sl_level, entry_price)


@router.get("/backtest")
def v2_gated_backtest(
    symbol: str = Query("SOLUSDT"), days: int = Query(971),
    mode: str = Query("B"),
    ema_period: int = Query(7), ema_slow: int = Query(20),
    tp_pct: float = Query(0.013), sl_pct: float = Query(0.013),
    bull_body: float = Query(0.5), bear_body: float = Query(0.6),
    fee_pct: float = Query(0.001), slippage_pct: float = Query(0.0005),
    swing_lb: int = Query(10), swing_atr: float = Query(0.5),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < max(ema_period, ema_slow) + 60:
        return {"error": f"Not enough: {len(rows)}"}

    O = np.array([r[1] for r in rows], dtype=float)
    H = np.array([r[2] for r in rows], dtype=float)
    L = np.array([r[3] for r in rows], dtype=float)
    C = np.array([r[4] for r in rows], dtype=float)
    V = np.array([r[5] for r in rows], dtype=float)
    n = len(rows)
    ef = _ema(C, ema_period); es = _ema(C, ema_slow)
    atr_arr = _atr(H, L, C, 14)
    vahs, vals, pocs = _compute_va(H.tolist(), L.tolist(), C.tolist(), V.tolist(), 50)

    cfg = Mode3BBCConfig()
    cfg.ema_period = ema_period; cfg.tp_pct = tp_pct; cfg.sl_pct = sl_pct
    cfg.bull_body_ratio_min = bull_body; cfg.bear_body_ratio_min = bear_body
    cfg.bull_mtf_15m_enabled = False; cfg.bear_mtf_15m_enabled = False
    cfg.sideways_mtf_15m_enabled = False; cfg.enable_sideways_trades = False
    cfg.direct_transition_enabled = True
    cfg.fee_pct_roundtrip = fee_pct; cfg.slippage_pct = slippage_pct

    det = ContinuationDetectorV2(ema_period, ema_slow, swing_lb, swing_atr, 3, min_pb_bars=1)
    sw = V2GatedSwitcher(cfg, mode=mode, detector=det)
    notional = 10.0 * 50.0

    for i in range(n):
        # V2 detector processes FIRST (updates regime/phase before switcher entry decision)
        det.process(i, O, H, L, C, ef, es, atr_arr)
        # Then switcher processes (entry gated by V2 state)
        sw.process_candle(i, O[i], H[i], L[i], C[i], ef[i], vahs[i], vals[i], pocs[i])

    trades = sw.trades; nt = len(trades)
    wins = [t for t in trades if t.pnl_usd > 0]
    total_pnl = sum(t.pnl_usd for t in trades)
    wr = round(100*len(wins)/nt, 2) if nt else 0

    # Per-trade quality metrics
    trade_metrics = []
    for t in trades:
        eb = t.entry_bar; ep = t.entry_price
        atr_e = atr_arr[eb] if atr_arr[eb] > 0 else 1
        # MFE/MAE over trade duration
        xb = t.exit_bar; mfe = 0; mae = 0
        for j in range(eb+1, min(xb+1, n)):
            if t.side == "LONG":
                fav = (H[j] - ep) / atr_e
                adv = (ep - L[j]) / atr_e
            else:
                fav = (ep - L[j]) / atr_e
                adv = (H[j] - ep) / atr_e
            if fav > mfe: mfe = fav
            if adv > mae: mae = adv
        # EMA hold
        hold_bars = min(4, xb - eb)
        if t.side == "LONG":
            ema_hold = all(C[j] > es[j] for j in range(eb+1, min(eb+hold_bars+1, n)))
        else:
            ema_hold = all(C[j] < es[j] for j in range(eb+1, min(eb+hold_bars+1, n)))
        # Protected intact (use protected level from detector... approximate)
        if t.side == "LONG":
            prot = float(min(L[max(0,eb-20):eb+1]))
            prot_ok = all(L[j] >= prot for j in range(eb+1, min(eb+hold_bars+1, n)))
        else:
            prot = float(max(H[max(0,eb-20):eb+1]))
            prot_ok = all(H[j] <= prot for j in range(eb+1, min(eb+hold_bars+1, n)))
        trade_metrics.append({"mfe": round(mfe,3), "mae": round(mae,3),
                              "ema_hold": ema_hold, "prot_ok": prot_ok})

    # Aggregate quality
    avg_mfe = round(np.mean([m["mfe"] for m in trade_metrics]),3) if trade_metrics else 0
    avg_mae = round(np.mean([m["mae"] for m in trade_metrics]),3) if trade_metrics else 0
    ema_hold_pct = round(100*sum(1 for m in trade_metrics if m["ema_hold"])/len(trade_metrics),1) if trade_metrics else 0
    prot_ok_pct = round(100*sum(1 for m in trade_metrics if m["prot_ok"])/len(trade_metrics),1) if trade_metrics else 0

    # Per side/tool
    tool_stats = {}
    for tool in ["BULL","BEAR"]:
        tt = [t for t in trades if t.tool == tool]
        tw = [t for t in tt if t.pnl_usd > 0]
        tm = [trade_metrics[i] for i, t in enumerate(trades) if t.tool == tool]
        if tt:
            tool_stats[tool] = {
                "count": len(tt), "wr": round(100*len(tw)/len(tt),1),
                "pnl": round(sum(t.pnl_usd for t in tt),2),
                "avg_mfe": round(np.mean([m["mfe"] for m in tm]),3),
                "avg_mae": round(np.mean([m["mae"] for m in tm]),3),
                "ema_hold_pct": round(100*sum(1 for m in tm if m["ema_hold"])/len(tm),1),
                "prot_ok_pct": round(100*sum(1 for m in tm if m["prot_ok"])/len(tm),1),
            }

    # Drawdown
    eq=0;pk=0;mdd=0;ms=0;cs=0
    for t in trades:
        eq+=t.pnl_usd
        if eq>pk:pk=eq
        dd=pk-eq
        if dd>mdd:mdd=dd
        if t.pnl_usd<=0:cs+=1;ms=max(ms,cs)
        else:cs=0

    # Rolling thirds
    third = n//3
    rolling = {}
    for wn, ws, we in [("early",0,third),("mid",third,2*third),("late",2*third,n)]:
        wt = [t for t in trades if ws <= t.entry_bar < we]
        ww = [t for t in wt if t.pnl_usd > 0]
        wm = [trade_metrics[i] for i,t in enumerate(trades) if ws <= t.entry_bar < we]
        rolling[wn] = {
            "trades": len(wt), "wr": round(100*len(ww)/len(wt),1) if wt else 0,
            "pnl": round(sum(t.pnl_usd for t in wt),2),
            "ema_hold": round(100*sum(1 for m in wm if m["ema_hold"])/len(wm),1) if wm else 0,
        }

    return {
        "symbol": symbol, "days": days, "candles": n, "mode": mode,
        "gate_stats": sw.gate_stats,
        "summary": {
            "trades": nt, "wins": len(wins), "wr": wr,
            "pnl": round(total_pnl,2), "expectancy": round(total_pnl/nt,3) if nt else 0,
            "max_dd": round(mdd,2), "max_ls": ms,
        },
        "quality": {
            "avg_mfe_atr": avg_mfe, "avg_mae_atr": avg_mae,
            "ema_hold_pct": ema_hold_pct, "prot_ok_pct": prot_ok_pct,
        },
        "per_tool": tool_stats,
        "rolling": rolling,
    }
