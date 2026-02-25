import pandas as pd
from flask import Flask, render_template, request, redirect
import os
import csv
import logging
from classes.constants import (
    TICKERS_TO_BE_RETRIEVED_FOLDER_PATH,
    SCRIPT_LOGS_FOLDER_PATH,
    BREAKOUT_LOG_MARKET_CLOSE,
    BREAKOUT_LOG_MARKET_OPEN
)

app = Flask(__name__)

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

@app.route("/breakout")
def breakout():
    from datetime import date
    log_path = os.path.join(LOG_FOLDER, BREAKOUT_LOG_MARKET_CLOSE)
    breakout_days = []
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            lines = f.readlines()
        day_dict = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Example: [2026-02-24] 20-days high Breakout tickers: PDD (Count: 1)
            import re
            m = re.match(r'\[(.*?)\] (.*?) Breakout tickers: ?(.*) \(Count: (\d+)\)', line)
            if m:
                date_str, label, tickers_str, count = m.groups()
                tickers = [t.strip() for t in tickers_str.split(',') if t.strip()] if tickers_str else []
                if date_str not in day_dict:
                    day_dict[date_str] = []
                day_dict[date_str].append({'label': label, 'tickers': tickers})
        for date_str in sorted(day_dict.keys(), reverse=True):
            breakout_days.append({'date': date_str, 'breakouts': day_dict[date_str]})
    today_date = str(date.today())
    return render_template('breakout.html', breakout_days=breakout_days, today_date=today_date)

@app.route("/tickers")
def tickers():
    sectors = []
    for sector_name, filename in get_sector_files():
        path = os.path.join(SECTOR_DIR, filename)
        tickers_list = []
        if os.path.exists(path):
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                tickers_list = [row['Ticker'] for row in reader]
        file_key = os.path.splitext(filename)[0]
        sectors.append({
            "name": sector_name,
            "tickers": tickers_list,
            "file_key": file_key,
            "filename": filename
        })
    return render_template("tickers.html", sectors=sectors)

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
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)