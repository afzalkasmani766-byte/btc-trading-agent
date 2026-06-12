import requests
import time

BINANCE_BASE = "https://api.binance.com/api/v3"

def get_current_price():
    try:
        r = requests.get(f"{BINANCE_BASE}/ticker/price", params={"symbol": "BTCUSDT"}, timeout=10)
        data = r.json()
        # Handle both formats
        if isinstance(data, dict) and "price" in data:
            return float(data["price"])
        return None
    except Exception as e:
        print(f"[ERROR] get_current_price: {e}")
        return None

def get_candles(interval="1h", limit=50):
    try:
        r = requests.get(f"{BINANCE_BASE}/klines", params={
            "symbol": "BTCUSDT",
            "interval": interval,
            "limit": limit
        }, timeout=10)
        raw = r.json()
        if not isinstance(raw, list):
            print(f"[ERROR] get_candles: unexpected response {raw}")
            return []
        candles = []
        for c in raw:
            try:
                candles.append({
                    "time":   int(c[0]),
                    "open":   float(c[1]),
                    "high":   float(c[2]),
                    "low":    float(c[3]),
                    "close":  float(c[4]),
                    "volume": float(c[5])
                })
            except (ValueError, IndexError) as e:
                print(f"[ERROR] candle parse: {e} — {c}")
                continue
        return candles
    except Exception as e:
        print(f"[ERROR] get_candles: {e}")
        return []

def get_market_snapshot():
    return {
        "price":       get_current_price(),
        "candles_1h":  get_candles("1h",  50),
        "candles_4h":  get_candles("4h",  30),
        "candles_1d":  get_candles("1d",  30),
        "candles_1w":  get_candles("1w",  12),
        "timestamp":   int(time.time())
    }