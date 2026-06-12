import requests
import time

BINANCE_BASE = "https://api.binance.com/api/v3"

def get_current_price():
    """Get live BTC/USDT price from Binance"""
    try:
        r = requests.get(f"{BINANCE_BASE}/ticker/price", params={"symbol": "BTCUSDT"}, timeout=10)
        return float(r.json()["price"])
    except Exception as e:
        print(f"[ERROR] get_current_price: {e}")
        return None

def get_candles(interval="1h", limit=50):
    """
    Get OHLCV candles from Binance
    interval options: 1m, 5m, 15m, 1h, 4h, 1d, 1w, 1M
    Returns list of dicts: {open, high, low, close, volume, time}
    """
    try:
        r = requests.get(f"{BINANCE_BASE}/klines", params={
            "symbol": "BTCUSDT",
            "interval": interval,
            "limit": limit
        }, timeout=10)
        raw = r.json()
        candles = []
        for c in raw:
            candles.append({
                "time": c[0],
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5])
            })
        return candles
    except Exception as e:
        print(f"[ERROR] get_candles: {e}")
        return []

def get_daily_candles(limit=30):
    return get_candles("1d", limit)

def get_hourly_candles(limit=50):
    return get_candles("1h", limit)

def get_weekly_candles(limit=12):
    return get_candles("1w", limit)

def get_market_snapshot():
    """Full market snapshot for agent decision"""
    return {
        "price": get_current_price(),
        "candles_1h": get_candles("1h", 50),
        "candles_4h": get_candles("4h", 30),
        "candles_1d": get_candles("1d", 30),
        "candles_1w": get_candles("1w", 12),
        "timestamp": int(time.time())
    }
