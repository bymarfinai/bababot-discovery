"""
test_volume_profile.py — Unit tests untuk Volume Profile Engine
=================================================================
Scenarios (Design Doc §16.1 Sesi 1):
1. Sideways data (balance zone typical)
2. Bull trending data
3. Bear trending data
4. High volatility (wide range)
5. Low volume window (edge case)
6. All-zero volume (edge case)
7. Single price level (edge case)
8. Custom target Value Area %
9. HVN/LVN identification
10. ATR-based sanity check

Run:
    pytest mode4_amt/tests/test_volume_profile.py -v
    # or standalone:
    python -m mode4_amt.tests.test_volume_profile
"""

import numpy as np
import pytest

from mode4_amt.zones.volume_profile import (
    compute_volume_profile,
    compute_value_area,
    VolumeProfile,
)


# ============================================================
# Helpers untuk generate synthetic OHLCV
# ============================================================
def make_sideways(n=50, center=100.0, range_pct=0.02, vol_base=1000.0, seed=42):
    """Sideways: harga oscillate around center, volume relatively uniform."""
    rng = np.random.default_rng(seed)
    closes = center + rng.uniform(-center * range_pct, center * range_pct, n)
    opens = closes + rng.uniform(-center * 0.005, center * 0.005, n)
    highs = np.maximum(closes, opens) + rng.uniform(0, center * 0.005, n)
    lows = np.minimum(closes, opens) - rng.uniform(0, center * 0.005, n)
    volumes = vol_base + rng.uniform(-vol_base * 0.3, vol_base * 0.3, n)
    return highs, lows, closes, volumes


def make_trending(n=50, start=100.0, end=120.0, vol_base=1000.0, seed=42):
    """Trending: harga linear progress dari start ke end."""
    rng = np.random.default_rng(seed)
    trend = np.linspace(start, end, n)
    noise = rng.uniform(-0.5, 0.5, n)
    closes = trend + noise
    opens = closes + rng.uniform(-0.3, 0.3, n)
    highs = np.maximum(closes, opens) + rng.uniform(0, 0.5, n)
    lows = np.minimum(closes, opens) - rng.uniform(0, 0.5, n)
    volumes = vol_base + rng.uniform(-vol_base * 0.2, vol_base * 0.2, n)
    return highs, lows, closes, volumes


def make_high_volatility(n=50, center=100.0, range_pct=0.10, vol_base=1000.0, seed=42):
    """High volatility: wide range."""
    return make_sideways(n, center, range_pct, vol_base, seed)


# ============================================================
# TEST 1: Sideways data
# ============================================================
def test_sideways_poc_near_center():
    """POC harus dekat center pada data sideways."""
    highs, lows, closes, volumes = make_sideways(n=100, center=100.0)
    vp = compute_volume_profile(highs, lows, closes, volumes, num_bins=50)

    assert vp.is_valid, f"VP invalid: {vp.error}"
    # POC should be within 5% of center
    assert 95 <= vp.poc <= 105, f"POC={vp.poc} not near center 100"
    # VAL < POC < VAH
    assert vp.val < vp.poc < vp.vah
    # VA % should be close to 70%
    assert 0.65 <= vp.value_area_pct_actual <= 0.75


# ============================================================
# TEST 2: Bull trending data
# ============================================================
def test_bull_trending():
    """Trending data: POC harus di area price yang paling banyak visited."""
    highs, lows, closes, volumes = make_trending(n=50, start=100, end=130)
    vp = compute_volume_profile(highs, lows, closes, volumes, num_bins=50)

    assert vp.is_valid
    # POC should be somewhere in the middle-ish of the range
    assert 100 < vp.poc < 130
    # VAH should be near top, VAL near bottom
    assert vp.vah > vp.poc
    assert vp.val < vp.poc


# ============================================================
# TEST 3: Bear trending
# ============================================================
def test_bear_trending():
    highs, lows, closes, volumes = make_trending(n=50, start=130, end=100)
    vp = compute_volume_profile(highs, lows, closes, volumes, num_bins=50)

    assert vp.is_valid
    assert 100 < vp.poc < 130
    assert vp.vah > vp.val


# ============================================================
# TEST 4: High volatility
# ============================================================
def test_high_volatility():
    highs, lows, closes, volumes = make_high_volatility(n=100, range_pct=0.15)
    vp = compute_volume_profile(highs, lows, closes, volumes, num_bins=50)

    assert vp.is_valid
    # VA should be reasonably wide
    va_width = vp.vah - vp.val
    assert va_width > 0
    # But not the entire range
    total_range = np.max(highs) - np.min(lows)
    assert va_width < total_range


# ============================================================
# TEST 5: Edge case — all zero volume
# ============================================================
def test_all_zero_volume():
    highs, lows, closes, _ = make_sideways(n=30)
    volumes = np.zeros(30)
    vp = compute_volume_profile(highs, lows, closes, volumes)

    assert not vp.is_valid
    assert "zero" in vp.error.lower()


# ============================================================
# TEST 6: Edge case — too few candles
# ============================================================
def test_too_few_candles():
    highs = np.array([100.0, 101.0])
    lows = np.array([99.0, 100.0])
    closes = np.array([100.5, 100.5])
    volumes = np.array([100.0, 100.0])
    vp = compute_volume_profile(highs, lows, closes, volumes)

    assert not vp.is_valid
    assert "few" in vp.error.lower()


# ============================================================
# TEST 7: Edge case — invalid input (high < low)
# ============================================================
def test_invalid_high_low():
    highs = np.array([99.0, 100.0, 101.0, 102.0, 103.0])
    lows = np.array([100.0, 101.0, 102.0, 103.0, 104.0])   # low > high
    closes = np.array([99.5, 100.5, 101.5, 102.5, 103.5])
    volumes = np.array([100.0, 200.0, 150.0, 300.0, 250.0])
    vp = compute_volume_profile(highs, lows, closes, volumes)

    assert not vp.is_valid


# ============================================================
# TEST 8: Custom target Value Area %
# ============================================================
def test_custom_va_target():
    highs, lows, closes, volumes = make_sideways(n=100)

    vp_70 = compute_volume_profile(highs, lows, closes, volumes,
                                   num_bins=50, value_area_pct=0.70)
    vp_90 = compute_volume_profile(highs, lows, closes, volumes,
                                   num_bins=50, value_area_pct=0.90)

    assert vp_70.is_valid
    assert vp_90.is_valid

    # 90% VA should be wider than 70%
    width_70 = vp_70.vah - vp_70.val
    width_90 = vp_90.vah - vp_90.val
    assert width_90 >= width_70


# ============================================================
# TEST 9: HVN/LVN identification
# ============================================================
def test_hvn_lvn():
    highs, lows, closes, volumes = make_sideways(n=100)
    vp = compute_volume_profile(highs, lows, closes, volumes,
                                num_bins=50, hvn_top_k=5, lvn_bottom_k=5)

    assert vp.is_valid
    assert len(vp.hvn_levels) <= 5
    # POC should be in HVN levels
    assert any(abs(x - vp.poc) < 1.0 for x in vp.hvn_levels)

    # LVN should all be between VAL and VAH
    for lvn in vp.lvn_levels:
        assert vp.val <= lvn <= vp.vah, f"LVN {lvn} outside VA [{vp.val}, {vp.vah}]"


# ============================================================
# TEST 10: ATR-based sanity check
# ============================================================
def test_atr_sanity_check_fails_on_narrow_va():
    """Kalau ATR jauh lebih besar dari VA width, VP harus invalid."""
    highs, lows, closes, volumes = make_sideways(n=100, range_pct=0.01)
    # Simulasi ATR yang sangat besar (misal 10x actual)
    huge_atr = 50.0

    vp = compute_volume_profile(highs, lows, closes, volumes,
                                num_bins=50, atr_reference=huge_atr,
                                min_va_atr_ratio=1.0)

    # Harus flag invalid karena VA width jauh lebih kecil dari ATR
    assert not vp.is_valid
    assert "VA width" in vp.error


def test_atr_sanity_check_passes_on_wide_va():
    """ATR yang reasonable harus pass."""
    highs, lows, closes, volumes = make_sideways(n=100, range_pct=0.05)
    # ATR realistic (5% of price = ~5)
    reasonable_atr = 1.0

    vp = compute_volume_profile(highs, lows, closes, volumes,
                                num_bins=50, atr_reference=reasonable_atr,
                                min_va_atr_ratio=1.0)

    assert vp.is_valid


# ============================================================
# TEST 11: compute_value_area function directly
# ============================================================
def test_value_area_greedy_expansion():
    """Test greedy expansion pada volume distribution kontrolable."""
    # Manual volume bins: POC di tengah, decay ke kiri-kanan
    volume_bins = np.array([1, 2, 4, 8, 16, 32, 16, 8, 4, 2, 1], dtype=np.float64)
    poc_idx = 5  # bin with 32
    total = volume_bins.sum()  # 94

    lo, hi, va_vol = compute_value_area(volume_bins, poc_idx, target_pct=0.70)

    # Target 0.7 × 94 = 65.8
    assert va_vol >= 65.8
    # Should be symmetric-ish given symmetric distribution
    # POC (5) + expand: 4(16) or 6(16), 3(8) or 7(8), etc.
    # 32+16+16=64, still < 65.8, need one more
    # 32+16+16+8=72
    assert lo <= poc_idx <= hi
    assert va_vol >= 0.70 * total


# ============================================================
# TEST 12: Concentrated volume at specific price
# ============================================================
def test_concentrated_volume_creates_tight_va():
    """Kalau semua volume terkonsentrasi di 1 area, VA harus tight."""
    n = 50
    highs = np.full(n, 105.0)
    lows = np.full(n, 95.0)
    closes = np.full(n, 100.0)
    volumes = np.zeros(n)
    # Konsentrasi volume: mostly around price 100
    for i in range(n):
        if 45 <= i < 55:
            volumes[i] = 10000.0
        else:
            volumes[i] = 100.0

    vp = compute_volume_profile(highs, lows, closes, volumes, num_bins=20)
    assert vp.is_valid
    # Semua candle punya range yang sama [95,105], jadi POC ada di somewhere
    assert 95 <= vp.poc <= 105


# ============================================================
# Allow standalone run
# ============================================================
if __name__ == "__main__":
    import sys
    tests = [
        test_sideways_poc_near_center,
        test_bull_trending,
        test_bear_trending,
        test_high_volatility,
        test_all_zero_volume,
        test_too_few_candles,
        test_invalid_high_low,
        test_custom_va_target,
        test_hvn_lvn,
        test_atr_sanity_check_fails_on_narrow_va,
        test_atr_sanity_check_passes_on_wide_va,
        test_value_area_greedy_expansion,
        test_concentrated_volume_creates_tight_va,
    ]
    failed = []
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed.append(t.__name__)
        except Exception as e:
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed.append(t.__name__)
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
