import pandas as pd
from flask import Flask, render_template, request
import os
import csv
import logging

app = Flask(__name__)

SECTOR_FILES = [
    ("Information Technology", "information_technology.csv"),
    ("Communication Services", "communication_services.csv"),
    ("Consumer Discretionary", "consumer_discretionary.csv"),
    ("Consumer Staples", "consumer_staples.csv"),
    ("Health Care", "health_care.csv"),
    ("Financials", "financials.csv"),
    ("Industrials", "industrials.csv"),
    ("Energy", "energy.csv"),
    ("Materials", "materials.csv"),
    ("Utilities", "utilities.csv"),
    ("Real Estate", "real_estate.csv"),
]
SECTOR_DIR = os.path.join(os.path.dirname(__file__), 'data', 'tickers_to_be_retrieved')

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/sectors")
def sectors():
    sectors = []
    for sector_name, filename in SECTOR_FILES:
        path = os.path.join(SECTOR_DIR, filename)
        tickers = []
        if os.path.exists(path):
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                tickers = [row['Ticker'] for row in reader]
        sectors.append({"name": sector_name, "tickers": tickers})
    return render_template("sectors.html", sectors=sectors)

LOG_FOLDER = os.path.join(os.path.dirname(__file__), 'script_logs')

# Set up logging to a file for errors
LOG_ERROR_FILE = os.path.join(os.path.dirname(__file__), 'templates', 'error_handling', 'flask_errors.log')
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