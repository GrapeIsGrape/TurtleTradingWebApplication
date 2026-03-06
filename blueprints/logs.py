"""Logs blueprint — script log browser."""

import logging
import os

from flask import Blueprint, current_app, render_template

from classes.constants import SCRIPT_LOGS_FOLDER_PATH

logs_bp = Blueprint('logs', __name__)

logger = logging.getLogger(__name__)


def _log_folder() -> str:
    return os.path.join(current_app.config['BASE_DIR'], SCRIPT_LOGS_FOLDER_PATH)


def _flask_error_log() -> str:
    return os.path.join(
        current_app.config['BASE_DIR'], 'templates', 'error_handling', 'flask_errors.log'
    )


def _get_log_files():
    log_folder = _log_folder()
    log_files = []
    if os.path.exists(log_folder):
        log_files = [
            f for f in os.listdir(log_folder)
            if os.path.isfile(os.path.join(log_folder, f)) and f != '.DS_Store'
        ]
    if os.path.exists(_flask_error_log()):
        log_files.append('flask_errors.log')
    return sorted(log_files)


@logs_bp.route('/')
def index():
    log_files = _get_log_files()
    selected_log = None
    log_content = None

    if log_files:
        selected_log = log_files[0]
        log_path = (
            _flask_error_log() if selected_log == 'flask_errors.log'
            else os.path.join(_log_folder(), selected_log)
        )
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                log_content = f.read()

    return render_template(
        'logs.html',
        log_files=log_files,
        log_content=log_content,
        selected_log=selected_log,
    )


@logs_bp.route('/<logfile>')
def view_log(logfile: str):
    log_files = _get_log_files()
    log_content = ''
    log_path = (
        _flask_error_log() if logfile == 'flask_errors.log'
        else os.path.join(_log_folder(), logfile)
    )

    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            log_content = f.read()

    return render_template(
        'logs.html',
        log_files=log_files,
        log_content=log_content,
        selected_log=logfile,
    )
