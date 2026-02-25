import pandas as pd
from flask import Flask, render_template, request, redirect
import os
import csv
import logging
from classes.constants import (
    TICKERS_TO_BE_RETRIEVED_FOLDER_PATH,
    SCRIPT_LOGS_FOLDER_PATH,
    BREAKOUT_LOG_MARKET_CLOSE,
    BREAKOUT_LOG_MARKET_OPEN,
    FILTER_MIN_PRICE,
    FILTER_MIN_VOLUME,
    FILTER_MIN_DOLLAR_VOLUME,
    FILTER_MIN_VOLATILITY,
    FILTER_MIN_ATR_PCT,
    FILTER_MAX_PER_SECTOR,
    FILTER_EARNINGS_SKIP_DAYS
)
from classes.breakout_checker import check_bullish_arrangement_for_tickers, get_breakout_ticker_information_close
from classes.helper import check_if_market_is_open

app = Flask(__name__)

# Context processor to make market_is_open available to all templates
@app.context_processor
def inject_market_status():
    return dict(market_is_open=check_if_market_is_open())

# Constants
SECTOR_DIR = os.path.join(os.path.dirname(__file__), TICKERS_TO_BE_RETRIEVED_FOLDER_PATH)
LOG_FOLDER = os.path.join(os.path.dirname(__file__), SCRIPT_LOGS_FOLDER_PATH)
LOG_ERROR_FILE = os.path.join(os.path.dirname(__file__), 'templates', 'error_handling', 'flask_errors.log')

def get_sector_files():
    sector_files = []
    if os.path.exists(SECTOR_DIR):
        for fname in sorted(os.listdir(SECTOR_DIR)):
            if fname.endswith('.csv') and os.path.isfile(os.path.join(SECTOR_DIR, fname)):
                sector_name = os.path.splitext(fname)[0].replace('_', ' ').title()
                sector_files.append((sector_name, fname))
    return sector_files

@app.route("/")
def home():
    return render_template("index.html")

def parse_breakout_log(log_path, group_by_date=True):
    """
    Parse breakout log file and return structured data.
    
    Args:
        log_path: Path to the log file
        group_by_date: If True, group by date only. If False, group by minute (YYYY-MM-DD HH:MM).
    
    Returns:
        List of dicts with timestamp/date, breakouts, and metadata
    """
    from datetime import date
    import re
    
    entries = []
    if not os.path.exists(log_path):
        return entries
    
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    entry_dict = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for market closed message
        closed_match = re.match(r'\[(.*?)\] Market is closed, no breakout check performed', line)
        if closed_match:
            timestamp = closed_match.group(1)
            if group_by_date:
                key = timestamp.split()[0]  # Extract date only
            else:
                # Extract up to minute: YYYY-MM-DD HH:MM
                parts = timestamp.split('.')[0].rsplit(':', 1)  # Remove milliseconds and seconds
                key = parts[0] if parts else timestamp
            if key not in entry_dict:
                entry_dict[key] = {'market_closed': True, 'breakouts': []}
            continue
        
        # Check for breakout tickers (handles both "Count:" and "count:" formats)
        breakout_match = re.match(r'\[(.*?)\] (.*?) [Bb]reakout tickers: ?(.*) \([Cc]ount: (\d+)\)', line)
        if breakout_match:
            timestamp, label, tickers_str, count = breakout_match.groups()
            tickers = [t.strip() for t in tickers_str.split(',') if t.strip()] if tickers_str else []
            if group_by_date:
                key = timestamp.split()[0]  # Extract date only
            else:
                # Extract up to minute: YYYY-MM-DD HH:MM
                parts = timestamp.split('.')[0].rsplit(':', 1)  # Remove milliseconds and seconds
                key = parts[0] if parts else timestamp
            if key not in entry_dict:
                entry_dict[key] = {'market_closed': False, 'breakouts': []}
            entry_dict[key]['breakouts'].append({'label': label, 'tickers': tickers})
    
    today_str = str(date.today())
    for key in sorted(entry_dict.keys(), reverse=True):
        is_today = key.startswith(today_str)
        entries.append({
            'timestamp': key,
            'is_today': is_today,
            'market_closed': entry_dict[key].get('market_closed', False),
            'breakouts': entry_dict[key].get('breakouts', [])
        })
    
    return entries

@app.route("/breakout")
def breakout():
    log_path = os.path.join(LOG_FOLDER, BREAKOUT_LOG_MARKET_CLOSE)
    entries = parse_breakout_log(log_path, group_by_date=True)
    # Collect all tickers from first entry for bullish check
    all_tickers = []
    if entries and not entries[0].get('market_closed'):
        for breakout in entries[0].get('breakouts', []):
            all_tickers.extend(breakout.get('tickers', []))
    bullish_tickers = set(check_bullish_arrangement_for_tickers(all_tickers)) if all_tickers else set()
    # Get detailed ticker information
    ticker_info_df = get_breakout_ticker_information_close(all_tickers) if all_tickers else pd.DataFrame()
    ticker_info = ticker_info_df.to_dict('records') if not ticker_info_df.empty else []
    return render_template('breakout.html', entries=entries, page_title="Breakout (Close)", bullish_tickers=bullish_tickers, ticker_info=ticker_info)

@app.route("/breakout_live")
def breakout_live():
    log_path = os.path.join(LOG_FOLDER, BREAKOUT_LOG_MARKET_OPEN)
    entries = parse_breakout_log(log_path, group_by_date=False)
    # Collect all tickers from first entry for bullish check
    all_tickers = []
    if entries and not entries[0].get('market_closed'):
        for breakout in entries[0].get('breakouts', []):
            all_tickers.extend(breakout.get('tickers', []))
    bullish_tickers = set(check_bullish_arrangement_for_tickers(all_tickers)) if all_tickers else set()
    # Get detailed ticker information
    ticker_info_df = get_breakout_ticker_information_close(all_tickers) if all_tickers else pd.DataFrame()
    ticker_info = ticker_info_df.to_dict('records') if not ticker_info_df.empty else []
    return render_template('breakout.html', entries=entries, page_title="Breakout (Live)", bullish_tickers=bullish_tickers, ticker_info=ticker_info)

@app.route("/tickers")
def tickers():
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
    bullish_tickers = set(check_bullish_arrangement_for_tickers(all_tickers)) if all_tickers else set()
    return render_template("tickers.html", sectors=sectors,
                         bullish_tickers=bullish_tickers,
                         FILTER_MIN_PRICE=FILTER_MIN_PRICE,
                         FILTER_MIN_VOLUME=FILTER_MIN_VOLUME,
                         FILTER_MIN_DOLLAR_VOLUME=FILTER_MIN_DOLLAR_VOLUME,
                         FILTER_MIN_VOLATILITY=FILTER_MIN_VOLATILITY,
                         FILTER_MIN_ATR_PCT=FILTER_MIN_ATR_PCT,
                         FILTER_MAX_PER_SECTOR=FILTER_MAX_PER_SECTOR,
                         FILTER_EARNINGS_SKIP_DAYS=FILTER_EARNINGS_SKIP_DAYS)

@app.route("/update_tickers", methods=["POST"])
def update_tickers():
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
def refresh_tickers():
    """
    Refresh tickers based on Turtle Trading criteria.
    This is a long-running operation.
    """
    from classes.ticker_filter import filter_and_save_tickers
    try:
        # Create output directory if it doesn't exist
        os.makedirs(SECTOR_DIR, exist_ok=True)
        total_filtered = filter_and_save_tickers(SECTOR_DIR)
        logging.info(f'Successfully refreshed tickers. Total filtered: {total_filtered}')
        return redirect('/tickers')
    except Exception as e:
        logging.error(f'Error refreshing tickers: {e}', exc_info=True)
        error_msg = f'Error refreshing tickers: {str(e)}'
        return render_template('error_handling/error_handling.html', error=error_msg, config=app.config), 500

# Set up logging to a file for errors
logging.basicConfig(
    filename=LOG_ERROR_FILE,
    level=None,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)

# Catch all unhandled exceptions
@app.errorhandler(Exception)
def unhandled_exception(e):
    logging.error('Unhandled Exception: %s\nRequest path: %s', e, request.path)
    return render_template('error_handling/error_handling.html', error=e, config=app.config), 500

# Raw Data Viewer page
@app.route("/raw_data")
def market_data():
    market_data_dir = os.path.join(os.path.dirname(__file__), 'data', 'market_data')
    csv_files = []
    if os.path.exists(market_data_dir):
        csv_files = [f for f in os.listdir(market_data_dir) if f.endswith('.csv') and os.path.isfile(os.path.join(market_data_dir, f))]
        csv_files.sort()
    selected_file = None
    table_data = None
    columns = []
    if csv_files:
        selected_file = csv_files[0]
        file_path = os.path.join(market_data_dir, selected_file)
        try:
            df = pd.read_csv(file_path)
            columns = df.columns.tolist()
            table_data = df.tail(100).iloc[::-1].values.tolist()  # Show last 100 rows, reversed (most recent at top)
        except Exception:
            table_data = None
    return render_template("raw_data.html", csv_files=csv_files, columns=columns, table_data=table_data, selected_file=selected_file)

@app.route("/raw_data/<filename>")
def view_raw_data(filename):
    market_data_dir = os.path.join(os.path.dirname(__file__), 'data', 'market_data')
    csv_files = []
    if os.path.exists(market_data_dir):
        csv_files = [f for f in os.listdir(market_data_dir) if f.endswith('.csv') and os.path.isfile(os.path.join(market_data_dir, f))]
        csv_files.sort()
    table_data = None
    columns = []
    selected_file = filename
    file_path = os.path.join(market_data_dir, filename)
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            columns = df.columns.tolist()
            table_data = df.tail(100).iloc[::-1].values.tolist()  # Show last 100 rows, reversed (most recent at top)
        except Exception:
            table_data = None
    return render_template("raw_data.html", csv_files=csv_files, columns=columns, table_data=table_data, selected_file=selected_file)

# Log viewer page
@app.route("/daily_script_logs")
def logs():
    log_files = []
    if os.path.exists(LOG_FOLDER):
        log_files = [f for f in os.listdir(LOG_FOLDER) if os.path.isfile(os.path.join(LOG_FOLDER, f))]
    selected_log = None
    log_content = None
    if log_files:
        selected_log = log_files[0]
        log_path = os.path.join(LOG_FOLDER, selected_log)
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                log_content = f.read()
    return render_template("daily_script_logs.html", log_files=log_files, log_content=log_content, selected_log=selected_log)

@app.route("/daily_script_logs/<logfile>")
def view_log(logfile):
    log_files = []
    if os.path.exists(LOG_FOLDER):
        log_files = [f for f in os.listdir(LOG_FOLDER) if os.path.isfile(os.path.join(LOG_FOLDER, f))]
    log_content = ""
    selected_log = logfile
    log_path = os.path.join(LOG_FOLDER, logfile)
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            log_content = f.read()
    return render_template("daily_script_logs.html", log_files=log_files, log_content=log_content, selected_log=selected_log)

@app.route("/about")
def about():
    return render_template("about.html",
                         FILTER_MIN_PRICE=FILTER_MIN_PRICE,
                         FILTER_MIN_VOLUME=FILTER_MIN_VOLUME,
                         FILTER_MIN_DOLLAR_VOLUME=FILTER_MIN_DOLLAR_VOLUME,
                         FILTER_MIN_VOLATILITY=FILTER_MIN_VOLATILITY,
                         FILTER_MIN_ATR_PCT=FILTER_MIN_ATR_PCT,
                         FILTER_MAX_PER_SECTOR=FILTER_MAX_PER_SECTOR,
                         FILTER_EARNINGS_SKIP_DAYS=FILTER_EARNINGS_SKIP_DAYS)

if __name__ == "__main__":
    app.run(debug=True)