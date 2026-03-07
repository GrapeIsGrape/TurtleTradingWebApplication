"""Positions blueprint — CRUD for Turtle, DCA, Bond, and Option positions."""

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
from models import BondPosition, DCAPosition, OptionPosition, TurtlePosition, now_hkt
from services.db_service import sync_positions_csv
from services.position_service import (
    enrich_bond_position,
    enrich_dca_position,
    enrich_option_position,
)

positions_bp = Blueprint('positions', __name__)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def enrich_turtle_position(pos: TurtlePosition) -> dict:
    """Add live price, sector, stop-loss levels, and market value."""
    data = pos.to_dict()

    try:
        info = yf.Ticker(pos.ticker).info
        data['current']       = info.get('currentPrice', info.get('regularMarketPrice', 0)) or 0
        data['gics_industry'] = info.get('sector', info.get('industry', 'N/A'))
    except Exception as e:
        logger.error(f'yfinance error for {pos.ticker}: {e}')
        data['current']       = 0
        data['gics_industry'] = 'N/A'

    csv_path = os.path.join(MARKET_DATA_FOLDER_PATH, f'{pos.ticker}.csv')
    try:
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
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

    data['market_value']  = pos.num_positions * data['current']
    data['stop_loss_atr'] = pos.entry_price - (STOP_LOSS_ATR_MULTIPLIER * pos.atr_20)
    data['stop_loss_low'] = data['days_low_20']
    return data


def _redirect_tab(tab: str):
    return redirect(f'/positions?tab={tab}')


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

@positions_bp.route('/')
def index():
    active_tab = request.args.get('tab', 'turtle')

    # Turtle
    turtle_positions = []
    for pos in TurtlePosition.query.all():
        try:
            turtle_positions.append(enrich_turtle_position(pos))
        except Exception as e:
            logger.error(f'Error enriching turtle position {pos.ticker}: {e}')
            turtle_positions.append(pos.to_dict())

    # DCA
    dca_positions = []
    for pos in DCAPosition.query.all():
        try:
            dca_positions.append(enrich_dca_position(pos))
        except Exception as e:
            logger.error(f'Error enriching DCA position {pos.ticker}: {e}')
            dca_positions.append(pos.to_dict())

    # Bonds
    bond_positions = []
    for pos in BondPosition.query.all():
        try:
            bond_positions.append(enrich_bond_position(pos))
        except Exception as e:
            logger.error(f'Error enriching bond position {pos.instrument}: {e}')
            bond_positions.append(pos.to_dict())

    # Options
    option_positions = []
    for pos in OptionPosition.query.all():
        try:
            option_positions.append(enrich_option_position(pos))
        except Exception as e:
            logger.error(f'Error enriching option position {pos.id}: {e}')
            option_positions.append(pos.to_dict())

    # Correlation (only compute when that tab is active to save time)
    correlation = None
    if active_tab == 'correlation':
        from services.correlation_service import compute_correlation_matrix
        correlation = compute_correlation_matrix()

    return render_template(
        'positions/index.html',
        positions=turtle_positions,
        dca_positions=dca_positions,
        bond_positions=bond_positions,
        option_positions=option_positions,
        correlation=correlation,
        active_tab=active_tab,
    )


# ---------------------------------------------------------------------------
# Turtle CRUD
# ---------------------------------------------------------------------------

@positions_bp.route('/turtle/add', methods=['POST'])
def turtle_add():
    try:
        ticker = request.form.get('ticker', '').strip().upper()
        entry  = float(request.form.get('entry', 0))
        atr20  = float(request.form.get('atr20', 0))
        num_positions = int(request.form.get('positions', 0))
        system = request.form.get('system', 'System 2')
        notes  = request.form.get('notes', '')
        if not ticker:
            return _redirect_tab('turtle')
        if TurtlePosition.query.filter_by(ticker=ticker).first():
            logger.warning(f'Ticker {ticker} already exists in turtle positions')
            return _redirect_tab('turtle')
        pos = TurtlePosition(
            ticker=ticker, entry_price=entry, atr_20=atr20,
            num_positions=num_positions, system=system, notes=notes,
            opened_at=now_hkt(), updated_at=now_hkt(),
        )
        db.session.add(pos)
        db.session.commit()
        sync_positions_csv()
        logger.info(f'Added turtle position: {ticker}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error adding turtle position: {e}')
    return _redirect_tab('turtle')


@positions_bp.route('/turtle/<int:pos_id>/edit', methods=['POST'])
def turtle_edit(pos_id: int):
    try:
        pos = TurtlePosition.query.get_or_404(pos_id)
        pos.ticker        = request.form.get('ticker', pos.ticker).strip().upper()
        pos.entry_price   = float(request.form.get('entry', pos.entry_price))
        pos.atr_20        = float(request.form.get('atr20', pos.atr_20))
        pos.num_positions = int(request.form.get('positions', pos.num_positions))
        pos.system        = request.form.get('system', pos.system)
        pos.notes         = request.form.get('notes', pos.notes)
        pos.updated_at    = now_hkt()
        db.session.commit()
        sync_positions_csv()
        logger.info(f'Edited turtle position: {pos.ticker}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error editing turtle position {pos_id}: {e}')
    return _redirect_tab('turtle')


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
    return _redirect_tab('turtle')


# ---------------------------------------------------------------------------
# DCA CRUD
# ---------------------------------------------------------------------------

@positions_bp.route('/dca/add', methods=['POST'])
def dca_add():
    try:
        ticker     = request.form.get('ticker', '').strip().upper()
        num_shares = float(request.form.get('num_shares', 0))
        avg_cost   = float(request.form.get('avg_cost', 0))
        notes      = request.form.get('notes', '')
        if not ticker:
            return _redirect_tab('dca')
        pos = DCAPosition(
            ticker=ticker, num_shares=num_shares, avg_cost=avg_cost,
            notes=notes, opened_at=now_hkt(), updated_at=now_hkt(),
        )
        db.session.add(pos)
        db.session.commit()
        logger.info(f'Added DCA position: {ticker}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error adding DCA position: {e}')
    return _redirect_tab('dca')


@positions_bp.route('/dca/<int:pos_id>/edit', methods=['POST'])
def dca_edit(pos_id: int):
    try:
        pos = DCAPosition.query.get_or_404(pos_id)
        pos.ticker     = request.form.get('ticker', pos.ticker).strip().upper()
        pos.num_shares = float(request.form.get('num_shares', pos.num_shares))
        pos.avg_cost   = float(request.form.get('avg_cost', pos.avg_cost))
        pos.notes      = request.form.get('notes', pos.notes)
        pos.updated_at = now_hkt()
        db.session.commit()
        logger.info(f'Edited DCA position: {pos.ticker}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error editing DCA position {pos_id}: {e}')
    return _redirect_tab('dca')


@positions_bp.route('/dca/<int:pos_id>/delete', methods=['POST'])
def dca_delete(pos_id: int):
    try:
        pos = DCAPosition.query.get_or_404(pos_id)
        ticker = pos.ticker
        db.session.delete(pos)
        db.session.commit()
        logger.info(f'Deleted DCA position: {ticker}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting DCA position {pos_id}: {e}')
    return _redirect_tab('dca')


# ---------------------------------------------------------------------------
# Bond CRUD
# ---------------------------------------------------------------------------

@positions_bp.route('/bonds/add', methods=['POST'])
def bond_add():
    try:
        instrument    = request.form.get('instrument', '').strip().upper()
        bond_type     = request.form.get('bond_type', 'bill')
        face_value    = float(request.form.get('face_value', 1000))
        purchase_price= float(request.form.get('purchase_price', 0))
        quantity      = float(request.form.get('quantity', 1))
        coupon_rate   = request.form.get('coupon_rate') or None
        maturity_date = request.form.get('maturity_date') or None
        notes         = request.form.get('notes', '')
        if coupon_rate:
            coupon_rate = float(coupon_rate)
        if not instrument:
            return _redirect_tab('bonds')
        pos = BondPosition(
            instrument=instrument, bond_type=bond_type, face_value=face_value,
            purchase_price=purchase_price, quantity=quantity,
            coupon_rate=coupon_rate, maturity_date=maturity_date, notes=notes,
            opened_at=now_hkt(), updated_at=now_hkt(),
        )
        db.session.add(pos)
        db.session.commit()
        logger.info(f'Added bond position: {instrument}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error adding bond position: {e}')
    return _redirect_tab('bonds')


@positions_bp.route('/bonds/<int:pos_id>/edit', methods=['POST'])
def bond_edit(pos_id: int):
    try:
        pos = BondPosition.query.get_or_404(pos_id)
        pos.instrument     = request.form.get('instrument', pos.instrument).strip().upper()
        pos.bond_type      = request.form.get('bond_type', pos.bond_type)
        pos.face_value     = float(request.form.get('face_value', pos.face_value))
        pos.purchase_price = float(request.form.get('purchase_price', pos.purchase_price))
        pos.quantity       = float(request.form.get('quantity', pos.quantity))
        cr = request.form.get('coupon_rate')
        pos.coupon_rate    = float(cr) if cr else None
        md = request.form.get('maturity_date')
        pos.maturity_date  = md if md else None
        pos.notes          = request.form.get('notes', pos.notes)
        pos.updated_at     = now_hkt()
        db.session.commit()
        logger.info(f'Edited bond position: {pos.instrument}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error editing bond position {pos_id}: {e}')
    return _redirect_tab('bonds')


@positions_bp.route('/bonds/<int:pos_id>/delete', methods=['POST'])
def bond_delete(pos_id: int):
    try:
        pos = BondPosition.query.get_or_404(pos_id)
        instrument = pos.instrument
        db.session.delete(pos)
        db.session.commit()
        logger.info(f'Deleted bond position: {instrument}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting bond position {pos_id}: {e}')
    return _redirect_tab('bonds')


# ---------------------------------------------------------------------------
# Option CRUD
# ---------------------------------------------------------------------------

@positions_bp.route('/options/add', methods=['POST'])
def option_add():
    try:
        ticker      = request.form.get('ticker', '').strip().upper()
        option_type = request.form.get('option_type', 'put')
        direction   = request.form.get('direction', 'short')
        strike      = float(request.form.get('strike', 0))
        expiry_date = request.form.get('expiry_date', '')
        premium     = float(request.form.get('premium', 0))
        contracts   = int(request.form.get('contracts', 1))
        notes       = request.form.get('notes', '')
        if not ticker or not expiry_date:
            return _redirect_tab('options')
        pos = OptionPosition(
            ticker=ticker, option_type=option_type, direction=direction,
            strike=strike, expiry_date=expiry_date, premium=premium,
            contracts=contracts, status='open', notes=notes,
            opened_at=now_hkt(), updated_at=now_hkt(),
        )
        db.session.add(pos)
        db.session.commit()
        logger.info(f'Added option position: {ticker} {option_type} {strike}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error adding option position: {e}')
    return _redirect_tab('options')


@positions_bp.route('/options/<int:pos_id>/edit', methods=['POST'])
def option_edit(pos_id: int):
    try:
        pos = OptionPosition.query.get_or_404(pos_id)
        pos.ticker      = request.form.get('ticker', pos.ticker).strip().upper()
        pos.option_type = request.form.get('option_type', pos.option_type)
        pos.direction   = request.form.get('direction', pos.direction)
        pos.strike      = float(request.form.get('strike', pos.strike))
        pos.expiry_date = request.form.get('expiry_date', pos.expiry_date)
        pos.premium     = float(request.form.get('premium', pos.premium))
        pos.contracts   = int(request.form.get('contracts', pos.contracts))
        pos.notes       = request.form.get('notes', pos.notes)
        pos.updated_at  = now_hkt()
        db.session.commit()
        logger.info(f'Edited option position: {pos.ticker}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error editing option position {pos_id}: {e}')
    return _redirect_tab('options')


@positions_bp.route('/options/<int:pos_id>/close', methods=['POST'])
def option_close(pos_id: int):
    """Mark an option as closed with a close price."""
    try:
        pos = OptionPosition.query.get_or_404(pos_id)
        pos.close_price = float(request.form.get('close_price', 0))
        pos.status      = request.form.get('status', 'closed')
        pos.updated_at  = now_hkt()
        db.session.commit()
        logger.info(f'Closed option position: {pos.ticker} #{pos_id}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error closing option position {pos_id}: {e}')
    return _redirect_tab('options')


@positions_bp.route('/options/<int:pos_id>/delete', methods=['POST'])
def option_delete(pos_id: int):
    try:
        pos = OptionPosition.query.get_or_404(pos_id)
        ticker = pos.ticker
        db.session.delete(pos)
        db.session.commit()
        logger.info(f'Deleted option position: {ticker} #{pos_id}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting option position {pos_id}: {e}')
    return _redirect_tab('options')
