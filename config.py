"""
Configuration for the Volatility Scanner.
Secrets (Dhan / Binance / Telegram / Discord) are loaded from ~/quant_4/.env
so keys live in one place. A local .env in this directory can override them.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load shared keys first, then local overrides (local wins)
load_dotenv(Path.home() / "quant_4" / ".env")
load_dotenv(Path(__file__).parent / ".env", override=True)


def _bool(key, default="false"):
    return os.getenv(key, default).lower() in ("true", "1", "yes")

def _float(key, default):
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return float(default)

def _int(key, default):
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return int(default)


# ── Credentials ───────────────────────────────────────────────────────────────
DHAN_CLIENT_ID      = os.getenv("DHAN_CLIENT_ID", "")
DHAN_ACCESS_TOKEN   = os.getenv("DHAN_ACCESS_TOKEN", "")
BINANCE_API_KEY     = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET  = os.getenv("BINANCE_API_SECRET", "")

ENABLE_TELEGRAM     = _bool("ENABLE_TELEGRAM", "true")
ENABLE_DISCORD      = _bool("ENABLE_DISCORD", "true")
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ── Flask ─────────────────────────────────────────────────────────────────────
FLASK_SECRET_KEY    = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
FLASK_PORT          = _int("VOLSCAN_PORT", 5050)          # separate port from quant_4
FLASK_DEBUG         = _bool("FLASK_DEBUG", "false")
DB_PATH             = "volscan.db"

# ── Scan parameters ───────────────────────────────────────────────────────────
RISK_FREE_RATE      = _float("RISK_FREE_RATE", 0.065)
MIN_OPEN_INTEREST   = _int("MIN_OPEN_INTEREST", 1)
STRIKE_RANGE_PCT    = _float("STRIKE_RANGE_PCT", 0.20)

# Dhan option-chain API is rate-limited (~1 req / 3 s) — pace universe scans.
DHAN_REQUEST_GAP_SEC = _float("DHAN_REQUEST_GAP_SEC", 3.1)

# How many India F&O stocks (by futures OI liquidity) to scan besides indices.
# Full universe (~180 names) at 1 req/3 s is ~10 min; default keeps scan < 5 min.
INDIA_UNIVERSE_LIMIT = _int("INDIA_UNIVERSE_LIMIT", 60)

# Crypto universe: top-N Binance USDT-perps by 24h quote volume
CRYPTO_UNIVERSE_LIMIT = _int("CRYPTO_UNIVERSE_LIMIT", 40)
CRYPTO_SCAN_INTERVAL_MIN = _int("CRYPTO_SCAN_INTERVAL_MIN", 30)

# US universe: highly liquid optionable indices/ETFs/mega-caps (yfinance)
US_UNIVERSE = [
    "SPY", "QQQ", "IWM", "DIA",
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD",
    "NFLX", "AVGO", "JPM", "BAC", "XOM", "CVX", "BA", "COIN",
    "PLTR", "SMCI", "MSTR", "INTC", "MU", "CRM", "ORCL", "UNH",
]

# ── Alert thresholds (V1 rule-based) ─────────────────────────────────────────
TOP_N_ALERTS            = _int("TOP_N_ALERTS", 10)     # digest size
GAP_ALERT_PCT           = _float("GAP_ALERT_PCT", 2.0) # |gap| > 2% → GAP_RISK
IMPLIED_MOVE_ALERT_PCT  = _float("IMPLIED_MOVE_ALERT_PCT", 3.0)
IV_HV_RATIO_ALERT       = _float("IV_HV_RATIO_ALERT", 1.5)
HV_RATIO_ALERT          = _float("HV_RATIO_ALERT", 1.8)  # short-term vs long-term realized vol
CRYPTO_FUNDING_ALERT    = _float("CRYPTO_FUNDING_ALERT", 0.0008)  # |8h funding| > 0.08%
CRYPTO_OI_CHANGE_ALERT  = _float("CRYPTO_OI_CHANGE_ALERT", 15.0)  # % OI change vs 24h ago
MIN_SCORE_FOR_ALERT     = _float("MIN_SCORE_FOR_ALERT", 60.0)     # composite 0-100

# Composite score weights (V1) — normalized percentile features
SCORE_WEIGHTS = {
    "implied_move":   0.30,
    "gap_pct":        0.20,
    "iv_hv_ratio":    0.15,
    "hv_ratio":       0.15,
    "oi_change":      0.10,
    "negative_gamma": 0.10,   # binary flag contribution
}

# ── Dhan static metadata ──────────────────────────────────────────────────────
DHAN_INDEX_MAP = {
    "NIFTY":      {"security_id": "13", "segment": "IDX_I",   "lot_size": 75},
    "BANKNIFTY":  {"security_id": "25", "segment": "IDX_I",   "lot_size": 30},
    "FINNIFTY":   {"security_id": "27", "segment": "IDX_I",   "lot_size": 65},
    "SENSEX":     {"security_id": "1",  "segment": "BSE_FNO", "lot_size": 10},
}

# Dhan instrument master (compact) — used to build the F&O stock universe
DHAN_INSTRUMENT_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
UNIVERSE_CACHE = "instance/fno_universe.csv"

IST_TZ = "Asia/Kolkata"
