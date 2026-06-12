# BTC Trading Agent 🤖

Rule-based paper trading agent for BTC/USDT.
Runs every hour via GitHub Actions using live Binance data.

## Architecture
```
Binance API (free, no key needed)
      ↓
Rules Engine (W/M pattern, breakout, 50% cross, trend)
      ↓
Decision (BUY / SELL / HOLD)
      ↓
Paper Trade ($10,000 virtual capital)
      ↓
trade_log.json (auto-committed to repo)
```

## Rules (from 47 trading videos)
- W Pattern → BUY signal
- M Pattern → SELL signal
- Consolidation breakout/breakdown
- 50% candle cross confirmation
- Trend alignment (HH/HL = uptrend, LH/LL = downtrend)
- Round level awareness (5000 point intervals)
- Big wick detection (limits move expectation)
- Consecutive candles (4+ = reversal possible)
- Min 1:3 Risk:Reward enforced
- Max 1% risk per trade
- Max 3% daily loss limit

## Files
```
agent/
  main.py          # Entry point (GitHub Actions calls this)
  market_data.py   # Binance live API
  rules_engine.py  # All trading rules
  decision.py      # Combines rules → BUY/SELL/HOLD
  paper_trade.py   # Virtual $10,000 portfolio manager
trade_log.json     # Live portfolio state (auto-updated)
requirements.txt
.github/workflows/agent.yml   # Hourly schedule
```

## Setup
1. Fork / clone this repo
2. Go to Settings → Actions → General → Allow all actions
3. Agent runs automatically every hour
4. Check `trade_log.json` for results
5. Manual trigger: Actions tab → "BTC Trading Agent" → Run workflow
