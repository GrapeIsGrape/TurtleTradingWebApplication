import os
from datetime import datetime

from classes.data_retriever import *
from classes.breakout_checker import *
from classes.helper import *

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory +'script_logs/breakout_check_market_open.log', 'a') as main_log_file:
    main_log_file.write(f'[START] {str(datetime.now())} Check breakout at market open job started\n')

    if check_if_market_is_open():
        tickers = get_all_unique_tickers(current_script_directory)

        n_days_list = [20,55]
        for n_days in n_days_list:
            price_breakout_tickers = check_price_breakout_for_tickers(tickers, n_days, True, current_script_directory)
            joined_ticker_list = f"{n_days}-days high breakout tickers: {', '.join(price_breakout_tickers)} (count: {len(price_breakout_tickers)})"
            
            print(joined_ticker_list)
            main_log_file.write(f'[INFO ] {str(datetime.now())} {joined_ticker_list}\n')

            with open(current_script_directory +'script_logs/breakout_check_market_open_full_breakout_list.log', 'a') as full_breakout_log_file:
                full_breakout_log_file.write(f'[{datetime.now()}] {joined_ticker_list}\n')
    else:
        main_log_file.write(f'[INFO ] {str(datetime.now())} Market is closed, skip checking breakout\n')
        with open(current_script_directory +'script_logs/breakout_check_market_open_full_breakout_list.log', 'a') as full_breakout_log_file:
            full_breakout_log_file.write(f'[{datetime.now()}] Market is closed, no breakout check performed\n')
    main_log_file.write(f'[END  ] {str(datetime.now())} Check breakout at market open job ended\n')
    