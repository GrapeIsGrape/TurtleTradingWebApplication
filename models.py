"""SQLAlchemy ORM models for Turtle Trading v2."""

from datetime import datetime, timezone
import pytz
from extensions import db

HKT = pytz.timezone('Asia/Hong_Kong')


def now_hkt() -> str:
    """Return current time in HKT as ISO8601 string."""
    return datetime.now(HKT).isoformat()


# =============================================================================
# POSITION MODELS
# =============================================================================

class TurtlePosition(db.Model):
    __tablename__ = 'positions_turtle'

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.Text, nullable=False, unique=True)
    entry_price = db.Column(db.Float, nullable=False)
    atr_20 = db.Column(db.Float, nullable=False)
    num_positions = db.Column(db.Integer, nullable=False)
    system = db.Column(db.Text, default='System 2')
    notes = db.Column(db.Text)
    opened_at = db.Column(db.Text, nullable=False, default=now_hkt)
    updated_at = db.Column(db.Text, nullable=False, default=now_hkt)

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'entry_price': self.entry_price,
            'atr_20': self.atr_20,
            'num_positions': self.num_positions,
            'system': self.system,
            'notes': self.notes,
            'opened_at': self.opened_at,
            'updated_at': self.updated_at,
        }


class DCAPosition(db.Model):
    __tablename__ = 'positions_dca'

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.Text, nullable=False)
    num_shares = db.Column(db.Float, nullable=False)
    avg_cost = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    opened_at = db.Column(db.Text, nullable=False, default=now_hkt)
    updated_at = db.Column(db.Text, nullable=False, default=now_hkt)

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'num_shares': self.num_shares,
            'avg_cost': self.avg_cost,
            'notes': self.notes,
            'opened_at': self.opened_at,
            'updated_at': self.updated_at,
        }


class BondPosition(db.Model):
    __tablename__ = 'positions_bonds'

    id = db.Column(db.Integer, primary_key=True)
    instrument = db.Column(db.Text, nullable=False)
    bond_type = db.Column(db.Text, nullable=False)   # 'bill', 'note', 'bond', 'etf'
    face_value = db.Column(db.Float, nullable=False)
    coupon_rate = db.Column(db.Float)                # NULL for T-bills
    maturity_date = db.Column(db.Text)               # NULL for ETFs
    purchase_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    opened_at = db.Column(db.Text, nullable=False, default=now_hkt)
    updated_at = db.Column(db.Text, nullable=False, default=now_hkt)

    def to_dict(self):
        return {
            'id': self.id,
            'instrument': self.instrument,
            'bond_type': self.bond_type,
            'face_value': self.face_value,
            'coupon_rate': self.coupon_rate,
            'maturity_date': self.maturity_date,
            'purchase_price': self.purchase_price,
            'quantity': self.quantity,
            'notes': self.notes,
            'opened_at': self.opened_at,
            'updated_at': self.updated_at,
        }


class OptionPosition(db.Model):
    __tablename__ = 'positions_options'

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.Text, nullable=False)
    option_type = db.Column(db.Text, nullable=False)   # 'call' or 'put'
    direction = db.Column(db.Text, nullable=False)      # 'long' or 'short'
    strike = db.Column(db.Float, nullable=False)
    expiry_date = db.Column(db.Text, nullable=False)
    premium = db.Column(db.Float, nullable=False)
    contracts = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.Text, nullable=False, default='open')  # 'open', 'closed', 'expired'
    close_price = db.Column(db.Float)
    notes = db.Column(db.Text)
    opened_at = db.Column(db.Text, nullable=False, default=now_hkt)
    updated_at = db.Column(db.Text, nullable=False, default=now_hkt)

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'option_type': self.option_type,
            'direction': self.direction,
            'strike': self.strike,
            'expiry_date': self.expiry_date,
            'premium': self.premium,
            'contracts': self.contracts,
            'status': self.status,
            'close_price': self.close_price,
            'notes': self.notes,
            'opened_at': self.opened_at,
            'updated_at': self.updated_at,
        }


# =============================================================================
# ALERTS
# =============================================================================

class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.Text, nullable=False)   # 'breakout_close', 'exit_close', etc.
    tickers = db.Column(db.Text, nullable=False)       # JSON array string
    period_days = db.Column(db.Integer)
    sent_at = db.Column(db.Text, nullable=False, default=now_hkt)
    telegram_sent = db.Column(db.Integer, default=0)
    telegram_msg_id = db.Column(db.Integer)


# =============================================================================
# SENTIMENT CACHE
# =============================================================================

class SentimentCache(db.Model):
    __tablename__ = 'sentiment_cache'

    id = db.Column(db.Integer, primary_key=True)
    cache_date = db.Column(db.Text, nullable=False, unique=True)   # 'YYYY-MM-DD'
    fear_greed = db.Column(db.Integer)
    fear_greed_label = db.Column(db.Text)
    vix = db.Column(db.Float)
    spy_1d_pct = db.Column(db.Float)
    qqq_1d_pct = db.Column(db.Float)
    news_summary = db.Column(db.Text)
    raw_headlines = db.Column(db.Text)   # JSON array string
    created_at = db.Column(db.Text, nullable=False, default=now_hkt)

    def to_dict(self):
        return {
            'id': self.id,
            'cache_date': self.cache_date,
            'fear_greed': self.fear_greed,
            'fear_greed_label': self.fear_greed_label,
            'vix': self.vix,
            'spy_1d_pct': self.spy_1d_pct,
            'qqq_1d_pct': self.qqq_1d_pct,
            'news_summary': self.news_summary,
            'raw_headlines': self.raw_headlines,
            'created_at': self.created_at,
        }


# =============================================================================
# AI ANALYSIS CACHE
# =============================================================================

class AIAnalysis(db.Model):
    __tablename__ = 'ai_analysis'

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.Text, nullable=False)
    analysis_type = db.Column(db.Text, nullable=False)   # 'fundamental', 'sentiment', 'outlook'
    prompt_hash = db.Column(db.Text, nullable=False)
    response_text = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.Text, nullable=False)
    input_tokens = db.Column(db.Integer)
    output_tokens = db.Column(db.Integer)
    created_at = db.Column(db.Text, nullable=False, default=now_hkt)

    __table_args__ = (
        db.UniqueConstraint('ticker', 'analysis_type', 'prompt_hash'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'analysis_type': self.analysis_type,
            'response_text': self.response_text,
            'model_used': self.model_used,
            'created_at': self.created_at,
        }


# =============================================================================
# SETTINGS
# =============================================================================

class Setting(db.Model):
    __tablename__ = 'settings'

    key = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.Text, nullable=False, default=now_hkt)


# =============================================================================
# IBKR STUB
# =============================================================================

class IBKROrderStub(db.Model):
    __tablename__ = 'ibkr_orders_stub'

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.Text, nullable=False)
    action = db.Column(db.Text, nullable=False)        # 'BUY', 'SELL'
    quantity = db.Column(db.Integer, nullable=False)
    order_type = db.Column(db.Text, nullable=False)    # 'MKT', 'LMT', 'STP'
    limit_price = db.Column(db.Float)
    status = db.Column(db.Text, default='pending')
    ibkr_order_id = db.Column(db.Text)
    created_at = db.Column(db.Text, nullable=False, default=now_hkt)
