"""
Turtle Trading Strategy - Main Entry Point

This module orchestrates the turtle trading strategy by:
1. Downloading market data for all S&P 500 tickers
2. Calculating technical indicators (moving averages, ATR, etc.)
3. Detecting price breakouts and bullish arrangements
4. Identifying positions to exit based on n-days low breakout

Usage:
    python turtle_trading.py
"""

from typing import List
import pandas as pd

from classes.data_retriever import (
    get_all_unique_tickers,
    download_market_data_for_tickers,
    enrich_with_indicators_for_tickers,
)
from classes.breakout_checker import (
    check_price_breakout_for_tickers,
    get_breakout_ticker_information_close,
    check_moving_average_breakout_for_tickers,
    check_bullish_arrangement_for_tickers,
)
from classes.helper import get_duplicated_items_from_lists
from classes.constants import PERIOD_5Y


# =============================================================================
# MAIN TRADING PIPELINE
# =============================================================================

def download_and_enrich_market_data(tickers: List[str]) -> None:
    """
    Download and enrich market data with technical indicators.
    
    Args:
        tickers: List of ticker symbols to process
    """
    download_market_data_for_tickers(tickers, PERIOD_5Y)
    enrich_with_indicators_for_tickers(tickers, PERIOD_5Y)


def identify_price_breakout_opportunities(
    tickers: List[str],
    breakout_days: int = 20
) -> pd.DataFrame:
    """
    Identify tickers with price breakouts and retrieve their information.
    
    Args:
        tickers: List of ticker symbols to check
        breakout_days: Number of days for breakout calculation (default: 20)
        
    Returns:
        DataFrame with breakout ticker information
    """
    price_breakout_tickers = check_price_breakout_for_tickers(tickers, breakout_days)
    return get_breakout_ticker_information_close(price_breakout_tickers)


def identify_multiple_signal_opportunities(
    tickers: List[str],
    ma_short: str = "MA-20",
    ma_long: str = "MA-50"
) -> List[str]:
    """
    Identify tickers with multiple bullish signals.
    
    Combines:
    - Price breakout (20-days high)
    - Moving average crossover
    - Bullish arrangement (MA-5 > MA-10 > ... > MA-200)
    
    Args:
        tickers: List of ticker symbols to check
        ma_short: Short-term moving average column name
        ma_long: Long-term moving average column name
        
    Returns:
        List of tickers with all three signals
    """
    price_breakout_tickers = check_price_breakout_for_tickers(tickers, 20)
    ma_breakout_tickers = check_moving_average_breakout_for_tickers(tickers, ma_short, ma_long)
    bullish_arrangement_tickers = check_bullish_arrangement_for_tickers(tickers)
    
    return get_duplicated_items_from_lists([
        price_breakout_tickers,
        ma_breakout_tickers,
        bullish_arrangement_tickers
    ])


def main() -> None:
    """
    Execute the turtle trading strategy pipeline.
    
    Steps:
    1. Retrieve all S&P 500 tickers
    2. Download 5-year market data
    3. Calculate technical indicators
    4. Identify price breakout opportunities
    5. Display results
    """
    # Get all unique S&P 500 tickers
    tickers = get_all_unique_tickers()
    
    # Download and enrich market data with technical indicators
    download_and_enrich_market_data(tickers)
    
    # Identify price breakout opportunities
    breakout_opportunities = identify_price_breakout_opportunities(tickers)
    
    # Display results
    print("\n" + "="*60)
    print("PRICE BREAKOUT OPPORTUNITIES (20-Day High)")
    print("="*60)
    print(breakout_opportunities)


if __name__ == "__main__":
    main()

