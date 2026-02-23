import os
from datetime import datetime

from classes.data_retriever import *
from classes.breakout_checker import *

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory +'script_logs/breakout_check_market_close.log', 'a') as f:
    f.write(f'[START] {str(datetime.now())} Check breakout at market close job started\n')
    f.write(f'[INFO ] {str(datetime.now())} Current script directory is {current_script_directory}\n')

    tickers = get_all_unique_tickers(current_script_directory)

    price_breakout_tickers = check_price_breakout_for_tickers(tickers, 20, False, current_script_directory)
    f.write(f'[INFO ] {str(datetime.now())} Number of price breakout tickers: {len(price_breakout_tickers)}\n')
    f.write(f'[INFO ] {str(datetime.now())} Tickers include: {", ".join(price_breakout_tickers)}\n')

    current_time = datetime.now()
    f.write(f'[END  ] {str(datetime.now())} Check breakout at market close job ended\n')
    