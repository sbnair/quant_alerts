"""
Discord sender — embeds for individual alerts and the ranked digest.
"""

import requests

import config

COLORS = {"CRITICAL": 0xDC143C, "HIGH": 0xFF8C00, "MEDIUM": 0x1E90FF, "INFO": 0x808080}
EMOJI  = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "📊", "INFO": "ℹ️"}


def _post(payload: dict) -> bool:
    if not config.ENABLE_DISCORD:
        return False
    if not config.DISCORD_WEBHOOK_URL:
        print("[Discord] Missing DISCORD_WEBHOOK_URL")
        return False
    try:
        r = requests.post(config.DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[Discord] send error: {e}")
        return False


def _fv(v, digits=2, suffix=""):
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return str(v)


def send_alert(alert: dict) -> bool:
    row = alert.get("row", {})
    sev = alert.get("severity", "MEDIUM")
    fields = [
        {"name": "Spot",         "value": _fv(row.get("spot")),                 "inline": True},
        {"name": "Gap",          "value": _fv(row.get("gap_pct"), 2, "%"),      "inline": True},
        {"name": "Implied Move", "value": _fv(row.get("implied_move"), 2, "%"), "inline": True},
        {"name": "ATM IV",       "value": _fv(row.get("atm_iv"), 1, "%"),       "inline": True},
        {"name": "IV/HV",        "value": _fv(row.get("iv_hv_ratio")),          "inline": True},
        {"name": "HV5/HV20",     "value": _fv(row.get("hv_ratio")),             "inline": True},
        {"name": "Regime",       "value": row.get("regime") or "N/A",           "inline": True},
        {"name": "Vol Score",    "value": _fv(row.get("score"), 1) + "/100",    "inline": True},
        {"name": "Market",       "value": alert.get("market_type", "N/A"),      "inline": True},
    ]
    return _post({"embeds": [{
        "title": f"{EMOJI.get(sev, '📌')} {alert['alert_type'].replace('_', ' ')} — {alert['symbol']}",
        "description": alert.get("message", ""),
        "color": COLORS.get(sev, 0x808080),
        "fields": fields,
        "footer": {"text": "Volatility Scanner"},
    }]})


def send_digest(scored_rows: list[dict], market_type: str, scan_kind: str) -> bool:
    title = {"premarket": "Pre-Market Volatility Scan",
             "postopen": "Post-Open Rescan"}.get(scan_kind, "Volatility Scan")
    lines = [f"`{'#':>2} {'SYMBOL':<12} {'SCORE':>5} {'GAP%':>6} {'IMPL%':>6}` FLAGS"]
    for r in scored_rows:
        gap = f"{r['gap_pct']:+.1f}" if r.get("gap_pct") is not None else "n/a"
        im  = f"{r['implied_move']:.1f}" if r.get("implied_move") is not None else "n/a"
        lines.append(f"`{r['rank']:>2} {r['symbol']:<12} {r['score']:>5.1f} "
                     f"{gap:>6} {im:>6}` {r.get('flags') or ''}")
    return _post({"embeds": [{
        "title": f"📋 {title} — {market_type}",
        "description": "\n".join(lines)[:4000],
        "color": 0x9B59B6,
        "footer": {"text": "High score → expect wide range: size down, wider stops."},
    }]})
