"""Technical indicator calculations for Turtle Trading strategy."""

from typing import List
import pandas as pd
from .constants import *


# =============================================================================
# TRUE RANGE CALCULATIONS
# =============================================================================

def calculate_true_range_column(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate True Range for entire DataFrame."""
    true_ranges = [calculate_true_range_at_index(df, index) for index in range(len(df))]
    df[TRUE_RANGE] = true_ranges
    return df


def calculate_true_range_at_index(df: pd.DataFrame, index: int) -> float:
    """
    Calculate True Range at a specific index.
    
    True Range = max(H-L, |H-C_prev|, |L-C_prev|)
    """
    row = df.iloc[index]
    
    if index == 0:
        return round(row[HIGH] - row[LOW], ROUND_DP)
    
    previous_row = df.iloc[index - 1]
    today_high = float(row[HIGH])
    today_low = float(row[LOW])
    yesterday_close = float(previous_row[CLOSE])
    
    today_range = today_high - today_low
    high_close_diff = abs(today_high - yesterday_close)
    low_close_diff = abs(today_low - yesterday_close)
    
    return round(max(today_range, high_close_diff, low_close_diff), ROUND_DP)


# =============================================================================
# AVERAGE TRUE RANGE (ATR) CALCULATIONS
# =============================================================================

def calculate_average_true_range_column(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Calculate ATR column using exponential moving average."""
    average_true_ranges = []
    
    for i in range(len(df)):
        if i >= days:
            previous_atr = average_true_ranges[-1]
            current_tr = df.iloc[i][TRUE_RANGE]
            atr = calculate_average_true_range(previous_atr, current_tr, days)
        else:
            atr = round(df.iloc[:i+1][TRUE_RANGE].mean(), ROUND_DP)
        average_true_ranges.append(atr)
    
    df[f'ATR-{days}'] = average_true_ranges
    return df


def calculate_average_true_range(previous_atr: float, current_tr: float, days: int) -> float:
    """Calculate ATR using EMA formula: (Previous ATR * (days - 1) + Current TR) / days"""
    return round((previous_atr * (days - 1) + current_tr) / days, ROUND_DP)


# =============================================================================
# MOVING AVERAGE CALCULATIONS
# =============================================================================

def calculate_moving_average_column(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Calculate simple moving average column."""
    actual_days = min(days, len(df) - 1) if len(df) > 1 else 1
    moving_averages = []
    
    for index in range(len(df)):
        if index < actual_days:
            closes = df.iloc[:index+1][CLOSE]
            ma = round(closes.mean(), ROUND_DP)
        else:
            ma = calculate_moving_average_at_index(df, index, actual_days)
        moving_averages.append(ma)
    
    df[f'MA-{days}'] = moving_averages
    return df


def calculate_moving_average_at_index(df: pd.DataFrame, index: int, days: int) -> float:
    """Calculate simple moving average at specific index."""
    actual_days = min(days, len(df), index + 1)
    closes = df.iloc[index - actual_days + 1:index + 1][CLOSE]
    return round(closes.mean(), ROUND_DP)


# =============================================================================
# N-DAYS HIGH CALCULATIONS
# =============================================================================

def calculate_n_days_high_column(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Calculate n-days high column."""
    actual_n = min(n, len(df))
    n_days_highs = []
    
    for index in range(len(df)):
        if index < actual_n:
            high = df.iloc[:index+1][HIGH].max()
        else:
            high = calculate_n_days_high_at_index(df, index, actual_n)
        n_days_highs.append(round(high, ROUND_DP))
    
    df[f'{n}-Days High'] = n_days_highs
    return df


def calculate_n_days_high_at_index(df: pd.DataFrame, index: int, n: int) -> float:
    """Calculate n-days high at specific index."""
    actual_n = min(n, len(df), index + 1)
    highs = df.iloc[index - actual_n + 1:index + 1][HIGH]
    return round(highs.max(), ROUND_DP)


# =============================================================================
# N-DAYS LOW CALCULATIONS
# =============================================================================

def calculate_n_days_low_column(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Calculate n-days low column."""
    actual_n = min(n, len(df))
    n_days_lows = []
    
    for index in range(len(df)):
        if index < actual_n:
            low = df.iloc[:index+1][LOW].min()
        else:
            low = calculate_n_days_low_at_index(df, index, actual_n)
        n_days_lows.append(round(low, ROUND_DP))
    
    df[f'{n}-Days Low'] = n_days_lows
    return df


def calculate_n_days_low_at_index(df: pd.DataFrame, index: int, n: int) -> float:
    """Calculate n-days low at specific index."""
    actual_n = min(n, len(df), index + 1)
    lows = df.iloc[index - actual_n + 1:index + 1][LOW]
    return round(lows.min(), ROUND_DP)


# =============================================================================
# BULLISH ARRANGEMENT CALCULATIONS
# =============================================================================

def calculate_bullish_arrangement_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate bullish arrangement for entire DataFrame.
    Bullish: MA-5 > MA-10 > MA-20 > MA-30 > MA-50 > MA-100 > MA-200
    """
    bullish_arrangements = [
        check_bullish_arrangement_at_index(df, index) for index in range(len(df))
    ]
    df[BULLISH_ARRANGEMENT] = bullish_arrangements
    return df


def check_bullish_arrangement_at_index(df: pd.DataFrame, index: int) -> bool:
    """Check if moving averages are in bullish arrangement at index."""
    row = df.iloc[index]
    ma_columns = [MA_5, MA_10, MA_20, MA_30, MA_50, MA_100, MA_200]
    
    for i in range(len(ma_columns) - 1):
        if row[ma_columns[i]] <= row[ma_columns[i + 1]]:
            return False
    return True


# =============================================================================
# BREAKOUT CALCULATIONS
# =============================================================================

def check_price_break_n_days_high(df: pd.DataFrame, days: int, price: float) -> bool:
    """Check if price breaks n-days high."""
    if len(df) == 0:
        return False
    
    actual_days = min(days, len(df))
    last_index = len(df) - 1
    start_index = max(0, last_index - actual_days + 1)
    n_days_high = df.iloc[start_index:last_index + 1][HIGH].max()
    
    return price > n_days_high


def check_price_break_n_days_low(df: pd.DataFrame, days: int, price: float) -> bool:
    """Check if price breaks n-days low."""
    if len(df) == 0:
        return False
    
    actual_days = min(days, len(df))
    last_index = len(df) - 1
    start_index = max(0, last_index - actual_days + 1)
    n_days_low = df.iloc[start_index:last_index + 1][LOW].min()
    
    return price < n_days_low
