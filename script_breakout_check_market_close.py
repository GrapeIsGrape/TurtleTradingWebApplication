import os
from datetime import datetime

from classes.data_retriever import *
from classes.breakout_checker import *

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory +'fill_market_data.log', 'a') as f:
    f.write(f'[START] {str(datetime.now())} Check breakout at market close job started\n')
    f.write(f'[INFO ] {str(datetime.now())} Current script directory is {current_script_directory}\n')

    tickers = get_all_unique_tickers(current_script_directory + '/')

    price_breakout_tickers = check_price_breakout_for_tickers(tickers, 20)
    # breakout_ticker_info = get_breakout_ticker_information(price_breakout_tickers)

    current_time = datetime.now()
    f.write(f'[END  ] {str(datetime.now())} heck breakout at market close job ended\n')

    