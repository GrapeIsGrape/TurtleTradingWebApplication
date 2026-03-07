import os
from datetime import datetime, date

from classes.data_retriever import *
from classes.breakout_checker import *
from classes.exit_checker import check_exit_by_stop_loss
from classes.helper import check_if_previous_night_market_was_open
from classes.constants import (
    SCRIPT_LOGS_FOLDER_PATH,
    MARKET_CLOSE_BREAKOUT_RESULT_FILE_NAME,
    MARKET_CLOSE_EXIT_RESULT_FILE_NAME,
    MAIN_LOG_MARKET_CLOSE_BREAKOUT_FILE_NAME,
    MAIN_LOG_MARKET_CLOSE_EXIT_FILE_NAME,
    N_DAYS_HIGH_LIST
)

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_MARKET_CLOSE_BREAKOUT_FILE_NAME, 'a') as main_log_file:
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

            with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MARKET_CLOSE_BREAKOUT_RESULT_FILE_NAME, 'a') as daily_log_file:
                daily_log_file.write(f'[{date.today()}] {joined_ticker_list}\n')

            main_log_file.write(f'[INFO ] {str(datetime.now())} [BREAKOUT] {joined_ticker_list}\n')
    else:
        main_log_file.write(f'[INFO ] {str(datetime.now())} Previous night market ({date.today()}) was closed, skip checking breakout\n')
        with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MARKET_CLOSE_BREAKOUT_RESULT_FILE_NAME, 'a') as daily_log_file:
            daily_log_file.write(f'[{date.today()}] Market is closed, no breakout check performed\n')

with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_MARKET_CLOSE_EXIT_FILE_NAME, 'a') as main_log_file:
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

            with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MARKET_CLOSE_EXIT_RESULT_FILE_NAME, 'a') as daily_log_file:
                daily_log_file.write(f'[{date.today()}] {joined_ticker_list}\n')

            main_log_file.write(f'[INFO ] {str(datetime.now())} {joined_ticker_list}\n')
    else:
        main_log_file.write(f'[INFO ] {str(datetime.now())} Previous night market ({date.today()}) was closed, skip checking exit\n')
        with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MARKET_CLOSE_EXIT_RESULT_FILE_NAME, 'a') as daily_log_file:
            daily_log_file.write(f'[{date.today()}] Market is closed, no exit check performed\n')

    main_log_file.write(f'[END  ] {str(datetime.now())} Check exit at market close job ended\n')

# Final log message
with open(current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MAIN_LOG_MARKET_CLOSE_BREAKOUT_FILE_NAME, 'a') as main_log_file:
    main_log_file.write(f'[END  ] {str(datetime.now())} Check breakout and exit at market close job ended\n')

# =========================================================================
# TELEGRAM ALERTS — sent only when tickers are non-empty
# =========================================================================
try:
    import re as _re
    from services.telegram_service import format_breakout_alert, format_exit_alert, send_message, save_alert

    _today = str(date.today())

    # Parse breakout results written above
    _breakout_groups = []
    _bo_path = current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MARKET_CLOSE_BREAKOUT_RESULT_FILE_NAME
    if os.path.exists(_bo_path):
        with open(_bo_path, 'r') as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line.startswith(f'[{_today}]'):
                    continue
                _m = _re.match(r'\[.*?\] (.*?) [Bb]reakout tickers: ?(.*) \([Cc]ount: \d+\)', _line)
                if _m:
                    _tickers = [t.strip() for t in _m.group(2).split(',') if t.strip()]
                    _breakout_groups.append({'label': _m.group(1), 'tickers': _tickers})

    _bo_text = format_breakout_alert(_today, _breakout_groups, is_live=False)
    if _bo_text:
        _sent = send_message(_bo_text)
        save_alert('breakout_close', [t for g in _breakout_groups for t in g['tickers']], telegram_sent=_sent)

    # Parse exit results written above
    _exit_groups = []
    _ex_path = current_script_directory + SCRIPT_LOGS_FOLDER_PATH + '/' + MARKET_CLOSE_EXIT_RESULT_FILE_NAME
    if os.path.exists(_ex_path):
        with open(_ex_path, 'r') as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line.startswith(f'[{_today}]'):
                    continue
                _m = _re.match(r'\[.*?\] (.*?-days low) Exit tickers: ?(.*) \([Cc]ount: \d+\)', _line)
                if _m:
                    _tickers = [t.strip() for t in _m.group(2).split(',') if t.strip()]
                    _exit_groups.append({'label': _m.group(1), 'tickers': _tickers})

    _ex_text = format_exit_alert(_today, _exit_groups, is_live=False)
    if _ex_text:
        _sent = send_message(_ex_text)
        save_alert('exit_close', [t for g in _exit_groups for t in g['tickers']], telegram_sent=_sent)

except Exception as _tg_err:
    print(f'[WARN] Telegram alert error (non-fatal): {_tg_err}')
