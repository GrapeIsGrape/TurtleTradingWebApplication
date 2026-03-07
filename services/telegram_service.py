"""
Telegram service — outbound message sending and alert formatting.

Works in both Flask app context and standalone script context:
  - Reads credentials from environment variables first, then falls back
    to reading directly from the SQLite settings table via sqlite3.
  - Uses the Telegram Bot HTTP API via `requests` (no async required for
    outbound-only sending).
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from datetime import date

import requests

logger = logging.getLogger(__name__)

# Resolve paths relative to this file (services/telegram_service.py → project root)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_PROJECT_ROOT, 'data', 'turtle_trading.db')
_LOG_DIR = os.path.join(_PROJECT_ROOT, 'script_logs')

TELEGRAM_API = 'https://api.telegram.org/bot{token}/{method}'


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

def _get_setting(key: str) -> str:
    """Read a setting value from env var → SQLite → empty string."""
    env_val = os.environ.get(key.upper(), '').strip()
    if env_val:
        return env_val
    if os.path.exists(_DB_PATH):
        try:
            con = sqlite3.connect(_DB_PATH)
            row = con.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            con.close()
            if row and row[0]:
                return row[0].strip()
        except Exception as e:
            logger.debug(f'sqlite read error for setting {key}: {e}')
    return ''


def _credentials() -> tuple[str, str]:
    """Return (bot_token, chat_id). Both may be empty strings."""
    return _get_setting('telegram_bot_token'), _get_setting('telegram_chat_id')


# ---------------------------------------------------------------------------
# Core send
# ---------------------------------------------------------------------------

def send_message(text: str, parse_mode: str = 'HTML') -> bool:
    """
    Send a Telegram message to the configured chat.
    Returns True on success, False on failure.
    Only sends if both token and chat_id are configured.
    """
    token, chat_id = _credentials()
    if not token or not chat_id:
        logger.debug('Telegram not configured — skipping send')
        return False

    url = TELEGRAM_API.format(token=token, method='sendMessage')
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.ok:
            logger.info('Telegram message sent successfully')
            return True
        logger.warning(f'Telegram API error: {resp.status_code} {resp.text[:200]}')
        return False
    except Exception as e:
        logger.error(f'Telegram send error: {e}')
        return False


def send_test_message() -> tuple[bool, str]:
    """Send a test message. Returns (success, error_message)."""
    token, chat_id = _credentials()
    if not token:
        return False, 'Telegram Bot Token is not configured.'
    if not chat_id:
        return False, 'Telegram Chat ID is not configured.'
    ok = send_message('✅ <b>Turtle Trading Bot</b> — test message OK')
    if ok:
        return True, ''
    return False, 'Message send failed. Check token and chat ID.'


# ---------------------------------------------------------------------------
# Alert formatters
# ---------------------------------------------------------------------------

def format_breakout_alert(date_str: str, breakouts: list, is_live: bool = False) -> str:
    """
    Format a breakout alert for Telegram HTML.

    breakouts: [{'label': '20-days high', 'tickers': ['AAPL', ...]}, ...]
    Only groups with non-empty tickers are included.
    Returns empty string if no tickers in any group.
    """
    groups = [(b['label'], b['tickers']) for b in breakouts if b.get('tickers')]
    if not groups:
        return ''

    mode = 'LIVE' if is_live else 'CLOSE'
    lines = [f'<b>📈 BREAKOUT SIGNAL — {mode}</b>', f'📅 {date_str}', '']
    for label, tickers in groups:
        lines.append(f'<b>{label}</b> ({len(tickers)})')
        lines.append(', '.join(f'<code>{t}</code>' for t in tickers))
        lines.append('')
    return '\n'.join(lines).rstrip()


def format_exit_alert(date_str: str, exits: list, is_live: bool = False) -> str:
    """
    Format an exit alert for Telegram HTML.

    exits: [{'label': '10-days low', 'tickers': ['TSLA', ...]}, ...]
    Returns empty string if no tickers in any group.
    """
    groups = [(e['label'], e['tickers']) for e in exits if e.get('tickers')]
    if not groups:
        return ''

    mode = 'LIVE' if is_live else 'CLOSE'
    lines = [f'<b>🚨 EXIT SIGNAL — {mode}</b>', f'📅 {date_str}', '']
    for label, tickers in groups:
        lines.append(f'<b>{label}</b> ({len(tickers)})')
        lines.append(', '.join(f'<code>{t}</code>' for t in tickers))
        lines.append('')
    return '\n'.join(lines).rstrip()


# ---------------------------------------------------------------------------
# Alert persistence
# ---------------------------------------------------------------------------

def save_alert(alert_type: str, tickers: list, period_days: int | None = None,
               telegram_sent: bool = False) -> None:
    """Write a sent alert to the alerts table (works outside Flask context)."""
    from models import Alert, now_hkt
    try:
        # Try Flask SQLAlchemy path first
        from extensions import db
        a = Alert(
            alert_type=alert_type,
            tickers=json.dumps(tickers),
            period_days=period_days,
            sent_at=now_hkt(),
            telegram_sent=1 if telegram_sent else 0,
        )
        db.session.add(a)
        db.session.commit()
    except Exception:
        # Fallback: raw sqlite3 (works from standalone scripts)
        try:
            from models import now_hkt as hkt
            con = sqlite3.connect(_DB_PATH)
            con.execute(
                'INSERT INTO alerts (alert_type, tickers, period_days, sent_at, telegram_sent) '
                'VALUES (?,?,?,?,?)',
                (alert_type, json.dumps(tickers), period_days, hkt(), 1 if telegram_sent else 0),
            )
            con.commit()
            con.close()
        except Exception as e2:
            logger.error(f'Failed to save alert to DB: {e2}')


# ---------------------------------------------------------------------------
# Latest-signal helpers (used by the bot)
# ---------------------------------------------------------------------------

def _parse_log_latest(log_file: str, signal_key: str) -> dict | None:
    """
    Read a signal log file and return the most recent non-closed entry as:
      {'date': '2026-03-06', 'groups': [{'label': ..., 'tickers': [...]}]}
    Returns None if file not found or only market-closed entries.
    """
    path = os.path.join(_LOG_DIR, log_file)
    if not os.path.exists(path):
        return None

    entries: dict[str, dict] = {}
    closed_re = re.compile(r'\[(.*?)\] Market is closed')
    signal_re = re.compile(r'\[(.*?)\] (.*?) tickers: ?(.*) \([Cc]ount: (\d+)\)')

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = closed_re.match(line)
            if m:
                key = m.group(1).split()[0]
                entries.setdefault(key, {'closed': True, 'groups': []})
                continue
            m = signal_re.match(line)
            if m:
                ts, label, tickers_str, _ = m.groups()
                key = ts.split()[0]
                tickers = [t.strip() for t in tickers_str.split(',') if t.strip()]
                entries.setdefault(key, {'closed': False, 'groups': []})
                entries[key]['groups'].append({'label': label, 'tickers': tickers})

    for key in sorted(entries.keys(), reverse=True):
        e = entries[key]
        if not e.get('closed'):
            return {'date': key, 'groups': e['groups']}
    return None


def get_latest_breakout_html() -> str:
    from classes.constants import MARKET_CLOSE_BREAKOUT_RESULT_FILE_NAME
    entry = _parse_log_latest(MARKET_CLOSE_BREAKOUT_RESULT_FILE_NAME, 'breakout')
    if not entry:
        return '<b>📈 Breakout</b>\nNo data found.'
    text = format_breakout_alert(entry['date'], entry['groups'])
    return text or f'<b>📈 Breakout — {entry["date"]}</b>\nNo breakout signals.'


def get_latest_exit_html() -> str:
    from classes.constants import MARKET_CLOSE_EXIT_RESULT_FILE_NAME
    entry = _parse_log_latest(MARKET_CLOSE_EXIT_RESULT_FILE_NAME, 'exit')
    if not entry:
        return '<b>🚨 Exit</b>\nNo data found.'
    text = format_exit_alert(entry['date'], entry['groups'])
    return text or f'<b>🚨 Exit — {entry["date"]}</b>\nNo exit signals.'
