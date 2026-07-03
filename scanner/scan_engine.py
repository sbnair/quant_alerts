"""
Scan orchestration: iterate a market's universe, build features, score,
persist to DB, and hand alerts to the alert engine.
"""

import json
import traceback
from datetime import datetime, timezone

import pandas as pd

import config
from models import db, ScanRun, ScanResult, IVHistory, Alert, \
    MARKET_INDIA, MARKET_CRYPTO, MARKET_US
from scanner import universe as uni
from scanner.volatility_score import score_universe
from data import india_market, crypto_market, us_market
from alerts import alert_engine

NUMERIC_FIELDS = [
    "spot", "prev_close", "gap_pct", "implied_move", "atm_iv", "iv_hv_ratio",
    "hv_short", "hv_long", "hv_ratio", "atr_pct", "dist_52w_pct", "pcr",
    "oi_total", "oi_change_pct", "gamma_flip", "funding_rate",
]


def _collect_india(progress) -> list[dict]:
    u = uni.india_universe()
    hists = india_market.batch_history(u["symbol"].tolist())
    feats = []
    for i, row in u.iterrows():
        progress(f"India {i + 1}/{len(u)}: {row['symbol']}")
        try:
            feats.append(india_market.fetch_symbol(
                row["symbol"], row["security_id"], row["segment"],
                int(row["lot_size"]), hists.get(row["symbol"])))
        except Exception as e:
            progress(f"  skip {row['symbol']}: {e}")
            feats.append(None)
    return [f for f in feats if f]


def _collect_crypto(progress) -> list[dict]:
    crypto_market.reset_cache()
    symbols = uni.crypto_universe()
    ticks = crypto_market.ticker_24h()
    feats = []
    for i, sym in enumerate(symbols):
        progress(f"Crypto {i + 1}/{len(symbols)}: {sym}")
        try:
            feats.append(crypto_market.fetch_symbol(sym, ticks[sym]))
        except Exception as e:
            progress(f"  skip {sym}: {e}")
    return feats


def _collect_us(progress) -> list[dict]:
    symbols = uni.us_universe()
    hists = us_market.batch_history(symbols)
    feats = []
    for i, sym in enumerate(symbols):
        progress(f"US {i + 1}/{len(symbols)}: {sym}")
        try:
            feats.append(us_market.fetch_symbol(sym, hists.get(sym)))
        except Exception as e:
            progress(f"  skip {sym}: {e}")
    return feats


COLLECTORS = {
    MARKET_INDIA:  _collect_india,
    MARKET_CRYPTO: _collect_crypto,
    MARKET_US:     _collect_us,
}


def run_scan(app, market_type: str, scan_kind: str = "manual",
             notify: bool = True) -> int | None:
    """Run one full scan for a market. Returns the ScanRun id (or None on failure)."""
    def progress(msg):
        print(f"[SCAN:{market_type}] {msg}")

    with app.app_context():
        run = ScanRun(market_type=market_type, scan_kind=scan_kind)
        db.session.add(run)
        db.session.commit()
        run_id = run.id

    try:
        feats = COLLECTORS[market_type](progress)
        scored = score_universe(feats)
    except Exception:
        traceback.print_exc()
        with app.app_context():
            run = db.session.get(ScanRun, run_id)
            run.status, run.finished_at = "failed", datetime.now(timezone.utc)
            db.session.commit()
        return None

    with app.app_context():
        run = db.session.get(ScanRun, run_id)
        n_err = 0
        today = datetime.now(timezone.utc).date()
        for _, row in scored.iterrows():
            rec = ScanResult(run_id=run_id, market_type=market_type,
                             symbol=row["symbol"],
                             score=row.get("score"), rank=int(row["rank"]),
                             regime=row.get("regime"),
                             flags=row.get("flags") or "")
            for f in NUMERIC_FIELDS:
                v = row.get(f)
                if v is not None and not pd.isna(v):
                    setattr(rec, f, float(v))
            raw = {k: (None if pd.isna(v) else v) for k, v in row.items()
                   if isinstance(v, (int, float, str, type(None)))}
            rec.features_json = json.dumps(raw, default=str)
            db.session.add(rec)

            # accumulate ATM IV history so IV Rank becomes computable over time
            iv = row.get("atm_iv")
            if iv is not None and not pd.isna(iv):
                exists = IVHistory.query.filter_by(symbol=row["symbol"],
                                                   date=today).first()
                if exists:
                    exists.atm_iv = float(iv)
                else:
                    db.session.add(IVHistory(symbol=row["symbol"],
                                             market_type=market_type,
                                             date=today, atm_iv=float(iv)))

        run.status, run.finished_at = "done", datetime.now(timezone.utc)
        run.n_symbols, run.n_errors = len(scored), n_err
        db.session.commit()

        if notify and not scored.empty:
            alert_engine.process_scan(scored, market_type, scan_kind)

    progress(f"done — {len(scored)} symbols scored")
    return run_id
