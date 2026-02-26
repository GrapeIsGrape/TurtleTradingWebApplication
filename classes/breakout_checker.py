import pandas as pd
import yfinance as yf
from datetime import date, datetime

from .constants import *
from .calculator import *

def get_breakout_ticker_information_live(tickers):
    today = date.today().strftime("%Y-%m-%d")
    result_df = pd.DataFrame(columns=[DATE, TICKER, OPEN, HIGH, LOW, CLOSE, CURRENT_PRICE, DAYS_HIGH_10, DAYS_HIGH_20, DAYS_HIGH_55, DAYS_HIGH_100, DAYS_HIGH_200, BULLISH_ARRANGEMENT, ATR_20, STOP_LOSS])
    
    for ticker in tickers:
        df = pd.read_csv(MARKET_DATA_FOLDER_PATH + '/' + ticker + '.csv')
        _20_days_average_true_range = df[ATR_20].loc[len(df)-1]
        bullish = df[BULLISH_ARRANGEMENT].loc[len(df)-1]
        
        stock = yf.Ticker(ticker)
        price = stock.info['regularMarketPrice']

        last_day_record = stock.history(PERIOD_1D).iloc[0]

        new_row_data = {
            DATE: today,
            TICKER: ticker,
            OPEN: round(last_day_record[OPEN], ROUND_DP),
            HIGH: round(last_day_record[HIGH], ROUND_DP),
            LOW: round(last_day_record[LOW], ROUND_DP),
            CLOSE: round(last_day_record[CLOSE], ROUND_DP),
            CURRENT_PRICE: price,
            DAYS_HIGH_10: calculate_n_days_high_at_index(df, len(df)-1, 10),
            DAYS_HIGH_20: calculate_n_days_high_at_index(df, len(df)-1, 20),
            DAYS_HIGH_55: calculate_n_days_high_at_index(df, len(df)-1, 50),
            DAYS_HIGH_100: calculate_n_days_high_at_index(df, len(df)-1, 100),
            DAYS_HIGH_200: calculate_n_days_high_at_index(df, len(df)-1, 200),
            BULLISH_ARRANGEMENT: bullish,
            ATR_20: _20_days_average_true_range,
            STOP_LOSS: round(price - 2 * _20_days_average_true_range, ROUND_DP)
        }
        result_df.loc[len(result_df)] = new_row_data
    
    return result_df

def get_breakout_ticker_information_close(tickers):
    today = date.today().strftime("%Y-%m-%d")
    result_df = pd.DataFrame(columns=[DATE, TICKER, OPEN, HIGH, LOW, CLOSE, CURRENT_PRICE, DAYS_HIGH_10, DAYS_HIGH_20, DAYS_HIGH_55, DAYS_HIGH_100, DAYS_HIGH_200, BULLISH_ARRANGEMENT, ATR_20, STOP_LOSS])
    
    for ticker in tickers:
        df = pd.read_csv(MARKET_DATA_FOLDER_PATH + '/' + ticker + '.csv')
        last_row = df.iloc[len(df)-1]

        new_row_data = {
            DATE: today,
            TICKER: ticker,
            OPEN: round(last_row[OPEN], ROUND_DP),
            HIGH: round(last_row[HIGH], ROUND_DP),
            LOW: round(last_row[LOW], ROUND_DP),
            CLOSE: round(last_row[CLOSE], ROUND_DP),
            CURRENT_PRICE: last_row[CLOSE],
            DAYS_HIGH_10: calculate_n_days_high_at_index(df, len(df)-1, 10),
            DAYS_HIGH_20: calculate_n_days_high_at_index(df, len(df)-1, 20),
            DAYS_HIGH_55: calculate_n_days_high_at_index(df, len(df)-1, 50),
            DAYS_HIGH_100: calculate_n_days_high_at_index(df, len(df)-1, 100),
            DAYS_HIGH_200: calculate_n_days_high_at_index(df, len(df)-1, 200),
            BULLISH_ARRANGEMENT: last_row[BULLISH_ARRANGEMENT],
            ATR_20: last_row[ATR_20],
            STOP_LOSS: round(last_row[CLOSE] - 2 * last_row[ATR_20], ROUND_DP)
        }
        result_df.loc[len(result_df)] = new_row_data
    
    return result_df

#region Price Breakout

def check_price_breakout_for_tickers(tickers, n_days, use_live_price = False, env_folder_path = None):
    #check which ticker breakout today
    tickers_reach_n_days_high = []
    if use_live_price:
        tickers_reach_n_days_high = check_breakout_with_todays_high_price(tickers, n_days, env_folder_path)
    else:
        tickers_reach_n_days_high = check_breakout_of_n_days_high_price_of_i_days_ago(tickers, n_days, 0, env_folder_path)

    print(f"{n_days}-days high Breakout tickers: {', '.join(tickers_reach_n_days_high)} (Count: {len(tickers_reach_n_days_high)})")

    # check each breakout tickers did not breakout in last n days
    # breakout_tickers = []
    # for ticker in tickers_reach_n_days_high:
    #     did_not_breakout_in_past_n_days = True
    #     for i in range(1, n_days+1): # 1 to days
    #         if check_high_of_previous_i_days_break_n_days_high(ticker, n_days, i, env_folder_path):
    #             did_not_breakout_in_past_n_days = False
    #             break
    #     if did_not_breakout_in_past_n_days:
    #         breakout_tickers.append(ticker)
    # print(f"Tickers that confirm breakout today (did not breakout in past {n_days} days): {', '.join(breakout_tickers)} (Count: {len(breakout_tickers)})")

    return tickers_reach_n_days_high

def check_breakout_with_todays_high_price(tickers, days, env_folder_path = None):
    breakout_tickers = []
    for ticker in tickers:
        df = pd.read_csv((env_folder_path + MARKET_DATA_FOLDER_PATH if env_folder_path else MARKET_DATA_FOLDER_PATH) + '/' + ticker + '.csv')
        stock = yf.Ticker(ticker)
        price = stock.info['dayHigh']               # use high of the day as the price
        # price = stock.info['regularMarketPrice']  # use current price of the day as the price
        if (check_price_break_n_days_high(df, days, price)):
            breakout_tickers.append(ticker)
    breakout_tickers.sort()
    return breakout_tickers

def check_price_break_n_days_high(df, days, price):
    if len(df) < days:
        days = len(df)
    last_index = len(df)-1
    n_days_high = max(df[HIGH].loc[last_index - days + 1:last_index])
    return price > n_days_high

def check_breakout_of_n_days_high_price_of_i_days_ago(tickers, days, i, env_folder_path = None):
    breakout_tickers = []
    for ticker in tickers:
        if (check_high_of_previous_i_days_break_n_days_high(ticker, days, i, env_folder_path)):
            breakout_tickers.append(ticker)
    breakout_tickers.sort()
    return breakout_tickers

def check_high_of_previous_i_days_break_n_days_high(ticker, days, n, env_folder_path = None):
    df = pd.read_csv((env_folder_path + MARKET_DATA_FOLDER_PATH if env_folder_path else MARKET_DATA_FOLDER_PATH) + '/' + ticker + '.csv')
    if n > 0:
        df = df.iloc[:-n]

    if len(df) < days+1:
        days = len(df)-1
    
    last_index = len(df)-1
    n_days_high = max(df[HIGH].loc[last_index-days:last_index-1])
    previous_high = df[HIGH].loc[len(df)-1]
    
    return previous_high > n_days_high

#endregion

#region Moving Average Breakout
    
def check_moving_average_breakout_for_tickers(tickers, first_moving_average, second_moving_average):
    breakout_tickers = []
    for ticker in tickers:
        print('Checking moving average breakout for ' + ticker)
        df = pd.read_csv(MARKET_DATA_FOLDER_PATH + '/' + ticker + '.csv')
        if (check_moving_average_breakout(df, first_moving_average, second_moving_average)):
            breakout_tickers.append(ticker)
    breakout_tickers.sort()
    return breakout_tickers

def check_moving_average_breakout(df, first_moving_average, second_moving_average):
    first_moving_average = df[first_moving_average]
    second_moving_average = df[second_moving_average]
    return first_moving_average.loc[len(df)-1] > second_moving_average.loc[len(df)-2] and first_moving_average.loc[len(df)-2] < second_moving_average.loc[len(df)-3]

#endregion

#region Bullish Arrangement

def check_bullish_arrangement_for_tickers(tickers):
    breakout_tickers = []
    for ticker in tickers:
        if (check_bullish_arrangement_for_ticker(ticker)):
            breakout_tickers.append(ticker)
    breakout_tickers.sort()
    return breakout_tickers

def check_bullish_arrangement_for_ticker(ticker):
    df = pd.read_csv(MARKET_DATA_FOLDER_PATH + '/' + ticker + '.csv')
    return check_bullish_arrangement_at_index(df, len(df)-1)

#endregion



