from flask import Flask, render_template
import os

app = Flask(__name__)

LOG_FOLDER = os.path.join(os.path.dirname(__file__), 'script_logs')

@app.route("/")
def home():
    log_files = []
    if os.path.exists(LOG_FOLDER):
        log_files = [f for f in os.listdir(LOG_FOLDER) if os.path.isfile(os.path.join(LOG_FOLDER, f))]
    return render_template("index.html", log_files=log_files, log_content=None, selected_log=None)

@app.route("/view_log/<logfile>")
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
    return render_template("index.html", log_files=log_files, log_content=log_content, selected_log=selected_log)

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)