"""
Paper Trading Engine
Manages virtual $10,000 portfolio
Tracks open positions, closed trades, P&L
"""

import json
import os
import time
from datetime import datetime

TRADE_LOG_PATH = "trade_log.json"
INITIAL_CAPITAL = 10000.0
MAX_RISK_PER_TRADE = 0.01   # 1% per trade (from knowledge.json)
MAX_DAILY_RISK     = 0.03   # 3% daily max (from knowledge.json)


def load_state():
    if os.path.exists(TRADE_LOG_PATH):
        with open(TRADE_LOG_PATH, "r") as f:
            return json.load(f)
    return {
        "capital":        INITIAL_CAPITAL,
        "open_position":  None,
        "closed_trades":  [],
        "daily_loss":     0.0,
        "daily_loss_date": "",
        "total_pnl":      0.0,
        "trade_count":    0,
        "win_count":      0,
        "loss_count":     0
    }


def save_state(state):
    with open(TRADE_LOG_PATH, "w") as f:
        json.dump(state, f, indent=2)


def reset_daily_loss_if_new_day(state):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if state["daily_loss_date"] != today:
        state["daily_loss"]     = 0.0
        state["daily_loss_date"] = today
    return state


def calculate_position_size(capital, entry, sl):
    """
    Risk 1% of capital per trade
    Position size = (capital * 0.01) / (entry - sl) in BTC units
    """
    risk_amount = capital * MAX_RISK_PER_TRADE
    risk_per_unit = abs(entry - sl)
    if risk_per_unit == 0:
        return 0
    size = risk_amount / risk_per_unit
    return round(size, 6)


def open_trade(state, decision, current_price):
    """Open a new paper trade"""
    state = reset_daily_loss_if_new_day(state)

    # Check daily loss limit
    if state["daily_loss"] >= state["capital"] * MAX_DAILY_RISK:
        print(f"[SKIP] Daily loss limit reached: {state['daily_loss']:.2f}")
        return state, False

    # No double position
    if state["open_position"]:
        print("[SKIP] Position already open")
        return state, False

    entry  = decision["entry"]
    sl     = decision["sl"]
    target = decision["target"]
    action = decision["action"]

    size = calculate_position_size(state["capital"], entry, sl)
    if size <= 0:
        print("[SKIP] Position size is zero")
        return state, False

    state["open_position"] = {
        "id":         state["trade_count"] + 1,
        "action":     action,
        "entry":      entry,
        "sl":         sl,
        "target":     target,
        "size":       size,
        "rr":         decision["rr"],
        "confidence": decision["confidence"],
        "reasons":    decision["reasons"],
        "open_time":  datetime.utcnow().isoformat(),
        "open_price": current_price
    }
    state["trade_count"] += 1
    print(f"[TRADE OPEN] {action} @ {entry} | SL: {sl} | Target: {target} | Size: {size} BTC | RR: {decision['rr']}")
    return state, True


def check_and_close_trade(state, current_price):
    """Check if open position hit SL or Target"""
    pos = state["open_position"]
    if not pos:
        return state, None

    action = pos["action"]
    hit    = None
    pnl    = 0

    if action == "BUY":
        if current_price <= pos["sl"]:
            hit = "SL"
            pnl = (pos["sl"] - pos["entry"]) * pos["size"]
        elif current_price >= pos["target"]:
            hit = "TARGET"
            pnl = (pos["target"] - pos["entry"]) * pos["size"]
    else:  # SELL
        if current_price >= pos["sl"]:
            hit = "SL"
            pnl = (pos["entry"] - pos["sl"]) * pos["size"]
        elif current_price <= pos["target"]:
            hit = "TARGET"
            pnl = (pos["entry"] - pos["target"]) * pos["size"]

    if hit:
        closed = {**pos, "close_reason": hit, "close_price": current_price,
                  "close_time": datetime.utcnow().isoformat(), "pnl": round(pnl, 4)}
        state["closed_trades"].append(closed)
        state["capital"]      += pnl
        state["total_pnl"]    += pnl
        state["open_position"] = None

        if pnl > 0:
            state["win_count"] += 1
        else:
            state["loss_count"]  += 1
            state["daily_loss"]  += abs(pnl)

        print(f"[TRADE CLOSED] {hit} | PnL: {pnl:.4f} | Capital: {state['capital']:.2f}")
        return state, closed

    # Still open — print update
    if action == "BUY":
        unrealized = (current_price - pos["entry"]) * pos["size"]
    else:
        unrealized = (pos["entry"] - current_price) * pos["size"]
    print(f"[POSITION OPEN] {action} @ {pos['entry']} | Current: {current_price} | Unrealized PnL: {unrealized:.4f}")
    return state, None


def get_summary(state):
    total   = state["win_count"] + state["loss_count"]
    win_rate = (state["win_count"] / total * 100) if total > 0 else 0
    return {
        "capital":     round(state["capital"], 2),
        "total_pnl":   round(state["total_pnl"], 4),
        "trade_count": state["trade_count"],
        "win_count":   state["win_count"],
        "loss_count":  state["loss_count"],
        "win_rate":    round(win_rate, 1),
        "open":        state["open_position"] is not None
    }
