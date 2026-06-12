"""
BTC Trading Agent — Main Entry Point
Runs every hour via GitHub Actions
Flow: Market Data → Rules Engine → Decision → Paper Trade
"""

import json
import sys
import os
from datetime import datetime

# Add agent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from market_data import get_market_snapshot
from decision    import make_decision
from paper_trade import (
    load_state, save_state,
    open_trade, check_and_close_trade,
    get_summary
)


def run():
    print(f"\n{'='*60}")
    print(f"BTC Agent Run — {datetime.utcnow().isoformat()} UTC")
    print(f"{'='*60}")

    # 1. Load portfolio state
    state = load_state()
    summary = get_summary(state)
    print(f"\n[PORTFOLIO] Capital: ${summary['capital']} | PnL: ${summary['total_pnl']} | "
          f"Trades: {summary['trade_count']} | Win Rate: {summary['win_rate']}%")

    # 2. Get live market data
    print("\n[MARKET] Fetching live data from Binance...")
    snapshot = get_market_snapshot()
    if not snapshot["price"]:
        print("[ERROR] Could not fetch market data. Exiting.")
        return

    price = snapshot["price"]
    print(f"[MARKET] BTC/USDT = ${price:,.2f}")

    # 3. Check if open position hit SL or Target
    state, closed = check_and_close_trade(state, price)
    if closed:
        print(f"[CLOSED] Trade #{closed['id']} — {closed['close_reason']} | PnL: ${closed['pnl']:.2f}")

    # 4. Make decision (only if no open position)
    if not state["open_position"]:
        print("\n[DECISION] Analyzing market...")
        decision = make_decision(snapshot)

        print(f"[DECISION] Action: {decision['action']}")
        for r in decision["reasons"]:
            print(f"  → {r}")

        if decision["action"] in ("BUY", "SELL"):
            print(f"\n[SIGNAL] {decision['action']} @ {decision['entry']} | "
                  f"SL: {decision['sl']} | Target: {decision['target']} | RR: {decision['rr']}")

            # 5. Open paper trade
            state, opened = open_trade(state, decision, price)
            if opened:
                print(f"[TRADE] Paper trade opened successfully")
        else:
            print("[HOLD] No trade this hour")
    else:
        pos = state["open_position"]
        print(f"\n[HOLDING] {pos['action']} position open since {pos['open_time']}")
        print(f"  Entry: {pos['entry']} | SL: {pos['sl']} | Target: {pos['target']}")

    # 6. Save state
    save_state(state)

    # 7. Final summary
    summary = get_summary(state)
    print(f"\n[SUMMARY] Capital: ${summary['capital']} | Total PnL: ${summary['total_pnl']} | "
          f"Trades: {summary['trade_count']} | Wins: {summary['win_count']} | Losses: {summary['loss_count']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
