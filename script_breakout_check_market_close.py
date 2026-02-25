import os
from datetime import datetime, date

from classes.data_retriever import *
from classes.breakout_checker import *

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory +'script_logs/breakout_check_market_close.log', 'a') as main_log_file:
    main_log_file.write(f'[START] {str(datetime.now())} Check breakout at market close job started\n')
    main_log_file.write(f'[INFO ] {str(datetime.now())} Current script directory is {current_script_directory}\n')

    tickers = get_all_unique_tickers(current_script_directory)

    n_days_list = [20,50]
    for n_days in n_days_list:
        price_breakout_tickers = check_price_breakout_for_tickers(tickers, n_days, False, current_script_directory)
        joined_ticker_list = f"{n_days}-days high Breakout tickers: {', '.join(price_breakout_tickers)} (Count: {len(price_breakout_tickers)})"

        with open(current_script_directory +'script_logs/breakout_check_market_close_full_breakout_list.log', 'a') as daily_log_file:
            daily_log_file.write(f'[{date.today()}] {joined_ticker_list}\n')

        main_log_file.write(f'[INFO ] {str(datetime.now())} {joined_ticker_list}\n')

    current_time = datetime.now()
    main_log_file.write(f'[END  ] {str(datetime.now())} Check breakout at market close job ended\n')
    