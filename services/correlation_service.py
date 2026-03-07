"""Correlation matrix for open Turtle and DCA equity positions.

Options and bonds are intentionally excluded:
- Options are derivatives with non-linear price behaviour (delta-dependent).
- Individual bonds/bills lack meaningful daily price series for return correlation.
"""
from __future__ import annotations

import logging
import os

import pandas as pd
import yfinance as yf

from classes.constants import MARKET_DATA_FOLDER_PATH

logger = logging.getLogger(__name__)
LOOKBACK = 252   # trading days (~1 year)


def _load_closes(ticker: str) -> pd.Series | None:
    """
    Return a Series of closing prices for `ticker`.
    Tries local market-data CSV first; falls back to yfinance download.
    Returns None if data is unavailable or too short.
    """
    # 1. Local CSV (fast path — always available for watchlist tickers)
    path = os.path.join(MARKET_DATA_FOLDER_PATH, f'{ticker}.csv')
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if 'Close' in df.columns and len(df) >= 20:
                return df['Close'].tail(LOOKBACK)
        except Exception as e:
            logger.warning(f'CSV read error for {ticker}: {e}')

    # 2. yfinance fallback (for DCA tickers like VTI, QQQM not in watchlist)
    try:
        logger.info(f'Downloading price history for {ticker} via yfinance')
        hist = yf.Ticker(ticker).history(period='1y')
        if not hist.empty and 'Close' in hist.columns and len(hist) >= 20:
            return hist['Close'].tail(LOOKBACK)
    except Exception as e:
        logger.error(f'yfinance fallback error for {ticker}: {e}')

    return None


def compute_correlation_matrix() -> dict:
    """
    Compute pairwise return correlations for all open Turtle + DCA equity positions.

    Returns:
        {
            'tickers': ['AAPL', 'VTI', ...],
            'matrix':  [[1.0, 0.72, ...], ...],   # NxN, None for missing pairs
            'error':   None  or  'reason string'
        }
    """
    from models import DCAPosition, TurtlePosition

    turtle_tickers = [p.ticker for p in TurtlePosition.query.all()]
    dca_tickers    = [p.ticker for p in DCAPosition.query.all()]
    tickers = list(dict.fromkeys(turtle_tickers + dca_tickers))   # ordered, deduplicated

    if len(tickers) < 2:
        return {
            'tickers': tickers,
            'matrix': [],
            'error': 'Need at least 2 positions to compute a correlation matrix.',
        }

    price_series = {}
    for ticker in tickers:
        closes = _load_closes(ticker)
        if closes is not None:
            price_series[ticker] = closes.values
        else:
            logger.warning(f'No price data available for {ticker} — excluded from correlation')

    if len(price_series) < 2:
        return {
            'tickers': tickers,
            'matrix': [],
            'error': 'Not enough price data found to compute correlation. '
                     'Ensure market data CSVs exist or internet is available for yfinance fallback.',
        }

    # Align on minimum available length
    min_len = min(len(v) for v in price_series.values())
    df_prices = pd.DataFrame({t: v[-min_len:] for t, v in price_series.items()})
    returns = df_prices.pct_change().dropna()
    corr = returns.corr()

    valid_tickers = list(corr.columns)
    matrix = []
    for t1 in valid_tickers:
        row = []
        for t2 in valid_tickers:
            val = corr.loc[t1, t2]
            row.append(round(float(val), 3) if not pd.isna(val) else None)
        matrix.append(row)

    return {'tickers': valid_tickers, 'matrix': matrix, 'error': None}
