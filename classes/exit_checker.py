import pandas as pd
import yfinance as yf

from .constants import *
from .breakout_checker import *

def check_exit_for_positions():
    days = 10
    positions_df = pd.read_csv(CURRENT_POSITIONS_FILE_PATH)
    exit_tickers = []
    for ticker in positions_df[TICKER]:
        stock = yf.Ticker(ticker)
        price = stock.info['dayLow']
        df = pd.read_csv(MARKET_DATA_FOLDER_PATH + '/' + ticker + '.csv')
        if (check_price_break_n_days_low(df, days, price)):
            exit_tickers.append(ticker)
    return exit_tickers

def check_price_break_n_days_low(df, days, price):
    if len(df) < days:
        days = len(df)
    last_index = len(df)-1
    n_days_low = min(df[LOW].loc[last_index - days + 1:last_index])
    return price < n_days_low