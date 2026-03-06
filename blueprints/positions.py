"""Positions blueprint — CRUD for all four position types."""

import logging
import os

import pandas as pd
import yfinance as yf
from flask import Blueprint, redirect, render_template, request

from classes.constants import (
    DAYS_LOW_10,
    DAYS_LOW_20,
    MARKET_DATA_FOLDER_PATH,
    STOP_LOSS_ATR_MULTIPLIER,
)
from extensions import db
from models import TurtlePosition, now_hkt
from services.db_service import sync_positions_csv

positions_bp = Blueprint('positions', __name__)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def enrich_turtle_position(pos: TurtlePosition) -> dict:
    """Add live price, sector, stop-loss, and market value to a turtle position."""
    data = pos.to_dict()
    data['entry'] = pos.entry_price
    data['atr20'] = pos.atr_20
    data['positions'] = pos.num_positions

    try:
        info = yf.Ticker(pos.ticker).info
        data['current'] = info.get('currentPrice', info.get('regularMarketPrice', 0)) or 0
        data['gics_industry'] = info.get('sector', info.get('industry', 'N/A'))
    except Exception as e:
        logger.error(f'yfinance error for {pos.ticker}: {e}')
        data['current'] = 0
        data['gics_industry'] = 'N/A'

    market_data_path = os.path.join(MARKET_DATA_FOLDER_PATH, f'{pos.ticker}.csv')
    try:
        if os.path.exists(market_data_path):
            df = pd.read_csv(market_data_path)
            if not df.empty:
                latest = df.iloc[-1]
                data['days_low_10'] = latest.get(DAYS_LOW_10, 0)
                data['days_low_20'] = latest.get(DAYS_LOW_20, 0)
            else:
                data['days_low_10'] = data['days_low_20'] = 0
        else:
            data['days_low_10'] = data['days_low_20'] = 0
    except Exception as e:
        logger.error(f'Market data error for {pos.ticker}: {e}')
        data['days_low_10'] = data['days_low_20'] = 0

    data['market_value'] = pos.num_positions * data['current']
    data['stop_loss_atr'] = pos.entry_price - (STOP_LOSS_ATR_MULTIPLIER * pos.atr_20)
    data['stop_loss_low'] = data['days_low_20']

    return data


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@positions_bp.route('/')
def index():
    """Main positions page — turtle tab by default."""
    turtle_positions = []
    for pos in TurtlePosition.query.all():
        try:
            turtle_positions.append(enrich_turtle_position(pos))
        except Exception as e:
            logger.error(f'Error enriching position {pos.ticker}: {e}')
            turtle_positions.append(pos.to_dict())

    return render_template('positions/index.html', positions=turtle_positions)


# ---------------------------------------------------------------------------
# Turtle CRUD
# ---------------------------------------------------------------------------

@positions_bp.route('/turtle/add', methods=['POST'])
def turtle_add():
    try:
        ticker = request.form.get('ticker', '').strip().upper()
        entry = float(request.form.get('entry', 0))
        atr20 = float(request.form.get('atr20', 0))
        num_positions = int(request.form.get('positions', 0))
        system = request.form.get('system', 'System 2')
        notes = request.form.get('notes', '')

        if not ticker:
            return redirect('/positions')

        if TurtlePosition.query.filter_by(ticker=ticker).first():
            logger.warning(f'Ticker {ticker} already exists in turtle positions')
            return redirect('/positions')

        pos = TurtlePosition(
            ticker=ticker,
            entry_price=entry,
            atr_20=atr20,
            num_positions=num_positions,
            system=system,
            notes=notes,
            opened_at=now_hkt(),
            updated_at=now_hkt(),
        )
        db.session.add(pos)
        db.session.commit()
        sync_positions_csv()
        logger.info(f'Added turtle position: {ticker}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error adding turtle position: {e}')

    return redirect('/positions')


@positions_bp.route('/turtle/<int:pos_id>/edit', methods=['POST'])
def turtle_edit(pos_id: int):
    try:
        pos = TurtlePosition.query.get_or_404(pos_id)
        pos.ticker = request.form.get('ticker', pos.ticker).strip().upper()
        pos.entry_price = float(request.form.get('entry', pos.entry_price))
        pos.atr_20 = float(request.form.get('atr20', pos.atr_20))
        pos.num_positions = int(request.form.get('positions', pos.num_positions))
        pos.system = request.form.get('system', pos.system)
        pos.notes = request.form.get('notes', pos.notes)
        pos.updated_at = now_hkt()
        db.session.commit()
        sync_positions_csv()
        logger.info(f'Edited turtle position: {pos.ticker}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error editing turtle position {pos_id}: {e}')

    return redirect('/positions')


@positions_bp.route('/turtle/<int:pos_id>/delete', methods=['POST'])
def turtle_delete(pos_id: int):
    try:
        pos = TurtlePosition.query.get_or_404(pos_id)
        ticker = pos.ticker
        db.session.delete(pos)
        db.session.commit()
        sync_positions_csv()
        logger.info(f'Deleted turtle position: {ticker}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting turtle position {pos_id}: {e}')

    return redirect('/positions')
