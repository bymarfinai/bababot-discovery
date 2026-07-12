"""
volume_profile.py — Volume Profile Engine
==========================================
Menghitung Point of Control (POC), Value Area High (VAH), Value Area Low (VAL),
serta High/Low Volume Nodes (HVN/LVN) dari OHLCV data.

Reference: Design Doc v1.0 §5 (Volume Profile Engine) dan §3.3 (Definisi).

Algoritma:
1. Bin harga jadi N bin uniform antara min(lows) dan max(highs).
2. Untuk setiap candle, distribusikan volume-nya UNIFORMLY ke bin-bin yang
   candle tersebut lewati (dari low ke high).
3. POC = bin dengan volume tertinggi.
4. VAH/VAL = greedy expansion dari POC sampai cumulative volume mencapai
   target (default 70%).

Contoh usage:
    from mode4_amt.zones import compute_volume_profile
    import numpy as np

    highs = np.array([100, 102, 101, 103, 104])
    lows  = np.array([ 98,  99, 100, 101, 102])
    closes = np.array([ 99, 101, 100, 102, 103])
    volumes = np.array([1000, 1500, 800, 2000, 1200])

    vp = compute_volume_profile(highs, lows, closes, volumes,
                                num_bins=50, value_area_pct=0.70)
    print(vp.poc, vp.vah, vp.val)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import numpy as np


# ============================================================
# Data class
# ============================================================
@dataclass
class VolumeProfile:
    """Hasil computation volume profile untuk 1 window."""
    # Core levels
    poc: float
    vah: float
    val: float

    # Bin data (untuk analisis / plotting)
    price_bins: np.ndarray = field(repr=False)     # length N+1 (bin edges)
    volume_bins: np.ndarray = field(repr=False)    # length N (volume per bin)
    poc_bin_idx: int = -1

    # Extended: HVN/LVN
    hvn_levels: List[float] = field(default_factory=list)  # High Volume Nodes
    lvn_levels: List[float] = field(default_factory=list)  # Low Volume Nodes

    # Metadata
    total_volume: float = 0.0
    value_area_volume: float = 0.0
    value_area_pct_actual: float = 0.0     # Should be ~0.70
    num_candles: int = 0

    # Status
    is_valid: bool = True
    error: Optional[str] = None

    def summary(self) -> str:
        """One-line summary untuk logging."""
        return (f"VP[poc={self.poc:.4f} vah={self.vah:.4f} val={self.val:.4f} "
                f"va%={self.value_area_pct_actual:.3f} candles={self.num_candles} "
                f"valid={self.is_valid}]")


# ============================================================
# Core functions
# ============================================================
def compute_volume_profile(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    num_bins: int = 50,
    value_area_pct: float = 0.70,
    atr_reference: Optional[float] = None,
    min_va_atr_ratio: float = 1.0,
    hvn_top_k: int = 5,
    lvn_bottom_k: int = 5,
) -> VolumeProfile:
    """
    Compute volume profile dari OHLCV arrays.

    Args:
        highs, lows, closes, volumes: numpy arrays same length
        num_bins: resolusi price binning (default 50 per Design Doc §5.2)
        value_area_pct: target % volume untuk Value Area (default 0.70)
        atr_reference: ATR pada awal window, untuk sanity check VA width
        min_va_atr_ratio: minimum ratio (VAH-VAL)/ATR untuk valid VP
        hvn_top_k: berapa HVN teratas dikembalikan
        lvn_bottom_k: berapa LVN terbawah dikembalikan

    Returns:
        VolumeProfile dataclass. Jika input invalid, is_valid=False dan
        error string diisi.

    Design Doc reference: §5.3 (algoritma) dan §5.5 (validasi).
    """
    # ---- Input validation ----
    n = len(highs)
    if n == 0:
        return _invalid_vp("empty input arrays")
    if not (len(lows) == len(closes) == len(volumes) == n):
        return _invalid_vp("array length mismatch")
    if n < 5:
        return _invalid_vp(f"too few candles ({n} < 5)")

    highs = np.asarray(highs, dtype=np.float64)
    lows = np.asarray(lows, dtype=np.float64)
    closes = np.asarray(closes, dtype=np.float64)
    volumes = np.asarray(volumes, dtype=np.float64)

    if np.any(highs < lows):
        return _invalid_vp("high < low in some candles")
    if np.any(volumes < 0):
        return _invalid_vp("negative volume")
    if np.all(volumes == 0):
        return _invalid_vp("all volumes zero")

    price_min = float(np.min(lows))
    price_max = float(np.max(highs))
    price_range = price_max - price_min
    if price_range <= 0:
        return _invalid_vp("zero price range")

    # ---- Build bin edges ----
    bin_size = price_range / num_bins
    price_bins = np.linspace(price_min, price_max, num_bins + 1)  # N+1 edges

    # ---- Distribute volume ----
    # Vectorized approach: for each candle compute bin range, then loop over
    # candles (n is typically 20-100, so python loop is fine).
    volume_bins = np.zeros(num_bins, dtype=np.float64)

    for i in range(n):
        c_low = lows[i]
        c_high = highs[i]
        c_vol = volumes[i]
        if c_vol == 0:
            continue

        # Bin indices covered by this candle
        low_bin = int((c_low - price_min) / bin_size)
        high_bin = int((c_high - price_min) / bin_size)
        # Clamp to valid range
        low_bin = max(0, min(low_bin, num_bins - 1))
        high_bin = max(0, min(high_bin, num_bins - 1))

        num_covered = high_bin - low_bin + 1
        vol_per_bin = c_vol / num_covered
        volume_bins[low_bin:high_bin + 1] += vol_per_bin

    total_volume = float(np.sum(volume_bins))
    if total_volume <= 0:
        return _invalid_vp("total binned volume zero")

    # ---- POC ----
    poc_bin_idx = int(np.argmax(volume_bins))
    poc_price = _bin_center(price_bins, poc_bin_idx)

    # ---- Value Area (greedy expansion) ----
    va_low_idx, va_high_idx, va_vol = compute_value_area(
        volume_bins, poc_bin_idx, target_pct=value_area_pct
    )
    val_price = float(price_bins[va_low_idx])          # bin bottom edge
    vah_price = float(price_bins[va_high_idx + 1])     # bin top edge
    va_pct_actual = va_vol / total_volume

    # ---- HVN/LVN ----
    # HVN: bins with volume in top-K, sorted by volume desc
    hvn_indices = np.argsort(volume_bins)[::-1][:hvn_top_k]
    hvn_levels = [float(_bin_center(price_bins, int(i))) for i in hvn_indices]

    # LVN: bins with non-zero but low volume (within VA range preferred)
    # Filter: only bins between VAL and VAH with volume < 30% of POC volume
    poc_vol = volume_bins[poc_bin_idx]
    lvn_candidates = []
    for i in range(va_low_idx, va_high_idx + 1):
        if volume_bins[i] > 0 and volume_bins[i] < 0.3 * poc_vol:
            lvn_candidates.append((volume_bins[i], i))
    lvn_candidates.sort()
    lvn_levels = [float(_bin_center(price_bins, i))
                  for _, i in lvn_candidates[:lvn_bottom_k]]

    # ---- Sanity check ----
    vp = VolumeProfile(
        poc=poc_price,
        vah=vah_price,
        val=val_price,
        price_bins=price_bins,
        volume_bins=volume_bins,
        poc_bin_idx=poc_bin_idx,
        hvn_levels=hvn_levels,
        lvn_levels=lvn_levels,
        total_volume=total_volume,
        value_area_volume=va_vol,
        value_area_pct_actual=va_pct_actual,
        num_candles=n,
        is_valid=True,
        error=None,
    )

    # Sanity: VAH-VAL width vs ATR (Design Doc §5.5)
    if atr_reference is not None and atr_reference > 0:
        va_width = vah_price - val_price
        if va_width < min_va_atr_ratio * atr_reference:
            vp.is_valid = False
            vp.error = (f"VA width ({va_width:.4f}) < "
                        f"{min_va_atr_ratio}×ATR ({atr_reference:.4f})")

    # Sanity: monotonic VAL <= POC <= VAH
    if not (val_price <= poc_price <= vah_price):
        vp.is_valid = False
        vp.error = f"VAL={val_price} POC={poc_price} VAH={vah_price} not monotonic"

    # Sanity: VA % within 68-72% window (Design Doc §5.5)
    if not (0.68 <= va_pct_actual <= 0.72):
        # Warning only, not fatal — greedy expansion sometimes overshoots
        if vp.error is None:
            vp.error = f"VA% actual {va_pct_actual:.3f} outside [0.68, 0.72]"
            # Keep is_valid=True; caller can decide

    return vp


def compute_value_area(
    volume_bins: np.ndarray,
    poc_bin_idx: int,
    target_pct: float = 0.70,
) -> Tuple[int, int, float]:
    """
    Greedy expansion dari POC ke atas dan ke bawah, memilih arah dengan
    volume terbesar per step, sampai cumulative volume >= target_pct.

    Args:
        volume_bins: array volume per bin
        poc_bin_idx: index of POC bin
        target_pct: target % dari total volume

    Returns:
        (val_bin_idx, vah_bin_idx, cumulative_va_volume)

    Design Doc reference: §3.3 (Value Area algorithm).
    """
    n = len(volume_bins)
    total = float(np.sum(volume_bins))
    if total <= 0:
        return poc_bin_idx, poc_bin_idx, 0.0

    target_vol = total * target_pct

    lo = hi = poc_bin_idx
    va_vol = float(volume_bins[poc_bin_idx])

    while va_vol < target_vol:
        # Volume di bin luar next step
        vol_above = float(volume_bins[hi + 1]) if hi + 1 < n else -1.0
        vol_below = float(volume_bins[lo - 1]) if lo - 1 >= 0 else -1.0

        # Kalau kedua sisi sudah habis, stop
        if vol_above < 0 and vol_below < 0:
            break

        # Pilih arah dengan volume terbesar; tie -> pilih atas
        if vol_above >= vol_below:
            hi += 1
            va_vol += vol_above
        else:
            lo -= 1
            va_vol += vol_below

    return lo, hi, va_vol


# ============================================================
# Helpers
# ============================================================
def _bin_center(price_bins: np.ndarray, bin_idx: int) -> float:
    """Return center price of bin at bin_idx."""
    return float((price_bins[bin_idx] + price_bins[bin_idx + 1]) / 2)


def _invalid_vp(error: str) -> VolumeProfile:
    """Construct an invalid VP with error message."""
    return VolumeProfile(
        poc=0.0, vah=0.0, val=0.0,
        price_bins=np.array([]),
        volume_bins=np.array([]),
        poc_bin_idx=-1,
        is_valid=False,
        error=error,
    )


__all__ = [
    "VolumeProfile",
    "compute_volume_profile",
    "compute_value_area",
]
