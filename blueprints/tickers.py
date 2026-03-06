"""Tickers blueprint — sector ticker management."""

import csv
import logging
import os

from flask import Blueprint, current_app, redirect, render_template, request

from classes.breakout_checker import filter_tickers_by_reset_signal, get_breakout_ticker_information_close
from classes.constants import (
    BULLISH_ARRANGEMENT,
    CURRENT_POSITIONS_FILE_PATH,
    FILTER_EARNINGS_SKIP_DAYS,
    FILTER_MAX_PER_SECTOR,
    FILTER_MIN_ATR_PCT,
    FILTER_MIN_DOLLAR_VOLUME,
    FILTER_MIN_PRICE,
    FILTER_MIN_VOLATILITY,
    FILTER_MIN_VOLUME,
    PERIOD_5Y,
    TICKERS_FOLDER_PATH,
)
from classes.data_retriever import download_market_data_for_ticker, enrich_with_indicators_for_tickers
from classes.ticker_filter import filter_and_save_tickers
from models import TurtlePosition

tickers_bp = Blueprint('tickers', __name__)

logger = logging.getLogger(__name__)


def _sector_dir() -> str:
    return os.path.join(current_app.config['BASE_DIR'], TICKERS_FOLDER_PATH)


def get_sector_files():
    sector_dir = _sector_dir()
    sector_files = []
    if os.path.exists(sector_dir):
        for fname in sorted(os.listdir(sector_dir)):
            if fname.endswith('.csv') and os.path.isfile(os.path.join(sector_dir, fname)):
                sector_name = os.path.splitext(fname)[0].replace('_', ' ').title()
                sector_files.append((sector_name, fname))
    return sector_files


@tickers_bp.route('/')
def tickers():
    sector_dir = _sector_dir()
    sectors = []
    all_tickers = []

    for sector_name, filename in get_sector_files():
        path = os.path.join(sector_dir, filename)
        tickers_list = []
        if os.path.exists(path):
            with open(path, newline='') as f:
                reader = csv.DictReader(f)
                tickers_list = [
                    str(row.get('Ticker', '')).strip().upper()
                    for row in reader
                    if str(row.get('Ticker', '')).strip()
                ]
        all_tickers.extend(tickers_list)
        file_key = os.path.splitext(filename)[0]
        sectors.append({
            'name': sector_name,
            'tickers': tickers_list,
            'file_key': file_key,
            'filename': filename,
        })

    # Bullish arrangement check
    bullish_tickers = set()
    if all_tickers:
        try:
            df = get_breakout_ticker_information_close(all_tickers)
            if not df.empty:
                bullish_tickers = set(
                    df[df[BULLISH_ARRANGEMENT] == True]['Ticker'].tolist()
                )
        except Exception as e:
            logger.error(f'Error getting bullish tickers: {e}')

    # Position tickers from SQLite
    position_tickers = {p.ticker for p in TurtlePosition.query.all()}

    reset_tickers_20 = set(filter_tickers_by_reset_signal(all_tickers, 20))
    reset_tickers_55 = set(filter_tickers_by_reset_signal(all_tickers, 55))

    return render_template(
        'tickers.html',
        sectors=sectors,
        bullish_tickers=bullish_tickers,
        position_tickers=position_tickers,
        reset_tickers_20=reset_tickers_20,
        reset_tickers_55=reset_tickers_55,
        FILTER_MIN_PRICE=FILTER_MIN_PRICE,
        FILTER_MIN_VOLUME=FILTER_MIN_VOLUME,
        FILTER_MIN_DOLLAR_VOLUME=FILTER_MIN_DOLLAR_VOLUME,
        FILTER_MIN_VOLATILITY=FILTER_MIN_VOLATILITY,
        FILTER_MIN_ATR_PCT=FILTER_MIN_ATR_PCT,
        FILTER_MAX_PER_SECTOR=FILTER_MAX_PER_SECTOR,
        FILTER_EARNINGS_SKIP_DAYS=FILTER_EARNINGS_SKIP_DAYS,
    )


@tickers_bp.route('/update', methods=['POST'])
def update_tickers():
    sector_key = request.form.get('sector_key')
    tickers_str = request.form.get('tickers', '')
    tickers_list = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]

    sector_filename = None
    for sector_name, filename in get_sector_files():
        if os.path.splitext(filename)[0] == sector_key:
            sector_filename = filename
            break

    if sector_filename:
        file_path = os.path.join(_sector_dir(), sector_filename)
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Ticker'])
            writer.writeheader()
            for ticker in tickers_list:
                writer.writerow({'Ticker': ticker})

    return redirect('/tickers')


@tickers_bp.route('/refresh', methods=['POST'])
def refresh_tickers():
    try:
        sector_dir = _sector_dir()
        os.makedirs(sector_dir, exist_ok=True)
        filter_and_save_tickers(sector_dir)
        return redirect('/tickers')
    except Exception as e:
        logger.error(f'Error refreshing tickers: {e}', exc_info=True)
        return render_template('error_handling/error_handling.html', error=str(e)), 500


@tickers_bp.route('/retrieve', methods=['POST'])
def retrieve_ticker_data():
    ticker = request.form.get('ticker', '').strip().upper()
    if not ticker:
        return redirect('/tickers')

    try:
        base_path = current_app.config['BASE_DIR'] + '/'
        download_market_data_for_ticker(ticker, PERIOD_5Y, base_path)
        enrich_with_indicators_for_tickers([ticker], PERIOD_5Y, base_path)
        return redirect('/tickers')
    except Exception as e:
        logger.error(f'Error retrieving data for {ticker}: {e}', exc_info=True)
        return render_template('error_handling/error_handling.html', error=str(e)), 500
