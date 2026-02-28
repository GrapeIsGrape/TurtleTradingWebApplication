"""Breakout detection for Turtle Trading strategy."""

from typing import List, Optional
import pandas as pd
import yfinance as yf
from datetime import date

from .constants import *
from .calculator import (
    calculate_n_days_high_at_index,
    check_bullish_arrangement_at_index,
    check_price_break_n_days_high
)


# =============================================================================
# TICKER INFORMATION RETRIEVAL
# =============================================================================

def get_breakout_ticker_information_live(tickers: List[str]) -> pd.DataFrame:
    """
    Get detailed ticker information using live market data.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        DataFrame with current prices and technical indicators
    """
    today = date.today().strftime("%Y-%m-%d")
    columns = [
        DATE, TICKER, OPEN, HIGH, LOW, CLOSE, CURRENT_PRICE,
        DAYS_HIGH_10, DAYS_HIGH_20, DAYS_HIGH_55, DAYS_HIGH_100, DAYS_HIGH_200,
        BULLISH_ARRANGEMENT, ATR_20, STOP_LOSS
    ]
    result_df = pd.DataFrame(columns=columns)
    
    for ticker in tickers:
        try:
            ticker_data = _get_live_ticker_data(ticker, today)
            if ticker_data:
                result_df.loc[len(result_df)] = ticker_data
        except Exception as e:
            print(f"Error fetching live data for {ticker}: {e}")
    
    return result_df


def get_breakout_ticker_information_close(tickers: List[str]) -> pd.DataFrame:
    """
    Get detailed ticker information using historical close data.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        DataFrame with close prices and technical indicators
    """
    today = date.today().strftime("%Y-%m-%d")
    columns = [
        DATE, TICKER, OPEN, HIGH, LOW, CLOSE, CURRENT_PRICE,
        DAYS_HIGH_10, DAYS_HIGH_20, DAYS_HIGH_55, DAYS_HIGH_100, DAYS_HIGH_200,
        BULLISH_ARRANGEMENT, ATR_20, STOP_LOSS
    ]
    result_df = pd.DataFrame(columns=columns)
    
    for ticker in tickers:
        try:
            ticker_data = _get_close_ticker_data(ticker, today)
            if ticker_data:
                result_df.loc[len(result_df)] = ticker_data
        except Exception as e:
            print(f"Error fetching close data for {ticker}: {e}")
    
    return result_df


def _get_live_ticker_data(ticker: str, today: str) -> Optional[dict]:
    """Get live ticker data from yfinance and local CSV."""
    df = pd.read_csv(f'{MARKET_DATA_FOLDER_PATH}/{ticker}.csv')
    last_index = len(df) - 1
    
    atr_20 = df.iloc[last_index][ATR_20]
    bullish = df.iloc[last_index][BULLISH_ARRANGEMENT]
    
    stock = yf.Ticker(ticker)
    current_price = stock.info.get('regularMarketPrice')
    if not current_price:
        return None
    
    last_day_record = stock.history(PERIOD_1D).iloc[0]
    
    return {
        DATE: today,
        TICKER: ticker,
        OPEN: round(last_day_record[OPEN], ROUND_DP),
        HIGH: round(last_day_record[HIGH], ROUND_DP),
        LOW: round(last_day_record[LOW], ROUND_DP),
        CLOSE: round(last_day_record[CLOSE], ROUND_DP),
        CURRENT_PRICE: current_price,
        DAYS_HIGH_10: calculate_n_days_high_at_index(df, last_index, 10),
        DAYS_HIGH_20: calculate_n_days_high_at_index(df, last_index, 20),
        DAYS_HIGH_55: calculate_n_days_high_at_index(df, last_index, 55),
        DAYS_HIGH_100: calculate_n_days_high_at_index(df, last_index, 100),
        DAYS_HIGH_200: calculate_n_days_high_at_index(df, last_index, 200),
        BULLISH_ARRANGEMENT: bullish,
        ATR_20: atr_20,
        STOP_LOSS: round(current_price - STOP_LOSS_ATR_MULTIPLIER * atr_20, ROUND_DP)
    }


def _get_close_ticker_data(ticker: str, today: str) -> Optional[dict]:
    """Get ticker data from local CSV only."""
    df = pd.read_csv(f'{MARKET_DATA_FOLDER_PATH}/{ticker}.csv')
    last_row = df.iloc[-1]
    last_index = len(df) - 1
    
    return {
        DATE: today,
        TICKER: ticker,
        OPEN: round(last_row[OPEN], ROUND_DP),
        HIGH: round(last_row[HIGH], ROUND_DP),
        LOW: round(last_row[LOW], ROUND_DP),
        CLOSE: round(last_row[CLOSE], ROUND_DP),
        CURRENT_PRICE: last_row[CLOSE],
        DAYS_HIGH_10: calculate_n_days_high_at_index(df, last_index, 10),
        DAYS_HIGH_20: calculate_n_days_high_at_index(df, last_index, 20),
        DAYS_HIGH_55: calculate_n_days_high_at_index(df, last_index, 55),
        DAYS_HIGH_100: calculate_n_days_high_at_index(df, last_index, 100),
        DAYS_HIGH_200: calculate_n_days_high_at_index(df, last_index, 200),
        BULLISH_ARRANGEMENT: last_row[BULLISH_ARRANGEMENT],
        ATR_20: last_row[ATR_20],
        STOP_LOSS: round(last_row[CLOSE] - STOP_LOSS_ATR_MULTIPLIER * last_row[ATR_20], ROUND_DP)
    }


# =============================================================================
# PRICE BREAKOUT DETECTION
# =============================================================================

def check_price_breakout_for_tickers(
    tickers: List[str],
    n_days: int,
    use_live_price: bool = False,
    env_folder_path: Optional[str] = None
) -> List[str]:
    """
    Check which tickers have price breakouts.
    
    Args:
        tickers: List of ticker symbols
        n_days: Number of days for breakout period
        use_live_price: Use live prices instead of historical
        env_folder_path: Optional environment folder path prefix
        
    Returns:
        List of tickers with breakouts
    """
    if use_live_price:
        breakout_tickers = _check_breakout_with_live_price(tickers, n_days, env_folder_path)
    else:
        breakout_tickers = _check_breakout_from_history(tickers, n_days, 0, env_folder_path)
    
    print(f"{n_days}-days high Breakout tickers: {', '.join(breakout_tickers)} (Count: {len(breakout_tickers)})")
    return breakout_tickers


def _check_breakout_with_live_price(
    tickers: List[str],
    days: int,
    env_folder_path: Optional[str] = None
) -> List[str]:
    """Check breakout using today's high price from yfinance."""
    breakout_tickers = []
    folder_path = f'{env_folder_path}{MARKET_DATA_FOLDER_PATH}' if env_folder_path else MARKET_DATA_FOLDER_PATH
    
    for ticker in tickers:
        try:
            df = pd.read_csv(f'{folder_path}/{ticker}.csv')
            stock = yf.Ticker(ticker)
            price = stock.info.get('dayHigh', stock.info.get('regularMarketPrice'))
            
            if price and check_price_break_n_days_high(df, days, price):
                breakout_tickers.append(ticker)
        except Exception as e:
            print(f"Error checking breakout for {ticker}: {e}")
    
    return sorted(breakout_tickers)


def _check_breakout_from_history(
    tickers: List[str],
    days: int,
    days_ago: int,
    env_folder_path: Optional[str] = None
) -> List[str]:
    """Check breakout using historical data from n days ago."""
    breakout_tickers = []
    
    for ticker in tickers:
        if _check_historical_breakout(ticker, days, days_ago, env_folder_path):
            breakout_tickers.append(ticker)
    
    return sorted(breakout_tickers)


def _check_historical_breakout(
    ticker: str,
    days: int,
    days_ago: int,
    env_folder_path: Optional[str] = None
) -> bool:
    """Check if ticker had a breakout n days ago."""
    try:
        folder_path = f'{env_folder_path}{MARKET_DATA_FOLDER_PATH}' if env_folder_path else MARKET_DATA_FOLDER_PATH
        df = pd.read_csv(f'{folder_path}/{ticker}.csv')
        
        if days_ago > 0:
            df = df.iloc[:-days_ago]
        
        if len(df) < days + 1:
            return False
        
        last_index = len(df) - 1
        n_days_high = df.iloc[last_index - days:last_index][HIGH].max()
        previous_high = df.iloc[last_index][HIGH]
        
        return previous_high > n_days_high
    except Exception as e:
        print(f"Error checking historical breakout for {ticker}: {e}")
        return False


# =============================================================================
# MOVING AVERAGE BREAKOUT DETECTION
# =============================================================================

def check_moving_average_breakout_for_tickers(
    tickers: List[str],
    first_ma: str,
    second_ma: str
) -> List[str]:
    """
    Check for moving average crossover breakouts.
    
    Args:
        tickers: List of ticker symbols
        first_ma: First moving average column name (e.g., MA_20)
        second_ma: Second moving average column name (e.g., MA_50)
        
    Returns:
        List of tickers with MA crossover
    """
    breakout_tickers = []
    
    for ticker in tickers:
        try:
            df = pd.read_csv(f'{MARKET_DATA_FOLDER_PATH}/{ticker}.csv')
            if _check_ma_crossover(df, first_ma, second_ma):
                breakout_tickers.append(ticker)
        except Exception as e:
            print(f"Error checking MA breakout for {ticker}: {e}")
    
    return sorted(breakout_tickers)


def _check_ma_crossover(df: pd.DataFrame, first_ma: str, second_ma: str) -> bool:
    """Check if first MA crossed above second MA recently."""
    if len(df) < 3:
        return False
    
    first_ma_vals = df[first_ma]
    second_ma_vals = df[second_ma]
    
    # Today: first > second, Yesterday: first < second
    return (first_ma_vals.iloc[-1] > second_ma_vals.iloc[-1] and 
            first_ma_vals.iloc[-2] < second_ma_vals.iloc[-2])


# =============================================================================
# BULLISH ARRANGEMENT DETECTION
# =============================================================================

def check_bullish_arrangement_for_tickers(tickers: List[str]) -> List[str]:
    """
    Check which tickers are in bullish arrangement.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        List of tickers in bullish arrangement
    """
    bullish_tickers = []
    
    for ticker in tickers:
        if check_bullish_arrangement_for_ticker(ticker):
            bullish_tickers.append(ticker)
    
    return sorted(bullish_tickers)


def check_bullish_arrangement_for_ticker(ticker: str) -> bool:
    """Check if a single ticker is in bullish arrangement."""
    try:
        df = pd.read_csv(f'{MARKET_DATA_FOLDER_PATH}/{ticker}.csv')
        return check_bullish_arrangement_at_index(df, len(df) - 1)
    except Exception as e:
        print(f"Error checking bullish arrangement for {ticker}: {e}")
        return False


# =============================================================================
# RESET SIGNAL DETECTION
# =============================================================================

def filter_tickers_by_reset_signal(tickers: List[str], n_days: int) -> List[str]:
    """
    Filter tickers where the most recent m-days low touch occurred after 
    the most recent n-days high touch (potential exit signal).
    
    Args:
        tickers: List of ticker symbols to check
        n_days: Number of days for high breakout (20 or 55)
        
    Returns:
        List of tickers that meet the exit criteria
    """
    # Determine m_days based on n_days
    if n_days == 20:
        m_days = 10
    elif n_days == 55:
        m_days = 20
    else:
        return []
    
    filtered_tickers = []
    
    for ticker in tickers:
        try:
            df = pd.read_csv(f'{MARKET_DATA_FOLDER_PATH}/{ticker}.csv')
            
            if len(df) < max(n_days, m_days) + 1:
                continue
            
            # Find the last date when low price hit m_days low
            previous_m_days_low_date = _find_last_low_breakout_date(df, m_days)
            
            # Find the last date when high price hit n_days high
            previous_n_days_high_date = _find_last_high_breakout_date(df, n_days)
            
            # If m_days low touch is more recent than n_days high touch
            if previous_m_days_low_date and previous_n_days_high_date:
                if previous_m_days_low_date > previous_n_days_high_date:
                    filtered_tickers.append(ticker)
                    
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
    
    return filtered_tickers


def _find_last_low_breakout_date(df: pd.DataFrame, m_days: int) -> Optional[int]:
    """
    Find the most recent date index where the low price hit the m_days low.
    
    Args:
        df: DataFrame with market data
        m_days: Number of days for low calculation
        
    Returns:
        Index of the most recent low breakout, or None if not found
    """
    # Start from the latest date and go backwards
    for i in range(len(df) - 1, m_days - 1, -1):
        # Calculate m_days low for the period before index i
        m_days_low = df.iloc[i - m_days:i][LOW].min()
        current_low = df.iloc[i][LOW]
        
        # Check if current low breaks below m_days low
        if current_low <= m_days_low:
            return i
    
    return None


def _find_last_high_breakout_date(df: pd.DataFrame, n_days: int) -> Optional[int]:
    """
    Find the most recent date index where the high price hit the n_days high.
    
    Args:
        df: DataFrame with market data
        n_days: Number of days for high calculation
        
    Returns:
        Index of the most recent high breakout, or None if not found
    """
    # Start from the latest date and go backwards
    for i in range(len(df) - 1, n_days - 1, -1):
        # Calculate n_days high for the period before index i
        n_days_high = df.iloc[i - n_days:i][HIGH].max()
        current_high = df.iloc[i][HIGH]
        
        # Check if current high breaks above n_days high
        if current_high >= n_days_high:
            return i
    
    return None
