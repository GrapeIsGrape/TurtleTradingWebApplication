from classes.data_retriever import *
from classes.calculator import *
from classes.constants import *
from classes.helper import *
from classes.data_retriever import *
from classes.breakout_checker import *
from classes.exit_checker import *

def main():
    # print('=====================[Start]======================')
    # start_time = datetime.now()
    # print('Start time: ', start_time)

    abc = check_if_market_is_open()
    print(abc)

    #region Download market data and calculate indicators for all tickers

    # print('===================Market Data====================')
    # tickers = get_all_unique_tickers()
    # download_market_data_for_tickers(tickers, PERIOD_5Y)
    # enrich_with_indicators_for_tickers(tickers, PERIOD_5Y)

    # #endregion

    # print('=====================BreakOut=====================')

    # price_breakout_tickers = check_price_breakout_for_tickers(tickers, 20)
    # breakout_ticker_info = get_breakout_ticker_information(price_breakout_tickers)
    # print(breakout_ticker_info)

    # print('=======================Exit=======================')

    # exit_tickers = check_exit_for_positions()
    # print('Positions to exit:') 
    # print(exit_tickers)

    # print('==================================================')

    # moving_average_breakout_tickers = check_moving_average_breakout_for_tickers(tickers, MA_20, MA_50)
    # bullish_arrangement_tickers = check_bullish_arrangement_for_tickers(tickers)
    
    # breakout_tickers = get_duplicated_items_from_lists([price_breakout_tickers, moving_average_breakout_tickers, bullish_arrangement_tickers])
    # print(price_breakout_tickers)

    # endTime = datetime.now()
    # print('End time: ', endTime)
    # print('Time used: ', endTime - start_time)

    # print('=======================[End]======================')

if __name__ == "__main__":
    main()
