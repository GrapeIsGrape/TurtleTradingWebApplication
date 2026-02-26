# Rounding

ROUND_DP = 4

# Column name

TICKER = 'Ticker'
CURRENT_PRICE = 'Current Price'
STOP_LOSS = 'Stop Loss'
BULLISH_ARRANGEMENT = 'Bullish'

DATE = 'Date'
OPEN = 'Open'
HIGH = 'High'
LOW = 'Low'
CLOSE = 'Close'
VOLUME = 'Volume'
TRUE_RANGE = 'True Range'
ATR_20 = 'ATR-20'
ATR_55 = 'ATR-55'
MA_5 = 'MA-5'
MA_10 = 'MA-10'
MA_20 = 'MA-20'
MA_30 = 'MA-30'
MA_50 = 'MA-50'
MA_100 = 'MA-100'
MA_200 = 'MA-200'
DAYS_HIGH_10 = '10-Days High'
DAYS_HIGH_20 = '20-Days High'
DAYS_HIGH_30 = '30-Days High'
DAYS_HIGH_55 = '55-Days High'
DAYS_HIGH_100 = '100-Days High'
DAYS_HIGH_200 = '200-Days High'
DAYS_LOW_10 = '10-Days Low'
DAYS_LOW_20 = '20-Days Low'
DAYS_LOW_30 = '30-Days Low'
DAYS_LOW_55 = '55-Days Low'
DAYS_LOW_100 = '100-Days Low'
DAYS_LOW_200 = '200-Days Low'

# yfinance history length

PERIOD_1D = '1d'
PERIOD_5D = '5d'
PERIOD_1M = '1mo'
PERIOD_3M = '3mo'
PERIOD_6M = '6mo'
PERIOD_1Y = '1y'
PERIOD_2Y = '2y'
PERIOD_5Y = '5y'
PERIOD_10Y = '10y'
PERIOD_YTD = 'ytd'
PERIOD_MAX = 'max'

# path

MARKET_DATA_FOLDER_PATH = 'data/market_data'
TICKERS_TO_BE_RETRIEVED_FOLDER_PATH = 'data/tickers_to_be_retrieved'
CURRENT_POSITIONS_FILE_PATH = 'data/positions.csv'
SCRIPT_LOGS_FOLDER_PATH = 'script_logs'
BREAKOUT_LOG_MARKET_CLOSE = 'breakout_check_market_close_full_breakout_list.log'
BREAKOUT_LOG_MARKET_OPEN = 'breakout_check_market_open_full_breakout_list.log'
MAIN_LOG_BREAKOUT_MARKET_CLOSE = 'breakout_check_market_close.log'
MAIN_LOG_BREAKOUT_MARKET_OPEN = 'breakout_check_market_open.log'
MAIN_LOG_FILL_MARKET_DATA = 'fill_market_data.log'

# Others

N_DAYS_HIGH_LIST = [20,55]

# Ticker Filter Criteria

FILTER_MIN_PRICE = 20  # Minimum price in USD
FILTER_MIN_VOLUME = 1_000_000  # Minimum 30-day avg daily share volume
FILTER_MIN_DOLLAR_VOLUME = 75_000_000  # Minimum 30-day avg daily dollar volume in USD
FILTER_MIN_VOLATILITY = 25  # Minimum 20-day annualized historical volatility percentage
FILTER_MIN_ATR_PCT = 1.8  # Minimum 14-day ATR as percentage of price
FILTER_MAX_PER_SECTOR = 7  # Maximum stocks per GICS sector
FILTER_EARNINGS_SKIP_DAYS = 5  # Skip stocks with earnings in next N days