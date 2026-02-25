# Tickers

TICKERS = ['GOOG', 'QCOM']

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
DAYS_HIGH_50 = '50-Days High'
DAYS_HIGH_100 = '100-Days High'
DAYS_HIGH_200 = '200-Days High'
DAYS_LOW_10 = '10-Days Low'

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

# tickers
# As of 2026-02-24
# Criterias for selecting these tickers:
# 1. Belongs to S&P 500 index
# 2. Liquidity (critical for Turtle breakouts):
# – 30-day avg daily share volume ≥ 1,000,000 shares
# – OR 30-day avg daily dollar volume ≥ $75–100 million (the stricter of the two).
# 3. Price: ≥ $20 (avoids large gap risk on low-priced names).
# 4. Volatility (to ensure tradable trends):
# – 20-day annualized historical volatility ≥ 25%
# – OR 14-day ATR as % of price ≥ 1.8–2.0%.
# 5. Diversification / Sector cap
# - Max 7 stocks per GICS sector (11 sectors).
# - Within each sector, ranked by liquidity score + volatility score, keeping the best trend-following candidates.
# 6. Soft rules: Skipped anything with earnings in the next 5 days at scan time; avoided obvious low-float or biotech weirdos.

TICKERS_INFORMATION_TECHNOLOGY = ['NVDA', 'AAPL', 'MSFT', 'AVGO', 'AMD', 'QCOM', 'TXN']
TICKERS_COMMUNICATION_SERVICES = ['META', 'GOOGL', 'GOOG', 'NFLX', 'DIS', 'CMCSA']
TICKERS_CONSUMER_DISCRETIONARY = ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'BKNG', 'TJX']
TICKERS_CONSUMER_STAPLES = ['PG', 'COST', 'KO', 'PEP', 'WMT', 'CL']
TICKERS_HEALTH_CARE = ['LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'PFE', 'AMGN']
TICKERS_FINANCIALS = ['JPM', 'V', 'MA', 'BRK-B', 'BAC', 'WFC', 'GS']
TICKERS_INDUSTRIALS = ['CAT', 'GE', 'HON', 'UNP', 'LMT', 'RTX', 'BA']
TICKERS_ENERGY = ['XOM', 'CVX', 'COP', 'SLB', 'EOG']
TICKERS_MATERIALS = ['LIN', 'SHW', 'FCX', 'NUE']
TICKERS_UTILITIES = ['NEE', 'SO', 'DUK']
TICKERS_REAL_ESTATE = ['PLD', 'AMT', 'WELL']

TICKERS_ALL_SECTORS = TICKERS_INFORMATION_TECHNOLOGY + TICKERS_COMMUNICATION_SERVICES + TICKERS_CONSUMER_DISCRETIONARY + TICKERS_CONSUMER_STAPLES + TICKERS_HEALTH_CARE + TICKERS_FINANCIALS + TICKERS_INDUSTRIALS + TICKERS_ENERGY + TICKERS_MATERIALS + TICKERS_UTILITIES + TICKERS_REAL_ESTATE