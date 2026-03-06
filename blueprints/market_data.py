"""Market data blueprint — raw CSV browser."""

import logging
import os

import pandas as pd
from flask import Blueprint, current_app, render_template

market_data_bp = Blueprint('market_data', __name__)

logger = logging.getLogger(__name__)


def _market_data_dir() -> str:
    return os.path.join(current_app.config['BASE_DIR'], 'data', 'market_data')


@market_data_bp.route('/')
def index():
    data_dir = _market_data_dir()
    csv_files = []
    if os.path.exists(data_dir):
        csv_files = sorted(
            f for f in os.listdir(data_dir)
            if f.endswith('.csv') and os.path.isfile(os.path.join(data_dir, f))
        )

    selected_file = None
    table_data = None
    columns = []

    if csv_files:
        selected_file = csv_files[0]
        file_path = os.path.join(data_dir, selected_file)
        try:
            df = pd.read_csv(file_path)
            columns = df.columns.tolist()
            table_data = df.tail(100).iloc[::-1].values.tolist()
        except Exception:
            pass

    return render_template(
        'market_data.html',
        csv_files=csv_files,
        columns=columns,
        table_data=table_data,
        selected_file=selected_file,
    )


@market_data_bp.route('/<filename>')
def view_file(filename: str):
    data_dir = _market_data_dir()
    csv_files = sorted(
        f for f in os.listdir(data_dir)
        if f.endswith('.csv') and os.path.isfile(os.path.join(data_dir, f))
    ) if os.path.exists(data_dir) else []

    table_data = None
    columns = []
    file_path = os.path.join(data_dir, filename)

    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            columns = df.columns.tolist()
            table_data = df.tail(100).iloc[::-1].values.tolist()
        except Exception:
            pass

    return render_template(
        'market_data.html',
        csv_files=csv_files,
        columns=columns,
        table_data=table_data,
        selected_file=filename,
    )
