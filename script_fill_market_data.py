# import sys
import os
# current_dir = os.path.dirname(os.path.abspath(__file__))
# target_folder = os.path.join(current_dir, '..', 'classes')
# sys.path.insert(0, target_folder)

from datetime import datetime

from classes.data_retriever import *
from classes.constants import *

current_script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'

with open(current_script_directory +'script_logs/fill_market_data.log', 'a') as f:
    f.write(f'[START] {str(datetime.now())} Fill market data job started\n')
    f.write(f'[INFO ] {str(datetime.now())} Current script directory is {current_script_directory}\n')

    tickers = get_all_unique_tickers(current_script_directory)
    f.write(f'[INFO ] {str(datetime.now())} Ready to fill data of {len(tickers)} tickers\n')
    download_market_data_for_tickers(tickers, PERIOD_5Y, current_script_directory)
    enrich_with_indicators_for_tickers(tickers, PERIOD_5Y, current_script_directory)

    current_time = datetime.now()
    f.write(f'[END  ] {str(datetime.now())} Fill market data job ended\n')

    