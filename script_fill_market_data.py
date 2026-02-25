import os
from datetime import datetime

from classes.data_retriever import *
from classes.constants import *

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory +'script_logs/fill_market_data.log', 'a') as f:
    f.write(f'[START] {str(datetime.now())} Fill market data job started\n')

    tickers = get_all_unique_tickers(current_script_directory)
    download_market_data_for_tickers(tickers, PERIOD_5Y, current_script_directory)
    enrich_with_indicators_for_tickers(tickers, PERIOD_5Y, current_script_directory)

    current_time = datetime.now()
    f.write(f'[END  ] {str(datetime.now())} Fill market data job ended ({len(tickers)} tickers filled)\n')

    