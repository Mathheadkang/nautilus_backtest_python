# Backtesting Framework

A **pure Python backtesting and trading framework** inspired by NautilusTrader. This lightweight, event-driven framework enables development, testing, and analysis of trading strategies using historical market data.

## Features

- 🎯 **Event-driven architecture** - Simulates real-time trading with proper event sequencing
- 💼 **Portfolio & risk management** - Built-in position tracking, PnL calculation, and risk controls
- 📊 **Technical indicators** - EMA, SMA, ATR indicators ready to use
- 📝 **Order management** - Market, limit, stop orders with proper state transitions
- ⚡ **Fast backtesting** - Efficient simulation with detailed performance metrics
- 🐍 **Pure Python** - Minimal dependencies for easy integration
- 🔌 **Polymarket integration** - Live trading and data client support

## Quick Start

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd backtesting_framework

# Install the package
pip install -e .

# Or install with live trading support
pip install -e ".[live]"
```

### Requirements

- Python >= 3.10
- pandas >= 1.5
- matplotlib >= 3.10.8

### Simple Example

```python
from nautilus_core.backtest import BacktestEngine, BacktestConfig
from nautilus_core.trading import Strategy, StrategyConfig
from nautilus_core.data import Bar
from datetime import datetime, timedelta
import pandas as pd

# Create a simple strategy
class MyStrategy(Strategy):
    def on_start(self):
        self.subscribe_bars(self.config.instrument_id)
    
    def on_bar(self, bar: Bar):
        if not self.portfolio.is_flat(self.config.instrument_id):
            return
        # Buy when price is below 50
        if bar.close < 50:
            self.buy(self.config.instrument_id, 1.0)

# Generate sample data
bars = [...]  # Your historical bar data

# Configure and run backtest
config = BacktestConfig(
    venue="SIM",
    starting_balances={"USD": 10000}
)

engine = BacktestEngine(config=config)
engine.add_instrument(instrument)
engine.add_strategy(MyStrategy(config=strategy_config))
engine.add_bars(instrument.id, bars)
engine.run()

# View results
results = engine.generate_report()
print(results)
```

## Architecture

### Core Components

- **Backtest Engine** - Main orchestrator for simulated trading
- **Strategy Framework** - Base classes for implementing trading logic
- **Portfolio Manager** - Tracks positions, PnL, and account balances
- **Execution Engine** - Handles order routing and lifecycle management
- **Data Engine** - Routes market data to subscribers
- **Cache** - Central repository for instruments, orders, and positions
- **Message Bus** - Pub/sub messaging system for events

### Module Structure

```
nautilus_core/
├── backtest/          # Backtesting engine and configuration
├── indicators/        # Technical indicators (EMA, SMA, ATR)
├── trading/           # Strategy framework
└── ...                # Core components (portfolio, execution, etc.)

polymarket/            # Polymarket integration
├── data_client.py     # Historical data client
├── live_client.py     # Live trading client
├── instruments.py     # Polymarket instruments
└── strategies.py      # Example strategies

examples/              # Example strategies and backtests
tests/                 # Test suite
```

## Examples

Check out the [examples](examples/) directory for complete working examples:

- **[buy_and_hold.py](examples/buy_and_hold.py)** - Simple buy and hold strategy
- **[ema_cross_strategy.py](examples/ema_cross_strategy.py)** - EMA crossover strategy
- **[run_backtest.py](examples/run_backtest.py)** - Full backtest example

### Polymarket Examples

- **[example_backtest_live_data.py](polymarket/example_backtest_live_data.py)** - Backtest using live Polymarket data
- **[example_backtest_synthetic.py](polymarket/example_backtest_synthetic.py)** - Backtest with synthetic data
- **[example_live_trading.py](polymarket/example_live_trading.py)** - Live trading example

## Documentation

For detailed documentation, see [DOCUMENTATION.md](DOCUMENTATION.md) which includes:

- Architecture overview
- Complete API reference
- Step-by-step tutorials
- Advanced topics and best practices

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test file
pytest tests/test_backtest_engine.py
```

### Project Structure

The framework follows a modular design:
- Core trading functionality in `nautilus_core/`
- Polymarket-specific code in `polymarket/`
- Examples in `examples/`
- Tests in `tests/`

## Live Trading

The framework supports live trading with Polymarket:

```python
from polymarket import PolymarketLiveClient
from dotenv import load_dotenv

load_dotenv()

client = PolymarketLiveClient(
    api_key=os.getenv("POLYMARKET_API_KEY"),
    # ... configuration
)

# Add your strategy and start trading
client.add_strategy(MyStrategy(config))
client.start()
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source. See LICENSE file for details.

## Acknowledgments

Inspired by [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) - A professional algorithmic trading platform.
