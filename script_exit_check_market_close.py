import os
from datetime import datetime, date

from classes.exit_checker import check_exit_by_stop_loss
from classes.constants import (
    SCRIPT_LOGS_FOLDER_PATH,
    EXIT_LOG_MARKET_CLOSE,
    MAIN_LOG_EXIT_CHECK_MARKET_CLOSE
)

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_EXIT_CHECK_MARKET_CLOSE, 'a') as main_log_file:
    main_log_file.write(f'[START] {str(datetime.now())} Check exit at market close job started\n')
    main_log_file.write(f'[INFO ] {str(datetime.now())} Current script directory is {current_script_directory}\n')

    # Check exit signals
    exit_tickers = check_exit_by_stop_loss(current_script_directory)

    for days in ['10', '20']:
        tickers = exit_tickers[days]
        joined_ticker_list = f"{days}-days low Exit tickers: {', '.join(tickers)} (Count: {len(tickers)})"

        with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + EXIT_LOG_MARKET_CLOSE, 'a') as daily_log_file:
            daily_log_file.write(f'[{date.today()}] {joined_ticker_list}\n')

        main_log_file.write(f'[INFO ] {str(datetime.now())} {joined_ticker_list}\n')

    main_log_file.write(f'[END  ] {str(datetime.now())} Check exit at market close job ended\n')
