import os
from datetime import datetime, date

from classes.data_retriever import *
from classes.breakout_checker import *
from classes.exit_checker import check_exit_by_stop_loss_live
from classes.helper import check_if_market_is_open
from classes.constants import (
    SCRIPT_LOGS_FOLDER_PATH,
    MARKET_OPEN_BREAKOUT_RESULT_FILE_NAME,
    MARKET_OPEN_EXIT_RESULT_FILE_NAME,
    MAIN_LOG_BREAKOUT_MARKET_OPEN,
    MAIN_LOG_EXIT_CHECK_MARKET_OPEN,
    N_DAYS_HIGH_LIST
)

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_BREAKOUT_MARKET_OPEN, 'a') as main_log_file:
    main_log_file.write(f'[START] {str(datetime.now())} Check breakout and exit at market open job started\n')

    if check_if_market_is_open():
        main_log_file.write(f'[INFO ] {str(datetime.now())} Market is open, starting breakout check\n')
        # =========================================================================
        # BREAKOUT CHECK
        # =========================================================================
        tickers = get_all_unique_tickers(current_script_directory)

        for n_days in N_DAYS_HIGH_LIST:
            price_breakout_tickers = check_price_breakout_for_tickers(tickers, n_days, True, current_script_directory)
            joined_ticker_list = f"{n_days}-days high breakout tickers: {', '.join(price_breakout_tickers)} (count: {len(price_breakout_tickers)})"
            
            print(joined_ticker_list)
            main_log_file.write(f'[INFO ] {str(datetime.now())} [BREAKOUT] {joined_ticker_list}\n')

            with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MARKET_OPEN_BREAKOUT_RESULT_FILE_NAME, 'a') as full_breakout_log_file:
                full_breakout_log_file.write(f'[{datetime.now()}] {joined_ticker_list}\n')
    else:
        main_log_file.write(f'[INFO ] {str(datetime.now())} Market is closed, skip checking breakout\n')
        with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MARKET_OPEN_BREAKOUT_RESULT_FILE_NAME, 'a') as full_breakout_log_file:
            full_breakout_log_file.write(f'[{datetime.now()}] Market is closed, no breakout check performed\n')

with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_EXIT_CHECK_MARKET_OPEN, 'a') as main_log_file:
    main_log_file.write(f'[START] {str(datetime.now())} Check exit at market open job started\n')
    main_log_file.write(f'[INFO ] {str(datetime.now())} Current script directory is {current_script_directory}\n')

    if check_if_market_is_open():
        main_log_file.write(f'[INFO ] {str(datetime.now())} Market is open, starting exit check\n')
        # =========================================================================
        # EXIT CHECK
        # =========================================================================
        exit_tickers = check_exit_by_stop_loss_live(current_script_directory)

        for days in ['10', '20']:
            tickers = exit_tickers[days]
            joined_ticker_list = f"{days}-days low Exit tickers: {', '.join(tickers)} (Count: {len(tickers)})"

            with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MARKET_OPEN_EXIT_RESULT_FILE_NAME, 'a') as daily_log_file:
                daily_log_file.write(f'[{str(datetime.now())}] {joined_ticker_list}\n')

            main_log_file.write(f'[INFO ] {str(datetime.now())} {joined_ticker_list}\n')
    else:
        main_log_file.write(f'[INFO ] {str(datetime.now())} Market is closed, skip checking exit\n')
        with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MARKET_OPEN_EXIT_RESULT_FILE_NAME, 'a') as daily_log_file:
            daily_log_file.write(f'[{str(datetime.now())}] Market is closed, no exit check performed\n')

    main_log_file.write(f'[END  ] {str(datetime.now())} Check exit at market open job ended\n')

# Final log message
with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_BREAKOUT_MARKET_OPEN, 'a') as main_log_file:
    main_log_file.write(f'[END  ] {str(datetime.now())} Check breakout and exit at market open job ended\n')
