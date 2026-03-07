"""
Turtle Trading Web Application v2 — Flask application factory.

Blueprints:
    /signals        - Breakout and exit signal routes
    /positions      - Position management (all strategy types)
    /tickers        - Sector ticker management
    /market-data    - Raw CSV data browser
    /logs           - Script log browser

v1 routes are preserved via redirects for backward compatibility.
"""

import logging
import os

from flask import Flask, redirect, render_template, request

from config import Config
from extensions import db
from classes.helper import check_if_market_is_open


def create_app(config_class=Config) -> Flask:
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # -------------------------------------------------------------------------
    # Extensions
    # -------------------------------------------------------------------------
    db.init_app(app)

    # -------------------------------------------------------------------------
    # Database initialisation (creates tables + seeds defaults + migrates CSV)
    # -------------------------------------------------------------------------
    from services.db_service import init_db
    init_db(app)

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    log_dir = os.path.join(config_class.BASE_DIR, 'templates', 'error_handling')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'flask_errors.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
    )

    # -------------------------------------------------------------------------
    # Blueprints
    # -------------------------------------------------------------------------
    from blueprints.signals import signals_bp
    from blueprints.positions import positions_bp
    from blueprints.tickers import tickers_bp
    from blueprints.market_data import market_data_bp
    from blueprints.logs import logs_bp
    from blueprints.settings import settings_bp

    app.register_blueprint(signals_bp, url_prefix='/signals')
    app.register_blueprint(positions_bp, url_prefix='/positions')
    app.register_blueprint(tickers_bp, url_prefix='/tickers')
    app.register_blueprint(market_data_bp, url_prefix='/market-data')
    app.register_blueprint(logs_bp, url_prefix='/logs')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    # -------------------------------------------------------------------------
    # Context processors
    # -------------------------------------------------------------------------
    @app.context_processor
    def inject_market_status():
        return {'market_is_open': check_if_market_is_open()}

    # -------------------------------------------------------------------------
    # Core routes
    # -------------------------------------------------------------------------
    @app.route('/')
    def home():
        return render_template('dashboard.html')

    @app.route('/about')
    def about():
        from classes.constants import (
            FILTER_EARNINGS_SKIP_DAYS, FILTER_MAX_PER_SECTOR, FILTER_MIN_ATR_PCT,
            FILTER_MIN_DOLLAR_VOLUME, FILTER_MIN_PRICE, FILTER_MIN_VOLATILITY,
            FILTER_MIN_VOLUME,
        )
        return render_template(
            'about.html',
            FILTER_MIN_PRICE=FILTER_MIN_PRICE,
            FILTER_MIN_VOLUME=FILTER_MIN_VOLUME,
            FILTER_MIN_DOLLAR_VOLUME=FILTER_MIN_DOLLAR_VOLUME,
            FILTER_MIN_VOLATILITY=FILTER_MIN_VOLATILITY,
            FILTER_MIN_ATR_PCT=FILTER_MIN_ATR_PCT,
            FILTER_MAX_PER_SECTOR=FILTER_MAX_PER_SECTOR,
            FILTER_EARNINGS_SKIP_DAYS=FILTER_EARNINGS_SKIP_DAYS,
        )

    # -------------------------------------------------------------------------
    # v1 backward-compatible URL redirects
    # -------------------------------------------------------------------------
    @app.route('/breakout')
    def v1_breakout():
        return redirect('/signals/breakout')

    @app.route('/breakout_live')
    def v1_breakout_live():
        return redirect('/signals/breakout/live')

    @app.route('/exit')
    def v1_exit():
        return redirect('/signals/exit')

    @app.route('/exit_live')
    def v1_exit_live():
        return redirect('/signals/exit/live')

    @app.route('/raw_data', defaults={'filename': None})
    @app.route('/raw_data/<filename>')
    def v1_raw_data(filename):
        if filename:
            return redirect(f'/market-data/{filename}')
        return redirect('/market-data')

    @app.route('/daily_script_logs/<logfile>')
    def v1_view_log(logfile):
        return redirect(f'/logs/{logfile}')

    @app.route('/update_tickers', methods=['POST'])
    def v1_update_tickers():
        from blueprints.tickers import update_tickers
        return update_tickers()

    @app.route('/refresh_tickers', methods=['POST'])
    def v1_refresh_tickers():
        from blueprints.tickers import refresh_tickers
        return refresh_tickers()

    @app.route('/retrieve_ticker_data', methods=['POST'])
    def v1_retrieve_ticker_data():
        from blueprints.tickers import retrieve_ticker_data
        return retrieve_ticker_data()

    @app.route('/run_fill_market_data', methods=['POST'])
    def v1_run_fill_market_data():
        from blueprints.signals import run_fill_market_data
        return run_fill_market_data()

    @app.route('/run_market_signal_close', methods=['POST'])
    def v1_run_market_signal_close():
        from blueprints.signals import run_market_signal_close
        return run_market_signal_close()

    @app.route('/run_market_signal_live', methods=['POST'])
    def v1_run_market_signal_live():
        from blueprints.signals import run_market_signal_live
        return run_market_signal_live()

    @app.route('/positions/add', methods=['POST'])
    def v1_add_position():
        from blueprints.positions import turtle_add
        return turtle_add()

    @app.route('/positions/delete', methods=['POST'])
    def v1_delete_position():
        ticker = request.form.get('ticker', '').strip().upper()
        from models import TurtlePosition
        from services.db_service import sync_positions_csv
        pos = TurtlePosition.query.filter_by(ticker=ticker).first()
        if pos:
            db.session.delete(pos)
            db.session.commit()
            sync_positions_csv()
        return redirect('/positions')

    # -------------------------------------------------------------------------
    # Error handlers
    # -------------------------------------------------------------------------
    @app.errorhandler(Exception)
    def unhandled_exception(e):
        logging.error(f'Unhandled Exception: {e}\nRequest path: {request.path}')
        return render_template(
            'error_handling/error_handling.html',
            error=e,
            config=app.config,
        ), 500

    return app


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
