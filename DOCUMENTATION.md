# Backtesting Framework Documentation

## Overview

This is a **pure Python backtesting/trading framework** inspired by NautilusTrader. It provides a lightweight, event-driven architecture for developing, testing, and analyzing trading strategies using historical market data.

### Key Features

- **Event-driven architecture**: Simulates real-time trading with proper event sequencing
- **Portfolio & risk management**: Built-in position tracking, PnL calculation, and risk controls
- **Technical indicators**: EMA, SMA, ATR indicators ready to use
- **Order management**: Market, limit, stop orders with proper state transitions
- **Backtesting engine**: Fast simulation with detailed performance metrics
- **Pure Python**: No external dependencies except pandas (and pytest for testing)

---

## Architecture

### Core Components

The framework is organized into several key modules:

#### 1. **Backtest Engine** (`nautilus_core.backtest.engine`)
The main orchestrator that:
- Manages simulated venues/exchanges
- Coordinates time-based event processing
- Routes market data to strategies
- Executes orders through simulated exchange
- Generates performance reports

#### 2. **Strategy Framework** (`nautilus_core.trading.strategy`)
Base class for implementing trading strategies with:
- Lifecycle hooks (`on_start`, `on_stop`, `on_bar`, etc.)
- Order submission methods
- Position management utilities
- Event handlers for orders and positions

#### 3. **Portfolio Manager** (`nautilus_core.portfolio`)
Tracks:
- Open and closed positions
- Realized and unrealized PnL
- Account balances across venues
- Net exposure and position sizing

#### 4. **Execution Engine** (`nautilus_core.execution_engine`)
Handles:
- Order routing to venues
- Order lifecycle management
- Risk checks before submission

#### 5. **Data Engine** (`nautilus_core.data_engine`)
- Routes market data (bars, ticks) to subscribers
- Manages data subscriptions

#### 6. **Cache** (`nautilus_core.cache`)
Central repository for:
- Instruments
- Accounts
- Orders
- Positions
- Other entities

#### 7. **Message Bus** (`nautilus_core.msgbus`)
Pub/sub messaging system for event distribution

---

## Installation & Setup

### Requirements
- Python >= 3.10
- pandas >= 1.5
- pytest >= 7.0 (for development)

### Installation

```bash
# Clone or navigate to the project directory
cd backtesting_framework

# Install in development mode (recommended)
pip install -e .

# Or install dependencies directly
pip install pandas pytest
```

---

## Quick Start Guide

### Basic Workflow

1. **Define an instrument** (what you're trading)
2. **Generate or load market data** (bars, ticks)
3. **Create a strategy** (your trading logic)
4. **Configure the backtest engine**
5. **Run the backtest**
6. **Analyze results**

### Example: Simple Buy and Hold Strategy

```python
from nautilus_core.backtest.engine import BacktestEngine
from nautilus_core.data import Bar, BarSpecification, BarType
from nautilus_core.enums import AccountType, AssetClass, BarAggregation, OmsType, PriceType
from nautilus_core.identifiers import InstrumentId, Symbol, Venue
from nautilus_core.instruments import Equity
from nautilus_core.objects import USD, Money, Price, Quantity
from nautilus_core.trading.strategy import Strategy
from nautilus_core.trading.config import StrategyConfig
from nautilus_core.enums import OrderSide
from decimal import Decimal

# 1. Setup instrument
venue = Venue("SIM")
symbol = Symbol("AAPL")
instrument_id = InstrumentId(symbol, venue)

instrument = Equity(
    instrument_id=instrument_id,
    quote_currency=USD,
    price_precision=2,
    size_precision=0,
    maker_fee=Decimal("0.0001"),
    taker_fee=Decimal("0.0002"),
)

# 2. Create bar type for 1-minute bars
bar_spec = BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST)
bar_type = BarType(instrument_id, bar_spec)

# 3. Generate or load data (simplified example)
bars = [
    Bar(
        bar_type=bar_type,
        open=Price(100.0, 2),
        high=Price(101.0, 2),
        low=Price(99.0, 2),
        close=Price(100.5, 2),
        volume=Quantity(1000, 0),
        ts_event=1_000_000_000_000_000_000,
        ts_init=1_000_000_000_000_000_000,
    ),
    # ... more bars
]

# 4. Define a simple strategy
class BuyAndHoldStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.bought = False
        
    def on_start(self):
        self.instrument_id = InstrumentId.from_str("AAPL.SIM")
    
    def on_bar(self, bar):
        if not self.bought:
            instrument = self.cache.instrument(self.instrument_id)
            qty = instrument.make_qty(100)
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                side=OrderSide.BUY,
                quantity=qty,
                ts_init=bar.ts_event,
            )
            self.submit_order(order)
            self.bought = True

# 5. Setup and run backtest
engine = BacktestEngine(trader_id="BACKTESTER-001")

engine.add_venue(
    venue_name="SIM",
    oms_type=OmsType.NETTING,
    account_type=AccountType.CASH,
    base_currency=USD,
    starting_balances=[Money("100000", USD)],
)

engine.add_instrument(instrument)
engine.add_data(bars)

strategy = BuyAndHoldStrategy()
engine.add_strategy(strategy)
strategy.subscribe_bars(bar_type)

# 6. Run and get results
engine.run()
result = engine.get_result()
print(result)
```

---

## Detailed Usage

### 1. Creating Strategies

Strategies inherit from `Strategy` base class and implement lifecycle methods:

#### Strategy Configuration

```python
from nautilus_core.trading.config import StrategyConfig
from nautilus_core.trading.strategy import Strategy

class MyStrategyConfig(StrategyConfig):
    def __init__(self, instrument_id: str, param1: int, param2: float):
        super().__init__(strategy_id="MyStrategy")
        self.instrument_id_str = instrument_id
        self.param1 = param1
        self.param2 = param2
```

#### Strategy Implementation

```python
class MyStrategy(Strategy):
    def __init__(self, config: MyStrategyConfig):
        super().__init__(config)
        self._config = config
        self.instrument_id = None
        
    def on_start(self):
        """Called once when the strategy starts"""
        self.instrument_id = InstrumentId.from_str(self._config.instrument_id_str)
        # Initialize indicators, state, etc.
        
    def on_bar(self, bar: Bar):
        """Called for each bar of subscribed data"""
        # Your trading logic here
        instrument = self.cache.instrument(self.instrument_id)
        
        # Check current position
        is_flat = self.portfolio.is_flat(self.instrument_id)
        is_long = self.portfolio.is_net_long(self.instrument_id)
        
        # Submit orders
        if is_flat and some_condition:
            qty = instrument.make_qty(100)
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                side=OrderSide.BUY,
                quantity=qty,
                ts_init=bar.ts_event,
            )
            self.submit_order(order)
            
    def on_stop(self):
        """Called when strategy stops - cleanup"""
        self.close_all_positions(self.instrument_id)
```

#### Available Lifecycle Hooks

- `on_start()`: Initialization when strategy starts
- `on_stop()`: Cleanup when strategy stops
- `on_bar(bar)`: Process bar data
- `on_quote_tick(tick)`: Process quote tick
- `on_trade_tick(tick)`: Process trade tick
- `on_order_filled(event)`: Handle order fill events
- `on_order_rejected(event)`: Handle order rejections
- `on_position_opened(event)`: New position opened
- `on_position_closed(event)`: Position closed

### 2. Using Indicators

The framework provides built-in technical indicators:

#### Exponential Moving Average (EMA)

```python
from nautilus_core.indicators.ema import ExponentialMovingAverage

class EMACrossStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.fast_ema = ExponentialMovingAverage(period=10)
        self.slow_ema = ExponentialMovingAverage(period=30)
        
    def on_bar(self, bar):
        # Update indicators
        self.fast_ema.handle_bar(bar)
        self.slow_ema.handle_bar(bar)
        
        # Wait until indicators are ready
        if not self.slow_ema.initialized:
            return
            
        # Use indicator values
        if self.fast_ema.value > self.slow_ema.value:
            # Bullish signal
            pass
```

#### Simple Moving Average (SMA)

```python
from nautilus_core.indicators.sma import SimpleMovingAverage

sma = SimpleMovingAverage(period=20)
sma.handle_bar(bar)
print(sma.value)  # Current SMA value
print(sma.initialized)  # True after 'period' bars
```

#### Average True Range (ATR)

```python
from nautilus_core.indicators.atr import AverageTrueRange

atr = AverageTrueRange(period=14)
atr.handle_bar(bar)
# Use for volatility-based position sizing or stop losses
stop_distance = atr.value * 2
```

#### Custom Indicators

```python
from nautilus_core.indicators.base import Indicator
from nautilus_core.data import Bar

class MyCustomIndicator(Indicator):
    def __init__(self, period: int):
        super().__init__(f"MyIndicator({period})")
        self.period = period
        self.value = 0.0
        
    def handle_bar(self, bar: Bar):
        self.has_inputs = True
        self._count += 1
        
        # Your calculation logic
        price = bar.close.as_double()
        self.value = price  # simplified
        
        if self._count >= self.period:
            self.initialized = True
            
    def reset(self):
        super().reset()
        self.value = 0.0
```

### 3. Order Management

#### Order Types

```python
from nautilus_core.enums import OrderSide, OrderType, TimeInForce

# Market Order (immediate execution at current price)
order = self.order_factory.market(
    instrument_id=instrument_id,
    side=OrderSide.BUY,  # or OrderSide.SELL
    quantity=qty,
    ts_init=timestamp,
)

# Limit Order (execute at specified price or better)
order = self.order_factory.limit(
    instrument_id=instrument_id,
    side=OrderSide.BUY,
    quantity=qty,
    price=limit_price,
    time_in_force=TimeInForce.GTC,  # Good Till Cancel
    ts_init=timestamp,
)

# Stop Market Order (triggered when price reaches stop price)
order = self.order_factory.stop_market(
    instrument_id=instrument_id,
    side=OrderSide.SELL,
    quantity=qty,
    trigger_price=stop_price,
    ts_init=timestamp,
)
```

#### Submitting & Managing Orders

```python
# Submit order
self.submit_order(order)

# Cancel order
self.cancel_order(order)

# Cancel all orders for an instrument
self.cancel_all_orders(instrument_id)

# Modify order (if supported)
self.modify_order(order, quantity=new_qty, price=new_price)
```

### 4. Position Management

#### Checking Positions

```python
# Check if flat (no position)
is_flat = self.portfolio.is_flat(instrument_id)

# Check if long
is_long = self.portfolio.is_net_long(instrument_id)

# Check if short
is_short = self.portfolio.is_net_short(instrument_id)

# Get net position quantity
net_qty = self.portfolio.net_position(instrument_id)
```

#### Closing Positions

```python
# Close a specific position
position = self.cache.positions_open(instrument_id=instrument_id)[0]
self.close_position(position, ts_init=timestamp)

# Close all positions for an instrument
self.close_all_positions(instrument_id, ts_init=timestamp)
```

#### Position Analytics

```python
# Realized PnL
realized = self.portfolio.realized_pnl(instrument_id)

# Unrealized PnL (requires current price)
unrealized = self.portfolio.unrealized_pnl(instrument_id, last_price)

# Total PnL
total = self.portfolio.total_pnl(instrument_id, last_price)

# Net exposure
exposure = self.portfolio.net_exposure(instrument_id, last_price)
```

### 5. Working with Market Data

#### Bar Data Structure

```python
from nautilus_core.data import Bar, BarSpecification, BarType
from nautilus_core.enums import BarAggregation, PriceType
from nautilus_core.objects import Price, Quantity

# Define bar specification
bar_spec = BarSpecification(
    step=1,  # 1 minute
    aggregation=BarAggregation.MINUTE,
    price_type=PriceType.LAST,
)

# Create bar type
bar_type = BarType(instrument_id, bar_spec)

# Create a bar
bar = Bar(
    bar_type=bar_type,
    open=Price(100.0, precision=2),
    high=Price(101.0, precision=2),
    low=Price(99.5, precision=2),
    close=Price(100.5, precision=2),
    volume=Quantity(1000, precision=0),
    ts_event=1_000_000_000_000_000_000,  # nanoseconds
    ts_init=1_000_000_000_000_000_000,
)
```

#### Subscribing to Data

```python
class MyStrategy(Strategy):
    def on_start(self):
        # Subscribe to bar data
        bar_type = BarType(instrument_id, bar_spec)
        self.subscribe_bars(bar_type)
        
        # Subscribe to quote ticks
        self.subscribe_quote_ticks(instrument_id)
        
        # Subscribe to trade ticks
        self.subscribe_trade_ticks(instrument_id)
```

### 6. Backtest Configuration

#### Setting up Venues

```python
from nautilus_core.enums import OmsType, AccountType
from nautilus_core.objects import USD, Money
from decimal import Decimal

# NETTING mode: single position per instrument
engine.add_venue(
    venue_name="SIM",
    oms_type=OmsType.NETTING,
    account_type=AccountType.CASH,
    base_currency=USD,
    starting_balances=[Money("100000", USD)],
)

# HEDGING mode: multiple positions per instrument
engine.add_venue(
    venue_name="HEDGE_SIM",
    oms_type=OmsType.HEDGING,
    account_type=AccountType.MARGIN,
    base_currency=USD,
    starting_balances=[Money("50000", USD)],
    default_leverage=Decimal("10"),
)
```

#### Adding Instruments

```python
from nautilus_core.instruments import Equity, CurrencyPair
from nautilus_core.enums import AssetClass

# Equity instrument
equity = Equity(
    instrument_id=InstrumentId(Symbol("AAPL"), Venue("SIM")),
    quote_currency=USD,
    price_precision=2,
    size_precision=0,
    maker_fee=Decimal("0.0001"),
    taker_fee=Decimal("0.0002"),
)

# Forex pair
forex = CurrencyPair(
    instrument_id=InstrumentId(Symbol("EUR/USD"), Venue("FX")),
    base_currency=EUR,
    quote_currency=USD,
    price_precision=5,
    size_precision=0,
    maker_fee=Decimal("0.00002"),
    taker_fee=Decimal("0.00002"),
)

engine.add_instrument(equity)
engine.add_instrument(forex)
```

#### Time Range Filtering

```python
# Run backtest for specific time range
engine.run(
    start=start_timestamp_ns,  # Start time in nanoseconds
    end=end_timestamp_ns,      # End time in nanoseconds
)

# Or run all data
engine.run()
```

### 7. Analyzing Results

#### Backtest Results

```python
# Get results object
result = engine.get_result()

# Print formatted results
print(result)

# Access specific metrics
print(f"Starting Balance: {result.starting_balance}")
print(f"Ending Balance: {result.ending_balance}")
print(f"Total Return: {result.total_return}")
print(f"Max Drawdown: {result.max_drawdown}")
print(f"Sharpe Ratio: {result.sharpe_ratio}")
print(f"Win Rate: {result.win_rate}")
print(f"Profit Factor: {result.profit_factor}")
print(f"Total Orders: {result.total_orders}")
print(f"Total Positions: {result.total_positions}")

# Convert to dictionary
result_dict = result.to_dict()

# Get balance curve as DataFrame
balance_df = result.to_dataframe()
```

#### Accessing Trade History

```python
# Get all orders
all_orders = engine.cache.orders()
for order in all_orders:
    print(f"{order.client_order_id}: {order.side.name} {order.quantity} @ {order.status.name}")

# Get filled orders only
filled_orders = [o for o in all_orders if o.is_filled]

# Get all positions
all_positions = engine.cache.positions()
for pos in all_positions:
    status = "OPEN" if pos.is_open else "CLOSED"
    print(f"{pos.id}: {pos.side.name} {pos.quantity}, "
          f"PnL={pos.realized_pnl}, {status}")

# Get positions by instrument
aapl_positions = engine.cache.positions(instrument_id=instrument_id)

# Get open positions only
open_positions = engine.cache.positions_open(instrument_id=instrument_id)
```

---

## Advanced Topics

### Custom Data Generation

The framework includes a helper for generating synthetic data for testing:

```python
import random
from nautilus_core.data import Bar, BarType
from nautilus_core.objects import Price, Quantity

def generate_synthetic_bars(
    bar_type: BarType,
    num_bars: int = 500,
    start_price: float = 100.0,
    volatility: float = 0.02,
    trend: float = 0.0001,
) -> list[Bar]:
    random.seed(42)
    bars = []
    price = start_price
    base_ts = 1_000_000_000_000_000_000
    
    for i in range(num_bars):
        change = random.gauss(trend, volatility)
        open_px = price
        close_px = price * (1 + change)
        
        high_px = max(open_px, close_px) * (1 + abs(random.gauss(0, volatility * 0.5)))
        low_px = min(open_px, close_px) * (1 - abs(random.gauss(0, volatility * 0.5)))
        volume = random.uniform(1000, 10000)
        
        ts = base_ts + i * 60_000_000_000  # 1-minute intervals
        
        bar = Bar(
            bar_type=bar_type,
            open=Price(open_px, 2),
            high=Price(high_px, 2),
            low=Price(low_px, 2),
            close=Price(close_px, 2),
            volume=Quantity(volume, 0),
            ts_event=ts,
            ts_init=ts,
        )
        bars.append(bar)
        price = close_px
    
    return bars
```

### Multi-Instrument Strategies

```python
class MultiInstrumentStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.instruments = []
        
    def on_start(self):
        # Subscribe to multiple instruments
        for inst_id_str in self._config.instrument_ids:
            inst_id = InstrumentId.from_str(inst_id_str)
            self.instruments.append(inst_id)
            
            bar_type = BarType(inst_id, bar_spec)
            self.subscribe_bars(bar_type)
            
    def on_bar(self, bar):
        # Handle bars from multiple instruments
        instrument_id = bar.bar_type.instrument_id
        
        # Apply different logic per instrument
        if instrument_id == self.instruments[0]:
            # Logic for first instrument
            pass
        elif instrument_id == self.instruments[1]:
            # Logic for second instrument
            pass
```

### Event Handlers

```python
class EventAwareStrategy(Strategy):
    def on_order_filled(self, event):
        """Called when an order is filled"""
        print(f"Order {event.client_order_id} filled: "
              f"{event.last_qty} @ {event.last_px}")
              
    def on_order_rejected(self, event):
        """Called when an order is rejected"""
        print(f"Order {event.client_order_id} rejected: {event.reason}")
        
    def on_position_opened(self, event):
        """Called when a new position is opened"""
        print(f"Position {event.position_id} opened")
        
    def on_position_closed(self, event):
        """Called when a position is closed"""
        print(f"Position {event.position_id} closed with PnL: {event.realized_pnl}")
```

---

## Core Data Types

### Price & Quantity

```python
from nautilus_core.objects import Price, Quantity
from decimal import Decimal

# Price with 2 decimal precision
price = Price(100.50, precision=2)
print(price.value)  # Decimal('100.50')
print(price.as_double())  # 100.5 (float)

# Quantity with 0 decimal precision (whole shares)
qty = Quantity(100, precision=0)
print(qty.value)  # Decimal('100')

# Arithmetic operations
price2 = Price(50.25, precision=2)
total = price + price2  # Price('150.75')
diff = price - price2   # Price('50.25')
```

### Money & Currency

```python
from nautilus_core.objects import USD, EUR, Money

# Create money objects
balance = Money("100000", USD)
print(balance.currency)  # USD
print(balance.amount)    # Decimal('100000')

# Predefined currencies
# USD, EUR, GBP, JPY (fiat)
# BTC, ETH, USDT (crypto)
```

### Identifiers

```python
from nautilus_core.identifiers import (
    InstrumentId, Symbol, Venue, 
    StrategyId, TraderId
)

# Instrument ID
symbol = Symbol("AAPL")
venue = Venue("NASDAQ")
instrument_id = InstrumentId(symbol, venue)
print(instrument_id)  # "AAPL.NASDAQ"

# Parse from string
instrument_id = InstrumentId.from_str("AAPL.NASDAQ")

# Other identifiers
trader_id = TraderId("TRADER-001")
strategy_id = StrategyId("MyStrategy-001")
```

### Enumerations

```python
from nautilus_core.enums import (
    OrderSide, OrderType, OrderStatus, TimeInForce,
    PositionSide, AccountType, OmsType,
    BarAggregation, PriceType, AssetClass
)

# Order sides
OrderSide.BUY
OrderSide.SELL

# Order types
OrderType.MARKET
OrderType.LIMIT
OrderType.STOP_MARKET

# Time in force
TimeInForce.GTC  # Good Till Cancel
TimeInForce.IOC  # Immediate Or Cancel
TimeInForce.FOK  # Fill Or Kill

# Position sides
PositionSide.FLAT
PositionSide.LONG
PositionSide.SHORT

# Account types
AccountType.CASH
AccountType.MARGIN

# OMS types
OmsType.NETTING   # Single position per instrument
OmsType.HEDGING   # Multiple positions per instrument

# Bar aggregations
BarAggregation.MINUTE
BarAggregation.HOUR
BarAggregation.DAY

# Asset classes
AssetClass.FX
AssetClass.EQUITY
AssetClass.COMMODITY
```

---

## Complete Example: EMA Cross Strategy

See [examples/ema_cross_strategy.py](examples/ema_cross_strategy.py) and [examples/run_backtest.py](examples/run_backtest.py) for a complete working example that implements a classic EMA crossover strategy:

**Strategy Logic:**
- Uses 10-period fast EMA and 30-period slow EMA
- Goes long when fast EMA crosses above slow EMA
- Goes short when fast EMA crosses below slow EMA
- Closes opposing positions before opening new ones

**Key Features Demonstrated:**
- Strategy configuration
- Indicator usage
- Position management
- Order submission
- Result analysis

---

## Testing

The framework includes comprehensive tests:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_backtest_engine.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_ema_cross.py::test_ema_cross_strategy
```

### Test Coverage

- `test_backtest_engine.py`: Core backtesting functionality
- `test_ema_cross.py`: EMA cross strategy validation
- `test_objects.py`: Price, Quantity, Money objects
- `test_orders.py`: Order lifecycle and state transitions
- `test_portfolio.py`: Portfolio calculations
- `test_position.py`: Position PnL and state management

---

## Performance Considerations

### Optimization Tips

1. **Data Sorting**: Data is sorted by timestamp once at the start - ensure your data is pre-sorted if possible
2. **Indicator Efficiency**: Indicators use incremental updates rather than recalculating from scratch
3. **Event Processing**: The event loop processes data sequentially - minimize heavy computations in `on_bar`
4. **Decimal Precision**: Use appropriate precision levels - higher precision = more memory

### Benchmarking

```python
import time

start = time.time()
engine.run()
elapsed = time.time() - start

bars_per_second = len(bars) / elapsed
print(f"Processed {len(bars)} bars in {elapsed:.2f}s")
print(f"Speed: {bars_per_second:.0f} bars/second")
```

---

## Limitations & Future Enhancements

### Current Limitations

- Only supports bar data (no tick-by-tick simulation yet)
- Simplified order matching (no order book depth simulation)
- No slippage modeling (executes at bar close)
- Cash account only for proper margin modeling
- No multi-asset portfolio optimization

### Planned Features

- Tick-level backtesting
- Advanced order types (trailing stops, bracket orders)
- Slippage and market impact models
- Risk metrics (VaR, CVaR, etc.)
- Parameter optimization tools
- Live trading integration
- Data loaders for common formats (CSV, Parquet, APIs)

---

## Troubleshooting

### Common Issues

**Issue: Orders not executing**
- Check if strategy is subscribed to bar data: `strategy.subscribe_bars(bar_type)`
- Verify instrument is added to engine: `engine.add_instrument(instrument)`
- Ensure venue is configured: `engine.add_venue(...)`

**Issue: Indicators not initialized**
- Indicators need a warm-up period: check `indicator.initialized` before using
- EMA needs `period` bars before it's ready

**Issue: Insufficient funds**
- Check starting balance in `add_venue()`
- Verify fees are not too high relative to balance
- Check if position sizing is appropriate

**Issue: Position not closing**
- Ensure you're using the correct position side when closing
- Verify quantity matches the open position
- Check order factory is registered with strategy

---

## API Reference Summary

### BacktestEngine

```python
BacktestEngine(trader_id: str)
.add_venue(venue_name, oms_type, account_type, base_currency, starting_balances)
.add_instrument(instrument)
.add_data(data_list)
.add_strategy(strategy)
.run(start=None, end=None)
.get_result() -> BacktestResult
```

### Strategy

```python
Strategy(config)
.on_start()
.on_stop()
.on_bar(bar)
.submit_order(order)
.cancel_order(order)
.close_position(position)
.close_all_positions(instrument_id)
.subscribe_bars(bar_type)
```

### Portfolio

```python
Portfolio(cache)
.is_flat(instrument_id) -> bool
.is_net_long(instrument_id) -> bool
.is_net_short(instrument_id) -> bool
.net_position(instrument_id) -> Decimal
.realized_pnl(instrument_id) -> Decimal
.unrealized_pnl(instrument_id, price) -> Decimal
```

### Indicators

```python
ExponentialMovingAverage(period)
SimpleMovingAverage(period)
AverageTrueRange(period)
.handle_bar(bar)
.value -> float
.initialized -> bool
```

---

## Contributing

This framework is designed to be extensible. To add new features:

1. **New Indicators**: Inherit from `Indicator` base class
2. **New Order Types**: Extend order factory and execution logic
3. **New Instruments**: Inherit from `Instrument` base class
4. **New Data Types**: Follow the pattern in `data.py`

---

## License & Attribution

This framework is inspired by [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) but implemented as a pure Python educational/research tool.

---

## Support & Resources

For questions, issues, or contributions:
- Review the examples in `/examples`
- Check the tests in `/tests` for usage patterns
- Read the source code - it's designed to be readable and well-documented

---

**Happy Backtesting! 📈**
