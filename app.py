"""
BabaBot AI Strategy Discovery — Backtesting API
FastAPI server with /backtest + /fetch-data endpoints.

Updated: Support custom pairs + timeframes in /fetch-data via ccxt.
"""

import os
import threading
import sqlite3
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Security, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from backtesting_core import Backtester, StrategyConfig, BacktestResult, ENTRY_LOGICS, calc_correlation, run_feature_study, run_marthias_study, test_ai_rules, bootstrap_validate_rules, run_sltp_optimization, run_paper_test, DCAConfig, backtest_dca, backtest_deret_statistik, analyze_deviation_clusters
# REMOVED: live_bot.py (Iron Legion) and dca_bot.py — superseded by baret_live.py
from baret_bot import start_baret, stop_baret, baret_status, get_baret_log
from baret_live import start_baret_live, stop_baret_live, baret_live_status, get_baret_live_log, close_position, close_all_positions, start_account_bot, stop_account_bot, account_bot_status
from ultron_engine import ultron_status, get_ultron_log, manual_analyze, clear_pair_skip, clear_hour_skip, clear_buffer_adjustment
from tick_discovery import (
        start_tick_discovery, stop_tick_discovery, get_discovery_status, get_discovery_log,
        extract_tick_events, analyze_tick_stats,
        start_sweep_engine, stop_sweep_engine, get_sweep_status,
        pause_sweep_engine, resume_sweep_engine,
        profile_winning_combo,
        cluster_levels, combo_sweep, custom_backtest,
        _load_data as td_load_data, DB_PATH as TD_DB_PATH,
    )
