"""
Market Data Fill Script

This script downloads and enriches market data for all S&P 500 tickers tracked
by the Turtle Trading system. It:

1. Retrieves all unique tickers from the configured ticker files
2. Downloads 5-year historical market data (OHLCV)
3. Enriches data with technical indicators (ATR, moving averages, etc.)

This is typically run periodically (e.g., daily after market close) to ensure
all ticker data is current for analysis and breakout detection.

Usage:
    python script_fill_market_data.py

Logs:
    - Main log: logs/fill_market_data_main.log

Environment:
    Uses configuration from classes/constants.py including:
    - PERIOD_5Y: 5-year historical period
    - SCRIPT_LOGS_FOLDER_PATH: Log directory path
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List

from classes.data_retriever import (
    get_all_unique_tickers,
    download_market_data_for_tickers,
    enrich_with_indicators_for_tickers,
)
from classes.constants import (
    SCRIPT_LOGS_FOLDER_PATH,
    MAIN_LOG_FILL_MARKET_DATA,
    PERIOD_5Y,
    LOG_LEVEL_START,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_END,
)
from classes.script_logger import get_script_directory, get_log_file_path, log_message


# =============================================================================
# DATA PROCESSING
# =============================================================================

def download_and_enrich_data(
    script_dir: str,
    tickers: List[str],
    period: str = PERIOD_5Y
) -> None:
    """
    Download and enrich market data for all tickers.
    
    Args:
        script_dir: Base script directory path
        tickers: List of ticker symbols to process
        period: Historical period to download (default: 5y)
    """
    print(f"Downloading market data for {len(tickers)} tickers...")
    download_market_data_for_tickers(tickers, period, script_dir)
    
    print(f"Enriching data with technical indicators...")
    enrich_with_indicators_for_tickers(tickers, period, script_dir)


def main() -> None:
    """Execute the market data fill job."""
    script_dir = get_script_directory()
    log_file_path = get_log_file_path(script_dir, SCRIPT_LOGS_FOLDER_PATH, MAIN_LOG_FILL_MARKET_DATA)
    
    try:
        # Log job start
        log_message(log_file_path, LOG_LEVEL_START, 'Fill market data job started')
        
        # Get all unique tickers
        print("Retrieving tickers...")
        tickers = get_all_unique_tickers(script_dir)
        
        if not tickers:
            log_message(log_file_path, LOG_LEVEL_WARN, 'No tickers found to process')
            log_message(log_file_path, LOG_LEVEL_END, 'Fill market data job ended (0 tickers)')
            return
        
        log_message(log_file_path, LOG_LEVEL_INFO, f'Processing {len(tickers)} unique tickers')
        
        # Download and enrich market data
        download_and_enrich_data(script_dir, tickers)
        
        # Log job completion
        log_message(
            log_file_path,
            LOG_LEVEL_END,
            f'Fill market data job ended ({len(tickers)} tickers processed)'
        )
        
        print(f"✓ Successfully processed {len(tickers)} tickers")
        
    except Exception as e:
        log_message(log_file_path, LOG_LEVEL_ERROR, f'Fatal error: {e}')
        print(f"✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()


    