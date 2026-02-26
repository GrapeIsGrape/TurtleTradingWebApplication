"""Exit signal detection for Turtle Trading positions."""

from typing import List
import pandas as pd
import yfinance as yf

from .constants import *
from .calculator import check_price_break_n_days_low


def check_exit_for_positions(exit_days: int = 10) -> List[str]:
    """
    Check current positions for exit signals.
    
    Args:
        exit_days: Number of days for low breakout exit signal
        
    Returns:
        List of tickers that should be exited
    """
    try:
        positions_df = pd.read_csv(CURRENT_POSITIONS_FILE_PATH)
    except FileNotFoundError:
        print(f"Positions file not found: {CURRENT_POSITIONS_FILE_PATH}")
        return []
    
    exit_tickers = []
    
    for ticker in positions_df[TICKER]:
        if _should_exit_position(ticker, exit_days):
            exit_tickers.append(ticker)
    
    return exit_tickers


def _should_exit_position(ticker: str, days: int) -> bool:
    """
    Check if a position should be exited based on n-days low breakout.
    
    Args:
        ticker: Ticker symbol
        days: Number of days for low calculation
        
    Returns:
        True if position should be exited
    """
    try:
        stock = yf.Ticker(ticker)
        current_price = stock.info.get('dayLow', stock.info.get('regularMarketPrice'))
        
        if not current_price:
            print(f"Could not get price for {ticker}")
            return False
        
        df = pd.read_csv(f'{MARKET_DATA_FOLDER_PATH}/{ticker}.csv')
        return check_price_break_n_days_low(df, days, current_price)
        
    except Exception as e:
        print(f"Error checking exit for {ticker}: {e}")
        return False
