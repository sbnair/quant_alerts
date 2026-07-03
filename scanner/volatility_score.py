"""
V1 rule-based composite volatility score (0–100) + threshold flags.

Each numeric feature is percentile-ranked cross-sectionally within the scan,
weighted per config.SCORE_WEIGHTS and summed. Flags fire on hard thresholds
regardless of rank so a single extreme name still alerts on a quiet day.
"""

import numpy as np
import pandas as pd

import config


def _pct_rank(series: pd.Series) -> pd.Series:
    """Percentile rank 0–1; NaNs get the neutral 0.5 so they neither boost nor sink."""
    r = series.rank(pct=True)
    return r.fillna(0.5)


def score_universe(features: list[dict]) -> pd.DataFrame:
    """features: list of per-symbol dicts. Returns df with score/rank/flags added."""
    df = pd.DataFrame(features)
    if df.empty:
        return df

    for col in ("implied_move", "gap_pct", "iv_hv_ratio", "hv_ratio",
                "oi_change_pct", "funding_rate", "atm_iv", "pcr"):
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "regime" not in df.columns:
        df["regime"] = None

    w = config.SCORE_WEIGHTS
    parts = (
        _pct_rank(df["implied_move"])         * w["implied_move"]
        + _pct_rank(df["gap_pct"].abs())      * w["gap_pct"]
        + _pct_rank(df["iv_hv_ratio"])        * w["iv_hv_ratio"]
        + _pct_rank(df["hv_ratio"])           * w["hv_ratio"]
        + _pct_rank(df["oi_change_pct"].abs())* w["oi_change"]
        + (df["regime"] == "Negative Gamma").astype(float) * w["negative_gamma"]
    )
    df["score"] = (parts / sum(w.values()) * 100).round(1)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    df["flags"] = df.apply(_flags, axis=1)
    return df


def _flags(row) -> str:
    f = []
    gap = row.get("gap_pct")
    if gap is not None and not pd.isna(gap) and abs(gap) >= config.GAP_ALERT_PCT:
        f.append("GAP_RISK")
    im = row.get("implied_move")
    if im is not None and not pd.isna(im) and im >= config.IMPLIED_MOVE_ALERT_PCT:
        f.append("IMPLIED_MOVE_SPIKE")
    ivhv = row.get("iv_hv_ratio")
    if ivhv is not None and not pd.isna(ivhv) and ivhv >= config.IV_HV_RATIO_ALERT:
        f.append("IV_RANK_EXTREME")
    hvr = row.get("hv_ratio")
    if hvr is not None and not pd.isna(hvr) and hvr >= config.HV_RATIO_ALERT:
        f.append("HOT_REALIZED_VOL")
    if row.get("regime") == "Negative Gamma" and gap is not None \
            and not pd.isna(gap) and abs(gap) >= 1.0:
        f.append("NEGATIVE_GAMMA_GAP")
    fr = row.get("funding_rate")
    if fr is not None and not pd.isna(fr) and abs(fr) >= config.CRYPTO_FUNDING_ALERT:
        f.append("FUNDING_EXTREME")
    oic = row.get("oi_change_pct")
    if oic is not None and not pd.isna(oic) and abs(oic) >= config.CRYPTO_OI_CHANGE_ALERT:
        f.append("OI_SPIKE")
    return ",".join(f)


# Severity of each flag when it becomes an individual alert
FLAG_SEVERITY = {
    "NEGATIVE_GAMMA_GAP":  "CRITICAL",
    "GAP_RISK":            "HIGH",
    "IMPLIED_MOVE_SPIKE":  "HIGH",
    "IV_RANK_EXTREME":     "MEDIUM",
    "HOT_REALIZED_VOL":    "MEDIUM",
    "OI_SPIKE":            "MEDIUM",
    "FUNDING_EXTREME":     "MEDIUM",
}

FLAG_GUIDANCE = {
    "NEGATIVE_GAMMA_GAP": "Negative gamma + gap: dealer hedging amplifies moves. Expect wide range; size down, avoid market orders at open.",
    "GAP_RISK":           "Large overnight gap. Expect elevated opening volatility; use wider stops.",
    "IMPLIED_MOVE_SPIKE": "Options price an outsized one-day move. Expect wide range; size positions accordingly.",
    "IV_RANK_EXTREME":    "IV far above realized vol — the market expects movement (possible event day).",
    "HOT_REALIZED_VOL":   "Short-term realized vol is running well above baseline; the hot streak tends to persist.",
    "OI_SPIKE":           "Unusual open-interest shift — positioning is changing fast.",
    "FUNDING_EXTREME":    "Extreme funding rate — crowded leverage; squeeze risk elevated.",
}
