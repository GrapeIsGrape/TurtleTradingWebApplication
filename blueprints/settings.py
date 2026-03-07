"""Settings blueprint — API key management, Telegram config, alert history."""

import json
import logging

from flask import Blueprint, redirect, render_template, request, url_for

from extensions import db
from models import Alert, Setting, now_hkt

settings_bp = Blueprint('settings', __name__)
logger = logging.getLogger(__name__)

# Settings keys with human-readable labels and descriptions
_SETTING_DEFS = [
    {
        'key': 'telegram_bot_token',
        'label': 'Telegram Bot Token',
        'description': 'Bot token from @BotFather',
        'type': 'password',
    },
    {
        'key': 'telegram_chat_id',
        'label': 'Telegram Chat ID',
        'description': 'Your personal or group chat ID',
        'type': 'text',
    },
    {
        'key': 'anthropic_api_key',
        'label': 'Anthropic API Key',
        'description': 'API key for Claude AI analysis',
        'type': 'password',
    },
    {
        'key': 'news_api_key',
        'label': 'NewsAPI Key',
        'description': 'API key from newsapi.org for headlines',
        'type': 'password',
    },
    {
        'key': 'claude_model',
        'label': 'Claude Model',
        'description': 'Model ID used for AI analysis (e.g. claude-opus-4-6)',
        'type': 'text',
    },
]

_DEFAULTS = {
    'claude_model': 'claude-opus-4-6',
}


def _get_all_settings() -> dict[str, str]:
    """Return all settings as a key→value dict, with defaults for missing keys."""
    rows = Setting.query.all()
    result = dict(_DEFAULTS)
    for row in rows:
        result[row.key] = row.value
    return result


def _upsert_setting(key: str, value: str) -> None:
    row = Setting.query.get(key)
    if row is None:
        row = Setting(key=key, value=value, updated_at=now_hkt())
        db.session.add(row)
    else:
        row.value = value
        row.updated_at = now_hkt()
    db.session.commit()


@settings_bp.route('/')
def index():
    current = _get_all_settings()
    alerts = (
        Alert.query
        .order_by(Alert.sent_at.desc())
        .limit(50)
        .all()
    )
    alert_rows = []
    for a in alerts:
        try:
            tickers = json.loads(a.tickers)
        except Exception:
            tickers = []
        alert_rows.append({
            'id': a.id,
            'alert_type': a.alert_type,
            'tickers': tickers,
            'period_days': a.period_days,
            'sent_at': a.sent_at,
            'telegram_sent': bool(a.telegram_sent),
        })

    return render_template(
        'settings.html',
        setting_defs=_SETTING_DEFS,
        current=current,
        alerts=alert_rows,
        test_result=None,
    )


@settings_bp.route('/update', methods=['POST'])
def update():
    for defn in _SETTING_DEFS:
        key = defn['key']
        val = request.form.get(key, '').strip()
        if val:
            _upsert_setting(key, val)
    return redirect(url_for('settings.index'))


@settings_bp.route('/test-telegram', methods=['POST'])
def test_telegram():
    from services.telegram_service import send_test_message
    success, error_msg = send_test_message()

    current = _get_all_settings()
    alerts = (
        Alert.query
        .order_by(Alert.sent_at.desc())
        .limit(50)
        .all()
    )
    alert_rows = []
    for a in alerts:
        try:
            tickers = json.loads(a.tickers)
        except Exception:
            tickers = []
        alert_rows.append({
            'id': a.id,
            'alert_type': a.alert_type,
            'tickers': tickers,
            'period_days': a.period_days,
            'sent_at': a.sent_at,
            'telegram_sent': bool(a.telegram_sent),
        })

    return render_template(
        'settings.html',
        setting_defs=_SETTING_DEFS,
        current=current,
        alerts=alert_rows,
        test_result={'success': success, 'error': error_msg},
    )
