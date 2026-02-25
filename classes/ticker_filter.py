"""
Ticker filtering module for Turtle Trading strategy.
Filters S&P 500 tickers based on liquidity, price, and volatility criteria.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import csv
import ssl

# Fix SSL certificate issue on macOS
ssl._create_default_https_context = ssl._create_unverified_context

def get_sp500_tickers():
    """
    Get list of S&P 500 tickers and their sectors.
    Returns: dict mapping ticker to sector
    """
    # Get S&P 500 tickers from Wikipedia
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    try:
        tables = pd.read_html(url)
        sp500_table = tables[0]
        
        ticker_sector_map = {}
        for _, row in sp500_table.iterrows():
            ticker = row['Symbol'].replace('.', '-')  # yfinance format
            sector = row['GICS Sector']
            ticker_sector_map[ticker] = sector
        
        return ticker_sector_map
    except Exception as e:
        print(f"Warning: Could not fetch S&P 500 list from Wikipedia: {e}")
        print("Using fallback static S&P 500 list...")
        # Fallback to a smaller hardcoded list of major stocks for testing
        return get_fallback_sp500_tickers()

def get_fallback_sp500_tickers():
    """
    Fallback S&P 500 tickers for when Wikipedia fetch fails.
    Returns a smaller list of major stocks from different sectors.
    """
    # Subset of S&P 500 stocks from different GICS sectors
    fallback_tickers = {
        'AAPL': 'Information Technology',
        'MSFT': 'Information Technology',
        'NVDA': 'Information Technology',
        'TSLA': 'Consumer Discretionary',
        'AMZN': 'Consumer Discretionary',
        'META': 'Communication Services',
        'GOOGL': 'Communication Services',
        'BRK-B': 'Financials',
        'JNJ': 'Health Care',
        'XOM': 'Energy',
        'JPM': 'Financials',
        'V': 'Financials',
        'WMT': 'Consumer Staples',
        'PG': 'Consumer Staples',
        'CVX': 'Energy',
        'KO': 'Consumer Staples',
        'BA': 'Industrials',
        'CAT': 'Industrials',
        'IBM': 'Information Technology',
        'CSCO': 'Information Technology',
        'ABT': 'Health Care',
        'UNH': 'Health Care',
        'MRK': 'Health Care',
        'PFE': 'Health Care',
        'GE': 'Industrials',
        'HON': 'Industrials',
        'INTC': 'Information Technology',
        'AMD': 'Information Technology',
        'QCOM': 'Information Technology',
        'ADBE': 'Information Technology',
        'CRM': 'Software',
        'ORCL': 'Software',
        'SAP': 'Software',
        'NOW': 'Software',
        'DIS': 'Communication Services',
        'NFLX': 'Communication Services',
        'CMCSA': 'Communication Services',
        'T': 'Communication Services',
        'VZ': 'Communication Services',
        'BKKING': 'Consumer Discretionary',
        'ABNB': 'Consumer Discretionary',
        'MCD': 'Consumer Discretionary',
        'NKE': 'Consumer Discretionary',
        'F': 'Consumer Discretionary',
        'GM': 'Consumer Discretionary',
        'HD': 'Consumer Discretionary',
        'LOW': 'Consumer Discretionary',
        'TJX': 'Consumer Discretionary',
        'MU': 'Information Technology',
        'UBER': 'Consumer Discretionary',
        'LYFT': 'Consumer Discretionary',
        'SPOT': 'Communication Services',
        'ZM': 'Communication Services',
    }
    return fallback_tickers

def calculate_ticker_metrics(ticker):
    """
    Calculate liquidity, price, and volatility metrics for a ticker.
    Returns: dict with metrics or None if data unavailable
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Get 60 days of data for calculations
        hist = stock.history(period='60d')
        
        if hist.empty or len(hist) < 30:
            return None
        
        # Current price
        current_price = hist['Close'].iloc[-1]
        
        # 30-day average volume
        avg_volume_30d = hist['Volume'].tail(30).mean()
        
        # 30-day average dollar volume
        avg_dollar_volume_30d = (hist['Close'] * hist['Volume']).tail(30).mean()
        
        # Calculate ATR (14-day)
        high_low = hist['High'] - hist['Low']
        high_close = abs(hist['High'] - hist['Close'].shift())
        low_close = abs(hist['Low'] - hist['Close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_14 = true_range.tail(14).mean()
        atr_pct = (atr_14 / current_price) * 100
        
        # Calculate 20-day annualized volatility
        returns = hist['Close'].pct_change().dropna()
        volatility_20d = returns.tail(20).std() * (252 ** 0.5) * 100  # Annualized %
        
        return {
            'ticker': ticker,
            'price': current_price,
            'avg_volume_30d': avg_volume_30d,
            'avg_dollar_volume_30d': avg_dollar_volume_30d,
            'atr_pct': atr_pct,
            'volatility_20d': volatility_20d
        }
    except Exception as e:
        print(f"Error processing {ticker}: {e}")
        return None

def filter_ticker(metrics):
    """
    Apply Turtle Trading criteria to filter tickers.
    Returns: True if ticker passes all criteria
    """
    if not metrics:
        return False
    
    # Price criterion: >= $20
    if metrics['price'] < 20:
        return False
    
    # Liquidity criterion: 30-day avg volume >= 1M shares OR avg dollar volume >= $75M
    if metrics['avg_volume_30d'] < 1_000_000 and metrics['avg_dollar_volume_30d'] < 75_000_000:
        return False
    
    # Volatility criterion: 20-day annualized volatility >= 25% OR 14-day ATR % >= 1.8%
    if metrics['volatility_20d'] < 25 and metrics['atr_pct'] < 1.8:
        return False
    
    return True

def calculate_score(metrics):
    """
    Calculate ranking score based on liquidity and volatility.
    Higher is better for trend-following.
    """
    liquidity_score = metrics['avg_dollar_volume_30d'] / 1_000_000  # In millions
    volatility_score = (metrics['volatility_20d'] + metrics['atr_pct'] * 10) / 2  # Weighted combo
    return liquidity_score + volatility_score * 10

def filter_and_save_tickers(output_dir, max_per_sector=7):
    """
    Main function to filter S&P 500 tickers and save by sector.
    """
    print(f"[{datetime.now()}] Starting ticker filtering process...")
    
    # Get S&P 500 tickers
    print(f"[{datetime.now()}] Fetching S&P 500 tickers...")
    ticker_sector_map = get_sp500_tickers()
    print(f"[{datetime.now()}] Found {len(ticker_sector_map)} tickers")
    
    # Calculate metrics for all tickers
    print(f"[{datetime.now()}] Calculating metrics for all tickers...")
    ticker_metrics = {}
    for i, ticker in enumerate(ticker_sector_map.keys(), 1):
        if i % 50 == 0:
            print(f"[{datetime.now()}] Processed {i}/{len(ticker_sector_map)} tickers...")
        metrics = calculate_ticker_metrics(ticker)
        if metrics and filter_ticker(metrics):
            metrics['sector'] = ticker_sector_map[ticker]
            metrics['score'] = calculate_score(metrics)
            ticker_metrics[ticker] = metrics
    
    print(f"[{datetime.now()}] {len(ticker_metrics)} tickers passed filtering criteria")
    
    # Group by sector and rank
    sector_tickers = {}
    for ticker, metrics in ticker_metrics.items():
        sector = metrics['sector']
        if sector not in sector_tickers:
            sector_tickers[sector] = []
        sector_tickers[sector].append((ticker, metrics['score']))
    
    # Select top tickers per sector and save to CSV
    os.makedirs(output_dir, exist_ok=True)
    
    for sector, tickers_scores in sector_tickers.items():
        # Sort by score (descending) and take top N
        tickers_scores.sort(key=lambda x: x[1], reverse=True)
        top_tickers = [ticker for ticker, _ in tickers_scores[:max_per_sector]]
        
        # Sort alphabetically before saving
        top_tickers.sort()
        
        # Save to CSV
        sector_filename = sector.lower().replace(' ', '_').replace('&', 'and') + '.csv'
        file_path = os.path.join(output_dir, sector_filename)
        
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Ticker'])
            writer.writeheader()
            for ticker in top_tickers:
                writer.writerow({'Ticker': ticker})
        
        print(f"[{datetime.now()}] Saved {len(top_tickers)} tickers to {sector_filename}")
    
    print(f"[{datetime.now()}] Ticker filtering complete!")
    return len(ticker_metrics)

if __name__ == "__main__":
    # For testing
    output_dir = '../data/tickers_to_be_retrieved'
    filter_and_save_tickers(output_dir)
