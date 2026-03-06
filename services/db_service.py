"""Database service — helpers, migrations, and CSV sync."""

import csv
import logging
import os

import pandas as pd

from extensions import db
from models import TurtlePosition, now_hkt

logger = logging.getLogger(__name__)

POSITIONS_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'positions.csv')


def init_db(app):
    """Create all tables if they don't exist (idempotent)."""
    with app.app_context():
        db.create_all()
        _seed_default_settings()
        _migrate_positions_csv_to_sqlite()


def _seed_default_settings():
    """Insert default settings rows if they don't already exist."""
    from models import Setting
    defaults = [
        ('telegram_bot_token', '', 'Telegram bot token from @BotFather'),
        ('telegram_chat_id', '', 'Your Telegram chat ID'),
        ('anthropic_api_key', '', 'Anthropic API key for Claude'),
        ('claude_model', 'claude-opus-4-6', 'Claude model to use for analysis'),
        ('news_api_key', '', 'NewsAPI.org API key'),
        ('admin_password', 'admin', 'Password for admin operations'),
        ('filter_min_price', '20', 'Minimum stock price (USD)'),
        ('filter_min_volume', '1000000', 'Minimum 30-day avg volume (shares)'),
        ('filter_min_dollar_volume', '75000000', 'Minimum 30-day avg dollar volume (USD)'),
        ('filter_min_volatility', '25', 'Minimum 20-day annualized volatility (%)'),
        ('filter_min_atr_pct', '1.8', 'Minimum 14-day ATR as % of price'),
        ('filter_max_per_sector', '7', 'Max tickers per GICS sector'),
    ]
    for key, value, desc in defaults:
        existing = Setting.query.get(key)
        if existing is None:
            db.session.add(Setting(key=key, value=value, description=desc, updated_at=now_hkt()))
    db.session.commit()


def _migrate_positions_csv_to_sqlite():
    """
    One-time migration: load data/positions.csv into positions_turtle table.
    Skips gracefully if table already has data or CSV doesn't exist.
    """
    if TurtlePosition.query.count() > 0:
        return  # Already migrated

    if not os.path.exists(POSITIONS_CSV_PATH):
        return

    try:
        df = pd.read_csv(POSITIONS_CSV_PATH)
        required = {'Ticker', 'Entry', 'ATR-20', 'Positions'}
        if not required.issubset(set(df.columns)):
            logger.warning('positions.csv missing required columns, skipping migration')
            return

        for _, row in df.iterrows():
            ticker = str(row['Ticker']).strip().upper()
            if not ticker:
                continue
            pos = TurtlePosition(
                ticker=ticker,
                entry_price=float(row['Entry']),
                atr_20=float(row['ATR-20']),
                num_positions=int(row['Positions']),
                opened_at=now_hkt(),
                updated_at=now_hkt(),
            )
            db.session.add(pos)
        db.session.commit()
        logger.info(f'Migrated {len(df)} positions from positions.csv to SQLite')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error migrating positions.csv: {e}')


def sync_positions_csv():
    """
    Write-through mirror: regenerate data/positions.csv from positions_turtle table.
    Called after every turtle position mutation so exit_checker.py stays compatible.
    """
    try:
        positions = TurtlePosition.query.all()
        os.makedirs(os.path.dirname(POSITIONS_CSV_PATH), exist_ok=True)
        with open(POSITIONS_CSV_PATH, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Ticker', 'Entry', 'ATR-20', 'Positions'])
            writer.writeheader()
            for p in positions:
                writer.writerow({
                    'Ticker': p.ticker,
                    'Entry': p.entry_price,
                    'ATR-20': p.atr_20,
                    'Positions': p.num_positions,
                })
        logger.debug(f'Synced {len(positions)} positions to positions.csv')
    except Exception as e:
        logger.error(f'Error syncing positions.csv: {e}')
