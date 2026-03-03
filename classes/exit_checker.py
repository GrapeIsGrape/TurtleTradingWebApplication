"""Exit signal detection for Turtle Trading positions."""

from typing import List, Dict, Tuple
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


def check_exit_by_stop_loss(env_folder_path: str = '') -> Dict[str, List[str]]:
    """
    Check current positions for stop loss exit signals (Entry Price - 2*ATR).
    
    Args:
        env_folder_path: Optional environment folder path prefix
        
    Returns:
        Dict with keys '10' and '20' containing lists of tickers that hit stop loss
    """
    try:
        positions_df = pd.read_csv(env_folder_path + CURRENT_POSITIONS_FILE_PATH)
    except FileNotFoundError:
        print(f"Positions file not found: {env_folder_path + CURRENT_POSITIONS_FILE_PATH}")
        return {'10': [], '20': []}
    
    exit_tickers_10 = []
    exit_tickers_20 = []
    
    for _, row in positions_df.iterrows():
        ticker = row[TICKER]
        entry_price = row['Entry']
        atr_20 = row['ATR-20']
        stop_loss = entry_price - (2 * atr_20)
        
        # Check 10-days low
        if _check_stop_loss_hit(ticker, stop_loss, 10, env_folder_path):
            exit_tickers_10.append(ticker)
        
        # Check 20-days low
        if _check_stop_loss_hit(ticker, stop_loss, 20, env_folder_path):
            exit_tickers_20.append(ticker)
    
    return {
        '10': exit_tickers_10,
        '20': exit_tickers_20
    }


def check_exit_by_stop_loss_live(env_folder_path: str = '') -> Dict[str, List[str]]:
    """
    Check current positions for stop loss exit signals using live market data.
    
    Args:
        env_folder_path: Optional environment folder path prefix
        
    Returns:
        Dict with keys '10' and '20' containing lists of tickers that hit stop loss
    """
    try:
        positions_df = pd.read_csv(env_folder_path + CURRENT_POSITIONS_FILE_PATH)
    except FileNotFoundError:
        print(f"Positions file not found: {env_folder_path + CURRENT_POSITIONS_FILE_PATH}")
        return {'10': [], '20': []}
    
    exit_tickers_10 = []
    exit_tickers_20 = []
    
    for _, row in positions_df.iterrows():
        ticker = row[TICKER]
        entry_price = row['Entry']
        atr_20 = row['ATR-20']
        stop_loss = entry_price - (2 * atr_20)
        
        # Check 10-days low
        if _check_stop_loss_hit_live(ticker, stop_loss, 10):
            exit_tickers_10.append(ticker)
        
        # Check 20-days low
        if _check_stop_loss_hit_live(ticker, stop_loss, 20):
            exit_tickers_20.append(ticker)
    
    return {
        '10': exit_tickers_10,
        '20': exit_tickers_20
    }


def _check_stop_loss_hit(ticker: str, stop_loss: float, days: int, env_folder_path: str = '') -> bool:
    """
    Check if an exit signal is triggered based on either condition:
    1) Last low hits (Entry Price - 2*ATR), or
    2) Last low hits the n-days low
    
    Args:
        ticker: Ticker symbol
        stop_loss: Stop loss price level (Entry Price - 2*ATR)
        days: Number of days to check (10 or 20)
        env_folder_path: Optional environment folder path prefix
        
    Returns:
        True if either exit condition is met
    """
    try:
        folder_path = f'{env_folder_path}{MARKET_DATA_FOLDER_PATH}' if env_folder_path else MARKET_DATA_FOLDER_PATH
        df = pd.read_csv(f'{folder_path}/{ticker}.csv')
        
        # Get the column names for n-days low
        if days == 10:
            days_low_col = DAYS_LOW_10
        elif days == 20:
            days_low_col = DAYS_LOW_20
        else:
            return False
        
        if days_low_col not in df.columns or LOW not in df.columns:
            print(f"Required columns not found for {ticker}")
            return False
        
        # Get the most recent (last) low from the Low column
        last_low = df[LOW].iloc[-1]
        
        # Condition 1: Last low hits stop loss level
        if last_low <= stop_loss:
            return True
        
        # Condition 2: Last low hits the n-days low
        most_recent_n_days_low = df[days_low_col].iloc[-1]
        if last_low <= most_recent_n_days_low:
            return True
        
        return False
        
    except Exception as e:
        print(f"Error checking stop loss for {ticker}: {e}")
        return False


def _check_stop_loss_hit_live(ticker: str, stop_loss: float, days: int) -> bool:
    """
    Check if an exit signal is triggered using live market data based on either condition:
    1) Current low hits (Entry Price - 2*ATR), or
    2) Current low hits the n-days low
    
    Args:
        ticker: Ticker symbol
        stop_loss: Stop loss price level (Entry Price - 2*ATR)
        days: Number of days to check (10 or 20)
        
    Returns:
        True if either exit condition is met
    """
    try:
        # Get live data from yfinance
        stock = yf.Ticker(ticker)
        current_low = stock.info.get('dayLow')
        
        if not current_low:
            print(f"Could not get current low for {ticker}")
            return False
        
        # Get historical data to get the n-days low
        df = pd.read_csv(f'{MARKET_DATA_FOLDER_PATH}/{ticker}.csv')
        
        # Get the column name for n-days low
        if days == 10:
            days_low_col = DAYS_LOW_10
        elif days == 20:
            days_low_col = DAYS_LOW_20
        else:
            return False
        
        if days_low_col not in df.columns:
            print(f"Column {days_low_col} not found for {ticker}")
            return False
        
        # Condition 1: Current low hits stop loss level
        if current_low <= stop_loss:
            return True
        
        # Condition 2: Current low hits the n-days low
        most_recent_n_days_low = df[days_low_col].iloc[-1]
        if current_low <= most_recent_n_days_low:
            return True
        
        return False
        
    except Exception as e:
        print(f"Error checking stop loss for {ticker} (live): {e}")
        return False


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
