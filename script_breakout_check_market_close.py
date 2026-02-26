"""
Breakout Check Script - Market Close

This script runs at market close to detect price breakouts across all tracked
tickers for the Turtle Trading strategy. It checks multiple breakout periods
(10-day, 20-day, 55-day, etc.) and logs results to both main and daily logs.

Usage:
    python script_breakout_check_market_close.py

Logs:
    - Main log: logs/breakout_check_main_close.log
    - Daily log: logs/breakout_check_daily_close.log
"""

import os
from datetime import datetime, date
from pathlib import Path
from typing import List

from classes.data_retriever import get_all_unique_tickers
from classes.breakout_checker import check_price_breakout_for_tickers
from classes.constants import (
    SCRIPT_LOGS_FOLDER_PATH,
    BREAKOUT_LOG_MARKET_CLOSE,
    MAIN_LOG_BREAKOUT_MARKET_CLOSE,
    N_DAYS_HIGH_LIST,
)


# =============================================================================
# LOGGING UTILITIES
# =============================================================================

def get_script_directory() -> str:
    """Get the absolute path to the script directory."""
    return os.path.dirname(os.path.abspath(__file__)) + '/'


def get_log_file_path(script_dir: str, log_file_name: str) -> Path:
    """
    Get the full path to a log file, creating directory if needed.
    
    Args:
        script_dir: Base script directory
        log_file_name: Name of the log file
        
    Returns:
        Path object pointing to the log file
    """
    log_path = Path(script_dir) / SCRIPT_LOGS_FOLDER_PATH / log_file_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path


def log_message(file_path: Path, level: str, message: str) -> None:
    """
    Write a timestamped log message to file.
    
    Args:
        file_path: Path to log file
        level: Log level (START, INFO, END, ERROR, etc.)
        message: Log message content
    """
    with open(file_path, 'a') as f:
        f.write(f'[{level:6}] {str(datetime.now())} {message}\n')


# =============================================================================
# BREAKOUT DETECTION
# =============================================================================

def check_breakouts_for_period(
    script_dir: str,
    daily_log_path: Path,
    main_log_path: Path,
    tickers: List[str],
    n_days: int
) -> None:
    """
    Check price breakouts for a specific period and log results.
    
    Args:
        script_dir: Base script directory path
        daily_log_path: Path to daily log file
        main_log_path: Path to main log file
        tickers: List of ticker symbols to check
        n_days: Number of days for breakout period (10, 20, 55, etc.)
    """
    # Check for breakouts using close prices (use_live_price=False)
    breakout_tickers = check_price_breakout_for_tickers(
        tickers,
        n_days,
        use_live_price=False,
        env_folder_path=script_dir
    )
    
    # Format log message
    log_entry = f"{n_days}-days high Breakout tickers: {', '.join(breakout_tickers)} (Count: {len(breakout_tickers)})"
    
    # Write to daily log (with date only, no time)
    with open(daily_log_path, 'a') as f:
        f.write(f'[{date.today()}] {log_entry}\n')
    
    # Write to main log (with full timestamp)
    log_message(main_log_path, 'INFO', log_entry)


def main() -> None:
    """Execute the market close breakout check job."""
    script_dir = get_script_directory()
    
    # Setup log file paths
    main_log_path = get_log_file_path(script_dir, MAIN_LOG_BREAKOUT_MARKET_CLOSE)
    daily_log_path = get_log_file_path(script_dir, BREAKOUT_LOG_MARKET_CLOSE)
    
    try:
        # Log job start
        log_message(main_log_path, 'START', 'Check breakout at market close job started')
        log_message(main_log_path, 'INFO', f'Current script directory is {script_dir}')
        
        # Get all unique tickers
        tickers = get_all_unique_tickers(script_dir)
        
        if not tickers:
            log_message(main_log_path, 'WARN', 'No tickers found to process')
            log_message(main_log_path, 'END', 'Check breakout at market close job ended')
            return
        
        # Check breakouts for each configured period
        for n_days in N_DAYS_HIGH_LIST:
            try:
                check_breakouts_for_period(
                    script_dir,
                    daily_log_path,
                    main_log_path,
                    tickers,
                    n_days
                )
            except Exception as e:
                log_message(main_log_path, 'ERROR', f'Error checking {n_days}-day breakouts: {e}')
        
        # Log job completion
        log_message(main_log_path, 'END', 'Check breakout at market close job ended')
        
    except Exception as e:
        log_message(main_log_path, 'ERROR', f'Fatal error: {e}')
        raise


if __name__ == "__main__":
    main()

    