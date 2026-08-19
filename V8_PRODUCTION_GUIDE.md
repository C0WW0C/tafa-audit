# TAFA V8 — Production Bot Guide

## ✨ What's New

### 1. **Resilience Architecture**
- ✅ **Exponential backoff** retry logic (OKX client)
- ✅ **Circuit breaker** pattern (prevent cascades)
- ✅ **State checkpoints** (atomic recovery from crashes)
- ✅ **Multi-strategy fusion** (consensus voting)

### 2. **Modular Dashboard**
- Separated **routes**, **payloads**, **handlers**
- Rate limiting ready (extensible)
- SSE/streaming ready
- Clean separation of concerns

### 3. **Production Ready**
- Proper thread-safety (`threading.RLock`)
- Comprehensive logging
- Error handling chains
- Graceful shutdown

---

## 🚀 Quick Start (OKX Demo)

### Setup

```bash
# 1. Clone & install
git clone https://github.com/C0WW0C/tafa-audit.git
cd tafa-audit
git checkout feature/bot-v8-production
pip install -r requirements_v8.txt

# 2. Create .env
cat > .env.v8 << EOF
OKX_API_KEY=your_demo_key
OKX_SECRET_KEY=your_demo_secret
OKX_PASSPHRASE=your_demo_passphrase
PAPER_TRADING=true
TAFA_MODE=PAPER
EOF

# 3. Run
python run_v8_okx_demo.py --symbol BTC-USDC --port 8765
```

### Monitor

```bash
# Health check
curl http://127.0.0.1:8765/api/health | jq .

# Bot status
curl http://127.0.0.1:8765/api/status | jq .
```

---

## 🏗️ Architecture

```
bot_v8_core.py
├── BotV8              (main orchestrator)
├── StateCheckpoint    (atomic recovery)
├── CircuitBreaker     (resilience)
└── StrategyFusion     (multi-strategy)

dashboard_v8.py
├── PayloadBuilder     (response generation)
├── RouteHandler       (endpoint routing)
└── DashboardV8        (HTTP handler)

run_v8_okx_demo.py    (entry point)
```

---

## 🔧 Extending

### Add a Strategy

```python
class MyStrategy:
    def analyze(self, symbol: str, price: float) -> str:
        # Return "BUY", "SELL", or "HOLD"
        return "HOLD"

bot = BotV8()
bot.strategy_fusion.register("my_strategy", MyStrategy(), weight=1.5)
```

### Add an API Endpoint

```python
class RouteHandler:
    def route(self, path: str, method: str = "GET"):
        if path == "/api/custom":
            return {"data": "custom"}, 200
        # ...
```

---

## 📊 State Persistence

Bot saves state every 50 cycles to `data/checkpoints/current.json`:

```json
{
  "timestamp": "2026-08-19T22:56:06.123456Z",
  "cycle_count": 2500,
  "symbol": "BTC-USDC",
  "last_price": 65432.50,
  "last_signal": "BUY"
}
```

On restart, state is **automatically recovered**.

---

## 🚨 Circuit Breaker

Triggered after 5 consecutive failures:

```
FAILURE #1 → retry
FAILURE #2 → retry
FAILURE #3 → retry
FAILURE #4 → retry
FAILURE #5 → CIRCUIT OPEN (30s cooldown)
      ↓
   (waiting)
      ↓
SUCCESS → CIRCUIT CLOSED (reset)
```

---

## 📈 Performance

- **Cycle latency**: ~50-100ms (paper trading)
- **Memory**: ~50MB
- **CPU**: <1% idle

---

## 🔐 Security

✅ OKX credentials in `.env` (not in code)
✅ Demo mode by default
✅ Loopback-only dashboard (127.0.0.1)
✅ No hardcoded secrets

---

## 📝 License

MIT — Use freely, modify as needed.
