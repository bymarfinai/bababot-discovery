"""Filtered Switcher — V0-V4 pre-entry filters on top of Full Switcher.

Subclasses mode3_bbc.Switcher. Overrides _open_bull/_open_bear to apply
filters BEFORE position creation. State machine, WAIT_SEE, direct transition
all run unmodified from parent.

V0: No filter (baseline = exact Full Switcher)
V1: EMA slope positive (both fast + slow rising for BULL)
V2: V1 + trend structure (HH/HL for BULL, LL/LH for BEAR)
V3: V2 + room to resistance (swing high/low distance > TP + fee)
V4: V3 + follow-through (candidate on N, entry on N+1 close if confirmed)

GET /filtered_switcher/backtest?symbol=SOLUSDT&days=971&version=0
    Must match Full Switcher baseline: 5667 trades, PnL ~-$4438.75
"""
import os, sqlite3, numpy as np
from fastapi import APIRouter, Query
from datetime import datetime
from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Switcher, Position

router = APIRouter(prefix="/filtered_switcher", tags=["filtered_switcher"])
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

def _compute_va(highs, lows, closes, volumes, window, phi=85, plo=15):
    n = len(highs); vahs=[None]*n; vals=[None]*n; pocs=[None]*n
    for i in range(window, n):
        hs=highs[i-window:i]; ls=lows[i-window:i]; cs=closes[i-window:i]
        vahs[i]=float(np.percentile(hs,phi)); vals[i]=float(np.percentile(ls,plo))
        vs=volumes[i-window:i]; tv=sum(vs) or 1
        tp=[(hs[j]+ls[j]+cs[j])/3 for j in range(window)]
        pocs[i]=sum(tp[j]*vs[j] for j in range(window))/tv
    return vahs, vals, pocs

class FilteredSwitcher(Switcher):
    def __init__(self, config, version=0, ema_fast_s=None, ema_slow_s=None,
                 all_H=None, all_L=None, all_C=None,
                 slope_lb=3, struct_lb=5, tp_for_room=0.013, fee_for_room=0.0015):
        super().__init__(config)
        self.version = version
        self._ef = ema_fast_s; self._es = ema_slow_s
        self._H = all_H; self._L = all_L; self._C = all_C
        self._slope_lb = slope_lb; self._struct_lb = struct_lb
        self._room_min = tp_for_room + fee_for_room
        self._pending_v4 = None; self._v4_open_this_bar = None
        self.fstats = {"attempts":0, "slope_blocked":0, "struct_blocked":0,
                       "room_blocked":0, "ft_blocked":0, "ft_confirmed":0, "passed":0}

    def _pre_entry_ok(self, bar_idx, side):
        if self.version < 1: return True
        i = bar_idx
        if self.version >= 1:
            lb = self._slope_lb
            if i >= lb and self._ef is not None and self._es is not None:
                if side == "LONG":
                    ok = (self._ef[i] > self._ef[i-lb]) and (self._es[i] > self._es[i-lb])
                else:
                    ok = (self._ef[i] < self._ef[i-lb]) and (self._es[i] < self._es[i-lb])
                if not ok: self.fstats["slope_blocked"] += 1; return False
        if self.version >= 2:
            slb = self._struct_lb
            if i >= slb and self._H is not None:
                rh = self._H[i-slb:i+1]; rl = self._L[i-slb:i+1]
                if side == "LONG":
                    ok = (self._H[i] >= float(np.percentile(rh,50))) and (self._L[i] >= float(np.min(rl[:-1])))
                else:
                    ok = (self._L[i] <= float(np.percentile(rl,50))) and (self._H[i] <= float(np.max(rh[:-1])))
                if not ok: self.fstats["struct_blocked"] += 1; return False
        if self.version >= 3:
            if i >= 20 and self._H is not None:
                c = self._C[i]
                if side == "LONG":
                    room = (float(np.max(self._H[i-20:i])) - c) / c
                else:
                    room = (c - float(np.min(self._L[i-20:i]))) / c
                if room < self._room_min: self.fstats["room_blocked"] += 1; return False
        return True

    def _open_bull(self, bar_idx, entry_high, sl_level, entry_price, trigger='ema_reclaim'):
        self.fstats["attempts"] += 1
        if not self._pre_entry_ok(bar_idx, "LONG"): return
        if self.version >= 4:
            self._pending_v4 = {"side":"LONG", "bar":bar_idx,
                "sig_high": float(self._H[bar_idx]) if self._H is not None else entry_high,
                "trigger": trigger}
            return
        self.fstats["passed"] += 1
        super()._open_bull(bar_idx, entry_high, sl_level, entry_price, trigger)

    def _open_bear(self, bar_idx, entry_high, entry_low, sl_level, entry_price):
        self.fstats["attempts"] += 1
        if not self._pre_entry_ok(bar_idx, "SHORT"): return
        if self.version >= 4:
            self._pending_v4 = {"side":"SHORT", "bar":bar_idx,
                "sig_low": float(self._L[bar_idx]) if self._L is not None else entry_low,
                "trigger": "ema_reject"}
            return
        self.fstats["passed"] += 1
        super()._open_bear(bar_idx, entry_high, entry_low, sl_level, entry_price)

    def process_candle(self, bar_idx, o, h, l, c, ema20, vah, val, poc=None):
        self._v4_open_this_bar = None
        if self._pending_v4 is not None and self.position is None:
            p = self._pending_v4
            if p["side"] == "LONG":
                ft_ok = (c > ema20) and (h > p["sig_high"])
            else:
                ft_ok = (c < ema20) and (l < p["sig_low"])
            self._pending_v4 = None
            if ft_ok:
                self._v4_open_this_bar = {"side":p["side"], "bar":bar_idx,
                    "o":o,"h":h,"l":l,"c":c,"ema":ema20,
                    "candidate_bar":p["bar"], "trigger":p.get("trigger","")}
                self.fstats["ft_confirmed"] += 1
            else:
                self.fstats["ft_blocked"] += 1

        super().process_candle(bar_idx, o, h, l, c, ema20, vah, val, poc)

        if self._v4_open_this_bar is not None and self.position is None:
            v = self._v4_open_this_bar
            ep = v["c"]
            if v["side"] == "LONG":
                sl = ep*(1-self.config.sl_pct) if self.config.sl_pct > 0 else v["l"]
                tp = ep*(1+self.config.tp_pct)
                self.position = Position(tool='BULL', side='LONG', entry_price=ep,
                    entry_bar=bar_idx, entry_high=v["h"], entry_low=v["l"],
                    sl_level=sl, original_sl=sl, tp_level=tp,
                    peak_high=v["h"], trough_low=v["l"], ema_at_entry=v["ema"],
                    entry_trigger='v4_ft')
                self._bull_entries += 1
            else:
                bsl = self.config.get_bear_sl_pct()
                sl = ep*(1+bsl) if bsl > 0 else v["h"]
                tp = ep*(1-self.config.get_bear_tp_pct())
                self.position = Position(tool='BEAR', side='SHORT', entry_price=ep,
                    entry_bar=bar_idx, entry_high=v["h"], entry_low=v["l"],
                    sl_level=sl, original_sl=sl, tp_level=tp,
                    peak_high=v["h"], trough_low=v["l"], ema_at_entry=v["ema"])
                self._bear_entries += 1
            self.fstats["passed"] += 1
            self._action_taken_this_bar = True
            self._v4_open_this_bar = None

@router.get("/backtest")
def filtered_switcher_backtest(
    symbol: str = Query("SOLUSDT"), days: int = Query(971, ge=1, le=1500),
    version: int = Query(0, ge=0, le=4),
    ema_period: int = Query(7, ge=3, le=100), ema_slow: int = Query(20, ge=5, le=200),
    tp_pct: float = Query(0.013, ge=0.001, le=0.10), sl_pct: float = Query(0.013, ge=0.001, le=0.10),
    bull_body: float = Query(0.5, ge=0.0, le=1.0), bear_body: float = Query(0.6, ge=0.0, le=1.0),
    fee_pct: float = Query(0.001), slippage_pct: float = Query(0.0005),
    slope_lb: int = Query(3, ge=1, le=10), struct_lb: int = Query(5, ge=3, le=20),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < max(ema_period, ema_slow) + 60:
        return {"error": f"Not enough candles: {len(rows)}"}

    O = np.array([r[1] for r in rows], dtype=float)
    H = np.array([r[2] for r in rows], dtype=float)
    L = np.array([r[3] for r in rows], dtype=float)
    C = np.array([r[4] for r in rows], dtype=float)
    V = np.array([r[5] for r in rows], dtype=float)

    ema_f = _ema(C, ema_period); ema_s = _ema(C, ema_slow)
    vahs, vals, pocs = _compute_va(H.tolist(), L.tolist(), C.tolist(), V.tolist(), 50)

    cfg = Mode3BBCConfig()
    cfg.ema_period = ema_period; cfg.tp_pct = tp_pct; cfg.sl_pct = sl_pct
    cfg.bull_body_ratio_min = bull_body; cfg.bear_body_ratio_min = bear_body
    cfg.bull_mtf_15m_enabled = False; cfg.bear_mtf_15m_enabled = False
    cfg.sideways_mtf_15m_enabled = False; cfg.enable_sideways_trades = False
    cfg.direct_transition_enabled = True
    cfg.fee_pct_roundtrip = fee_pct; cfg.slippage_pct = slippage_pct

    sw = FilteredSwitcher(cfg, version=version,
        ema_fast_s=ema_f, ema_slow_s=ema_s, all_H=H, all_L=L, all_C=C,
        slope_lb=slope_lb, struct_lb=struct_lb,
        tp_for_room=tp_pct, fee_for_room=fee_pct+slippage_pct)

    for i in range(len(rows)):
        sw.process_candle(i, O[i], H[i], L[i], C[i], ema_f[i], vahs[i], vals[i], pocs[i])

    trades = sw.trades; n = len(trades)
    wins = [t for t in trades if t.pnl_usd > 0]
    total_pnl = sum(t.pnl_usd for t in trades)
    wr = round(100*len(wins)/n, 2) if n else 0

    tool_stats = {}
    for tool in ['BULL','BEAR','SIDEWAYS']:
        tt = [t for t in trades if t.tool == tool]
        if tt:
            tw = [t for t in tt if t.pnl_usd > 0]
            tool_stats[tool] = {"count":len(tt), "wr_pct":round(100*len(tw)/len(tt),2), "pnl_usd":round(sum(t.pnl_usd for t in tt),2)}

    side_stats = {}
    for sn in ['LONG','SHORT']:
        st = [t for t in trades if t.side == sn]
        if st:
            stw = [t for t in st if t.pnl_usd > 0]
            side_stats[sn] = {"count":len(st), "wr_pct":round(100*len(stw)/len(st),2), "pnl_usd":round(sum(t.pnl_usd for t in st),2)}

    exit_bd = {}
    for t in trades: exit_bd[t.exit_type] = exit_bd.get(t.exit_type, 0) + 1

    eq=0;pk=0;mdd=0;ms=0;cs=0
    for t in trades:
        eq+=t.pnl_usd
        if eq>pk:pk=eq
        dd=pk-eq
        if dd>mdd:mdd=dd
        if t.pnl_usd<=0:cs+=1;ms=max(ms,cs)
        else:cs=0

    same_bar = sum(1 for t in trades if t.entry_bar == t.exit_bar)

    trade_list = [{"tool":t.tool,"side":t.side,"entry_price":round(t.entry_price,4),
        "exit_price":round(t.exit_price,4),"entry_bar":t.entry_bar,"exit_bar":t.exit_bar,
        "exit_type":t.exit_type,"pnl_pct":round(t.pnl_pct*100,3),"pnl_usd":round(t.pnl_usd,2),
        "entry_trigger":t.entry_trigger,"ema_at_entry":round(t.ema_at_entry,4)} for t in trades]

    return {
        "symbol":symbol, "days":days, "candles":len(rows), "version":f"V{version}",
        "config":{"ema_period":ema_period,"ema_slow":ema_slow,"tp_pct":tp_pct,"sl_pct":sl_pct,
            "bull_body":bull_body,"bear_body":bear_body,"fee_pct":fee_pct,"slippage_pct":slippage_pct,
            "mtf":False,"sideways_trades":False,"direct_transition":True,"slope_lb":slope_lb,"struct_lb":struct_lb},
        "filter_stats":sw.fstats,
        "summary":{"total_trades":n,"wins":len(wins),"losses":n-len(wins),"win_rate_pct":wr,
            "total_pnl_usd":round(total_pnl,2),"max_drawdown_usd":round(mdd,2),"max_loss_streak":ms,
            "same_bar_exits":same_bar,"exit_breakdown":exit_bd,
            "expectancy_usd":round(total_pnl/n,3) if n else 0},
        "per_tool":tool_stats, "per_side":side_stats, "trades":trade_list,
    }
