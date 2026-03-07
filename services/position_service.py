"""Position enrichment and P&L calculations for DCA, Bond, and Option positions."""

import logging
import os
from datetime import datetime

import pytz
import yfinance as yf

logger = logging.getLogger(__name__)
HKT = pytz.timezone('Asia/Hong_Kong')


def enrich_dca_position(pos) -> dict:
    """Add live price and P&L to a DCA position."""
    data = pos.to_dict()
    try:
        info = yf.Ticker(pos.ticker).info
        data['current'] = info.get('currentPrice', info.get('regularMarketPrice', 0)) or 0
    except Exception as e:
        logger.error(f'yfinance error for DCA {pos.ticker}: {e}')
        data['current'] = 0

    data['cost_basis'] = pos.num_shares * pos.avg_cost
    data['market_value'] = pos.num_shares * data['current']
    data['pnl'] = data['market_value'] - data['cost_basis']
    data['pnl_pct'] = (data['pnl'] / data['cost_basis'] * 100) if data['cost_basis'] else 0
    return data


def enrich_bond_position(pos) -> dict:
    """Add computed yield and value to a bond/bill/note/ETF position."""
    data = pos.to_dict()
    data['total_cost'] = pos.purchase_price * pos.quantity

    if pos.bond_type == 'etf':
        try:
            info = yf.Ticker(pos.instrument).info
            data['current_price'] = (
                info.get('currentPrice', info.get('regularMarketPrice', pos.purchase_price))
                or pos.purchase_price
            )
        except Exception as e:
            logger.error(f'yfinance error for bond ETF {pos.instrument}: {e}')
            data['current_price'] = pos.purchase_price
        data['market_value'] = data['current_price'] * pos.quantity
        data['pnl'] = data['market_value'] - data['total_cost']
        data['expected_yield'] = None
    else:
        # T-bill / note / bond: no live price; use face value for return
        data['current_price'] = pos.purchase_price
        data['market_value'] = data['total_cost']
        data['pnl'] = (pos.face_value - pos.purchase_price) * pos.quantity
        data['expected_yield'] = None
        if pos.maturity_date:
            try:
                maturity = datetime.strptime(pos.maturity_date, '%Y-%m-%d')
                now = datetime.now(HKT).replace(tzinfo=None)
                years = max((maturity - now).days / 365.25, 0.001)
                ytm = ((pos.face_value / pos.purchase_price) ** (1.0 / years) - 1) * 100
                data['expected_yield'] = round(ytm, 2)
            except Exception as e:
                logger.error(f'YTM calc error for {pos.instrument}: {e}')

    return data


def enrich_option_position(pos) -> dict:
    """Add DTE and P&L to an option position."""
    data = pos.to_dict()
    premium_total = pos.premium * pos.contracts * 100
    data['premium_total'] = premium_total

    if pos.status != 'open' and pos.close_price is not None:
        close_total = pos.close_price * pos.contracts * 100
        if pos.direction == 'short':
            data['pnl'] = premium_total - close_total   # collected − buyback
        else:
            data['pnl'] = close_total - premium_total   # sold for − paid for
    else:
        data['pnl'] = None  # open position — no realised P&L

    try:
        expiry = datetime.strptime(pos.expiry_date, '%Y-%m-%d')
        now = datetime.now(HKT).replace(tzinfo=None)
        data['dte'] = max((expiry - now).days, 0)
    except Exception:
        data['dte'] = None

    return data
