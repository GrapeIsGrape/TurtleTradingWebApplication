import yfinance as yf
import pandas as pd
import os
from datetime import date, timedelta

from .constants import *
from .calculator import *
from .file_handler import *

basic_columns = [DATE, OPEN, HIGH, LOW, CLOSE, VOLUME]
n_days_high_columns = [DAYS_HIGH_10, DAYS_HIGH_20, DAYS_HIGH_30, DAYS_HIGH_50, DAYS_HIGH_100, DAYS_HIGH_200]
n_days_low_columns = [DAYS_LOW_10]
moving_average_columns = [MA_5, MA_10, MA_20, MA_30, MA_50, MA_100, MA_200]
true_range_columns = [TRUE_RANGE, ATR_20, ATR_55]
bullish_columns = [BULLISH_ARRANGEMENT]

numeric_columns = [OPEN, HIGH, LOW, CLOSE] + n_days_high_columns + n_days_low_columns + moving_average_columns + true_range_columns

def get_all_unique_tickers(env_folder_path = None):
    folder_path = env_folder_path + TICKERS_TO_BE_RETRIEVED_FOLDER_PATH if env_folder_path else TICKERS_TO_BE_RETRIEVED_FOLDER_PATH
    files = read_file_names_in_path(folder_path)

    all_tickers = []
    for file in files:
        df = pd.read_csv(folder_path + '/' + file + '.csv')
        print('Number of tickers in the file ' + file + ' is ' + str(len(df)))
        all_tickers = all_tickers + df['Ticker'].tolist()

    all_tickers = list(set(all_tickers))
    all_tickers.sort()
    print('Total number of unique tickers is ' + str(len(all_tickers)))
    return all_tickers

#region Download tickers from yfinance and write to files

def download_market_data_for_tickers(tickers, duration, env_folder_path = None):
    for ticker in tickers:
        try:
            download_market_data_for_ticker(ticker, duration, env_folder_path)
        except Exception as e:
            print(f'Error when downloading data of {ticker} from yfinance: {str(e)}')

def download_market_data_for_ticker(ticker, duration, env_folder_path = None):
    columns_to_keep = [OPEN, HIGH, LOW, CLOSE, VOLUME]

    data = yf.Ticker(ticker)
    if len(data.info) <= 1:
        print(f'Error when retrieving data of {ticker} from yfinance')
        return
    df = data.history(period=duration)
    df = df[columns_to_keep]

    df = standardize_columns_to_decimal_places(df, ROUND_DP)

    df = df.reset_index()
    df[DATE] = df[DATE].dt.date.astype(str)

    today = date.today().strftime("%Y-%m-%d")
    if df[DATE].loc[len(df)-1] == today:
        df = df.iloc[:-10]

    columns_to_be_calculated = n_days_high_columns + n_days_low_columns + moving_average_columns + true_range_columns + bullish_columns

    for column in columns_to_be_calculated:
        df = add_column(df, column)

    folder_path = env_folder_path + MARKET_DATA_FOLDER_PATH if env_folder_path else MARKET_DATA_FOLDER_PATH
    save_csv(df, folder_path + '/', ticker + '.csv')
    print('Finished downloading all data of ' + ticker)
    return

#endregion

#region Fill ticker data up to today to exising ticker files

def enrich_with_indicators_for_tickers(tickers, duration, env_folder_path = None):
    for ticker in tickers:
        try:
            enrich_with_indicators_for_ticker(ticker, duration, env_folder_path)
        except Exception as e:
            print(f'Error when enriching data of {ticker}: {str(e)}')

def enrich_with_indicators_for_ticker(ticker, duration, env_folder_path = None):    
    today = date.today()
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    folder_path = env_folder_path + MARKET_DATA_FOLDER_PATH if env_folder_path else MARKET_DATA_FOLDER_PATH
    file_path = folder_path + '/' + ticker + '.csv'
    if not os.path.exists(file_path):
        download_market_data_for_ticker(ticker, duration, env_folder_path)
        return
    
    df = pd.read_csv(file_path)
    date_of_last_row = df[DATE].loc[len(df)-1]

    if today.weekday() == 6 and date_of_last_row == (today - timedelta(2)).strftime("%Y-%m-%d"): # Today is Sunday and last record is 2 days ago (Friday)
        return

    today = today.strftime("%Y-%m-%d")
    if date_of_last_row == today or date_of_last_row == yesterday:
        return
        
    columns = df.columns

    data = yf.Ticker(ticker)
    latest_df = data.history(period=duration)
    latest_df = latest_df.reset_index()
    latest_df = standardize_columns_to_decimal_places(latest_df, ROUND_DP)
    latest_df[DATE] = latest_df[DATE].dt.date.astype(str)

    if latest_df[DATE].loc[len(latest_df)-1] == today:
        latest_df = latest_df.iloc[:-1]

    index_of_first_missing_data = latest_df[DATE].eq(date_of_last_row).idxmax() + 1

    index = index_of_first_missing_data
    while index < len(latest_df):
        new_row = {}
        for column in columns:
            new_row[column] = 0
            value = 0
            if column in basic_columns:
                value = latest_df.loc[index][column]
            if column in n_days_high_columns:
                days = column.split('-')[0]
                value = calculate_n_days_high_at_index(latest_df, index, int(days))
            if column in n_days_low_columns:
                days = column.split('-')[0]
                value = calculate_n_days_low_at_index(latest_df, index, int(days))
            if column in moving_average_columns:
                days = column.split('-')[1]
                value = calculate_moving_average_at_index(latest_df, index, int(days))
            if column in true_range_columns:
                if column == TRUE_RANGE:
                    value = calculate_true_range_at_index(latest_df, index)
                else:
                    days = column.split('-')[1]
                    current_true_range = calculate_true_range_at_index(latest_df, index)
                    previous_average_true_range = df[column].loc[len(df)-1]
                    value = calculate_average_true_range(previous_average_true_range, current_true_range, int(days))
            new_row[column] = value
        df.loc[len(df)] = new_row
            
        index += 1
    save_csv(df, folder_path + '/', ticker + '.csv')
    print('Finished filling data of ' + ticker)

#endregion

def standardize_columns_to_decimal_places(df, dp):
    columns_to_be_rounded = numeric_columns
    for column in columns_to_be_rounded:
        if column in df.columns:
            df[column] = df[column].round(dp)
    return df

def remove_column(df, column_name):
    return df.drop(column_name, axis=1)

def add_column(df, columnName):
    if columnName in df.columns:
        return df
    
    if columnName == TRUE_RANGE:
        return calculate_true_range_column(df)
        
    if 'ATR' in columnName:
        days = columnName.split('-')[1]
        return calculate_average_true_range_column(df, int(days))

    if 'MA' in columnName:
        days = columnName.split('-')[1]
        return calculate_moving_average_column(df, int(days))

    if 'Days High' in columnName:
        days = columnName.split('-')[0]
        return calculate_n_days_high_column(df, int(days))

    if 'Days Low' in columnName:
        days = columnName.split('-')[0]
        return calculate_n_days_low_column(df, int(days))
    
    if columnName == BULLISH_ARRANGEMENT:
        return calculate_bullish_arrangement_column(df)

