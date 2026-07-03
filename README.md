# Volatility Scanner

Cross-sectional pre-market volatility scanner for **Indian F&O** (Dhan),
**Crypto** (Binance USDT perps + options), and **US** (yfinance) markets.
Ranks each universe by a composite expected-volatility score and delivers a
ranked digest + threshold alerts to **Telegram**, **Discord**, and the web
dashboard.

Companion to `~/quant_4` (Gamma Alert System) — reuses its Dhan/Binance/
Telegram/Discord credentials from `~/quant_4/.env` (a local `.env` here can
override any value).

## Run

```bash
./run.sh            # or: venv/bin/python app.py
```

Dashboard: http://localhost:5050 (port via `VOLSCAN_PORT`).

## Scheduled scans

| Market | When | What |
|---|---|---|
| India  | 09:07 IST Mon–Fri | pre-market scan (option chain reflects overnight IV repricing) |
| India  | 09:20 IST Mon–Fri | post-open rescan with the actual opening print |
| US     | 09:10 ET Mon–Fri  | pre-market scan (pre-market indicative prices) |
| Crypto | every 30 min 24/7 | interval scan |

Manual scans: **Scan Now** button per market, or `POST /api/scan/<MARKET>/run`.

## Signals per symbol

- **Straddle-implied move** (nearest expiry, √t-normalized to 1 day)
- **Gap %** vs previous session close
- **ATM IV** and **IV/HV ratio** (options-implied vs 20d realized)
- **HV5/HV20** ratio (hot realized vol), **ATR%**, **52-week distance**
- **PCR**, **total OI + overnight ΔOI** (Dhan chains carry previous_oi)
- **Gamma regime** (Positive/Negative) + flip level — gamma_lite.py
- Crypto extras: **funding rate**, **24h OI change**

Composite score = weighted cross-sectional percentile ranks
(weights in `config.SCORE_WEIGHTS`). Flags fire on hard thresholds:
`GAP_RISK`, `IMPLIED_MOVE_SPIKE`, `IV_RANK_EXTREME`, `HOT_REALIZED_VOL`,
`NEGATIVE_GAMMA_GAP` (critical), `OI_SPIKE`, `FUNDING_EXTREME`.

## Alerting

After each scan: one ranked **digest** (top `TOP_N_ALERTS`) plus individual
alerts for flagged symbols scoring ≥ `MIN_SCORE_FOR_ALERT`
(NEGATIVE_GAMMA_GAP always fires). Same symbol+flag deduped to once per
market per day. All alerts also stored in SQLite and shown at `/alerts`.

## India universe

`scanner/universe.py` parses the Dhan instrument master into
`instance/fno_universe.csv` (all ~226 FUTSTK underlyings with equity
security IDs + lot sizes). Dhan's option-chain API allows 1 request / 3 s,
so scans are paced; `INDIA_UNIVERSE_LIMIT` (default 60) caps how many
stocks are scanned after the 4 indices — the most liquid names first.
Refresh the master with `universe.build_india_universe(force=True)`.

## Data notes / limitations

- **Dhan token** expires periodically — regenerate at web.dhan.co and update
  `DHAN_ACCESS_TOKEN` in `~/quant_4/.env` (error 808 = expired token).
- Yahoo per-leg IVs are often junk pre-market/0DTE, so US ATM IV is derived
  from the traded ATM straddle (Brenner–Subrahmanyam approximation).
- `IVHistory` accumulates daily ATM IV per symbol so a true IV Rank can be
  added once a few months of history is logged (V2 roadmap: LightGBM model
  trained on the `features_json` snapshots + realized outcomes).
- India VIX / GIFT Nifty are not Dhan-native; not yet wired in (V1.5).

## Config knobs (env vars)

`INDIA_UNIVERSE_LIMIT`, `CRYPTO_UNIVERSE_LIMIT`, `CRYPTO_SCAN_INTERVAL_MIN`,
`TOP_N_ALERTS`, `MIN_SCORE_FOR_ALERT`, `GAP_ALERT_PCT`,
`IMPLIED_MOVE_ALERT_PCT`, `IV_HV_RATIO_ALERT`, `HV_RATIO_ALERT`,
`CRYPTO_FUNDING_ALERT`, `CRYPTO_OI_CHANGE_ALERT`, `VOLSCAN_PORT`,
`ENABLE_TELEGRAM`, `ENABLE_DISCORD`.
