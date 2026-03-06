"""Signals blueprint — breakout and exit signal routes."""

import io
import logging
import os
import re
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from typing import Any, Dict, List, Tuple

from flask import Blueprint, current_app, jsonify, render_template

from classes.breakout_checker import (
    check_bullish_arrangement_for_tickers,
    filter_tickers_by_reset_signal,
    get_breakout_ticker_information_close,
    get_breakout_ticker_information_live,
)
from classes.constants import (
    BULLISH_ARRANGEMENT,
    MARKET_CLOSE_BREAKOUT_RESULT_FILE_NAME,
    MARKET_CLOSE_EXIT_RESULT_FILE_NAME,
    MARKET_OPEN_BREAKOUT_RESULT_FILE_NAME,
    MARKET_OPEN_EXIT_RESULT_FILE_NAME,
    SCRIPT_LOGS_FOLDER_PATH,
)
from classes.helper import check_if_market_is_open

signals_bp = Blueprint('signals', __name__)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_folder() -> str:
    return os.path.join(current_app.config['BASE_DIR'], SCRIPT_LOGS_FOLDER_PATH)


def parse_breakout_log(log_path: str, group_by_date: bool = True) -> List[Dict[str, Any]]:
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

        closed_match = re.match(r'\[(.*?)\] Market is closed, no breakout check performed', line)
        if closed_match:
            timestamp = closed_match.group(1)
            key = timestamp.split()[0] if group_by_date else timestamp.split('.')[0].rsplit(':', 1)[0]
            if key not in entry_dict:
                entry_dict[key] = {'market_closed': True, 'breakouts': []}
            continue

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

        closed_match = re.match(r'\[(.*?)\] Market is closed, no exit check performed', line)
        if closed_match:
            timestamp = closed_match.group(1)
            key = timestamp.split()[0] if group_by_date else timestamp.split('.')[0].rsplit(':', 1)[0]
            if key not in entry_dict:
                entry_dict[key] = {'market_closed': True, 'exits': []}
            continue

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


def _run_script(script_name: str, label: str):
    """Execute a script file in-process and return JSON response."""
    try:
        script_path = os.path.join(current_app.config['BASE_DIR'], script_name)
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        try:
            with open(script_path, 'r') as f:
                script_code = f.read()
            script_globals = {
                '__name__': '__main__',
                '__file__': script_path,
                'os': os,
                'sys': sys,
            }
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(script_code, script_globals)
            return jsonify({
                'status': 'success',
                'message': f'{label} completed',
                'exit_code': 0,
                'stdout': stdout_capture.getvalue()[-20000:],
                'stderr': stderr_capture.getvalue()[-20000:],
            }), 200
        except Exception as e:
            logger.error(f'Error executing {script_name}: {e}', exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'Script execution failed',
                'exit_code': 1,
                'stdout': stdout_capture.getvalue()[-20000:],
                'stderr': f'{str(e)}\n{stderr_capture.getvalue()[-1500:]}',
            }), 200
    except Exception as e:
        logger.error(f'Error preparing {script_name}: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': str(e), 'exit_code': -1}), 500


# ---------------------------------------------------------------------------
# Routes — Breakout
# ---------------------------------------------------------------------------

@signals_bp.route('/breakout')
def breakout():
    log_path = os.path.join(_log_folder(), MARKET_CLOSE_BREAKOUT_RESULT_FILE_NAME)
    entries = parse_breakout_log(log_path, group_by_date=True)

    all_tickers = []
    for entry in entries:
        if entry.get('market_closed'):
            continue
        tickers = [t for b in entry.get('breakouts', []) for t in b.get('tickers', [])]
        if tickers:
            all_tickers = tickers
            break

    bullish_tickers, ticker_info = get_breakout_ticker_info(all_tickers, use_live=False)
    reset_tickers = (
        set(filter_tickers_by_reset_signal(all_tickers, 20)) |
        set(filter_tickers_by_reset_signal(all_tickers, 55))
    )
    for entry in entries:
        entry['reset_tickers'] = reset_tickers

    return render_template(
        'signals/breakout.html',
        entries=entries,
        page_title='Breakout (Close)',
        bullish_tickers=bullish_tickers,
        ticker_info=ticker_info,
    )


@signals_bp.route('/breakout/live')
def breakout_live():
    log_path = os.path.join(_log_folder(), MARKET_OPEN_BREAKOUT_RESULT_FILE_NAME)
    entries = parse_breakout_log(log_path, group_by_date=False)

    all_tickers = []
    for entry in entries:
        if entry.get('market_closed'):
            continue
        tickers = [t for b in entry.get('breakouts', []) for t in b.get('tickers', [])]
        if tickers:
            all_tickers = tickers
            break

    bullish_tickers, ticker_info = get_breakout_ticker_info(
        all_tickers, use_live=check_if_market_is_open()
    )
    reset_tickers = (
        set(filter_tickers_by_reset_signal(all_tickers, 20)) |
        set(filter_tickers_by_reset_signal(all_tickers, 55))
    )
    for entry in entries:
        entry['reset_tickers'] = reset_tickers

    return render_template(
        'signals/breakout.html',
        entries=entries,
        page_title='Breakout (Live)',
        bullish_tickers=bullish_tickers,
        ticker_info=ticker_info,
    )


# ---------------------------------------------------------------------------
# Routes — Exit
# ---------------------------------------------------------------------------

@signals_bp.route('/exit')
def exit_close():
    log_path = os.path.join(_log_folder(), MARKET_CLOSE_EXIT_RESULT_FILE_NAME)
    entries = parse_exit_log(log_path, group_by_date=True)

    all_tickers = []
    for entry in entries:
        if entry.get('market_closed'):
            continue
        tickers = [t for ex in entry.get('exits', []) for t in ex.get('tickers', [])]
        if tickers:
            all_tickers = tickers
            break

    bullish_tickers, ticker_info = get_breakout_ticker_info(all_tickers, use_live=False)

    return render_template(
        'signals/exit.html',
        entries=entries,
        page_title='Exit (Close)',
        bullish_tickers=bullish_tickers,
        ticker_info=ticker_info,
    )


@signals_bp.route('/exit/live')
def exit_live():
    log_path = os.path.join(_log_folder(), MARKET_OPEN_EXIT_RESULT_FILE_NAME)
    entries = parse_exit_log(log_path, group_by_date=False)

    all_tickers = []
    for entry in entries:
        if entry.get('market_closed'):
            continue
        tickers = [t for ex in entry.get('exits', []) for t in ex.get('tickers', [])]
        if tickers:
            all_tickers = tickers
            break

    bullish_tickers, ticker_info = get_breakout_ticker_info(
        all_tickers, use_live=check_if_market_is_open()
    )

    return render_template(
        'signals/exit.html',
        entries=entries,
        page_title='Exit (Live)',
        bullish_tickers=bullish_tickers,
        ticker_info=ticker_info,
    )


# ---------------------------------------------------------------------------
# Routes — Script runners
# ---------------------------------------------------------------------------

@signals_bp.route('/run/fill-data', methods=['POST'])
def run_fill_market_data():
    return _run_script('script_fill_market_data.py', 'Fill market data script')


@signals_bp.route('/run/close', methods=['POST'])
def run_market_signal_close():
    return _run_script('script_market_signal_close.py', 'Market signal close script')


@signals_bp.route('/run/live', methods=['POST'])
def run_market_signal_live():
    return _run_script('script_market_signal_live.py', 'Market signal live script')
