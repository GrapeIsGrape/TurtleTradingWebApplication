"""
Breakout Check Script - Market Open

This script runs during market hours to detect price breakouts using live market
data. It checks multiple breakout periods (10-day, 20-day, 55-day, etc.) and logs
results only if the market is open. If market is closed, it logs this status.

Usage:
    python script_breakout_check_market_open.py

Logs:
    - Main log: logs/breakout_check_main_open.log
    - Live log: logs/breakout_check_daily_open.log (with timestamps)

Note:
    This script is typically run via a scheduler during market hours.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List

from classes.data_retriever import get_all_unique_tickers
from classes.breakout_checker import check_price_breakout_for_tickers
from classes.helper import check_if_market_is_open
from classes.constants import (
    SCRIPT_LOGS_FOLDER_PATH,
    BREAKOUT_LOG_MARKET_OPEN,
    MAIN_LOG_BREAKOUT_MARKET_OPEN,
    N_DAYS_HIGH_LIST,
    LOG_LEVEL_START,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_END,
)
from classes.script_logger import get_script_directory, get_log_file_path, log_message


# =============================================================================
# BREAKOUT DETECTION
# =============================================================================

def check_breakouts_for_period(
    script_dir: str,
    open_log_path: Path,
    main_log_path: Path,
    tickers: List[str],
    n_days: int
) -> None:
    """
    Check price breakouts for a specific period using live data and log results.
    
    Args:
        script_dir: Base script directory path
        open_log_path: Path to market open log file
        main_log_path: Path to main log file
        tickers: List of ticker symbols to check
        n_days: Number of days for breakout period (10, 20, 55, etc.)
    """
    # Check for breakouts using live prices (use_live_price=True)
    breakout_tickers = check_price_breakout_for_tickers(
        tickers,
        n_days,
        use_live_price=True,
        env_folder_path=script_dir
    )
    
    # Format log message (with consistent formatting)
    log_entry = f"{n_days}-days high breakout tickers: {', '.join(breakout_tickers)} (count: {len(breakout_tickers)})"
    
    # Print to console for visibility
    print(log_entry)
    
    # Write to main log
    log_message(main_log_path, LOG_LEVEL_INFO, log_entry)
    
    # Write to open market log (with full timestamp)
    with open(open_log_path, 'a') as f:
        f.write(f'[{datetime.now()}] {log_entry}\n')


def handle_market_closed(
    open_log_path: Path,
    main_log_path: Path
) -> None:
    """
    Handle case when market is closed.
    
    Args:
        open_log_path: Path to market open log file
        main_log_path: Path to main log file
    """
    message = 'Market is closed, no breakout check performed'
    log_message(main_log_path, LOG_LEVEL_INFO, 'Market is closed, skip checking breakout')
    
    with open(open_log_path, 'a') as f:
        f.write(f'[{datetime.now()}] {message}\n')


def main() -> None:
    """Execute the market open breakout check job."""
    script_dir = get_script_directory()
    
    # Setup log file paths
    main_log_path = get_log_file_path(script_dir, SCRIPT_LOGS_FOLDER_PATH, MAIN_LOG_BREAKOUT_MARKET_OPEN)
    open_log_path = get_log_file_path(script_dir, SCRIPT_LOGS_FOLDER_PATH, BREAKOUT_LOG_MARKET_OPEN)
    
    try:
        # Log job start
        log_message(main_log_path, LOG_LEVEL_START, 'Check breakout at market open job started')
        
        # Check if market is open
        if not check_if_market_is_open():
            handle_market_closed(open_log_path, main_log_path)
            log_message(main_log_path, LOG_LEVEL_END, 'Check breakout at market open job ended')
            return
        
        # Get all unique tickers
        tickers = get_all_unique_tickers(script_dir)
        
        if not tickers:
            log_message(main_log_path, LOG_LEVEL_WARN, 'No tickers found to process')
            log_message(main_log_path, LOG_LEVEL_END, 'Check breakout at market open job ended')
            return
        
        # Check breakouts for each configured period
        for n_days in N_DAYS_HIGH_LIST:
            try:
                check_breakouts_for_period(
                    script_dir,
                    open_log_path,
                    main_log_path,
                    tickers,
                    n_days
                )
            except Exception as e:
                log_message(main_log_path, LOG_LEVEL_ERROR, f'Error checking {n_days}-day breakouts: {e}')
        
        # Log job completion
        log_message(main_log_path, LOG_LEVEL_END, 'Check breakout at market open job ended')
        
    except Exception as e:
        log_message(main_log_path, LOG_LEVEL_ERROR, f'Fatal error: {e}')
        raise


if __name__ == "__main__":
    main()

    