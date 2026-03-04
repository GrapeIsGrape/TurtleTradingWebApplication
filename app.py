"""
Turtle Trading Web Application - Flask Backend

This Flask application provides a web interface for the Turtle Trading strategy,
allowing users to:
- View and manage S&P 500 sector tickers
- Monitor breakout opportunities (market open and close)
- Monitor exit signals (market open and close)
- Manage trading positions with CRUD operations
- View and filter ticker data
- Retrieve new ticker market data
- View application logs

Routes:
    /                  - Home page
    /tickers          - Manage and view S&P 500 tickers by sector
    /breakout         - View breakout opportunities (market close)
    /breakout_live    - View breakout opportunities (market open)
    /exit             - View exit signals (market close)
    /exit_live        - View exit signals (market open)
    /positions        - Manage trading positions with enriched data
    /positions/add    - Add new position (POST)
    /positions/edit   - Edit existing position (POST)
    /positions/delete - Delete position (POST)
    /raw_data         - Browse historical market data
    /logs             - View application logs
    /about            - About the application
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime
import pandas as pd
import os
import csv
import logging
import re
import subprocess
import sys
import yfinance as yf
from flask import Flask, render_template, request, redirect, jsonify

from classes.constants import (
    BULLISH_ARRANGEMENT,
    TICKERS_FOLDER_PATH,
    SCRIPT_LOGS_FOLDER_PATH,
    MARKET_CLOSE_BREAKOUT_RESULT_FILE_NAME,
    MARKET_OPEN_BREAKOUT_RESULT_FILE_NAME,
    MARKET_CLOSE_EXIT_RESULT_FILE_NAME,
    MARKET_OPEN_EXIT_RESULT_FILE_NAME,
    FILTER_MIN_PRICE,
    FILTER_MIN_VOLUME,
    FILTER_MIN_DOLLAR_VOLUME,
    FILTER_MIN_VOLATILITY,
    FILTER_MIN_ATR_PCT,
    FILTER_MAX_PER_SECTOR,
    FILTER_EARNINGS_SKIP_DAYS,
    PERIOD_5Y,
    CURRENT_POSITIONS_FILE_PATH,
    MARKET_DATA_FOLDER_PATH,
    DAYS_LOW_10,
    DAYS_LOW_20,
    STOP_LOSS_ATR_MULTIPLIER,
)
from classes.breakout_checker import (
    check_bullish_arrangement_for_tickers,
    get_breakout_ticker_information_close,
    get_breakout_ticker_information_live,
    filter_tickers_by_reset_signal,
)
from classes.exit_checker import check_exit_by_stop_loss, check_exit_by_stop_loss_live
from classes.helper import check_if_market_is_open
from classes.data_retriever import (
    download_market_data_for_ticker,
    enrich_with_indicators_for_tickers,
)
from classes.ticker_filter import filter_and_save_tickers


# =============================================================================
# FLASK APP SETUP
# =============================================================================

app = Flask(__name__)

# Get base directory
BASE_DIR = os.path.dirname(__file__)
SECTOR_DIR = os.path.join(BASE_DIR, TICKERS_FOLDER_PATH)
LOG_FOLDER = os.path.join(BASE_DIR, SCRIPT_LOGS_FOLDER_PATH)
LOG_ERROR_FILE = os.path.join(BASE_DIR, 'templates', 'error_handling', 'flask_errors.log')
MARKET_DATA_DIR = os.path.join(BASE_DIR, 'data', 'market_data')

# Configure logging
logging.basicConfig(
    filename=LOG_ERROR_FILE,
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)


# =============================================================================
# CONTEXT PROCESSORS & HELPERS
# =============================================================================

@app.context_processor
def inject_market_status() -> Dict[str, bool]:
    """Make market status available to all templates."""
    return {'market_is_open': check_if_market_is_open()}


def get_sector_files() -> List[Tuple[str, str]]:
    """
    Get all sector CSV files.
    
    Returns:
        List of tuples (sector_name, filename)
    """
    sector_files = []
    if os.path.exists(SECTOR_DIR):
        for fname in sorted(os.listdir(SECTOR_DIR)):
            if fname.endswith('.csv') and os.path.isfile(os.path.join(SECTOR_DIR, fname)):
                sector_name = os.path.splitext(fname)[0].replace('_', ' ').title()
                sector_files.append((sector_name, fname))
    return sector_files


def parse_breakout_log(log_path: str, group_by_date: bool = True) -> List[Dict[str, Any]]:
    """
    Parse breakout log file and return structured data.
    
    Args:
        log_path: Path to the log file
        group_by_date: If True, group by date only. If False, group by minute (YYYY-MM-DD HH:MM).
    
    Returns:
        List of dicts with timestamp/date, breakouts, and metadata
    """
    entries = []
    if not os.path.exists(log_path):
        return entries
    
    entry_dict: Dict[str, Dict[str, Any]] = {}
    
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for market closed message
        closed_match = re.match(r'\[(.*?)\] Market is closed, no breakout check performed', line)
        if closed_match:
            timestamp = closed_match.group(1)
            key = timestamp.split()[0] if group_by_date else timestamp.split('.')[0].rsplit(':', 1)[0]
            if key not in entry_dict:
                entry_dict[key] = {'market_closed': True, 'breakouts': []}
            continue
        
        # Check for breakout tickers
        breakout_match = re.match(
            r'\[(.*?)\] (.*?) [Bb]reakout tickers: ?(.*) \([Cc]ount: (\d+)\)',
            line
        )
        if breakout_match:
            timestamp, label, tickers_str, count = breakout_match.groups()
            tickers = [t.strip() for t in tickers_str.split(',') if t.strip()]
            key = timestamp.split()[0] if group_by_date else timestamp.split('.')[0].rsplit(':', 1)[0]
            if key not in entry_dict:
                entry_dict[key] = {'market_closed': False, 'breakouts': []}
            entry_dict[key]['breakouts'].append({'label': label, 'tickers': tickers})
    
    today_str = str(date.today())
    for key in sorted(entry_dict.keys(), reverse=True):
        entries.append({
            'timestamp': key,
            'is_today': key.startswith(today_str),
            'market_closed': entry_dict[key].get('market_closed', False),
            'breakouts': entry_dict[key].get('breakouts', [])
        })
    
    return entries


def parse_exit_log(log_path: str, group_by_date: bool = True) -> List[Dict[str, Any]]:
    """
    Parse exit log file and return structured data.
    
    Args:
        log_path: Path to the log file
        group_by_date: If True, group by date only. If False, group by minute (YYYY-MM-DD HH:MM).
    
    Returns:
        List of dicts with timestamp/date, exits, and metadata
    """
    entries = []
    if not os.path.exists(log_path):
        return entries
    
    entry_dict: Dict[str, Dict[str, Any]] = {}
    
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for market closed message
        closed_match = re.match(r'\[(.*?)\] Market is closed, no exit check performed', line)
        if closed_match:
            timestamp = closed_match.group(1)
            key = timestamp.split()[0] if group_by_date else timestamp.split('.')[0].rsplit(':', 1)[0]
            if key not in entry_dict:
                entry_dict[key] = {'market_closed': True, 'exits': []}
            continue
        
        # Check for exit tickers
        exit_match = re.match(
            r'\[(.*?)\] (.*?-days low) Exit tickers: ?(.*) \([Cc]ount: (\d+)\)',
            line
        )
        if exit_match:
            timestamp, label, tickers_str, count = exit_match.groups()
            tickers = [t.strip() for t in tickers_str.split(',') if t.strip()]
            key = timestamp.split()[0] if group_by_date else timestamp.split('.')[0].rsplit(':', 1)[0]
            if key not in entry_dict:
                entry_dict[key] = {'market_closed': False, 'exits': []}
            entry_dict[key]['exits'].append({'label': label, 'tickers': tickers})
    
    today_str = str(date.today())
    for key in sorted(entry_dict.keys(), reverse=True):
        entries.append({
            'timestamp': key,
            'is_today': key.startswith(today_str),
            'market_closed': entry_dict[key].get('market_closed', False),
            'exits': entry_dict[key].get('exits', [])
        })
    
    return entries


def get_breakout_ticker_info(
    tickers: List[str],
    use_live: bool = False
) -> Tuple[set, List[Dict[str, Any]]]:
    """
    Get breakout ticker information and bullish tickers.
    
    Args:
        tickers: List of tickers to analyze
        use_live: If True, use live market data; otherwise use close prices
        
    Returns:
        Tuple of (bullish_tickers_set, ticker_info_list)
    """
    if not tickers:
        return set(), []
    
    if use_live:
        ticker_info_df = get_breakout_ticker_information_live(tickers)
    else:
        ticker_info_df = get_breakout_ticker_information_close(tickers)
    
    if ticker_info_df.empty:
        return set(), []
    
    bullish_tickers = set(
        ticker_info_df[ticker_info_df[BULLISH_ARRANGEMENT] == True]['Ticker'].tolist()
    )
    ticker_info = ticker_info_df.to_dict('records')
    
    return bullish_tickers, ticker_info


# =============================================================================
# ROUTES - HOME & PAGES
# =============================================================================

@app.route("/")
def home() -> str:
    """Render home page."""
    return render_template("index.html")


@app.route("/about")
def about() -> str:
    """Render about page with filter configuration."""
    return render_template(
        "about.html",
        FILTER_MIN_PRICE=FILTER_MIN_PRICE,
        FILTER_MIN_VOLUME=FILTER_MIN_VOLUME,
        FILTER_MIN_DOLLAR_VOLUME=FILTER_MIN_DOLLAR_VOLUME,
        FILTER_MIN_VOLATILITY=FILTER_MIN_VOLATILITY,
        FILTER_MIN_ATR_PCT=FILTER_MIN_ATR_PCT,
        FILTER_MAX_PER_SECTOR=FILTER_MAX_PER_SECTOR,
        FILTER_EARNINGS_SKIP_DAYS=FILTER_EARNINGS_SKIP_DAYS,
    )


# =============================================================================
# ROUTES - BREAKOUT
# =============================================================================

@app.route("/breakout")
def breakout() -> str:
    """Display breakout opportunities at market close."""
    log_path = os.path.join(LOG_FOLDER, MARKET_CLOSE_BREAKOUT_RESULT_FILE_NAME)
    entries = parse_breakout_log(log_path, group_by_date=True)
    
    # Collect all tickers from the first entry with breakouts
    all_tickers = []
    for entry in entries:
        if entry.get('market_closed'):
            continue
        entry_tickers = []
        for breakout in entry.get('breakouts', []):
            entry_tickers.extend(breakout.get('tickers', []))
        if entry_tickers:
            all_tickers = entry_tickers
            break
    
    bullish_tickers, ticker_info = get_breakout_ticker_info(all_tickers, use_live=False)
    
    # Calculate reset tickers for both 20 and 55 day periods
    reset_tickers_20 = set(filter_tickers_by_reset_signal(all_tickers, 20))
    reset_tickers_55 = set(filter_tickers_by_reset_signal(all_tickers, 55))
    reset_tickers = reset_tickers_20 | reset_tickers_55
    
    # Add reset_tickers to each entry
    for entry in entries:
        entry['reset_tickers'] = reset_tickers
    
    return render_template(
        'breakout.html',
        entries=entries,
        page_title="Breakout (Close)",
        bullish_tickers=bullish_tickers,
        ticker_info=ticker_info
    )


@app.route("/breakout_live")
def breakout_live() -> str:
    """Display breakout opportunities during market hours."""
    log_path = os.path.join(LOG_FOLDER, MARKET_OPEN_BREAKOUT_RESULT_FILE_NAME)
    entries = parse_breakout_log(log_path, group_by_date=False)
    
    # Collect all tickers from the first entry with breakouts
    all_tickers = []
    for entry in entries:
        if entry.get('market_closed'):
            continue
        entry_tickers = []
        for breakout in entry.get('breakouts', []):
            entry_tickers.extend(breakout.get('tickers', []))
        if entry_tickers:
            all_tickers = entry_tickers
            break
    
    bullish_tickers, ticker_info = get_breakout_ticker_info(
        all_tickers,
        use_live=check_if_market_is_open()
    )
    
    # Calculate reset tickers for both 20 and 55 day periods
    reset_tickers_20 = set(filter_tickers_by_reset_signal(all_tickers, 20))
    reset_tickers_55 = set(filter_tickers_by_reset_signal(all_tickers, 55))
    reset_tickers = reset_tickers_20 | reset_tickers_55
    
    # Add reset_tickers to each entry
    for entry in entries:
        entry['reset_tickers'] = reset_tickers
    
    return render_template(
        'breakout.html',
        entries=entries,
        page_title="Breakout (Live)",
        bullish_tickers=bullish_tickers,
        ticker_info=ticker_info
    )


# =============================================================================
# ROUTES - EXIT
# =============================================================================

@app.route("/exit")
def exit() -> str:
    """Display exit opportunities at market close."""
    log_path = os.path.join(LOG_FOLDER, MARKET_CLOSE_EXIT_RESULT_FILE_NAME)
    entries = parse_exit_log(log_path, group_by_date=True)
    
    # Collect all tickers from the first entry with exits
    all_tickers = []
    for entry in entries:
        if entry.get('market_closed'):
            continue
        entry_tickers = []
        for exit_signal in entry.get('exits', []):
            entry_tickers.extend(exit_signal.get('tickers', []))
        if entry_tickers:
            all_tickers = entry_tickers
            break
    
    bullish_tickers, ticker_info = get_breakout_ticker_info(all_tickers, use_live=False)
    
    return render_template(
        'exit.html',
        entries=entries,
        page_title="Exit (Close)",
        bullish_tickers=bullish_tickers,
        ticker_info=ticker_info
    )


@app.route("/exit_live")
def exit_live() -> str:
    """Display exit opportunities during market hours."""
    log_path = os.path.join(LOG_FOLDER, MARKET_OPEN_EXIT_RESULT_FILE_NAME)
    entries = parse_exit_log(log_path, group_by_date=False)
    
    # Collect all tickers from the first entry with exits
    all_tickers = []
    for entry in entries:
        if entry.get('market_closed'):
            continue
        entry_tickers = []
        for exit_signal in entry.get('exits', []):
            entry_tickers.extend(exit_signal.get('tickers', []))
        if entry_tickers:
            all_tickers = entry_tickers
            break
    
    bullish_tickers, ticker_info = get_breakout_ticker_info(
        all_tickers,
        use_live=check_if_market_is_open()
    )
    
    return render_template(
        'exit.html',
        entries=entries,
        page_title="Exit (Live)",
        bullish_tickers=bullish_tickers,
        ticker_info=ticker_info
    )


# =============================================================================
# ROUTES - TICKERS
# =============================================================================

@app.route("/tickers")
def tickers() -> str:
    """Display and manage S&P 500 tickers by sector."""
    sectors = []
    all_tickers = []
    
    for sector_name, filename in get_sector_files():
        path = os.path.join(SECTOR_DIR, filename)
        tickers_list = []
        if os.path.exists(path):
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                tickers_list = [row['Ticker'] for row in reader]
        all_tickers.extend(tickers_list)
        file_key = os.path.splitext(filename)[0]
        sectors.append({
            "name": sector_name,
            "tickers": tickers_list,
            "file_key": file_key,
            "filename": filename
        })
    
    bullish_tickers, _ = get_breakout_ticker_info(all_tickers, use_live=False)
    
    # Calculate reset tickers for both 20 and 55 day periods
    reset_tickers_20 = set(filter_tickers_by_reset_signal(all_tickers, 20))
    reset_tickers_55 = set(filter_tickers_by_reset_signal(all_tickers, 55))
    
    return render_template(
        "tickers.html",
        sectors=sectors,
        bullish_tickers=bullish_tickers,
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


@app.route("/update_tickers", methods=["POST"])
def update_tickers() -> str:
    """Update tickers for a specific sector."""
    sector_key = request.form.get("sector_key")
    tickers_str = request.form.get("tickers", "")
    
    # Parse tickers from comma-separated string
    tickers_list = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
    
    # Find the matching sector file
    sector_filename = None
    for sector_name, filename in get_sector_files():
        if os.path.splitext(filename)[0] == sector_key:
            sector_filename = filename
            break
    
    if sector_filename:
        file_path = os.path.join(SECTOR_DIR, sector_filename)
        # Write updated tickers to CSV
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Ticker'])
            writer.writeheader()
            for ticker in tickers_list:
                writer.writerow({'Ticker': ticker})
    
    return redirect('/tickers')


@app.route("/refresh_tickers", methods=["POST"])
def refresh_tickers() -> Tuple[str, int]:
    """Refresh tickers based on Turtle Trading criteria."""
    try:
        os.makedirs(SECTOR_DIR, exist_ok=True)
        total_filtered = filter_and_save_tickers(SECTOR_DIR)
        logging.info(f'Successfully refreshed tickers. Total filtered: {total_filtered}')
        return redirect('/tickers')
    except Exception as e:
        logging.error(f'Error refreshing tickers: {e}', exc_info=True)
        error_msg = f'Error refreshing tickers: {str(e)}'
        return render_template(
            'error_handling/error_handling.html',
            error=error_msg,
            config=app.config
        ), 500


@app.route("/retrieve_ticker_data", methods=["POST"])
def retrieve_ticker_data() -> Tuple[str, int]:
    """Download market data for a specific ticker."""
    ticker = request.form.get("ticker", "").strip().upper()
    if not ticker:
        return redirect('/tickers')
    
    try:
        base_path = BASE_DIR + '/'
        download_market_data_for_ticker(ticker, PERIOD_5Y, base_path)
        enrich_with_indicators_for_tickers([ticker], PERIOD_5Y, base_path)
        logging.info(f'Successfully retrieved data for ticker: {ticker}')
        return redirect('/tickers')
    except Exception as e:
        logging.error(f'Error retrieving data for ticker {ticker}: {e}', exc_info=True)
        error_msg = f'Error retrieving data for ticker {ticker}: {str(e)}'
        return render_template(
            'error_handling/error_handling.html',
            error=error_msg,
            config=app.config
        ), 500


@app.route("/run_fill_market_data", methods=["POST"])
def run_fill_market_data() -> Tuple[Dict[str, Any], int]:
    """Run script_fill_market_data.py via subprocess."""
    try:
        script_path = os.path.join(BASE_DIR, 'script_fill_market_data.py')
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=3600
        )
        logging.info(f'Executed script_fill_market_data.py. Exit code: {result.returncode}')
        return jsonify({
            'status': 'success' if result.returncode == 0 else 'error',
            'message': 'Fill market data script completed',
            'exit_code': result.returncode,
            'stdout': result.stdout[-500:] if result.stdout else '',  # Last 500 chars
            'stderr': result.stderr[-500:] if result.stderr else ''
        }), 200
    except subprocess.TimeoutExpired:
        logging.error('script_fill_market_data.py execution timed out')
        return jsonify({
            'status': 'error',
            'message': 'Script execution timed out (max 1 hour)',
            'exit_code': -1
        }), 500
    except Exception as e:
        logging.error(f'Error running script_fill_market_data.py: {e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error executing script: {str(e)}',
            'exit_code': -1
        }), 500


@app.route("/run_market_signal_close", methods=["POST"])
def run_market_signal_close() -> Tuple[Dict[str, Any], int]:
    """Run script_market_signal_close.py via subprocess."""
    try:
        script_path = os.path.join(BASE_DIR, 'script_market_signal_close.py')
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=3600
        )
        logging.info(f'Executed script_market_signal_close.py. Exit code: {result.returncode}')
        return jsonify({
            'status': 'success' if result.returncode == 0 else 'error',
            'message': 'Market signal close script completed',
            'exit_code': result.returncode,
            'stdout': result.stdout[-500:] if result.stdout else '',
            'stderr': result.stderr[-500:] if result.stderr else ''
        }), 200
    except subprocess.TimeoutExpired:
        logging.error('script_market_signal_close.py execution timed out')
        return jsonify({
            'status': 'error',
            'message': 'Script execution timed out (max 1 hour)',
            'exit_code': -1
        }), 500
    except Exception as e:
        logging.error(f'Error running script_market_signal_close.py: {e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error executing script: {str(e)}',
            'exit_code': -1
        }), 500


@app.route("/run_market_signal_live", methods=["POST"])
def run_market_signal_live() -> Tuple[Dict[str, Any], int]:
    """Run script_market_signal_live.py via subprocess."""
    try:
        script_path = os.path.join(BASE_DIR, 'script_market_signal_live.py')
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=3600
        )
        logging.info(f'Executed script_market_signal_live.py. Exit code: {result.returncode}')
        return jsonify({
            'status': 'success' if result.returncode == 0 else 'error',
            'message': 'Market signal live script completed',
            'exit_code': result.returncode,
            'stdout': result.stdout[-500:] if result.stdout else '',
            'stderr': result.stderr[-500:] if result.stderr else ''
        }), 200
    except subprocess.TimeoutExpired:
        logging.error('script_market_signal_live.py execution timed out')
        return jsonify({
            'status': 'error',
            'message': 'Script execution timed out (max 1 hour)',
            'exit_code': -1
        }), 500
    except Exception as e:
        logging.error(f'Error running script_market_signal_live.py: {e}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error executing script: {str(e)}',
            'exit_code': -1
        }), 500


# =============================================================================
# ROUTES - DATA VIEWING
# =============================================================================

@app.route("/raw_data")
def market_data() -> str:
    """Display market data file browser."""
    csv_files = []
    if os.path.exists(MARKET_DATA_DIR):
        csv_files = [
            f for f in os.listdir(MARKET_DATA_DIR)
            if f.endswith('.csv') and os.path.isfile(os.path.join(MARKET_DATA_DIR, f))
        ]
        csv_files.sort()
    
    selected_file = None
    table_data = None
    columns = []
    
    if csv_files:
        selected_file = csv_files[0]
        file_path = os.path.join(MARKET_DATA_DIR, selected_file)
        try:
            df = pd.read_csv(file_path)
            columns = df.columns.tolist()
            # Show last 100 rows, reversed (most recent at top)
            table_data = df.tail(100).iloc[::-1].values.tolist()
        except Exception:
            table_data = None
    
    return render_template(
        "raw_data.html",
        csv_files=csv_files,
        columns=columns,
        table_data=table_data,
        selected_file=selected_file
    )


@app.route("/raw_data/<filename>")
def view_raw_data(filename: str) -> str:
    """Display specific market data file."""
    csv_files = []
    if os.path.exists(MARKET_DATA_DIR):
        csv_files = [
            f for f in os.listdir(MARKET_DATA_DIR)
            if f.endswith('.csv') and os.path.isfile(os.path.join(MARKET_DATA_DIR, f))
        ]
        csv_files.sort()
    
    table_data = None
    columns = []
    selected_file = filename
    file_path = os.path.join(MARKET_DATA_DIR, filename)
    
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            columns = df.columns.tolist()
            # Show last 100 rows, reversed (most recent at top)
            table_data = df.tail(100).iloc[::-1].values.tolist()
        except Exception:
            table_data = None
    
    return render_template(
        "raw_data.html",
        csv_files=csv_files,
        columns=columns,
        table_data=table_data,
        selected_file=selected_file
    )


# =============================================================================
# ROUTES - POSITIONS MANAGEMENT
# =============================================================================

def format_number(value: Any) -> str:
    """Format number with thousand separator."""
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


def enrich_position_data(ticker: str, entry: float, atr20: float, positions: int) -> Dict[str, Any]:
    """
    Enrich position data with current price, GICS industry, and calculated fields.
    
    Args:
        ticker: Stock ticker symbol
        entry: Entry price
        atr20: 20-day ATR value
        positions: Number of positions
    
    Returns:
        Dictionary with all enriched position data (13 columns)
    """
    # Initialize with base data
    data = {
        'ticker': ticker,
        'entry': entry,
        'atr20': atr20,
        'positions': positions,
        'system': 'System 2',
        'risk': 128,
    }
    
    # Get current price and GICS Industry from yfinance
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        data['current'] = info.get('currentPrice', info.get('regularMarketPrice', 0))
        data['gics_industry'] = info.get('sector', info.get('industry', 'N/A'))
    except Exception as e:
        logging.error(f"Error fetching yfinance data for {ticker}: {e}")
        data['current'] = 0
        data['gics_industry'] = 'N/A'
    
    # Get 10-days and 20-days low from market_data CSV
    market_data_path = os.path.join(MARKET_DATA_FOLDER_PATH, f"{ticker}.csv")
    try:
        if os.path.exists(market_data_path):
            df = pd.read_csv(market_data_path)
            if not df.empty:
                latest_row = df.iloc[-1]
                data['days_low_10'] = latest_row.get(DAYS_LOW_10, 0)
                data['days_low_20'] = latest_row.get(DAYS_LOW_20, 0)
            else:
                data['days_low_10'] = 0
                data['days_low_20'] = 0
        else:
            data['days_low_10'] = 0
            data['days_low_20'] = 0
    except Exception as e:
        logging.error(f"Error reading market data for {ticker}: {e}")
        data['days_low_10'] = 0
        data['days_low_20'] = 0
    
    # Calculate derived fields
    data['market_value'] = positions * data['current']
    data['stop_loss_atr'] = entry - (STOP_LOSS_ATR_MULTIPLIER * atr20)
    data['stop_loss_low'] = data['days_low_20']
    
    return data


@app.route("/positions")
def positions() -> str:
    """Display positions management page with enriched data."""
    positions_data = []
    
    if os.path.exists(CURRENT_POSITIONS_FILE_PATH):
        try:
            df = pd.read_csv(CURRENT_POSITIONS_FILE_PATH)
            for _, row in df.iterrows():
                enriched = enrich_position_data(
                    ticker=row['Ticker'],
                    entry=row['Entry'],
                    atr20=row['ATR-20'],
                    positions=row['Positions']
                )
                positions_data.append(enriched)
        except Exception as e:
            logging.error(f"Error loading positions: {e}")
    
    return render_template(
        "positions.html",
        positions=positions_data,
        format_number=format_number
    )


@app.route("/positions/add", methods=["POST"])
def add_position() -> str:
    """Add new position to positions.csv."""
    try:
        ticker = request.form.get('ticker', '').strip().upper()
        entry = float(request.form.get('entry', 0))
        atr20 = float(request.form.get('atr20', 0))
        positions = int(request.form.get('positions', 0))
        
        # Validate ticker exists via yfinance
        try:
            ticker_obj = yf.Ticker(ticker)
            _ = ticker_obj.info.get('currentPrice')
        except Exception:
            logging.error(f"Invalid ticker: {ticker}")
            return redirect('/positions')
        
        # Read existing positions
        if os.path.exists(CURRENT_POSITIONS_FILE_PATH):
            df = pd.read_csv(CURRENT_POSITIONS_FILE_PATH)
            # Check if ticker already exists
            if ticker in df['Ticker'].values:
                logging.warning(f"Ticker {ticker} already exists in positions")
                return redirect('/positions')
        else:
            df = pd.DataFrame(columns=['Ticker', 'Entry', 'ATR-20', 'Positions'])
        
        # Append new position
        new_row = pd.DataFrame([{
            'Ticker': ticker,
            'Entry': entry,
            'ATR-20': atr20,
            'Positions': positions
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(CURRENT_POSITIONS_FILE_PATH, index=False)
        
        logging.info(f"Added new position: {ticker}")
    except Exception as e:
        logging.error(f"Error adding position: {e}")
    
    return redirect('/positions')


@app.route("/positions/edit", methods=["POST"])
def edit_position() -> str:
    """Edit existing position in positions.csv."""
    try:
        original_ticker = request.form.get('original_ticker', '').strip().upper()
        ticker = request.form.get('ticker', '').strip().upper()
        entry = float(request.form.get('entry', 0))
        atr20 = float(request.form.get('atr20', 0))
        positions = int(request.form.get('positions', 0))
        
        if not os.path.exists(CURRENT_POSITIONS_FILE_PATH):
            return redirect('/positions')
        
        df = pd.read_csv(CURRENT_POSITIONS_FILE_PATH)
        
        # Find and update the row
        mask = df['Ticker'] == original_ticker
        if mask.any():
            df.loc[mask, 'Ticker'] = ticker
            df.loc[mask, 'Entry'] = entry
            df.loc[mask, 'ATR-20'] = atr20
            df.loc[mask, 'Positions'] = positions
            
            df.to_csv(CURRENT_POSITIONS_FILE_PATH, index=False)
            logging.info(f"Updated position: {original_ticker} -> {ticker}")
        else:
            logging.warning(f"Position not found: {original_ticker}")
    except Exception as e:
        logging.error(f"Error editing position: {e}")
    
    return redirect('/positions')


@app.route("/positions/delete", methods=["POST"])
def delete_position() -> str:
    """Delete position from positions.csv."""
    try:
        ticker = request.form.get('ticker', '').strip().upper()
        
        if not os.path.exists(CURRENT_POSITIONS_FILE_PATH):
            return redirect('/positions')
        
        df = pd.read_csv(CURRENT_POSITIONS_FILE_PATH)
        
        # Remove the row
        df = df[df['Ticker'] != ticker]
        df.to_csv(CURRENT_POSITIONS_FILE_PATH, index=False)
        
        logging.info(f"Deleted position: {ticker}")
    except Exception as e:
        logging.error(f"Error deleting position: {e}")
    
    return redirect('/positions')


# =============================================================================
# ROUTES - LOGS
# =============================================================================

@app.route("/logs")
def logs() -> str:
    """Display log file browser."""
    log_files = []
    if os.path.exists(LOG_FOLDER):
        log_files = [
            f for f in os.listdir(LOG_FOLDER)
            if os.path.isfile(os.path.join(LOG_FOLDER, f)) and f != '.DS_Store'
        ]
    
    # Add flask_errors.log to the list
    if os.path.exists(LOG_ERROR_FILE):
        log_files.append('flask_errors.log')
    
    log_files.sort()
    
    selected_log = None
    log_content = None
    
    if log_files:
        selected_log = log_files[0]
        log_path = (
            LOG_ERROR_FILE if selected_log == 'flask_errors.log'
            else os.path.join(LOG_FOLDER, selected_log)
        )
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                log_content = f.read()
    
    return render_template(
        "logs.html",
        log_files=log_files,
        log_content=log_content,
        selected_log=selected_log
    )


@app.route("/daily_script_logs/<logfile>")
def view_log(logfile: str) -> str:
    """Display specific log file."""
    log_files = []
    if os.path.exists(LOG_FOLDER):
        log_files = [
            f for f in os.listdir(LOG_FOLDER)
            if os.path.isfile(os.path.join(LOG_FOLDER, f)) and f != '.DS_Store'
        ]
    
    # Add flask_errors.log to the list
    if os.path.exists(LOG_ERROR_FILE):
        log_files.append('flask_errors.log')
    
    log_files.sort()
    
    log_content = ""
    selected_log = logfile
    log_path = (
        LOG_ERROR_FILE if logfile == 'flask_errors.log'
        else os.path.join(LOG_FOLDER, logfile)
    )
    
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            log_content = f.read()
    
    return render_template(
        "logs.html",
        log_files=log_files,
        log_content=log_content,
        selected_log=selected_log
    )


# =============================================================================
# ERROR HANDLING
# =============================================================================

@app.errorhandler(Exception)
def unhandled_exception(e: Exception) -> Tuple[str, int]:
    """Handle unhandled exceptions."""
    logging.error(f'Unhandled Exception: {e}\nRequest path: {request.path}')
    return render_template(
        'error_handling/error_handling.html',
        error=e,
        config=app.config
    ), 500


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    app.run(debug=True)
