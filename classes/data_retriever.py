"""Market data retrieval and enrichment for Turtle Trading."""

from typing import List, Optional
import yfinance as yf
import pandas as pd
import os
from datetime import date, timedelta

from .constants import *
from .calculator import *
from .file_handler import save_csv

# Column definitions
BASIC_COLUMNS = [DATE, OPEN, HIGH, LOW, CLOSE, VOLUME]
N_DAYS_HIGH_COLUMNS = [DAYS_HIGH_10, DAYS_HIGH_20, DAYS_HIGH_30, DAYS_HIGH_55, DAYS_HIGH_100, DAYS_HIGH_200]
N_DAYS_LOW_COLUMNS = [DAYS_LOW_10, DAYS_LOW_20]
MOVING_AVERAGE_COLUMNS = [MA_5, MA_10, MA_20, MA_30, MA_50, MA_100, MA_200]
TRUE_RANGE_COLUMNS = [TRUE_RANGE, ATR_20, ATR_55]
BULLISH_COLUMNS = [BULLISH_ARRANGEMENT]

NUMERIC_COLUMNS = [OPEN, HIGH, LOW, CLOSE] + N_DAYS_HIGH_COLUMNS + N_DAYS_LOW_COLUMNS + MOVING_AVERAGE_COLUMNS + TRUE_RANGE_COLUMNS


# =============================================================================
# TICKER COLLECTION
# =============================================================================

def get_all_unique_tickers(env_folder_path: Optional[str] = None) -> List[str]:
    """
    Get all unique tickers from CSV files in tickers folder.
    
    Args:
        env_folder_path: Optional environment folder path prefix
        
    Returns:
        Sorted list of unique ticker symbols
    """
    from .file_handler import read_file_names_in_path
    
    folder_path = f'{env_folder_path}{TICKERS_TO_BE_RETRIEVED_FOLDER_PATH}' if env_folder_path else TICKERS_TO_BE_RETRIEVED_FOLDER_PATH
    
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return []
    
    files = read_file_names_in_path(folder_path)
    all_tickers = []
    
    for file in files:
        try:
            df = pd.read_csv(f'{folder_path}/{file}.csv')
            tickers = df[TICKER].tolist()
            all_tickers.extend(tickers)
            print(f'Number of tickers in {file}: {len(tickers)}')
        except Exception as e:
            print(f'Error reading {file}: {e}')
    
    unique_tickers = sorted(list(set(all_tickers)))
    print(f'Total unique tickers: {len(unique_tickers)}')
    
    return unique_tickers


# =============================================================================
# DATA DOWNLOAD
# =============================================================================

def download_market_data_for_tickers(
    tickers: List[str],
    duration: str,
    env_folder_path: Optional[str] = None
) -> None:
    """Download market data for multiple tickers."""
    for ticker in tickers:
        try:
            download_market_data_for_ticker(ticker, duration, env_folder_path)
        except Exception as e:
            print(f'Error downloading {ticker}: {e}')


def download_market_data_for_ticker(
    ticker: str,
    duration: str,
    env_folder_path: Optional[str] = None
) -> None:
    """
    Download and process market data for a single ticker.
    
    Args:
        ticker: Ticker symbol
        duration: Period for historical data (e.g., '5y')
        env_folder_path: Optional environment folder path prefix
    """
    data = yf.Ticker(ticker)
    
    if len(data.info) <= 1:
        print(f'No data available for {ticker}')
        return
    
    # Download and process data
    df = data.history(period=duration)
    df = df.reset_index()
    df = df[BASIC_COLUMNS]
    df = _standardize_columns(df, ROUND_DP)
    df[DATE] = df[DATE].dt.date.astype(str)
    
    # Remove today's incomplete data if present
    today = date.today().strftime("%Y-%m-%d")
    if len(df) > 0 and df[DATE].iloc[-1] == today:
        df = df.iloc[:-SKIP_RECENT_ROWS]
    
    # Calculate all technical indicators
    df = _add_all_indicators(df)
    
    # Save to file
    folder_path = f'{env_folder_path}{MARKET_DATA_FOLDER_PATH}' if env_folder_path else MARKET_DATA_FOLDER_PATH
    save_csv(df, f'{folder_path}/', f'{ticker}.csv')
    print(f'Downloaded and processed data for {ticker}')


def _add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to DataFrame."""
    columns_to_add = (
        N_DAYS_HIGH_COLUMNS + 
        N_DAYS_LOW_COLUMNS + 
        MOVING_AVERAGE_COLUMNS + 
        TRUE_RANGE_COLUMNS + 
        BULLISH_COLUMNS
    )
    
    for column in columns_to_add:
        df = _add_column(df, column)
    
    return df


# =============================================================================
# DATA ENRICHMENT (UPDATE EXISTING FILES)
# =============================================================================

def enrich_with_indicators_for_tickers(
    tickers: List[str],
    duration: str,
    env_folder_path: Optional[str] = None
) -> None:
    """Enrich existing ticker files with latest data."""
    for ticker in tickers:
        try:
            enrich_with_indicators_for_ticker(ticker, duration, env_folder_path)
        except Exception as e:
            print(f'Error enriching {ticker}: {e}')


def enrich_with_indicators_for_ticker(
    ticker: str,
    duration: str,
    env_folder_path: Optional[str] = None
) -> None:
    """
    Update existing ticker file with latest data and indicators.
    
    Args:
        ticker: Ticker symbol
        duration: Period for historical data
        env_folder_path: Optional environment folder path prefix
    """
    folder_path = f'{env_folder_path}{MARKET_DATA_FOLDER_PATH}' if env_folder_path else MARKET_DATA_FOLDER_PATH
    file_path = f'{folder_path}/{ticker}.csv'
    
    # Download if file doesn't exist
    if not os.path.exists(file_path):
        download_market_data_for_ticker(ticker, duration, env_folder_path)
        return
    
    # Check if update is needed
    df = pd.read_csv(file_path)
    today = date.today()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    last_date = df[DATE].iloc[-1]
    
    if _is_data_current(last_date, today, yesterday):
        return
    
    # Fetch latest data and merge
    latest_df = _fetch_latest_data(ticker, duration)
    if latest_df is None:
        return
    
    # Find where to start adding new rows
    try:
        first_new_index = latest_df[DATE].eq(last_date).idxmax() + 1
    except:
        print(f'Could not find matching date for {ticker}')
        return
    
    # Add new rows with calculated indicators
    df = _append_new_rows(df, latest_df, first_new_index)
    
    # Save updated data
    save_csv(df, f'{folder_path}/', f'{ticker}.csv')
    print(f'Enriched data for {ticker}')


def _is_data_current(last_date: str, today: date, yesterday: str) -> bool:
    """Check if existing data is already up to date."""
    today_str = today.strftime("%Y-%m-%d")
    
    # If today is Sunday and last record is Friday
    if today.weekday() == 6 and last_date == (today - timedelta(2)).strftime("%Y-%m-%d"):
        return True
    
    # If data is from today or yesterday
    if last_date in [today_str, yesterday]:
        return True
    
    return False


def _fetch_latest_data(ticker: str, duration: str) -> Optional[pd.DataFrame]:
    """Fetch latest market data from yfinance."""
    try:
        data = yf.Ticker(ticker)
        latest_df = data.history(period=duration)
        latest_df = latest_df.reset_index()
        latest_df = _standardize_columns(latest_df, ROUND_DP)
        latest_df[DATE] = latest_df[DATE].dt.date.astype(str)
        
        # Remove today's data if present
        today = date.today().strftime("%Y-%m-%d")
        if len(latest_df) > 0 and latest_df[DATE].iloc[-1] == today:
            latest_df = latest_df.iloc[:-1]
        
        return latest_df
    except Exception as e:
        print(f'Error fetching latest data: {e}')
        return None


def _append_new_rows(
    df: pd.DataFrame,
    latest_df: pd.DataFrame,
    start_index: int
) -> pd.DataFrame:
    """Append new rows with calculated indicators to existing DataFrame."""
    columns = df.columns
    
    for index in range(start_index, len(latest_df)):
        new_row = _calculate_row_values(df, latest_df, index, columns)
        df.loc[len(df)] = new_row
    
    return df


def _calculate_row_values(
    df: pd.DataFrame,
    latest_df: pd.DataFrame,
    index: int,
    columns: pd.Index
) -> dict:
    """Calculate all column values for a new row."""
    new_row = {}
    
    for column in columns:
        if column in BASIC_COLUMNS:
            new_row[column] = latest_df.iloc[index][column]
            
        elif column in N_DAYS_HIGH_COLUMNS:
            days = int(column.split('-')[0])
            new_row[column] = calculate_n_days_high_at_index(latest_df, index, days)
            
        elif column in N_DAYS_LOW_COLUMNS:
            days = int(column.split('-')[0])
            new_row[column] = calculate_n_days_low_at_index(latest_df, index, days)
            
        elif column in MOVING_AVERAGE_COLUMNS:
            days = int(column.split('-')[1])
            new_row[column] = calculate_moving_average_at_index(latest_df, index, days)
            
        elif column == TRUE_RANGE:
            new_row[column] = calculate_true_range_at_index(latest_df, index)
            
        elif column in [ATR_20, ATR_55]:
            days = int(column.split('-')[1])
            current_tr = calculate_true_range_at_index(latest_df, index)
            previous_atr = df.iloc[-1][column]
            new_row[column] = calculate_average_true_range(previous_atr, current_tr, days)
            
        elif column == BULLISH_ARRANGEMENT:
            # Will be calculated after all MAs are available
            new_row[column] = False
        else:
            new_row[column] = 0
    
    return new_row


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _standardize_columns(df: pd.DataFrame, decimal_places: int) -> pd.DataFrame:
    """Round numeric columns to specified decimal places."""
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = df[column].round(decimal_places)
    return df


def _add_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Add a calculated column to DataFrame.
    
    Args:
        df: DataFrame to add column to
        column_name: Name of column to add
        
    Returns:
        DataFrame with new column
    """
    if column_name in df.columns:
        return df
    
    if column_name == TRUE_RANGE:
        return calculate_true_range_column(df)
    
    if 'ATR' in column_name:
        days = int(column_name.split('-')[1])
        return calculate_average_true_range_column(df, days)
    
    if 'MA' in column_name:
        days = int(column_name.split('-')[1])
        return calculate_moving_average_column(df, days)
    
    if 'Days High' in column_name:
        days = int(column_name.split('-')[0])
        return calculate_n_days_high_column(df, days)
    
    if 'Days Low' in column_name:
        days = int(column_name.split('-')[0])
        return calculate_n_days_low_column(df, days)
    
    if column_name == BULLISH_ARRANGEMENT:
        return calculate_bullish_arrangement_column(df)
    
    return df
