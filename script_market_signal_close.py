import os
from datetime import datetime, date

from classes.data_retriever import *
from classes.breakout_checker import *
from classes.exit_checker import check_exit_by_stop_loss
from classes.helper import check_if_previous_night_market_was_open
from classes.constants import (
    SCRIPT_LOGS_FOLDER_PATH,
    BREAKOUT_LOG_MARKET_CLOSE,
    EXIT_LOG_MARKET_CLOSE,
    MAIN_LOG_BREAKOUT_MARKET_CLOSE,
    MAIN_LOG_EXIT_CHECK_MARKET_CLOSE,
    N_DAYS_HIGH_LIST
)

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_BREAKOUT_MARKET_CLOSE, 'a') as main_log_file:
    main_log_file.write(f'[START] {str(datetime.now())} Check breakout and exit at market close job started\n')
    
    if check_if_previous_night_market_was_open():
        main_log_file.write(f'[INFO ] {str(datetime.now())} Previous night market was open, starting breakout check\n')
        # =========================================================================
        # BREAKOUT CHECK
        # =========================================================================
        tickers = get_all_unique_tickers(current_script_directory)

        for n_days in N_DAYS_HIGH_LIST:
            price_breakout_tickers = check_price_breakout_for_tickers(tickers, n_days, False, current_script_directory)
            joined_ticker_list = f"{n_days}-days high Breakout tickers: {', '.join(price_breakout_tickers)} (Count: {len(price_breakout_tickers)})"

            with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + BREAKOUT_LOG_MARKET_CLOSE, 'a') as daily_log_file:
                daily_log_file.write(f'[{date.today()}] {joined_ticker_list}\n')

            main_log_file.write(f'[INFO ] {str(datetime.now())} [BREAKOUT] {joined_ticker_list}\n')
    else:
        main_log_file.write(f'[INFO ] {str(datetime.now())} Previous night market ({date.today()}) was closed, skip checking breakout\n')
        with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + BREAKOUT_LOG_MARKET_CLOSE, 'a') as daily_log_file:
            daily_log_file.write(f'[{date.today()}] Market is closed, no breakout check performed\n')

with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_EXIT_CHECK_MARKET_CLOSE, 'a') as main_log_file:
    main_log_file.write(f'[START] {str(datetime.now())} Check exit at market close job started\n')
    main_log_file.write(f'[INFO ] {str(datetime.now())} Current script directory is {current_script_directory}\n')

    if check_if_previous_night_market_was_open():
        main_log_file.write(f'[INFO ] {str(datetime.now())} Previous night market was open, starting exit check\n')
        # =========================================================================
        # EXIT CHECK
        # =========================================================================
        exit_tickers = check_exit_by_stop_loss(current_script_directory)

        for days in ['10', '20']:
            tickers = exit_tickers[days]
            joined_ticker_list = f"{days}-days low Exit tickers: {', '.join(tickers)} (Count: {len(tickers)})"

            with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + EXIT_LOG_MARKET_CLOSE, 'a') as daily_log_file:
                daily_log_file.write(f'[{date.today()}] {joined_ticker_list}\n')

            main_log_file.write(f'[INFO ] {str(datetime.now())} {joined_ticker_list}\n')
    else:
        main_log_file.write(f'[INFO ] {str(datetime.now())} Previous night market ({date.today()}) was closed, skip checking exit\n')
        with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + EXIT_LOG_MARKET_CLOSE, 'a') as daily_log_file:
            daily_log_file.write(f'[{date.today()}] Market is closed, no exit check performed\n')

    main_log_file.write(f'[END  ] {str(datetime.now())} Check exit at market close job ended\n')

# Final log message
with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_BREAKOUT_MARKET_CLOSE, 'a') as main_log_file:
    main_log_file.write(f'[END  ] {str(datetime.now())} Check breakout and exit at market close job ended\n')
