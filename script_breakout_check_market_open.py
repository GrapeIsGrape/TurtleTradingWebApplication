import os
from datetime import datetime

from classes.data_retriever import *
from classes.breakout_checker import *
from classes.helper import *
from classes.constants import SCRIPT_LOGS_FOLDER_PATH, BREAKOUT_LOG_MARKET_OPEN, MAIN_LOG_BREAKOUT_MARKET_OPEN

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_BREAKOUT_MARKET_OPEN, 'a') as main_log_file:
    main_log_file.write(f'[START] {str(datetime.now())} Check breakout at market open job started\n')

    if check_if_market_is_open():
        tickers = get_all_unique_tickers(current_script_directory)

        for n_days in N_DAYS_HIGH_LIST:
            price_breakout_tickers = check_price_breakout_for_tickers(tickers, n_days, True, current_script_directory)
            joined_ticker_list = f"{n_days}-days high breakout tickers: {', '.join(price_breakout_tickers)} (count: {len(price_breakout_tickers)})"
            
            print(joined_ticker_list)
            main_log_file.write(f'[INFO ] {str(datetime.now())} {joined_ticker_list}\n')

            with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + BREAKOUT_LOG_MARKET_OPEN, 'a') as full_breakout_log_file:
                full_breakout_log_file.write(f'[{datetime.now()}] {joined_ticker_list}\n')
    else:
        main_log_file.write(f'[INFO ] {str(datetime.now())} Market is closed, skip checking breakout\n')
        with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + BREAKOUT_LOG_MARKET_OPEN, 'a') as full_breakout_log_file:
            full_breakout_log_file.write(f'[{datetime.now()}] Market is closed, no breakout check performed\n')
    main_log_file.write(f'[END  ] {str(datetime.now())} Check breakout at market open job ended\n')
    