#!/usr/bin/env python3
"""
Turtle Trading — Telegram Bot (polling mode).

Run this as a long-running process on the Synology server:
    python script_telegram_bot.py

Commands:
    /help       — List commands
    /start      — Same as /help
    /status     — US market open / closed
    /positions  — All open turtle positions
    /breakout   — Latest close breakout signals
    /exit       — Latest close exit signals
"""

import logging
import os
import sqlite3
import sys

# Ensure the project root is in sys.path when run directly
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from classes.helper import check_if_market_is_open
from services.telegram_service import (
    _get_setting,
    get_latest_breakout_html,
    get_latest_exit_html,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(_ROOT, 'data', 'turtle_trading.db')


def _db_rows(sql: str, params=()) -> list:
    con = sqlite3.connect(_DB_PATH)
    rows = con.execute(sql, params).fetchall()
    con.close()
    return rows


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        '<b>Turtle Trading Bot</b>\n\n'
        '/status — US market open or closed\n'
        '/positions — Open turtle positions\n'
        '/breakout — Latest breakout signals\n'
        '/exit — Latest exit signals\n'
        '/help — Show this message'
    )
    await update.message.reply_html(text)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    is_open = check_if_market_is_open()
    emoji  = '🟢' if is_open else '🔴'
    status = 'OPEN' if is_open else 'CLOSED'
    await update.message.reply_html(f'{emoji} <b>US Market is {status}</b>')


async def cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = _db_rows(
        'SELECT ticker, entry_price, num_positions, system, notes '
        'FROM positions_turtle ORDER BY ticker'
    )
    if not rows:
        await update.message.reply_text('No turtle positions.')
        return

    lines = ['<b>🐢 Turtle Positions</b>', '']
    for ticker, entry, num_pos, system, notes in rows:
        line = f'<code>{ticker}</code>  entry: <b>${entry:.2f}</b>  pos: {num_pos}  ({system})'
        if notes:
            line += f'  <i>{notes}</i>'
        lines.append(line)
    await update.message.reply_html('\n'.join(lines))


async def cmd_breakout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(get_latest_breakout_html())


async def cmd_exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(get_latest_exit_html())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    token = _get_setting('telegram_bot_token')
    if not token:
        logger.error(
            'TELEGRAM_BOT_TOKEN is not configured. '
            'Set it in Settings (/settings) or in the .env file.'
        )
        sys.exit(1)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler('start',     cmd_help))
    app.add_handler(CommandHandler('help',      cmd_help))
    app.add_handler(CommandHandler('status',    cmd_status))
    app.add_handler(CommandHandler('positions', cmd_positions))
    app.add_handler(CommandHandler('breakout',  cmd_breakout))
    app.add_handler(CommandHandler('exit',      cmd_exit))

    logger.info('Bot started — polling mode')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
