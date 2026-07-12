"""
mode4_amt — Auction Market Theory Framework
============================================
Mode 4 engine untuk BabaBot. Zone-based, structure-based trading.

Reference: BabaBot_Mode4_AMT_Design_Doc_v1.docx

Sub-strategies:
- 4A: Breakout Continuation (entry di retracement setelah true breakout)
- 4B: SFP Reversal (entry setelah liquidity sweep + CHoCH)

Module tree:
    zones/          — Volume profile, balance state
    liquidity/      — BSL/SSL, session, equal levels
    structure/      — Swings, HH/HL/LH/LL, BOS/CHoCH, impulse
    tier1_manipulation/  — Sweep detection, breakout classifier
    tier3_confirmation/  — FVG, structural confirm, retracement zone
    setup/          — Setup scorer, registry, expiry
    entry_engine/   — Sub-strategy 4A/4B, entry trigger
    execution/      — SL, TP, sizing, trade manager
    backtest/       — Backtest engine, walk-forward
    api/            — Flask endpoints, activity logger
"""

__version__ = "0.1.0-alpha"
__status__ = "Sesi 1 — Foundation (Volume Profile)"

from .config import Mode4Config

__all__ = ["Mode4Config", "__version__", "__status__"]
