# Nautilus Core — Complete Deep Dive Documentation

> A pure-Python backtesting framework inspired by NautilusTrader's architecture.  
> This document explains **every folder, every file, every class, and every function** inside `nautilus_core/`.

---

## Table of Contents

1. [Architecture Overview & File Map](#1-architecture-overview--file-map)
2. [How the Package Works — Data Flow](#2-how-the-package-works--data-flow)
3. [Key Components](#3-key-components)
4. [Key Features](#4-key-features)
5. [Basic Usage Examples](#5-basic-usage-examples)
6. [File-by-File Deep Dive](#6-file-by-file-deep-dive)
   - [Root-Level Files](#61-root-level-files-nautilus_core)
   - [backtest/ Sub-package](#62-backtest-sub-package)
   - [indicators/ Sub-package](#63-indicators-sub-package)
   - [trading/ Sub-package](#64-trading-sub-package)

---

## 1. Architecture Overview & File Map

### 1.1 Directory Tree

```
nautilus_core/
├── __init__.py              # Package marker (empty)
│
│   ── FOUNDATION LAYER (Primitives & Enums) ──
├── enums.py                 # All enum types (OrderSide, OrderType, OrderStatus, etc.)
├── identifiers.py           # Strongly-typed IDs (InstrumentId, AccountId, etc.)
├── objects.py               # Value objects (Price, Quantity, Money, Currency, AccountBalance)
│
│   ── DATA LAYER ──
├── data.py                  # Market data types (Bar, QuoteTick, TradeTick, BarType, BarSpecification)
├── data_wranglers.py        # DataFrame/CSV → Bar/QuoteTick/TradeTick converters
├── instruments.py           # Instrument definitions (Equity, CurrencyPair, CryptoPerpetual, etc.)
│
│   ── EVENT LAYER ──
├── events.py                # All event dataclasses (OrderFilled, PositionOpened, AccountState, etc.)
│
│   ── INFRASTRUCTURE LAYER ──
├── msgbus.py                # Pub/sub message bus for inter-component communication
├── clock.py                 # Clock abstraction (TestClock for backtest, LiveClock for real-time)
├── cache.py                 # Central in-memory store for instruments, orders, positions, bars
│
│   ── DOMAIN LAYER ──
├── account.py               # Account model (CashAccount, MarginAccount)
├── orders.py                # Order model & FSM (MarketOrder, LimitOrder, StopMarketOrder, StopLimitOrder)
├── order_factory.py         # Factory for creating orders cleanly
├── position.py              # Position model with PnL tracking
├── portfolio.py             # Portfolio aggregation (net exposure, PnL, balances)
│
│   ── ENGINE LAYER ──
├── data_engine.py           # Routes market data → Cache + MessageBus
├── execution_engine.py      # Routes orders → Risk Engine → Exchange; manages positions
├── risk_engine.py           # Pre-trade risk validation
│
├── backtest/                # ── BACKTEST SUB-PACKAGE ──
│   ├── __init__.py          # Package marker (empty)
│   ├── config.py            # Backtest configuration dataclasses
│   ├── engine.py            # The main BacktestEngine (orchestrator)
│   ├── exchange.py          # SimulatedExchange (matching engine)
│   └── results.py           # BacktestResult data container
│
├── indicators/              # ── INDICATORS SUB-PACKAGE ──
│   ├── __init__.py          # Package marker (empty)
│   ├── base.py              # Abstract Indicator base class
│   ├── ema.py               # Exponential Moving Average
│   ├── sma.py               # Simple Moving Average
│   └── atr.py               # Average True Range
│
└── trading/                 # ── TRADING SUB-PACKAGE ──
    ├── __init__.py          # Package marker (empty)
    ├── config.py            # StrategyConfig dataclass
    └── strategy.py          # Strategy base class (user extends this)
```

### 1.2 Dependency / Connection Map

Below is how files depend on each other. Arrows mean "imports from":

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FOUNDATION LAYER                               │
│                                                                         │
│   enums.py ◄──── identifiers.py ◄──── objects.py                       │
│      ▲                  ▲                  ▲                            │
│      │                  │                  │                            │
└──────┼──────────────────┼──────────────────┼────────────────────────────┘
       │                  │                  │
┌──────┼──────────────────┼──────────────────┼────────────────────────────┐
│      │           DATA LAYER                │                            │
│      │                  │                  │                            │
│   data.py ◄─────── instruments.py          │                            │
│      ▲                  ▲                  │                            │
│      │                  │                  │                            │
│   data_wranglers.py     │                  │                            │
│                         │                  │                            │
└─────────────────────────┼──────────────────┼────────────────────────────┘
                          │                  │
┌─────────────────────────┼──────────────────┼────────────────────────────┐
│                    EVENT LAYER             │                            │
│                         │                  │                            │
│   events.py ◄───────────┘──────────────────┘                            │
│      ▲                                                                  │
└──────┼──────────────────────────────────────────────────────────────────┘
       │
┌──────┼──────────────────────────────────────────────────────────────────┐
│      │         INFRASTRUCTURE LAYER                                     │
│      │                                                                  │
│   msgbus.py        clock.py        cache.py                            │
│      ▲                ▲               ▲                                │
└──────┼────────────────┼───────────────┼────────────────────────────────┘
       │                │               │
┌──────┼────────────────┼───────────────┼────────────────────────────────┐
│      │          DOMAIN LAYER          │                                │
│      │                │               │                                │
│   account.py    orders.py    order_factory.py    position.py           │
│      ▲             ▲              ▲                   ▲                │
│      │             │              │                   │                │
│   portfolio.py ────┘──────────────┘───────────────────┘                │
│      ▲                                                                 │
└──────┼─────────────────────────────────────────────────────────────────┘
       │
┌──────┼─────────────────────────────────────────────────────────────────┐
│      │            ENGINE LAYER                                         │
│      │                                                                 │
│   data_engine.py     execution_engine.py     risk_engine.py            │
│      ▲                      ▲                      ▲                   │
└──────┼──────────────────────┼──────────────────────┼───────────────────┘
       │                      │                      │
┌──────┼──────────────────────┼──────────────────────┼───────────────────┐
│      │              BACKTEST LAYER                  │                   │
│      │                      │                      │                   │
│   backtest/engine.py ───────┤──────────────────────┘                   │
│      │                      │                                          │
│   backtest/exchange.py ─────┘                                          │
│   backtest/config.py                                                   │
│   backtest/results.py                                                  │
│                                                                        │
│              TRADING LAYER                                             │
│                                                                        │
│   trading/strategy.py  (user subclasses this)                          │
│                                                                        │
│              INDICATORS LAYER                                          │
│                                                                        │
│   indicators/base.py ◄── indicators/ema.py                             │
│                      ◄── indicators/sma.py                             │
│                      ◄── indicators/atr.py                             │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Runtime Data Flow (How a Backtest Runs)

```
  CSV / DataFrame
       │
       ▼
  DataWranglers ──────► list[Bar]
                           │
                           ▼
               BacktestEngine.add_data(bars)
                           │
                           ▼
               BacktestEngine.run()
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
      TestClock      SimulatedExchange   DataEngine
     (advance)       (match orders)    (publish data)
          │                │                │
          │                ▼                ▼
          │         ExecutionEngine     MessageBus
          │           │        │        (pub/sub)
          │           ▼        ▼            │
          │      RiskEngine  Cache          ▼
          │           │        │        Strategy
          │           ▼        │       (on_bar, on_order_filled, etc.)
          │      OrderDenied   │            │
          │        or pass     │            ▼
          │                    │      OrderFactory.market() / .limit()
          │                    │            │
          │                    │            ▼
          │                    │      ExecutionEngine.submit_order()
          │                    │            │
          │                    ▼            ▼
          │              Position ◄── OrderFilled events
          │                    │
          │                    ▼
          │              Portfolio (PnL, exposure)
          │
          ▼
   BacktestResult (metrics, balance curve)
```

---

## 2. How the Package Works — Data Flow

### Step-by-step Backtest Lifecycle

1. **Setup Phase**
   - Create a `BacktestEngine`
   - Add a venue (exchange) with `add_venue()` → creates a `SimulatedExchange` and an `Account`
   - Add instruments with `add_instrument()`
   - Load bar data (via `BarDataWrangler`) and call `add_data()`
   - Create a custom `Strategy` subclass and add it with `add_strategy()`

2. **Run Phase** (`engine.run()`)
   - All data is sorted chronologically by `ts_event`
   - The engine calls `strategy.on_start()`
   - For each bar (time step):
     1. `TestClock` is advanced to the bar's timestamp
     2. The bar is sent to `SimulatedExchange.process_bar()` — this checks if any pending orders should fill
     3. The bar is sent to `DataEngine.process_bar()` — this caches the bar and publishes it on the `MessageBus`
     4. The `MessageBus` delivers the bar to `Strategy._handle_bar()` → which feeds indicators → then calls `strategy.on_bar()`
     5. Inside `on_bar()`, your strategy decides whether to create orders (via `OrderFactory`) and submit them (via `submit_order()`)
     6. Submitted orders go: `Strategy → ExecutionEngine → RiskEngine (validation) → SimulatedExchange`
     7. When a fill occurs, `SimulatedExchange` generates an `OrderFilled` event → `ExecutionEngine` updates the order/position in `Cache` → publishes events on `MessageBus` → Strategy receives `on_order_filled()` / `on_position_opened()`

3. **Result Phase**
   - After all data is processed, `strategy.on_stop()` is called
   - `BacktestResult` is built with metrics: total return, Sharpe ratio, max drawdown, win rate, profit factor, etc.

---

## 3. Key Components

| Component | File | Role |
|---|---|---|
| **BacktestEngine** | `backtest/engine.py` | The orchestrator — wires everything together and runs the event loop |
| **SimulatedExchange** | `backtest/exchange.py` | Simulates an exchange matching engine — accepts, fills, and cancels orders |
| **Strategy** | `trading/strategy.py` | Base class you subclass to implement your trading logic |
| **ExecutionEngine** | `execution_engine.py` | Routes orders, manages position lifecycle |
| **DataEngine** | `data_engine.py` | Routes market data to cache and publishes to message bus |
| **RiskEngine** | `risk_engine.py` | Pre-trade risk checks (halted state, quantity/price validation) |
| **MessageBus** | `msgbus.py` | Pub/sub system — the glue that connects all components |
| **Cache** | `cache.py` | Central in-memory store for all stateful data |
| **Portfolio** | `portfolio.py` | Aggregates positions for net exposure and PnL queries |
| **OrderFactory** | `order_factory.py` | Clean API for creating orders with auto-incrementing IDs |

---

## 4. Key Features

- **Event-Driven Architecture** — All components communicate through events on a message bus, making the system modular and extensible.
- **Order State Machine** — Orders follow a strict finite state machine (FSM) with validated transitions (e.g., INITIALIZED → SUBMITTED → ACCEPTED → FILLED).
- **Multiple Order Types** — Market, Limit, Stop Market, Stop Limit.
- **Position Management** — Supports both HEDGING (multiple positions per instrument) and NETTING (one net position per instrument) modes.
- **Risk Engine** — Pre-trade validation (trading state, quantity/price precision, min/max constraints).
- **Technical Indicators** — Built-in SMA, EMA, ATR with an extensible base class.
- **Data Wranglers** — Convert pandas DataFrames and CSV files into typed Bar/Tick objects.
- **Precise Arithmetic** — Uses Python `Decimal` everywhere for financial precision (no floating-point rounding errors).
- **Strongly-Typed Identifiers** — Every ID (instrument, order, position, account, etc.) is a distinct type for compile-time/IDE safety.
- **Comprehensive Backtest Results** — Sharpe ratio, max drawdown, win rate, profit factor, balance curve with DataFrame export.

---

## 5. Basic Usage Examples

### 5.1 Minimal Backtest Setup

```python
from decimal import Decimal
from nautilus_core.backtest.engine import BacktestEngine
from nautilus_core.data import BarSpecification, BarType
from nautilus_core.data_wranglers import BarDataWrangler
from nautilus_core.enums import BarAggregation, OmsType, OrderSide, PriceType
from nautilus_core.identifiers import InstrumentId, Symbol, Venue
from nautilus_core.instruments import Equity
from nautilus_core.objects import Money, Price, Quantity, USD
from nautilus_core.trading.strategy import Strategy

# 1. Create instrument
instrument_id = InstrumentId(Symbol("AAPL"), Venue("NASDAQ"))
instrument = Equity(
    instrument_id=instrument_id,
    quote_currency=USD,
    price_precision=2,
    size_precision=0,
    taker_fee=Decimal("0.001"),
)

# 2. Create bar type
bar_spec = BarSpecification(1, BarAggregation.DAY, PriceType.LAST)
bar_type = BarType(instrument_id, bar_spec)

# 3. Load data from CSV
wrangler = BarDataWrangler(bar_type, price_precision=2, size_precision=0)
bars = wrangler.from_csv("aapl_daily.csv")

# 4. Create engine
engine = BacktestEngine()
engine.add_venue("NASDAQ", oms_type=OmsType.HEDGING, starting_balances=[Money(100_000, USD)])
engine.add_instrument(instrument)
engine.add_data(bars)

# 5. Create and add strategy (see below)
engine.add_strategy(my_strategy)

# 6. Run
engine.run()
result = engine.get_result()
print(result)
```

### 5.2 Simple Buy-and-Hold Strategy

```python
from nautilus_core.data import Bar
from nautilus_core.trading.strategy import Strategy
from nautilus_core.trading.config import StrategyConfig
from nautilus_core.enums import OrderSide

class BuyAndHold(Strategy):
    def __init__(self, instrument_id, bar_type):
        super().__init__(StrategyConfig(strategy_id="BuyAndHold"))
        self._instrument_id = instrument_id
        self._bar_type = bar_type
        self._entered = False

    def on_start(self):
        self.subscribe_bars(self._bar_type)

    def on_bar(self, bar: Bar):
        if not self._entered:
            order = self.order_factory.market(
                instrument_id=self._instrument_id,
                side=OrderSide.BUY,
                quantity=self.cache.instrument(self._instrument_id).make_qty(100),
                ts_init=bar.ts_event,
            )
            self.submit_order(order)
            self._entered = True
```

### 5.3 EMA Crossover Strategy

```python
from nautilus_core.indicators.ema import ExponentialMovingAverage

class EMACross(Strategy):
    def __init__(self, instrument_id, bar_type, fast_period=10, slow_period=20):
        super().__init__(StrategyConfig(strategy_id="EMACross"))
        self._instrument_id = instrument_id
        self._bar_type = bar_type
        self.fast_ema = ExponentialMovingAverage(fast_period)
        self.slow_ema = ExponentialMovingAverage(slow_period)

    def on_start(self):
        self.register_indicator_for_bars(self._bar_type, self.fast_ema)
        self.register_indicator_for_bars(self._bar_type, self.slow_ema)
        self.subscribe_bars(self._bar_type)

    def on_bar(self, bar: Bar):
        if not self.fast_ema.initialized or not self.slow_ema.initialized:
            return

        if self.fast_ema.value > self.slow_ema.value:
            if self.portfolio.is_flat(self._instrument_id):
                order = self.order_factory.market(
                    instrument_id=self._instrument_id,
                    side=OrderSide.BUY,
                    quantity=Quantity(100, 0),
                    ts_init=bar.ts_event,
                )
                self.submit_order(order)

        elif self.fast_ema.value < self.slow_ema.value:
            if self.portfolio.is_net_long(self._instrument_id):
                self.close_all_positions(self._instrument_id, ts_init=bar.ts_event)
```

---

## 6. File-by-File Deep Dive

---

### 6.1 Root-Level Files (`nautilus_core/`)

---

#### 📄 `__init__.py`

**Purpose:** Empty file that marks `nautilus_core/` as a Python package. Without this file, Python would not recognize the directory as a package and you could not do `from nautilus_core.xxx import ...`.

**Packages used:** None.

---

#### 📄 `enums.py`

**Purpose:** Defines **all enumeration types** used throughout the framework. Enums are fixed sets of named constants that prevent "magic strings" and typos. This file is the **single source of truth** for all categorical values.

##### Classes

| Class | Purpose |
|---|---|
| `OrderSide` | Whether an order is `BUY` or `SELL` |
| `OrderType` | `MARKET`, `LIMIT`, `STOP_MARKET`, `STOP_LIMIT` |
| `TimeInForce` | How long an order stays active: `GTC` (Good Till Cancel), `IOC` (Immediate or Cancel), `FOK` (Fill or Kill), `GTD` (Good Till Date), `DAY` |
| `OrderStatus` | Full lifecycle: `INITIALIZED → SUBMITTED → ACCEPTED → FILLED` (and more) |
| `PositionSide` | `FLAT`, `LONG`, `SHORT` |
| `AccountType` | `CASH` or `MARGIN` |
| `OmsType` | Order Management System type: `HEDGING` (multiple positions) or `NETTING` (one net position) |
| `AssetClass` | `FX`, `EQUITY`, `COMMODITY`, `CRYPTO`, `BOND`, `INDEX`, `METAL` |
| `CurrencyType` | `FIAT` or `CRYPTO` |
| `BookAction` | Order book actions: `ADD`, `UPDATE`, `DELETE`, `CLEAR` |
| `LiquiditySide` | `MAKER`, `TAKER`, `NO_LIQUIDITY_SIDE` |
| `BarAggregation` | Time frame: `TICK`, `SECOND`, `MINUTE`, `HOUR`, `DAY` |
| `PriceType` | `BID`, `ASK`, `MID`, `LAST` |
| `TradingState` | `ACTIVE`, `REDUCING`, `HALTED` |

##### Constants

| Name | Purpose |
|---|---|
| `ORDER_STATUS_TRANSITIONS` | A dictionary defining the **finite state machine** (FSM) for valid order status transitions. For example, from `INITIALIZED` you can only go to `DENIED` or `SUBMITTED`. This prevents illegal state changes. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `enum.Enum` | Python's built-in enumeration base class. You subclass `Enum` to create a group of named constants. | All enum classes inherit from `Enum`. |
| `enum.auto()` | Automatically assigns incrementing integer values to enum members so you don't have to number them manually. | Every enum member uses `auto()` for its value. |

---

#### 📄 `identifiers.py`

**Purpose:** Defines **strongly-typed identifier classes**. Instead of passing raw strings everywhere (error-prone), every ID is its own class. This means `AccountId("abc")` is a different type from `TraderId("abc")` — the IDE and type checker will catch if you accidentally swap them.

##### Classes

| Class | Purpose |
|---|---|
| `_Identifier` | Private base class. Stores a string value, implements `__eq__`, `__hash__`, `__repr__`. Uses `__slots__` for memory efficiency. |
| `TraderId` | Identifies a trader (e.g., `"BACKTESTER-001"`). |
| `StrategyId` | Identifies a strategy (e.g., `"EMACross"`). |
| `InstrumentId` | Identifies a tradable instrument. Format: `SYMBOL.VENUE` (e.g., `"AAPL.NASDAQ"`). Has `.symbol` and `.venue` properties. Has a `from_str()` classmethod to parse from string. |
| `Venue` | Identifies an exchange/venue (e.g., `"NASDAQ"`, `"BINANCE"`). |
| `Symbol` | Identifies a symbol/ticker (e.g., `"AAPL"`, `"BTC-USDT"`). |
| `AccountId` | Identifies an account (e.g., `"NASDAQ-001"`). |
| `ClientOrderId` | Client-side order ID (e.g., `"O-EMACross-1"`). Generated by `OrderFactory`. |
| `VenueOrderId` | Exchange-side order ID (e.g., `"V-NASDAQ-1"`). Assigned by the simulated exchange. |
| `PositionId` | Position ID (e.g., `"P-1"`). Assigned by `ExecutionEngine`. |
| `TradeId` | Trade/fill ID (e.g., `"T-NASDAQ-1"`). Assigned by the simulated exchange. |
| `OrderListId` | ID for a group/list of orders (defined but not heavily used yet). |

##### Key Methods on `_Identifier`

| Method | Purpose |
|---|---|
| `__init__(value: str)` | Validates the string is non-empty, stores it. |
| `value` (property) | Returns the raw string value. |
| `__eq__` / `__hash__` | Two identifiers are equal if they are the same type AND have the same string value. Hashable so they can be dict keys. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `from __future__ import annotations` | Enables "postponed evaluation of annotations" (PEP 604). This lets you write `str | None` instead of `Optional[str]` and use forward references freely without `"quotes"`. | Used at the top of the file to enable modern type hint syntax. |

---

#### 📄 `objects.py`

**Purpose:** Defines the **core value objects** for financial arithmetic: `Price`, `Quantity`, `Money`, `Currency`, and `AccountBalance`. These objects use Python's `Decimal` for exact arithmetic (no floating-point rounding errors — critical for financial calculations).

##### Classes

| Class | Purpose |
|---|---|
| `Currency` | A frozen dataclass representing a currency (`code`, `precision`, `currency_type`). For example, `USD` has `precision=2` (2 decimal places). |
| `Price` | Represents a price value with fixed precision. Supports arithmetic (`+`, `-`, `*`), comparisons (`<`, `>`, `==`), and conversion (`as_double()`, `float()`). |
| `Quantity` | Represents a non-negative quantity with fixed precision. Enforces `value >= 0`. Same operators as `Price`. |
| `Money` | Represents an amount of a specific currency. Prevents adding different currencies (e.g., `USD + EUR` raises an error). |
| `AccountBalance` | A dataclass holding `total`, `locked`, and `free` Money balances. Validates all three use the same currency. |

##### Pre-defined Currency Constants

| Constant | Description |
|---|---|
| `USD`, `EUR`, `GBP`, `JPY` | Fiat currencies with standard precisions |
| `BTC`, `ETH` | Crypto currencies with 8 decimal places |
| `USDT` | Tether stablecoin with 2 decimal places |

##### Key Design Decisions

- **`__slots__`** — Both `Price` and `Quantity` use `__slots__ = ("_value", "_precision")`. This tells Python NOT to create a `__dict__` for each instance, saving memory and making attribute access faster. Important when you create millions of Price/Quantity objects during a backtest.
- **`Decimal` everywhere** — Raw `float` has issues like `0.1 + 0.2 = 0.30000000000000004`. `Decimal` avoids this entirely.
- **`ROUND_HALF_UP`** — The rounding mode used when quantizing. `2.5` rounds to `3`, not `2` (which is what "banker's rounding" would do). This matches how financial systems typically round.

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `dataclasses.dataclass` | A decorator that auto-generates `__init__`, `__repr__`, `__eq__` for classes. `frozen=True` makes instances immutable (like tuples). | `Currency` and `AccountBalance` are dataclasses. |
| `decimal.Decimal` | Python's arbitrary-precision decimal arithmetic. Unlike `float`, it stores numbers exactly. `Decimal("0.1")` is exactly 0.1, not 0.1000000000000000055511151231257827021181583404541015625. | All Price/Quantity/Money values are `Decimal` internally. |
| `decimal.ROUND_HALF_UP` | A rounding constant. When the digit after your precision is exactly 5, round up. | Used in `quantize()` to fix the number of decimal places. |

---

#### 📄 `data.py`

**Purpose:** Defines the **market data types** that flow through the system: bars (OHLCV candles), quote ticks (bid/ask), and trade ticks (individual trades).

##### Classes

| Class | Purpose |
|---|---|
| `BarSpecification` | A frozen dataclass defining the "shape" of a bar: `step` (e.g., 1), `aggregation` (e.g., `DAY`), `price_type` (e.g., `LAST`). Example: `1-DAY-LAST` means 1-day bars of last prices. |
| `BarType` | A frozen dataclass combining an `InstrumentId` with a `BarSpecification`. Example: `AAPL.NASDAQ-1-DAY-LAST`. This uniquely identifies what data stream you're subscribing to. |
| `Bar` | A single OHLCV bar. Fields: `bar_type`, `open`, `high`, `low`, `close` (all `Price`), `volume` (`Quantity`), `ts_event`, `ts_init` (timestamps in nanoseconds). Has `from_dict()` and `to_dict()` for serialization. |
| `QuoteTick` | A single bid/ask quote. Fields: `instrument_id`, `bid_price`, `ask_price`, `bid_size`, `ask_size`, timestamps. |
| `TradeTick` | A single trade. Fields: `instrument_id`, `price`, `size`, `aggressor_side` (who initiated: buyer or seller), `trade_id`, timestamps. |

##### Key Design Decision: Nanosecond Timestamps

All timestamps (`ts_event`, `ts_init`) are stored as **integers in nanoseconds** since Unix epoch. This gives sub-microsecond precision and avoids timezone issues. `ts_event` = when the event actually occurred; `ts_init` = when the system first processed it.

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `dataclasses.dataclass` | Auto-generates boilerplate. `frozen=True` on `BarSpecification` and `BarType` makes them immutable and hashable (usable as dict keys). | All data classes here are dataclasses. |

---

#### 📄 `data_wranglers.py`

**Purpose:** **Data ingestion utilities** — converts raw data (pandas DataFrames, CSV files) into the typed data objects (`Bar`, `QuoteTick`, `TradeTick`) that the framework understands.

##### Classes

| Class | Purpose |
|---|---|
| `BarDataWrangler` | Converts DataFrame rows (with columns `open`, `high`, `low`, `close`, `volume`) into `Bar` objects. |
| `QuoteTickDataWrangler` | Converts DataFrame rows (with columns `bid_price`, `ask_price`, `bid_size`, `ask_size`) into `QuoteTick` objects. |
| `TradeTickDataWrangler` | Converts DataFrame rows (with columns `price`, `size`, `aggressor_side`, `trade_id`) into `TradeTick` objects. |

##### Key Methods (same pattern for all three)

| Method | Purpose |
|---|---|
| `__init__(bar_type/instrument_id, price_precision, size_precision)` | Stores the target type and precision settings. |
| `from_dataframe(df)` | Iterates over DataFrame rows, extracts timestamp (from DatetimeIndex, `timestamp` column, or `ts_event` column), creates typed objects. |
| `from_csv(filepath)` | Reads a CSV with `pd.read_csv()`, then delegates to `from_dataframe()`. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `pandas` (imported lazily inside methods) | The dominant data analysis library in Python. `pd.read_csv()` reads CSV files into DataFrames. `df.iterrows()` iterates row-by-row. | Used to read CSV files and iterate over DataFrames. Imported lazily (inside the function, not at the top) to avoid making pandas a hard dependency if you never use these wranglers. |

---

#### 📄 `instruments.py`

**Purpose:** Defines **financial instrument types** — the tradable products. Each instrument carries metadata like price/size precision, fees, quantity limits, etc.

##### Classes

| Class | Purpose |
|---|---|
| `Instrument` | Base class. Holds all common fields: `id`, `symbol`, `venue`, `asset_class`, `quote_currency`, `price_precision`, `size_precision`, `price_increment`, `size_increment`, `multiplier`, `lot_size`, `maker_fee`, `taker_fee`, `min/max_quantity`, `min/max_price`, `base_currency`. |
| `CurrencyPair` | Forex pair (e.g., EUR/USD). `asset_class = FX`. Has both `base_currency` and `quote_currency`. |
| `Equity` | A stock (e.g., AAPL). `asset_class = EQUITY`. Defaults: `price_precision=2`, `size_precision=0` (whole shares), `lot_size=1`. |
| `CryptoPerpetual` | A perpetual futures contract on crypto (e.g., BTC-USDT perp). `asset_class = CRYPTO`. Has a `settlement_currency`. |
| `FuturesContract` | A dated futures contract. Has an `expiry_date` string. |

##### Key Methods on `Instrument`

| Method | Purpose |
|---|---|
| `make_price(value)` | Creates a `Price` object with the instrument's `price_precision`. Convenience helper so you don't have to remember the precision. |
| `make_qty(value)` | Creates a `Quantity` with the instrument's `size_precision`. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `decimal.Decimal` | Exact arithmetic. | Used for `multiplier`, `maker_fee`, `taker_fee`, and computing default increments. |

---

#### 📄 `events.py`

**Purpose:** Defines all **event dataclasses** — immutable records of things that happened. The entire framework is event-driven: when an order is filled, an `OrderFilled` event is created and propagated through the system.

##### Base Class

| Class | Purpose |
|---|---|
| `Event` | Base for all events. Fields: `event_id` (auto-generated UUID), `ts_event` (when it happened), `ts_init` (when it was created). |

##### Order Events (Lifecycle of an Order)

| Class | When It's Created |
|---|---|
| `OrderInitialized` | When `OrderFactory` creates an order |
| `OrderDenied` | When `RiskEngine` rejects the order before submission |
| `OrderSubmitted` | When `ExecutionEngine` sends the order to the exchange |
| `OrderAccepted` | When the exchange acknowledges the order |
| `OrderRejected` | When the exchange rejects the order |
| `OrderCanceled` | When the order is canceled |
| `OrderExpired` | When the order expires (TTL/GTD) |
| `OrderUpdated` | When the order is modified (quantity, price, trigger price) |
| `OrderFilled` | When the order is (partially or fully) filled. Contains `last_qty`, `last_px`, `commission`, `trade_id`, `position_id`. |

##### Position Events

| Class | When It's Created |
|---|---|
| `PositionOpened` | When a new position is created from a fill |
| `PositionChanged` | When an existing position's size/side changes |
| `PositionClosed` | When a position is fully closed (qty = 0) |

##### Account Events

| Class | When It's Created |
|---|---|
| `AccountState` | Snapshot of account balances at a point in time |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `uuid.uuid4()` | Generates a random UUID (Universally Unique Identifier) — a 128-bit random string like `"550e8400-e29b-41d4-a716-446655440000"`. | Each event gets a unique `event_id` by default. |
| `dataclasses.dataclass` | With `frozen=True`, events are immutable — once created, they can never be changed. This is important for audit trails and event sourcing. | All event classes are frozen dataclasses. |
| `dataclasses.field` | Customize dataclass fields. `field(default_factory=list)` creates a new empty list for each instance instead of sharing one (a common Python gotcha). | Used for `AccountState.balances`. |

---

#### 📄 `msgbus.py`

**Purpose:** Implements a **publish/subscribe message bus** — the central nervous system of the framework. Components publish events to topics, and other components subscribe to those topics to receive events. This decouples components from each other.

##### Class: `MessageBus`

| Method | Purpose |
|---|---|
| `__init__(trader_id)` | Creates the bus with empty subscription and endpoint dictionaries. |
| `subscribe(topic, handler)` | Register a callback function to be called whenever a message is published to `topic`. |
| `unsubscribe(topic, handler)` | Remove a callback from a topic. |
| `publish(topic, msg)` | Send `msg` to ALL handlers subscribed to `topic`. |
| `register(endpoint, handler)` | Register a point-to-point endpoint (one handler per endpoint). |
| `deregister(endpoint)` | Remove an endpoint. |
| `send(endpoint, msg)` | Send `msg` to the ONE handler registered at `endpoint`. |
| `has_subscribers(topic)` | Check if any handlers are listening. |
| `subscriptions(topic)` | Get list of handlers for a topic. |
| `topics` (property) | Get all topics that have subscribers. |
| `endpoints` (property) | Get all registered endpoints. |

##### How Topics Are Named

- `"data.bars.{bar_type}"` — bar data (e.g., `"data.bars.AAPL.NASDAQ-1-DAY-LAST"`)
- `"data.quotes.{instrument_id}"` — quote ticks
- `"data.trades.{instrument_id}"` — trade ticks
- `"events.order.{strategy_id}"` — order events for a specific strategy
- `"events.position.{strategy_id}"` — position events for a specific strategy

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `collections.defaultdict` | A `dict` subclass that auto-creates a default value when you access a missing key. `defaultdict(list)` auto-creates empty lists. | `_subscriptions` is a `defaultdict(list)` so you can do `self._subscriptions[topic].append(handler)` without checking if the key exists first. |
| `typing.Callable` | Type hint for "any callable" (function, method, lambda). | Used to type the handler parameters. |
| `typing.Any` | Type hint meaning "any type". | Used for the `msg` parameter since messages can be any type. |

---

#### 📄 `clock.py`

**Purpose:** Provides **time abstractions**. In a backtest, time is simulated (you can jump forward instantly). In live trading, time is real. The `Clock` base class provides a common interface so strategies don't need to know which mode they're in.

##### Classes

| Class | Purpose |
|---|---|
| `TimeEvent` | A dataclass representing a timer firing. Fields: `name`, `ts_event`, `ts_init`, `callback`. |
| `Timer` | A dataclass representing a recurring timer. Fields: `name`, `callback`, `interval_ns`, `start_time_ns`, `next_time_ns`, `stop_time_ns`. |
| `Clock` | Abstract base. Provides `timestamp_ns` (abstract), `timestamp_ms`, `set_timer()`, `cancel_timer()`, `timer_names`, `timer_count`. |
| `TestClock` | For backtesting. Time is manually controlled. `set_time(ns)` sets current time. `advance_time(to_ns)` advances time and fires any timers whose `next_time_ns` falls within the range, returning a sorted list of `TimeEvent`s. |
| `LiveClock` | For live trading. `timestamp_ns` returns `time.time() * 1e9` (current real time). |

##### Key Method: `TestClock.advance_time(to_time_ns)`

This is called by the backtest engine for each data point. It:
1. Checks all registered timers
2. Fires timers whose `next_time_ns <= to_time_ns` (creates `TimeEvent`s)
3. Advances the timer's `next_time_ns` by `interval_ns`
4. Removes expired timers
5. Sets `_time_ns = to_time_ns`
6. Returns all events sorted by timestamp

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `time` | Python's built-in time module. `time.time()` returns current Unix timestamp as a float (seconds since Jan 1, 1970). | `LiveClock` multiplies by 1e9 to get nanoseconds. |
| `dataclasses.dataclass` / `field` | Auto-generated boilerplate for `TimeEvent` and `Timer`. | Both are dataclasses. |
| `typing.Callable` | Type hint for callback functions. | Timer callbacks are `Callable`. |

---

#### 📄 `cache.py`

**Purpose:** The **central in-memory data store**. All stateful data (instruments, accounts, orders, positions, bars, ticks) lives here. Other components read from and write to the cache.

##### Class: `Cache`

The cache maintains these internal dictionaries:

| Storage | Type | Purpose |
|---|---|---|
| `_instruments` | `dict[InstrumentId, Instrument]` | All known instruments |
| `_accounts` | `dict[AccountId, Account]` | All accounts |
| `_orders` | `dict[ClientOrderId, Order]` | All orders |
| `_positions` | `dict[PositionId, Position]` | All positions |
| `_bars` | `dict[BarType, list[Bar]]` | Historical bars by type |
| `_quote_ticks` | `dict[InstrumentId, list[QuoteTick]]` | Quote tick history |
| `_trade_ticks` | `dict[InstrumentId, list[TradeTick]]` | Trade tick history |

Plus **index maps** for fast lookups:

| Index | Purpose |
|---|---|
| `_orders_by_venue` | Find orders by venue |
| `_orders_by_strategy` | Find orders by strategy |
| `_orders_by_instrument` | Find orders by instrument |
| `_positions_by_venue` | Find positions by venue |
| `_positions_by_strategy` | Find positions by strategy |
| `_positions_by_instrument` | Find positions by instrument |

##### Key Methods

| Method | Purpose |
|---|---|
| `add_order(order)` | Stores order and updates all index maps. |
| `orders_open(instrument_id, strategy_id)` | Returns only orders with `is_open == True`. |
| `orders_closed(instrument_id, strategy_id)` | Returns only orders with `is_closed == True`. |
| `positions_open(...)` / `positions_closed(...)` | Same pattern for positions. |
| `account_for_venue(venue)` | Finds the account whose ID contains the venue name. |

##### Packages Used

Only internal imports — no external packages.

---

#### 📄 `account.py`

**Purpose:** Models **trading accounts** — where your money lives. Tracks balances (total, free, locked) and accumulated commissions.

##### Classes

| Class | Purpose |
|---|---|
| `Account` | Base class. Fields: `id`, `account_type`, `base_currency`, `balances` (dict by currency), `commissions` (dict by currency), `_events` (list of `AccountState`). |
| `CashAccount` | A cash account (`AccountType.CASH`). No leverage. |
| `MarginAccount` | A margin account (`AccountType.MARGIN`). Has a `leverage` field. |

##### Key Methods

| Method | Purpose |
|---|---|
| `balance_total(currency)` | Get total balance for a currency (defaults to `base_currency`). |
| `balance_free(currency)` | Get available/free balance. |
| `balance_locked(currency)` | Get locked/reserved balance. |
| `apply(event: AccountState)` | Apply an account state event (updates balances). |
| `update_balance(currency, total, locked)` | Directly update balance (used by `SimulatedExchange`). Computes `free = total - locked`. |
| `update_commissions(currency, amount)` | Add commission to running total. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `decimal.Decimal` | Exact arithmetic. | Commission tracking uses `Decimal`. |

---

#### 📄 `orders.py`

**Purpose:** Implements the **order model with a finite state machine (FSM)**. Orders transition through states (INITIALIZED → SUBMITTED → ACCEPTED → FILLED) and this module enforces valid transitions.

##### Classes

| Class | Purpose |
|---|---|
| `Order` | Base class. Holds all common order state: `client_order_id`, `instrument_id`, `side`, `order_type`, `quantity`, `status`, `filled_qty`, `leaves_qty`, `avg_px`, `venue_order_id`, `events`. |
| `MarketOrder` | Validates `order_type == MARKET`. Fills at best available price. |
| `LimitOrder` | Requires a `price`. Fills at `price` or better. Has `_apply_updated()` to handle price modifications. |
| `StopMarketOrder` | Requires a `trigger_price`. Becomes a market order when trigger is hit. |
| `StopLimitOrder` | Requires both `trigger_price` and `price`. Becomes a limit order when trigger is hit. |

##### Key Methods on `Order`

| Method | Purpose |
|---|---|
| `is_open` (property) | True if status is ACCEPTED, TRIGGERED, PENDING_UPDATE, PENDING_CANCEL, or PARTIALLY_FILLED. |
| `is_closed` (property) | True if status is DENIED, REJECTED, CANCELED, EXPIRED, or FILLED. |
| `is_filled` (property) | True if status is FILLED. |
| `apply(event)` | The core state machine method. Takes any order event, validates the transition, and updates the order state. |
| `_apply_filled(event)` | Handles fill events: updates `filled_qty`, `leaves_qty`, and `avg_px` (weighted average). Transitions to PARTIALLY_FILLED or FILLED. |
| `_apply_updated(event)` | Handles modification events: updates quantity and recomputes `leaves_qty`. |
| `_check_transition(new_status)` | Checks if `current_status → new_status` is in the `ORDER_STATUS_TRANSITIONS` dict. Raises `RuntimeError` if invalid. |

##### Weighted Average Price Calculation

When an order is partially filled multiple times:
```
avg_px = (old_avg_px × old_filled_qty + fill_px × fill_qty) / new_total_filled_qty
```

##### The `_EVENT_TO_STATUS` Map

Maps event types to their resulting status. For example:
- `OrderSubmitted → SUBMITTED`
- `OrderAccepted → ACCEPTED`  
- `OrderFilled → None` (handled specially because it could go to PARTIALLY_FILLED or FILLED)

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `decimal.Decimal` | Exact arithmetic. | Average price calculation. |

---

#### 📄 `order_factory.py`

**Purpose:** A **factory pattern** for creating orders. Generates auto-incrementing `ClientOrderId`s and wires in the `trader_id` and `strategy_id` automatically.

##### Class: `OrderFactory`

| Method | Purpose |
|---|---|
| `__init__(trader_id, strategy_id)` | Stores IDs and initializes counter to 0. |
| `_next_order_id()` | Increments counter and returns `ClientOrderId("O-{strategy_id}-{counter}")`. |
| `reset()` | Resets counter to 0. |
| `market(instrument_id, side, quantity, ...)` | Creates a `MarketOrder` via `OrderInitialized` event. |
| `limit(instrument_id, side, quantity, price, ...)` | Creates a `LimitOrder`. |
| `stop_market(instrument_id, side, quantity, trigger_price, ...)` | Creates a `StopMarketOrder`. |
| `stop_limit(instrument_id, side, quantity, price, trigger_price, ...)` | Creates a `StopLimitOrder`. |

Each method:
1. Creates an `OrderInitialized` event with all the order parameters
2. Passes that event to the appropriate Order constructor
3. Returns the new order

##### Packages Used

Only internal imports — no external packages.

---

#### 📄 `position.py`

**Purpose:** Models a **trading position** — tracks entry/exit, calculates realized and unrealized PnL, handles position flipping (e.g., going from long to short in one trade).

##### Class: `Position`

| Property / Method | Purpose |
|---|---|
| `is_open` | True if `side != FLAT`. |
| `is_closed` | True if `side == FLAT` and at least one fill has occurred. |
| `is_long` / `is_short` | Side checks. |
| `ts_opened` / `ts_closed` | Timestamps of first and last fills. |
| `apply(fill: OrderFilled)` | The core method. Routes to `_apply_buy()` or `_apply_sell()` based on `fill.order_side`. |
| `_apply_buy(fill_qty, fill_px)` | If FLAT/LONG: adds to position, updates weighted average open price. If SHORT: closes/reduces position, calculates realized PnL as `close_qty × (avg_px_open - fill_px)`, handles flip to long. |
| `_apply_sell(fill_qty, fill_px)` | Mirror of `_apply_buy`. If FLAT/SHORT: adds to short. If LONG: closes with PnL = `close_qty × (fill_px - avg_px_open)`. |
| `_update_side_and_qty()` | Recalculates `side` and `quantity` from `signed_qty`. |
| `unrealized_pnl(last_price)` | PnL if you closed right now. Long: `qty × (last_px - avg_open)`. Short: `qty × (avg_open - last_px)`. |
| `total_pnl(last_price)` | `realized_pnl + unrealized_pnl`. |
| `notional_value(last_price)` | `abs(signed_qty) × last_px`. |
| `total_commissions()` | Returns dict of all commissions paid. |

##### Key Design: `signed_qty`

- Positive = LONG, Negative = SHORT, Zero = FLAT
- The absolute value = the position size
- This makes PnL calculations straightforward

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `decimal.Decimal` | Exact PnL arithmetic. | All monetary calculations. |

---

#### 📄 `portfolio.py`

**Purpose:** An **aggregation layer** that queries the Cache to provide portfolio-level views: net position, PnL, exposure, and account balances.

##### Class: `Portfolio`

| Method | Purpose |
|---|---|
| `net_position(instrument_id)` | Sum of `signed_qty` across all open positions for an instrument. |
| `is_net_long(instrument_id)` | True if net position > 0. |
| `is_net_short(instrument_id)` | True if net position < 0. |
| `is_flat(instrument_id)` | True if net position == 0. |
| `unrealized_pnl(instrument_id, last_price)` | Sum of unrealized PnL across all open positions. |
| `realized_pnl(instrument_id)` | Sum of realized PnL across ALL positions (open and closed). |
| `net_exposure(instrument_id, last_price)` | Sum of notional values of all open positions. |
| `total_pnl(instrument_id, last_price)` | `realized + unrealized`. |
| `balance_total(venue, currency)` | Delegates to `Account.balance_total()` via cache lookup. |
| `balance_free(venue, currency)` | Available balance. |
| `balance_locked(venue, currency)` | Locked balance. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `decimal.Decimal` | Exact arithmetic for PnL aggregation. | Used for all return values. |

---

#### 📄 `data_engine.py`

**Purpose:** Routes **incoming market data** to the Cache (for storage) and to the MessageBus (for distribution to strategies).

##### Class: `DataEngine`

| Method | Purpose |
|---|---|
| `subscribe_bars(bar_type)` | Records that someone wants bar data for this type. |
| `unsubscribe_bars(bar_type)` | Removes the subscription. |
| `subscribe_quote_ticks(instrument_id)` / `unsubscribe_quote_ticks(...)` | Same for quotes. |
| `subscribe_trade_ticks(instrument_id)` / `unsubscribe_trade_ticks(...)` | Same for trades. |
| `process_bar(bar)` | Adds bar to cache, publishes to topic `"data.bars.{bar_type}"`. |
| `process_quote_tick(tick)` | Adds tick to cache, publishes to topic `"data.quotes.{instrument_id}"`. |
| `process_trade_tick(tick)` | Adds tick to cache, publishes to topic `"data.trades.{instrument_id}"`. |

##### Packages Used

Only internal imports — no external packages.

---

#### 📄 `execution_engine.py`

**Purpose:** The **central order routing and position management engine**. Handles the full lifecycle: order submission → risk check → venue routing → fill processing → position creation/update.

##### Class: `ExecutionEngine`

| Method | Purpose |
|---|---|
| `register_venue(venue, exchange, oms_type)` | Associates a venue with its exchange and order management type. |
| `submit_order(order)` | Main entry point. (1) Validates via `RiskEngine`, (2) creates `OrderSubmitted` event, (3) adds to cache, (4) publishes event, (5) routes to the venue's exchange. |
| `cancel_order(order)` | Routes cancel request to the venue's exchange. |
| `modify_order(order, ...)` | Routes modify request to the venue's exchange. |
| `process_event(event)` | Receives events FROM the exchange. Routes `OrderFilled` to `_handle_fill()`, other events to `_handle_order_event()`. |
| `_handle_order_event(event)` | Updates order state in cache, publishes event on msgbus. |
| `_handle_fill(event)` | Updates order, then delegates to `_handle_fill_netting()` or `_handle_fill_hedging()` based on OMS type. |
| `_handle_fill_netting(event, order)` | NETTING mode: finds existing open position for the instrument, updates it. If no position exists, opens a new one. |
| `_handle_fill_hedging(event, order)` | HEDGING mode: if event has a `position_id`, updates that specific position. Otherwise, finds first open position for the instrument. If none, opens a new one. |
| `_open_position(event, order)` | Creates a new `Position`, adds to cache, publishes `PositionOpened` event. |

##### Packages Used

Only internal imports — no external packages.

---

#### 📄 `risk_engine.py`

**Purpose:** **Pre-trade risk management**. Validates orders before they reach the exchange. Can block orders entirely when trading is halted.

##### Class: `RiskEngine`

| Method | Purpose |
|---|---|
| `set_trading_state(state)` | Set to `ACTIVE`, `REDUCING`, or `HALTED`. |
| `validate_order(order)` | Returns `OrderDenied` event if validation fails, or `None` if the order is okay. |

##### Validation Checks (in order)

1. **Trading state = HALTED?** → Deny all orders.
2. **Instrument exists?** → Deny if not found in cache.
3. **Quantity precision matches instrument?** → Deny if wrong.
4. **Quantity within min/max bounds?** → Deny if out of range.
5. **Price positive? Price precision matches?** → For limit/stop orders only.
6. **Trading state = REDUCING?** → Only allow orders that reduce the current position (e.g., can't buy more if already long).

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `decimal.Decimal` | For comparing positions (net position check in REDUCING mode). | Used implicitly through portfolio. |

---

### 6.2 `backtest/` Sub-Package

---

#### 📄 `backtest/__init__.py`

**Purpose:** Empty file marking `backtest/` as a Python sub-package.

---

#### 📄 `backtest/config.py`

**Purpose:** Configuration dataclasses for setting up a backtest.

##### Classes

| Class | Purpose |
|---|---|
| `BacktestVenueConfig` | Configuration for a simulated venue: `venue_name`, `oms_type`, `account_type`, `base_currency`, `starting_balances`, `default_leverage`. |
| `BacktestEngineConfig` | Configuration for the engine itself: `trader_id`. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `dataclasses.dataclass` / `field` | Auto-generates boilerplate. `field(default_factory=list)` creates fresh lists per instance. | Both configs are dataclasses. |
| `decimal.Decimal` | For `default_leverage`. | Default value is `Decimal("1")`. |

---

#### 📄 `backtest/engine.py`

**Purpose:** The **main orchestrator** — the `BacktestEngine`. This is what you instantiate to run a backtest. It wires together all components and runs the main event loop.

##### Class: `BacktestEngine`

| Method | Purpose |
|---|---|
| `__init__(trader_id)` | Creates ALL components: `TestClock`, `MessageBus`, `Cache`, `Portfolio`, `RiskEngine`, `ExecutionEngine`, `DataEngine`. |
| `add_venue(venue_name, oms_type, account_type, base_currency, starting_balances, default_leverage)` | Creates a `SimulatedExchange` and `Account`, registers with `ExecutionEngine`, stores in cache. |
| `add_instrument(instrument)` | Adds to cache and to the exchange for that venue. |
| `add_data(data)` | Appends bars/ticks to the internal data list. |
| `add_strategy(strategy)` | Creates an `OrderFactory` for the strategy, calls `strategy.register()` to inject all dependencies. |
| `run(start, end)` | **THE MAIN EVENT LOOP.** (1) Sorts data by timestamp. (2) Calls `on_start()`. (3) For each data point: advance clock → process time events → route to exchange → route to data engine → record balance. (4) Calls `on_stop()`. (5) Builds result. |
| `get_result()` | Returns the `BacktestResult`. |
| `reset()` | Clears data and result. |
| `dispose()` | Full cleanup. |
| `_get_total_balance()` | Sums balances across all exchanges. |
| `_build_result(starting_balance, balance_curve)` | Computes all performance metrics: total return, max drawdown, win rate, profit factor, Sharpe ratio, etc. |

##### Sharpe Ratio Calculation

The engine computes a simplified annualized Sharpe ratio:
1. For each consecutive balance point, compute the return: `(current - previous) / previous`
2. Calculate mean return and standard deviation
3. `Sharpe = (mean_return / std_return) × √252` (annualized assuming daily bars)

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `math` | Python's built-in math module. | `math.sqrt()` for Sharpe ratio calculation (square root of 252 for annualization, square root of variance for standard deviation). |
| `decimal.Decimal` | Exact arithmetic. | All balance and PnL calculations. |

---

#### 📄 `backtest/exchange.py`

**Purpose:** The **simulated exchange / matching engine**. Simulates how a real exchange would process, accept, fill, and cancel orders. This is where the "fake market" lives.

##### Class: `SimulatedExchange`

| Method | Purpose |
|---|---|
| `__init__(venue, oms_type, account_type, base_currency, starting_balances, exec_engine, default_leverage, fill_model)` | Creates the exchange with an account (Cash or Margin), sets starting balances. |
| `add_instrument(instrument)` | Registers an instrument for order matching. |
| `process_order(order)` | Called when `ExecutionEngine` routes an order here. (1) Assigns a `VenueOrderId`. (2) Sends `OrderAccepted` event. (3) Adds to `_open_orders` list. |
| `cancel_order(order)` | Removes from `_open_orders`, generates `OrderCanceled` event. |
| `modify_order(order, ...)` | Generates `OrderUpdated` event. |
| `process_bar(bar)` | **The core matching loop.** For each open order matching this bar's instrument, calls `_check_fill()`. If it returns a price, calls `_fill_order()`. |
| `_check_fill(order, bar)` | Determines if and at what price an order fills given the bar's OHLCV: |
| | - **Market**: fills at bar's open price |
| | - **Buy Limit**: fills if `bar.low <= limit_price`, at `min(limit, open)` |
| | - **Sell Limit**: fills if `bar.high >= limit_price`, at `max(limit, open)` |
| | - **Buy Stop**: fills if `bar.high >= trigger`, at `max(trigger, open)` |
| | - **Sell Stop**: fills if `bar.low <= trigger`, at `min(trigger, open)` |
| | - **Buy Stop Limit**: trigger if `bar.high >= trigger`, fill if `bar.low <= limit` |
| | - **Sell Stop Limit**: trigger if `bar.low <= trigger`, fill if `bar.high >= limit` |
| `_fill_order(order, fill_px, ts_event)` | (1) Calculates commission = `notional × taker_fee`. (2) Generates `TradeId`. (3) Creates `OrderFilled` event. (4) Updates account balance. (5) Sends event to `ExecutionEngine`. |

##### Account Balance Updates on Fill

- **BUY**: `new_balance = current_balance - (notional + commission)`
- **SELL**: `new_balance = current_balance + (notional - commission)`

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `uuid` | For generating unique IDs. | Not actually used (counter-based IDs are used instead). Imported but the `uuid` call is in `events.py`. |
| `decimal.Decimal` | Exact arithmetic for fill prices and commissions. | All financial calculations. |
| `typing.TYPE_CHECKING` | A special constant that is `True` only when a type checker (like mypy or Pylance) is running, and `False` at runtime. This lets you import types for annotations without causing circular imports at runtime. | Used to import `Bar`, `ExecutionEngine`, `Instrument`, `Order` only for type hints, avoiding circular import issues. |

---

#### 📄 `backtest/results.py`

**Purpose:** A **data container** for backtest results. Stores all performance metrics and provides export methods.

##### Class: `BacktestResult`

| Field | Description |
|---|---|
| `start_time_ns` / `end_time_ns` | Backtest time range |
| `total_orders` / `total_positions` / `total_fills` | Activity counts |
| `starting_balance` / `ending_balance` | Before/after balances |
| `total_return` | `ending - starting` |
| `total_commissions` | Sum of all commissions |
| `max_drawdown` | Largest peak-to-trough decline |
| `sharpe_ratio` | Risk-adjusted return (annualized) |
| `win_rate` | Fraction of winning trades |
| `profit_factor` | `gross_profit / gross_loss` |
| `avg_win` / `avg_loss` | Average winning/losing trade PnL |
| `balance_curve` | List of `(timestamp_ns, balance)` tuples |

| Method | Purpose |
|---|---|
| `to_dict()` | Returns all metrics as a flat dictionary (with percentage variants for return and drawdown). |
| `to_dataframe()` | Converts `balance_curve` to a pandas DataFrame with columns `timestamp_ns` and `balance`. |
| `__str__()` | Pretty-prints all metrics in a formatted table. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `dataclasses.dataclass` / `field` | Auto-generated boilerplate. | `BacktestResult` is a dataclass. `balance_curve` uses `field(default_factory=list)`. |
| `decimal.Decimal` | All numeric fields are `Decimal`. | Ensures exact arithmetic when displayed. |
| `pandas` (imported lazily in `to_dataframe()`) | For creating a DataFrame from the balance curve. | Used only if the user calls `to_dataframe()`, so `pandas` is not a hard dependency for the results module. |

---

### 6.3 `indicators/` Sub-Package

---

#### 📄 `indicators/__init__.py`

**Purpose:** Empty file marking `indicators/` as a Python sub-package.

---

#### 📄 `indicators/base.py`

**Purpose:** Defines the **abstract base class** for all indicators.

##### Class: `Indicator`

| Attribute / Method | Purpose |
|---|---|
| `name` | Human-readable name (e.g., `"EMA(20)"`). |
| `initialized` | `True` once the indicator has received enough data to produce valid output (e.g., SMA(20) needs 20 bars). |
| `has_inputs` | `True` after the first input. |
| `_count` | Number of inputs received. |
| `handle_bar(bar)` | Abstract — subclasses must implement this. |
| `reset()` | Resets all state back to initial. |

##### Packages Used

Only internal imports (`nautilus_core.data.Bar`).

---

#### 📄 `indicators/ema.py`

**Purpose:** **Exponential Moving Average** — gives more weight to recent prices, reacts faster to price changes than SMA.

##### Class: `ExponentialMovingAverage`

| Attribute / Method | Purpose |
|---|---|
| `period` | The lookback period (e.g., 20). |
| `value` | The current EMA value (float). |
| `_multiplier` | `2 / (period + 1)` — the smoothing factor. |
| `handle_bar(bar)` | On first bar: `value = close_price`. On subsequent bars: `value = (close - value) × multiplier + value`. Marks `initialized = True` after `period` bars. |
| `reset()` | Resets `value` to 0. |

##### EMA Formula

$$EMA_t = (P_t - EMA_{t-1}) \times \alpha + EMA_{t-1}$$

Where $\alpha = \frac{2}{period + 1}$

##### Packages Used

Only internal imports.

---

#### 📄 `indicators/sma.py`

**Purpose:** **Simple Moving Average** — the unweighted mean of the last N prices.

##### Class: `SimpleMovingAverage`

| Attribute / Method | Purpose |
|---|---|
| `period` | The lookback period. |
| `value` | The current SMA value. |
| `_prices` | A `deque(maxlen=period)` — a fixed-size double-ended queue. When full, adding a new item automatically removes the oldest. |
| `handle_bar(bar)` | Appends `close_price` to `_prices`, computes `value = sum(prices) / len(prices)`. |
| `reset()` | Resets value and clears the deque. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `collections.deque` | A double-ended queue (pronounced "deck"). Unlike a list, it supports O(1) append and pop from both ends. With `maxlen`, it automatically discards old items — perfect for a sliding window. | `_prices` is a `deque(maxlen=period)` acting as a sliding window of recent prices. |

---

#### 📄 `indicators/atr.py`

**Purpose:** **Average True Range** — measures market volatility. The "true range" for a bar is the largest of: (high-low), |high-prev_close|, |low-prev_close|.

##### Class: `AverageTrueRange`

| Attribute / Method | Purpose |
|---|---|
| `period` | The lookback period. |
| `value` | Current ATR value. |
| `_prev_close` | Previous bar's close (needed for true range calculation). |
| `_sum_tr` | Running sum for the initial average (first `period` bars). |
| `handle_bar(bar)` | Computes true range. For the first `period` bars, accumulates sum then divides. After that, uses Wilder's smoothing: `ATR = (ATR_prev × (period-1) + TR) / period`. |

##### True Range Formula

$$TR = \max(H - L, |H - C_{prev}|, |L - C_{prev}|)$$

##### ATR Smoothing (Wilder's Method)

$$ATR_t = \frac{ATR_{t-1} \times (period - 1) + TR_t}{period}$$

##### Packages Used

Only internal imports.

---

### 6.4 `trading/` Sub-Package

---

#### 📄 `trading/__init__.py`

**Purpose:** Empty file marking `trading/` as a Python sub-package.

---

#### 📄 `trading/config.py`

**Purpose:** Configuration dataclass for strategies.

##### Class: `StrategyConfig`

| Field | Purpose |
|---|---|
| `strategy_id` | String identifier for the strategy. Defaults to empty string (in which case the class name is used). |
| `oms_type` | Order Management System type: `HEDGING` or `NETTING`. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `dataclasses.dataclass` | With `frozen=True`, config objects are immutable once created. | `StrategyConfig` is a frozen dataclass. |

---

#### 📄 `trading/strategy.py`

**Purpose:** The **Strategy base class** — the most important file for users. You subclass `Strategy` and override the callback methods (`on_bar`, `on_order_filled`, etc.) to implement your trading logic.

##### Class: `Strategy`

###### Injected Dependencies (set by `register()`)

| Attribute | Type | Purpose |
|---|---|---|
| `clock` | `Clock` | Access to current time, set timers |
| `cache` | `Cache` | Query instruments, orders, positions |
| `portfolio` | `Portfolio` | Query net positions, PnL, balances |
| `msgbus` | `MessageBus` | Subscribe/publish messages |
| `order_factory` | `OrderFactory` | Create orders with auto-IDs |
| `_exec_engine` | `ExecutionEngine` | Submit/cancel/modify orders |
| `_data_engine` | `DataEngine` | Subscribe to data feeds |

###### Lifecycle Methods (Override These)

| Method | When It's Called |
|---|---|
| `on_start()` | Once, at the beginning of the backtest. Use this to subscribe to data and register indicators. |
| `on_stop()` | Once, at the end of the backtest. Use for cleanup. |
| `on_reset()` | When the engine is reset. |

###### Data Handlers (Override These)

| Method | When It's Called |
|---|---|
| `on_bar(bar)` | Every time a new bar arrives for a subscribed bar type. **This is where most trading logic goes.** |
| `on_quote_tick(tick)` | Every time a new quote tick arrives. |
| `on_trade_tick(tick)` | Every time a new trade tick arrives. |
| `on_data(data)` | Generic data handler. |

###### Order Event Handlers (Override These)

| Method | When It's Called |
|---|---|
| `on_order_submitted(event)` | When your order is submitted to the exchange. |
| `on_order_accepted(event)` | When the exchange accepts your order. |
| `on_order_rejected(event)` | When the exchange rejects your order. |
| `on_order_denied(event)` | When the risk engine blocks your order. |
| `on_order_filled(event)` | When your order is filled. |
| `on_order_canceled(event)` | When your order is canceled. |

###### Position Event Handlers (Override These)

| Method | When It's Called |
|---|---|
| `on_position_opened(event)` | When a new position is opened. |
| `on_position_changed(event)` | When a position size changes. |
| `on_position_closed(event)` | When a position is fully closed. |

###### Action Methods (Call These)

| Method | Purpose |
|---|---|
| `submit_order(order)` | Submit an order for execution. |
| `cancel_order(order)` | Cancel a pending order. |
| `modify_order(order, ...)` | Modify a pending order's quantity/price. |
| `cancel_all_orders(instrument_id)` | Cancel all open orders for an instrument. |
| `close_position(position, ts_init)` | Submit a market order to close a specific position. |
| `close_all_positions(instrument_id, ts_init)` | Close all open positions for an instrument. |
| `register_indicator_for_bars(bar_type, indicator)` | Register an indicator to auto-update on each bar. |
| `subscribe_bars(bar_type)` | Subscribe to bar data (registers with data engine and message bus). |
| `subscribe_quote_ticks(instrument_id)` | Subscribe to quote tick data. |
| `subscribe_trade_ticks(instrument_id)` | Subscribe to trade tick data. |

###### Internal Handler Methods

| Method | Purpose |
|---|---|
| `_handle_bar(bar)` | Feeds all registered indicators for this bar type, then calls `on_bar()`. |
| `_handle_quote_tick(tick)` | Calls `on_quote_tick()`. |
| `_handle_trade_tick(tick)` | Calls `on_trade_tick()`. |
| `_handle_order_event(event)` | Dispatches to the appropriate `on_order_*()` method. |
| `_handle_position_event(event)` | Dispatches to the appropriate `on_position_*()` method. |

##### Packages Used

| Package | What It Is | How It's Used |
|---|---|---|
| `typing.TYPE_CHECKING` | A boolean constant. `True` during type checking, `False` at runtime. Imports inside `if TYPE_CHECKING:` are only used by type checkers, not at runtime — this breaks circular imports. | Used to import `Cache`, `Clock`, `DataEngine`, `ExecutionEngine`, `MessageBus`, `OrderFactory`, `Portfolio` without causing circular dependencies at runtime. |

---

## Summary: How to Build Your Own Backtest Framework

Based on this analysis, the key architectural patterns to replicate are:

1. **Strong Typing** — Use separate classes for identifiers, prices, quantities. Don't pass raw floats/strings.
2. **Event-Driven Design** — Use a message bus (pub/sub) so components are decoupled.
3. **Finite State Machine for Orders** — Define valid transitions explicitly and enforce them.
4. **Separation of Concerns** — Data engine handles data, execution engine handles orders, risk engine validates, strategy makes decisions.
5. **Simulated Exchange** — A matching engine that processes orders against bar data (OHLCV).
6. **Decimal Arithmetic** — Never use `float` for money. Always use `Decimal`.
7. **Cache as Single Source of Truth** — One central store that all components read from and write to.
8. **Strategy as Subclass** — Users only need to override callbacks. All wiring is done by the engine.
