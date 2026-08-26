"""Causal raw-5m signal adapters for frozen B27DQ LONG + SHORT20.

These adapters are shadow-safe and contain no exchange I/O. A confirmation can
only be learned at a completed-bar close; an entry candidate can only be emitted
on the following 5m bar-open event.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import math
import numpy as np
import pandas as pd

BAR5 = pd.Timedelta(minutes=5)
REF_DUR = pd.Timedelta(hours=5, minutes=30)
EXEC_DUR = pd.Timedelta(hours=6, minutes=30)
REF_BARS = 66
EXEC_BARS = 78

LONG_ZONE_CLOCKS = {
    'ALT_0330': 210,
    'RAW_0530': 330,
    'LONDON': 480,
    'RAW_2330': 1410,
}
SHORT20_CLOCK = 1200


@dataclass(frozen=True)
class EntrySignal:
    side: str
    source: str
    anchor_date_utc: str
    entry_ts: pd.Timestamp
    entry_px: float
    confirmation_bar_start: pd.Timestamp
    H: float
    L: float
    R: float
    entry_level: float
    stop_level: float
    target_level: float
    touch_elapsed_min: float

    @property
    def identity(self) -> str:
        return f'{self.side}|{self.source}|{self.entry_ts.isoformat()}'


def _validate_ref(ref: pd.DataFrame, ref_start: pd.Timestamp, ref_end: pd.Timestamp):
    if len(ref) != REF_BARS:
        raise ValueError(f'reference needs {REF_BARS} bars, got {len(ref)}')
    if ref.index[0] != ref_start or ref.index[-1] + BAR5 != ref_end:
        raise ValueError('reference bars do not exactly cover frozen window')


def _range_features(ref: pd.DataFrame, ref_start: pd.Timestamp):
    H = float(ref.high.max()); L = float(ref.low.min())
    if not (math.isfinite(H) and math.isfinite(L) and H > L):
        raise ValueError('invalid frozen range')
    hv = ref.high.to_numpy(float); lv = ref.low.to_numpy(float)
    hi = np.flatnonzero(np.isclose(hv, H, rtol=0.0, atol=max(1e-10, abs(H)*1e-12)))
    li = np.flatnonzero(np.isclose(lv, L, rtol=0.0, atol=max(1e-10, abs(L)*1e-12)))
    if not len(hi) or not len(li):
        raise ValueError('range extreme occurrence missing')
    hts = ref.index[int(hi[0])]; lts = ref.index[int(li[0])]
    completion = max(hts, lts)
    completion_elapsed = float((completion-ref_start)/pd.Timedelta(minutes=1))
    return H, L, H-L, completion_elapsed


class _BaseSession:
    def __init__(self, source: str, anchor: pd.Timestamp, ref: pd.DataFrame):
        self.source = source
        self.anchor = pd.Timestamp(anchor)
        if self.anchor.tzinfo is None:
            self.anchor = self.anchor.tz_localize('UTC')
        else:
            self.anchor = self.anchor.tz_convert('UTC')
        self.ref_start = ref.index[0]
        self.ref_end = self.ref_start + REF_DUR
        self.exec_start = self.ref_end
        self.exec_end = self.exec_start + EXEC_DUR
        _validate_ref(ref, self.ref_start, self.ref_end)
        self.H, self.L, self.R, self.range_completion_elapsed_min = _range_features(ref, self.ref_start)
        self.state = 'SEEK_K1'
        self.pending_entry_ts: Optional[pd.Timestamp] = None
        self.pending_confirmation_bar: Optional[pd.Timestamp] = None
        self.pending_touch_elapsed: Optional[float] = None
        self.last_open_ts: Optional[pd.Timestamp] = None
        self.last_close_ts: Optional[pd.Timestamp] = None
        self.emitted = False

    def _event_ts(self, value) -> pd.Timestamp:
        t = pd.Timestamp(value)
        return t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')

    def _dedup_open(self, ts) -> bool:
        t = self._event_ts(ts)
        if self.last_open_ts is not None:
            if t < self.last_open_ts: raise RuntimeError('out-of-order bar open')
            if t == self.last_open_ts: return True
        self.last_open_ts = t
        return False

    def _dedup_close(self, ts) -> bool:
        t = self._event_ts(ts)
        if self.last_close_ts is not None:
            if t < self.last_close_ts: raise RuntimeError('out-of-order bar close')
            if t == self.last_close_ts: return True
        self.last_close_ts = t
        return False

    def _inside_exec(self, ts) -> bool:
        t = self._event_ts(ts)
        return self.exec_start <= t < self.exec_end


class LongF85Session(_BaseSession):
    def __init__(self, source: str, anchor: pd.Timestamp, ref: pd.DataFrame):
        if source not in LONG_ZONE_CLOCKS:
            raise ValueError(source)
        super().__init__(source, anchor, ref)
        self.F85 = self.L + 0.85*self.R
        self.F35 = self.L + 0.35*self.R
        self.E20 = self.H + 0.20*self.R
        self.hi_touching = False; self.lo_touching = False
        self.hi_visits = 0; self.lo_visits = 0
        if source in ('RAW_0530','RAW_2330') and self.range_completion_elapsed_min < 165.0:
            self.state = 'FILTERED_RANGE_COMPLETION'

    def on_bar_open(self, bar_start, open_px: float) -> Optional[EntrySignal]:
        ts=self._event_ts(bar_start)
        if self._dedup_open(ts): return None
        if self.state!='PENDING_ENTRY' or self.pending_entry_ts is None: return None
        if ts < self.pending_entry_ts: return None
        if ts > self.pending_entry_ts or ts >= self.exec_end:
            self.state='DONE'; return None
        px=float(open_px); self.state='DONE'
        if not (self.F35 < px < self.H): return None
        self.emitted=True
        return EntrySignal('LONG',self.source,str(self.anchor.date()),ts,px,self.pending_confirmation_bar,
                           self.H,self.L,self.R,self.F85,self.F35,self.E20,float(self.pending_touch_elapsed))

    def on_bar_close(self, bar_start, open_px: float, high: float, low: float, close: float):
        ts=self._event_ts(bar_start)
        if self._dedup_close(ts): return
        if not self._inside_exec(ts) or self.state in ('DONE','FILTERED_RANGE_COMPLETION','PENDING_ENTRY'): return
        hi=float(high); lo=float(low); cl=float(close)

        if self.state=='SEEK_K1':
            if cl>self.H or cl<self.L:
                self.state='DONE'; return
            hit_hi=hi>=self.H and cl<=self.H
            hit_lo=lo<=self.L and cl>=self.L
            if hit_hi and hit_lo:
                self.state='DONE'; return
            if hit_hi and not self.hi_touching:
                self.hi_visits += 1
                if self.hi_visits==1 and self.lo_visits==0:
                    self.state='K1_EPISODE'; return
            if hit_lo and not self.lo_touching:
                self.lo_visits += 1
            self.hi_touching=bool(hit_hi); self.lo_touching=bool(hit_lo)
            return

        if self.state=='K1_EPISODE':
            if cl>self.H or cl<self.L:
                self.state='DONE'; return
            if hi>=self.H and cl<=self.H:
                return
            self.state='SEEK_F_TOUCH'; return

        if self.state=='SEEK_F_TOUCH':
            # H2/opposite break owns this completed bar before any F85 touch.
            if hi>=self.H or cl<self.L:
                self.state='DONE'; return
            if lo<=self.F85<=hi:
                elapsed=float((ts-self.exec_start)/pd.Timedelta(minutes=1))
                if self.source=='ALT_0330' and elapsed>195.0:
                    self.state='DONE'; return
                if cl>self.F85:
                    nxt=ts+BAR5
                    if nxt>=self.exec_end:
                        self.state='DONE'; return
                    self.pending_entry_ts=nxt
                    self.pending_confirmation_bar=ts
                    self.pending_touch_elapsed=elapsed
                    self.state='PENDING_ENTRY'
                else:
                    # Frozen research uses only the first F85 touch.
                    self.state='DONE'


class ShortF15Session(_BaseSession):
    def __init__(self, anchor: pd.Timestamp, ref: pd.DataFrame):
        super().__init__('SHORT_2000',anchor,ref)
        self.F15=self.L+0.15*self.R
        self.F65=self.L+0.65*self.R
        self.E20_DOWN=self.L-0.20*self.R
        self.hi_touching=False; self.lo_touching=False
        self.hi_visits=0; self.lo_visits=0

    def on_bar_open(self, bar_start, open_px: float) -> Optional[EntrySignal]:
        ts=self._event_ts(bar_start)
        if self._dedup_open(ts): return None
        if self.state!='PENDING_ENTRY' or self.pending_entry_ts is None: return None
        if ts<self.pending_entry_ts: return None
        if ts>self.pending_entry_ts or ts>=self.exec_end:
            self.state='DONE'; return None
        px=float(open_px); self.state='DONE'
        if not (self.L < px < self.F65): return None
        self.emitted=True
        return EntrySignal('SHORT',self.source,str(self.anchor.date()),ts,px,self.pending_confirmation_bar,
                           self.H,self.L,self.R,self.F15,self.F65,self.E20_DOWN,float(self.pending_touch_elapsed))

    def on_bar_close(self, bar_start, open_px: float, high: float, low: float, close: float):
        ts=self._event_ts(bar_start)
        if self._dedup_close(ts): return
        if not self._inside_exec(ts) or self.state in ('DONE','PENDING_ENTRY'): return
        hi=float(high); lo=float(low); cl=float(close)

        if self.state=='SEEK_K1':
            if cl>self.H or cl<self.L:
                self.state='DONE'; return
            hit_hi=hi>=self.H and cl<=self.H
            hit_lo=lo<=self.L and cl>=self.L
            if hit_hi and hit_lo:
                self.state='DONE'; return
            if hit_lo and not self.lo_touching:
                self.lo_visits += 1
                if self.lo_visits==1 and self.hi_visits==0:
                    self.state='K1_EPISODE'; return
            if hit_hi and not self.hi_touching:
                self.hi_visits += 1
            self.hi_touching=bool(hit_hi); self.lo_touching=bool(hit_lo)
            return

        if self.state=='K1_EPISODE':
            if cl<self.L or cl>self.H:
                self.state='DONE'; return
            if lo<=self.L and cl>=self.L:
                return
            self.state='SEEK_F_TOUCH'; return

        if self.state=='SEEK_F_TOUCH':
            # Low H2/opposite High break owns this bar before any F15 touch.
            if lo<=self.L or cl>self.H:
                self.state='DONE'; return
            if lo<=self.F15<=hi:
                elapsed=float((ts-self.exec_start)/pd.Timedelta(minutes=1))
                if cl<self.F15:
                    nxt=ts+BAR5
                    if nxt>=self.exec_end:
                        self.state='DONE'; return
                    self.pending_entry_ts=nxt
                    self.pending_confirmation_bar=ts
                    self.pending_touch_elapsed=elapsed
                    self.state='PENDING_ENTRY'
                else:
                    self.state='DONE'


def replay_session(adapter: _BaseSession, exe: pd.DataFrame):
    """Historical event replay preserving live ordering: bar-open, then bar-close."""
    out=[]
    for ts,r in exe.iterrows():
        sig=adapter.on_bar_open(ts,float(r.open))
        if sig is not None: out.append(sig)
        adapter.on_bar_close(ts,float(r.open),float(r.high),float(r.low),float(r.close))
    return out
