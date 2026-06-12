"""
Rules Engine — extracted from 47 video knowledge base
All rules are derived from trainer's teachings in knowledge.json
"""

def detect_trend(candles):
    """
    Higher High + Higher Low = Uptrend
    Lower High + Lower Low = Downtrend
    """
    if len(candles) < 5:
        return "sideways"
    
    highs = [c["high"] for c in candles[-10:]]
    lows  = [c["low"]  for c in candles[-10:]]
    
    hh = highs[-1] > highs[-3] > highs[-5]
    hl = lows[-1]  > lows[-3]  > lows[-5]
    lh = highs[-1] < highs[-3] < highs[-5]
    ll = lows[-1]  < lows[-3]  < lows[-5]
    
    if hh and hl:
        return "uptrend"
    elif lh and ll:
        return "downtrend"
    else:
        return "sideways"


def detect_w_pattern(candles):
    """
    W pattern: market falls, bounces, falls again to similar low, then recovers
    Second low >= first low (higher low) = W confirmed
    """
    if len(candles) < 10:
        return False, None
    
    c = candles[-15:]
    lows = [x["low"] for x in c]
    
    # Find two significant lows
    min1_idx = lows.index(min(lows[:8]))
    min2_idx = min1_idx + 3 + lows[min1_idx+3:].index(min(lows[min1_idx+3:])) if min1_idx + 3 < len(lows) else None
    
    if min2_idx is None:
        return False, None
    
    low1 = lows[min1_idx]
    low2 = lows[min2_idx]
    
    # W pattern: second low within 1% of first, and last candle recovering
    if abs(low2 - low1) / low1 < 0.015 and c[-1]["close"] > c[-1]["open"]:
        entry = c[-1]["close"]
        sl    = min(low1, low2) * 0.998
        target = entry + (entry - sl) * 3
        return True, {"entry": entry, "sl": sl, "target": target, "pattern": "W_PATTERN"}
    
    return False, None


def detect_m_pattern(candles):
    """
    M pattern: market rises, pulls back, rises again to similar high, then fails
    Second high <= first high = M confirmed = sell signal
    """
    if len(candles) < 10:
        return False, None
    
    c = candles[-15:]
    highs = [x["high"] for x in c]
    
    max1_idx = highs.index(max(highs[:8]))
    max2_idx = max1_idx + 3 + highs[max1_idx+3:].index(max(highs[max1_idx+3:])) if max1_idx + 3 < len(highs) else None
    
    if max2_idx is None:
        return False, None
    
    high1 = highs[max1_idx]
    high2 = highs[max2_idx]
    
    if abs(high2 - high1) / high1 < 0.015 and c[-1]["close"] < c[-1]["open"]:
        entry = c[-1]["close"]
        sl    = max(high1, high2) * 1.002
        target = entry - (sl - entry) * 3
        return True, {"entry": entry, "sl": sl, "target": target, "pattern": "M_PATTERN"}
    
    return False, None


def detect_breakout(candles):
    """
    Consolidation (2+ candles in tight range) followed by breakout
    """
    if len(candles) < 6:
        return False, None
    
    c = candles[-6:]
    # Check consolidation in candles[-4:-2]
    consol = c[-4:-2]
    ranges = [x["high"] - x["low"] for x in consol]
    avg_range = sum(ranges) / len(ranges)
    
    last = c[-1]
    prev_high = max(x["high"] for x in consol)
    prev_low  = min(x["low"]  for x in consol)
    
    body = abs(last["close"] - last["open"])
    
    # Bullish breakout
    if last["close"] > prev_high and body > avg_range * 1.5:
        entry  = last["close"]
        sl     = prev_high * 0.998
        target = entry + (entry - sl) * 3
        return True, {"entry": entry, "sl": sl, "target": target, "direction": "BUY", "pattern": "BREAKOUT"}
    
    # Bearish breakdown
    if last["close"] < prev_low and body > avg_range * 1.5:
        entry  = last["close"]
        sl     = prev_low * 1.002
        target = entry - (sl - entry) * 3
        return True, {"entry": entry, "sl": sl, "target": target, "direction": "SELL", "pattern": "BREAKDOWN"}
    
    return False, None


def detect_50pct_candle_cross(candles):
    """
    If price crosses 50% of a significant previous candle — direction signal
    """
    if len(candles) < 5:
        return None
    
    # Find biggest candle in last 10
    last10 = candles[-10:-1]
    if not last10:
        return None
    
    big = max(last10, key=lambda x: abs(x["close"] - x["open"]))
    mid = (big["open"] + big["close"]) / 2
    current = candles[-1]["close"]
    
    if big["close"] > big["open"]:  # was bullish
        if current < mid:
            return "SELL"  # 50% crossed downward
    else:  # was bearish
        if current > mid:
            return "BUY"   # 50% crossed upward
    
    return None


def detect_round_level(price):
    """
    Check if price is near a round level (every 5000 points for BTC)
    Returns level and distance %
    """
    interval = 5000
    nearest = round(price / interval) * interval
    distance_pct = abs(price - nearest) / price * 100
    return nearest, distance_pct


def detect_consolidation(candles, lookback=5):
    """
    Returns True if market is in sideways/consolidation
    """
    if len(candles) < lookback:
        return False
    
    c = candles[-lookback:]
    highs  = [x["high"]  for x in c]
    lows   = [x["low"]   for x in c]
    closes = [x["close"] for x in c]
    
    range_pct = (max(highs) - min(lows)) / min(lows) * 100
    return range_pct < 3.0  # within 3% = sideways


def detect_consecutive_candles(candles, direction="bull", count=4):
    """
    Returns True if last `count` candles are consecutive in direction
    direction: "bull" or "bear"
    """
    if len(candles) < count:
        return False
    
    c = candles[-count:]
    if direction == "bull":
        return all(x["close"] > x["open"] for x in c)
    else:
        return all(x["close"] < x["open"] for x in c)


def detect_big_wick(candle):
    """
    Returns True if candle has a big wick (wick > 60% of total range)
    Big wick = limited move expected
    """
    total = candle["high"] - candle["low"]
    if total == 0:
        return False
    body = abs(candle["close"] - candle["open"])
    return body / total < 0.4


def detect_inverted_hammer(candle):
    """
    Inverted hammer: small body at bottom, long upper wick
    Potential reversal signal after downtrend
    """
    body  = abs(candle["close"] - candle["open"])
    total = candle["high"] - candle["low"]
    if total == 0:
        return False
    upper_wick = candle["high"] - max(candle["open"], candle["close"])
    return upper_wick > body * 2 and body / total < 0.35


def compute_atr(candles, period=14):
    """Average True Range for volatility measure"""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, period + 1):
        c = candles[-i]
        p = candles[-i-1]
        tr = max(c["high"] - c["low"],
                 abs(c["high"] - p["close"]),
                 abs(c["low"]  - p["close"]))
        trs.append(tr)
    return sum(trs) / len(trs)


def check_risk_reward(entry, sl, target, min_rr=3.0):
    """Validate minimum risk:reward ratio"""
    risk   = abs(entry - sl)
    reward = abs(target - entry)
    if risk == 0:
        return False, 0
    rr = reward / risk
    return rr >= min_rr, round(rr, 2)
