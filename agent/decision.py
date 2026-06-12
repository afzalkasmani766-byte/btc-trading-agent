"""
Decision Engine
Combines all rules from knowledge.json to produce BUY / SELL / HOLD decision
Priority:
  1. Don't trade in sideways (option sell zone)
  2. Pattern signals (W, M, Breakout, Breakdown)
  3. Confirmation (trend + 50% candle + consecutive candles)
  4. Risk management validation (min 1:3 RR)
"""

from rules_engine import (
    detect_trend,
    detect_w_pattern,
    detect_m_pattern,
    detect_breakout,
    detect_50pct_candle_cross,
    detect_round_level,
    detect_consolidation,
    detect_consecutive_candles,
    detect_big_wick,
    detect_inverted_hammer,
    compute_atr,
    check_risk_reward
)


def make_decision(snapshot):
    """
    Main decision function.
    Returns dict: {action, entry, sl, target, rr, confidence, reasons}
    """
    price      = snapshot["price"]
    candles_1h = snapshot["candles_1h"]
    candles_4h = snapshot["candles_4h"]
    candles_1d = snapshot["candles_1d"]
    candles_1w = snapshot["candles_1w"]

    reasons    = []
    signals    = []  # list of (direction, weight, trade_info)

    # ── FILTER 1: No trade if no data ──────────────────────────────────
    if not price or not candles_1h:
        return _hold("No market data available")

    # ── FILTER 2: Sideways on 4H = no directional trade ───────────────
    if detect_consolidation(candles_4h, lookback=6):
        reasons.append("4H sideways — no directional trade")
        return _hold(" | ".join(reasons))

    # ── TREND ─────────────────────────────────────────────────────────
    trend_1d = detect_trend(candles_1d)
    trend_4h = detect_trend(candles_4h)
    trend_1h = detect_trend(candles_1h)
    reasons.append(f"Trend — 1D:{trend_1d} 4H:{trend_4h} 1H:{trend_1h}")

    # ── BIG WICK CHECK on last daily candle ───────────────────────────
    if candles_1d and detect_big_wick(candles_1d[-1]):
        reasons.append("Big wick on daily — limited move expected, reducing confidence")
        big_wick_day = True
    else:
        big_wick_day = False

    # ── ATR (volatility) ──────────────────────────────────────────────
    atr = compute_atr(candles_1h, 14) or 500

    # ── PATTERN DETECTION ─────────────────────────────────────────────

    # W Pattern (Buy)
    w_found, w_info = detect_w_pattern(candles_4h)
    if w_found:
        reasons.append("W Pattern on 4H — BUY signal")
        signals.append(("BUY", 3, w_info))

    # M Pattern (Sell)
    m_found, m_info = detect_m_pattern(candles_4h)
    if m_found:
        reasons.append("M Pattern on 4H — SELL signal")
        signals.append(("SELL", 3, m_info))

    # Breakout / Breakdown on 1H
    bo_found, bo_info = detect_breakout(candles_1h)
    if bo_found:
        direction = bo_info.get("direction", "BUY")
        reasons.append(f"{bo_info['pattern']} on 1H — {direction} signal")
        signals.append((direction, 2, bo_info))

    # 50% candle cross on 4H
    cross_signal = detect_50pct_candle_cross(candles_4h)
    if cross_signal:
        reasons.append(f"50% candle cross on 4H — {cross_signal} signal")
        signals.append((cross_signal, 1, None))

    # Consecutive candles (4+ bull = sell expected, 4+ bear = buy expected)
    if detect_consecutive_candles(candles_1h, "bull", 4):
        reasons.append("4 consecutive bullish 1H candles — reversal possible, SELL bias")
        signals.append(("SELL", 1, None))

    if detect_consecutive_candles(candles_1h, "bear", 4):
        reasons.append("4 consecutive bearish 1H candles — reversal possible, BUY bias")
        signals.append(("BUY", 1, None))

    # ── ROUND LEVEL ───────────────────────────────────────────────────
    round_lvl, dist_pct = detect_round_level(price)
    if dist_pct < 1.0:
        reasons.append(f"Near round level {round_lvl} ({dist_pct:.2f}% away) — strong S/R zone")

    # ── TREND CONFIRMATION FILTER ─────────────────────────────────────
    # With-trend trades get double weight, against-trend get half
    weighted = []
    for direction, weight, info in signals:
        if direction == "BUY" and trend_1d == "uptrend":
            weight *= 2
        elif direction == "SELL" and trend_1d == "downtrend":
            weight *= 2
        elif direction == "BUY" and trend_1d == "downtrend":
            weight = max(1, weight // 2)
            reasons.append("BUY signal against daily downtrend — reducing weight")
        elif direction == "SELL" and trend_1d == "uptrend":
            weight = max(1, weight // 2)
            reasons.append("SELL signal against daily uptrend — reducing weight")
        weighted.append((direction, weight, info))

    # ── AGGREGATE SIGNALS ─────────────────────────────────────────────
    buy_weight  = sum(w for d, w, _ in weighted if d == "BUY")
    sell_weight = sum(w for d, w, _ in weighted if d == "SELL")

    if buy_weight == 0 and sell_weight == 0:
        return _hold("No pattern signals detected — " + " | ".join(reasons))

    # ── PICK DIRECTION ────────────────────────────────────────────────
    if buy_weight >= sell_weight:
        direction = "BUY"
        best = next((info for d, w, info in weighted if d == "BUY" and info), None)
    else:
        direction = "SELL"
        best = next((info for d, w, info in weighted if d == "SELL" and info), None)

    # ── BUILD TRADE INFO IF PATTERN FOUND ────────────────────────────
    if best:
        entry  = best["entry"]
        sl     = best["sl"]
        target = best["target"]
    else:
        # Fallback: ATR-based SL and 1:3 target
        entry = price
        if direction == "BUY":
            sl     = price - atr * 1.5
            target = price + atr * 4.5
        else:
            sl     = price + atr * 1.5
            target = price - atr * 4.5

    # ── RISK:REWARD CHECK (min 1:3) ───────────────────────────────────
    valid_rr, rr = check_risk_reward(entry, sl, target, min_rr=3.0)
    if not valid_rr:
        return _hold(f"RR {rr} < 3.0 — skipping trade | " + " | ".join(reasons))

    # ── BIG WICK PENALTY ──────────────────────────────────────────────
    confidence = "HIGH"
    if big_wick_day:
        confidence = "MEDIUM"

    # ── AGAINST TREND PENALTY ────────────────────────────────────────
    if (direction == "BUY" and trend_1d == "downtrend") or \
       (direction == "SELL" and trend_1d == "uptrend"):
        confidence = "LOW"

    return {
        "action":     direction,
        "entry":      round(entry, 2),
        "sl":         round(sl, 2),
        "target":     round(target, 2),
        "rr":         rr,
        "confidence": confidence,
        "reasons":    reasons,
        "buy_score":  buy_weight,
        "sell_score": sell_weight
    }


def _hold(reason):
    return {
        "action":     "HOLD",
        "entry":      None,
        "sl":         None,
        "target":     None,
        "rr":         None,
        "confidence": None,
        "reasons":    [reason],
        "buy_score":  0,
        "sell_score": 0
    }
