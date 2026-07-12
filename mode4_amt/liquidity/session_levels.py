"""
session_levels.py — Session High/Low Tracker
==============================================
Design Doc reference: §7.2.1 (BSL-3 kategori).

Trading sessions (UTC):
- Asia:   00:00 - 08:00
- London: 07:00 - 16:00
- NY:     13:00 - 22:00

Note: session overlap (London+NY 13:00-16:00 misalnya) tetap dihitung per session.

Untuk setiap session di rentang timestamps, catat H dan L. Level dari session
sebelumnya jadi liquidity magnet sampai ditembus.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple
import numpy as np
from datetime import datetime, timezone


class SessionType(str, Enum):
    ASIA = "ASIA"
    LONDON = "LONDON"
    NY = "NY"


@dataclass
class SessionLevel:
    """High dan Low dari satu session pada tanggal tertentu."""
    session: SessionType
    date: str              # ISO date YYYY-MM-DD (UTC)
    high: float
    low: float
    high_idx: int          # index candle where high occurred
    low_idx: int
    session_start_idx: int
    session_end_idx: int

    def __repr__(self):
        return (f"SessionLevel({self.session.value} {self.date} "
                f"H={self.high:.4f} L={self.low:.4f})")


# UTC hour ranges (start_hour, end_hour), end exclusive
SESSION_RANGES: Dict[SessionType, Tuple[int, int]] = {
    SessionType.ASIA: (0, 8),
    SessionType.LONDON: (7, 16),
    SessionType.NY: (13, 22),
}


def detect_session_levels(
    highs: np.ndarray,
    lows: np.ndarray,
    timestamps_ms: np.ndarray,
    sessions: List[SessionType] = None,
) -> List[SessionLevel]:
    """
    Deteksi H/L per session per hari.

    Args:
        highs, lows: OHLCV arrays (1h atau lower TF, harus include intraday)
        timestamps_ms: candle open timestamps in milliseconds (UTC)
        sessions: list of session types to track (default: semua)

    Returns:
        List of SessionLevel, sorted by session_start_idx.
    """
    if sessions is None:
        sessions = [SessionType.ASIA, SessionType.LONDON, SessionType.NY]

    n = len(highs)
    if n == 0 or n != len(lows) or n != len(timestamps_ms):
        return []

    highs = np.asarray(highs, dtype=np.float64)
    lows = np.asarray(lows, dtype=np.float64)
    timestamps_ms = np.asarray(timestamps_ms, dtype=np.int64)

    # Compute hour and date per candle
    hours = np.zeros(n, dtype=np.int32)
    dates = [""] * n
    for i in range(n):
        dt = datetime.fromtimestamp(int(timestamps_ms[i]) / 1000, tz=timezone.utc)
        hours[i] = dt.hour
        dates[i] = dt.strftime("%Y-%m-%d")

    results: List[SessionLevel] = []

    for session in sessions:
        start_h, end_h = SESSION_RANGES[session]
        # Group by date, then find candles within session hour range
        current_date = None
        session_start_idx = -1
        for i in range(n):
            in_session = start_h <= hours[i] < end_h
            if in_session:
                if dates[i] != current_date:
                    # New session starts
                    if session_start_idx >= 0 and current_date is not None:
                        # Close previous session
                        end_idx = i - 1
                        seg_h = highs[session_start_idx:end_idx + 1]
                        seg_l = lows[session_start_idx:end_idx + 1]
                        h_idx_local = int(np.argmax(seg_h))
                        l_idx_local = int(np.argmin(seg_l))
                        results.append(SessionLevel(
                            session=session,
                            date=current_date,
                            high=float(seg_h[h_idx_local]),
                            low=float(seg_l[l_idx_local]),
                            high_idx=session_start_idx + h_idx_local,
                            low_idx=session_start_idx + l_idx_local,
                            session_start_idx=session_start_idx,
                            session_end_idx=end_idx,
                        ))
                    current_date = dates[i]
                    session_start_idx = i
            else:
                if session_start_idx >= 0 and current_date is not None:
                    # Session ended
                    end_idx = i - 1
                    seg_h = highs[session_start_idx:end_idx + 1]
                    seg_l = lows[session_start_idx:end_idx + 1]
                    h_idx_local = int(np.argmax(seg_h))
                    l_idx_local = int(np.argmin(seg_l))
                    results.append(SessionLevel(
                        session=session,
                        date=current_date,
                        high=float(seg_h[h_idx_local]),
                        low=float(seg_l[l_idx_local]),
                        high_idx=session_start_idx + h_idx_local,
                        low_idx=session_start_idx + l_idx_local,
                        session_start_idx=session_start_idx,
                        session_end_idx=end_idx,
                    ))
                    current_date = None
                    session_start_idx = -1

        # Handle open session at end of array
        if session_start_idx >= 0 and current_date is not None:
            end_idx = n - 1
            seg_h = highs[session_start_idx:end_idx + 1]
            seg_l = lows[session_start_idx:end_idx + 1]
            h_idx_local = int(np.argmax(seg_h))
            l_idx_local = int(np.argmin(seg_l))
            results.append(SessionLevel(
                session=session,
                date=current_date,
                high=float(seg_h[h_idx_local]),
                low=float(seg_l[l_idx_local]),
                high_idx=session_start_idx + h_idx_local,
                low_idx=session_start_idx + l_idx_local,
                session_start_idx=session_start_idx,
                session_end_idx=end_idx,
            ))

    results.sort(key=lambda x: x.session_start_idx)
    return results


__all__ = ["SessionType", "SessionLevel", "SESSION_RANGES", "detect_session_levels"]
