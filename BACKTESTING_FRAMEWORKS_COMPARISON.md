# 🔬 Backtesting Frameworks Comparison

## NautilusTrader vs. Backtrader vs. Backtesting.py

> A comprehensive comparison of three major open-source Python backtesting frameworks — their architecture, logic, capabilities, trade-offs, and what we can learn from each to build a superior custom framework.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Logic & Definition Comparison](#2-logic--definition-comparison)
   - [Instruments](#21-instruments)
   - [Venues](#22-venues)
   - [Engines](#23-engines)
   - [Strategies](#24-strategies)
   - [Data Handling](#25-data-handling)
   - [Order Types & Execution](#26-order-types--execution)
   - [Scenarios & Use Cases](#27-scenarios--use-cases)
   - [Platform Support & Dependencies](#28-platform-support--dependencies)
   - [Limitations](#29-limitations)
3. [Framework Structure Maps](#3-framework-structure-maps)
   - [NautilusTrader Structure](#31-nautilustrader-structure)
   - [Backtrader Structure](#32-backtrader-structure)
   - [Backtesting.py Structure](#33-backtestingpy-structure)
4. [Availability, Scalability & Extensibility](#4-availability-scalability--extensibility)
   - [Availability](#41-availability)
   - [Scalability](#42-scalability)
   - [Extensibility](#43-extensibility)
5. [Side-by-Side Comparison Matrix](#5-side-by-side-comparison-matrix)
6. [Combined Advantages → Proposed Custom Framework](#6-combined-advantages--proposed-custom-framework)
   - [Key Strengths to Borrow](#61-key-strengths-to-borrow)
   - [Proposed Architecture](#62-proposed-architecture)
   - [Proposed File Structure](#63-proposed-file-structure)
   - [Design Principles](#64-design-principles)

---

## 1. Executive Summary

| Aspect | NautilusTrader | Backtrader | Backtesting.py |
|--------|---------------|------------|----------------|
| **Philosophy** | Institutional-grade, production parity | Full-featured, community-driven | Minimalist, researcher-friendly |
| **Language** | Rust core + Python/Cython bindings | Pure Python (with metaclass magic) | Pure Python (numpy/pandas) |
| **GitHub Stars** | ~18.8k ⭐ | ~20.3k ⭐ | ~7.9k ⭐ |
| **License** | LGPL-3.0 | GPL-3.0 | AGPL-3.0 |
| **Active Maintenance** | ✅ Very active (daily commits) | ❌ Stale (last commit 3+ years ago) | ⚠️ Low activity (last commit 2 months ago) |
| **Live Trading** | ✅ First-class support | ✅ IB, Oanda, Visual Chart | ❌ No |
| **Learning Curve** | 🔴 Steep | 🟡 Moderate | 🟢 Easy |
| **Lines of Code** | ~100k+ (Rust+Python+Cython) | ~20k+ (Python) | ~2k (Python) |

---

## 2. Logic & Definition Comparison

### 2.1 Instruments

| Feature | NautilusTrader | Backtrader | Backtesting.py |
|---------|---------------|------------|----------------|
| **Instrument Model** | First-class `Instrument` types with full specification | No formal instrument model; data feeds are the "instruments" | No instrument model; plain OHLCV DataFrame |
| **Instrument Types** | `CurrencyPair`, `Equity`, `FuturesContract`, `OptionsContract`, `CryptoPerpetual`, `CryptoFuture`, `BettingInstrument`, etc. | Implicit via data feed type (CSV, IB contract strings like `TICKER-STK-EXCHANGE`) | None — any candlestick data works |
| **Multi-Instrument** | ✅ Native multi-instrument, multi-venue | ✅ Multiple data feeds via `cerebro.adddata()` | ❌ Single instrument per backtest (unless using `MultiBacktest`) |
| **Precision** | 128-bit / 64-bit integer fixed-point (`Price`, `Quantity`, `Money`) | Python float | Python float / numpy float64 |
| **Tick Size / Lot Size** | Enforced via instrument spec (`price_increment`, `size_increment`) | Not enforced | `.pip` property on data, but not enforced |
| **Currency Awareness** | Full multi-currency support (`Currency`, `Money` types) | Basic via commission schemes | None — cash only |

**NautilusTrader** has by far the most sophisticated instrument model. Every instrument is a strongly-typed object with:
- `InstrumentId` (symbol + venue)
- Price/quantity precision, increments, multipliers
- Margin requirements, maker/taker fees
- Asset class and instrument class enums

**Backtrader** uses data feeds as implicit instruments. The contract specification is encoded in the data feed name string (e.g., `TICKER-YYYYMM-EXCHANGE-CURRENCY-MULT` for futures).

**Backtesting.py** is completely instrument-agnostic — any DataFrame with OHLCV columns works. This is its greatest simplicity and its greatest limitation.

---

### 2.2 Venues

| Feature | NautilusTrader | Backtrader | Backtesting.py |
|---------|---------------|------------|----------------|
| **Venue Model** | First-class `Venue` with `SimulatedExchange` | `Broker` (single simulated or live) | Internal `_Broker` (single, simulated) |
| **Multi-Venue** | ✅ Multiple simultaneous venues with independent order management | ❌ Single broker instance per cerebro | ❌ Single broker |
| **OMS Types** | `NETTING`, `HEDGING` per venue | Single mode (similar to netting) | `hedging=True/False` parameter |
| **Account Types** | `CASH`, `MARGIN`, `BETTING` | Simulated with configurable commission | Margin parameter (1.0 = cash, <1.0 = leverage) |
| **Order Book** | Full L1/L2/L3 order book simulation | No order book | No order book |
| **Slippage Model** | Configurable `FillModel` | Configurable slippage (fixed, percentage, volume) | `spread` parameter |
| **Latency Model** | ✅ Configurable `LatencyModel` | ❌ No | ❌ No |
| **Fee Model** | Configurable `FeeModel` (maker/taker) | `CommissionInfo` with flexible schemes | `commission` (fixed, relative, or callable) |

**NautilusTrader** excels with its multi-venue architecture. You can simultaneously backtest across BINANCE, NASDAQ, and BETFAIR with independent order management systems per venue. Each venue has its own:
- `SimulatedExchange` with `OrderMatchingEngine`
- Account type (cash, margin, betting)
- OMS type (netting vs hedging)
- Fill model, fee model, latency model

**Backtrader** has a single `BackBroker` with flexible commission and slippage, but no multi-venue support.

**Backtesting.py** has the simplest broker — just cash, spread, and commission.

---

### 2.3 Engines

| Feature | NautilusTrader | Backtrader | Backtesting.py |
|---------|---------------|------------|----------------|
| **Main Engine** | `BacktestEngine` + `NautilusKernel` | `Cerebro` | `Backtest` class |
| **Architecture** | Event-driven with message bus | Event-driven with line-based iteration | Simple for-loop iteration |
| **Core in** | Rust (`BacktestEngine` in `crates/backtest/src/engine.rs`) + Cython wrapper | Pure Python with metaclass pattern | Pure Python |
| **Data Engine** | Dedicated `DataEngine` for data distribution | Built into Cerebro's run loop | Built into `Backtest.run()` |
| **Execution Engine** | Dedicated `ExecEngine` for order routing | Built into Broker | Built into `_Broker.next()` |
| **Risk Engine** | Dedicated `RiskEngine` for pre-trade checks | No dedicated risk engine | No risk engine |
| **Message Bus** | ✅ Pub/Sub `MessageBus` | ❌ Direct callbacks (notify_order, notify_trade) | ❌ None |
| **Clock** | `TestClock` (simulated time) | Implicitly data-driven time | Implicitly data-driven time |
| **Cache** | Dedicated `Cache` for state management | Strategy holds state | Strategy holds state |
| **Streaming Mode** | ✅ Chunked streaming for large datasets | ✅ `exactbars` memory optimization | ❌ All data in memory |

**NautilusTrader's** architecture is the most decoupled:
```
BacktestEngine
├── NautilusKernel
│   ├── DataEngine          (distributes market data)
│   ├── ExecutionEngine     (routes orders to venues)
│   ├── RiskEngine          (pre-trade risk checks)
│   ├── MessageBus          (pub/sub event routing)
│   ├── Cache               (centralized state)
│   ├── Clock               (simulated time)
│   └── Portfolio           (position/PnL tracking)
├── SimulatedExchange(s)    (one per venue)
│   └── OrderMatchingEngine
├── DataIterator            (chronological data replay)
└── Strategies/Actors
```

**Backtrader's** `Cerebro` is the monolithic controller:
```
Cerebro
├── Broker (BackBroker)
├── Data Feeds[]
├── Strategies[]
│   ├── Indicators[]
│   ├── Observers[]
│   ├── Analyzers[]
│   └── Sizers[]
└── Writers[]
```

**Backtesting.py** is minimally structured:
```
Backtest
├── _Broker
├── _Data (wrapped DataFrame)
└── Strategy instance
    ├── Indicators (via self.I())
    ├── Orders[]
    ├── Trades[]
    └── Position
```

---

### 2.4 Strategies

| Feature | NautilusTrader | Backtrader | Backtesting.py |
|---------|---------------|------------|----------------|
| **Base Class** | `Strategy(Actor)` | `Strategy(StrategyBase)` | `Strategy(ABC)` |
| **Lifecycle Methods** | `on_start()`, `on_stop()`, `on_data()`, `on_bar()`, `on_order()`, `on_position_changed()`, etc. | `start()`, `prenext()`, `nextstart()`, `next()`, `stop()`, `notify_order()`, `notify_trade()` | `init()`, `next()` |
| **Indicator Registration** | Register with `self.register_indicator()` | Auto-detected from `__init__` via metaclass magic | `self.I(func, *args)` wrapper |
| **Parameter System** | Pydantic-based `StrategyConfig` | `params` tuple/dict with metaclass `MetaParams` | Class variables as strategy parameters |
| **Multi-Strategy** | ✅ Multiple strategies per engine | ✅ Multiple strategies per cerebro (even optimization) | ❌ Single strategy per backtest |
| **Execution Algorithms** | ✅ TWAP, VWAP, etc. via `ExecAlgorithm` | ❌ No | ❌ No |
| **Actor Model** | ✅ `Actor` base class for non-trading logic | ❌ No | ❌ No |

**NautilusTrader** has the richest strategy interface with fine-grained event handlers:
```python
class MyStrategy(Strategy):
    def on_start(self): ...
    def on_stop(self): ...
    def on_bar(self, bar: Bar): ...
    def on_quote_tick(self, tick: QuoteTick): ...
    def on_trade_tick(self, tick: TradeTick): ...
    def on_order_book_deltas(self, deltas): ...
    def on_event(self, event: Event): ...
    def on_order_filled(self, event: OrderFilled): ...
    def on_position_changed(self, event: PositionChanged): ...
```

**Backtrader** relies on `next()` plus notification callbacks. The metaclass system auto-discovers indicators.

**Backtesting.py** is the simplest — just `init()` and `next()`. Indicators are wrapped via `self.I()`.

---

### 2.5 Data Handling

| Feature | NautilusTrader | Backtrader | Backtesting.py |
|---------|---------------|------------|----------------|
| **Data Types** | `QuoteTick`, `TradeTick`, `Bar`, `OrderBookDelta`, `OrderBookDepth10`, `InstrumentStatus`, custom | OHLCV lines + custom lines | OHLCV DataFrame + custom columns |
| **Time Resolution** | Nanosecond (`uint64_t ns`) | Datetime (float-encoded) | DataFrame DatetimeIndex |
| **Data Wranglers** | ✅ Built-in wranglers for CSV/Parquet/Databento | ❌ Each feed is its own wrangler | ❌ User provides pre-processed DataFrame |
| **Data Catalog** | ✅ `ParquetDataCatalog` for persistent storage | ❌ No | ❌ No |
| **Resampling** | ✅ Bar aggregation from ticks | ✅ Built-in `resampledata()`, `replaydata()` | ❌ User must pre-resample |
| **Multiple Timeframes** | ✅ Via subscriptions | ✅ Via multiple data feeds with different timeframes | ❌ Single timeframe |
| **Online Data** | ✅ 15+ venue adapters (Binance, IB, Betfair, etc.) | ⚠️ Yahoo, IB, Oanda (many broken/outdated) | ❌ No built-in sources |

**NautilusTrader** has the most sophisticated data pipeline:
1. Raw data → `DataWrangler` → normalized types
2. `ParquetDataCatalog` for storage
3. `DataEngine` for subscription management and distribution
4. Nanosecond precision timestamps

**Backtrader** supports multiple data sources but many are outdated (Yahoo API issues, etc.).

**Backtesting.py** just needs a pandas DataFrame — extremely simple but limiting.

---

### 2.6 Order Types & Execution

| Order Type | NautilusTrader | Backtrader | Backtesting.py |
|------------|---------------|------------|----------------|
| **Market** | ✅ | ✅ | ✅ (default) |
| **Limit** | ✅ | ✅ | ✅ |
| **Stop Market** | ✅ | ✅ | ✅ |
| **Stop Limit** | ✅ | ✅ | ❌ |
| **Trailing Stop** | ✅ | ✅ (StopTrail, StopTrailLimit) | ⚠️ Via `TrailingStrategy` helper |
| **Market-to-Limit** | ✅ | ❌ | ❌ |
| **Limit-if-Touched** | ✅ | ❌ | ❌ |
| **Market-if-Touched** | ✅ | ❌ | ❌ |
| **Bracket Orders** | ✅ | ✅ | ✅ (SL/TP on buy/sell) |
| **OCO** | ✅ | ✅ | ❌ |
| **OTO** | ✅ | ❌ | ❌ |
| **Time in Force** | `IOC`, `FOK`, `GTC`, `GTD`, `DAY`, `AT_THE_OPEN`, `AT_THE_CLOSE` | `GTC`, `GTD`, `DAY` (via `valid` param) | `GTC` only |
| **Post-Only** | ✅ | ❌ | ❌ |
| **Reduce-Only** | ✅ | ❌ | ❌ |
| **Iceberg** | ✅ | ❌ | ❌ |
| **Order State Machine** | Full FSM: `INITIALIZED → SUBMITTED → ACCEPTED → FILLED/CANCELED/EXPIRED/DENIED` | `Created → Submitted → Accepted → Completed/Canceled/Expired/Margin/Rejected` | Simple pending → executed |
| **Partial Fills** | ✅ | ✅ | ❌ |

**NautilusTrader** has the most comprehensive order model, mimicking real exchange behavior with a full finite state machine and advanced order types found in institutional trading.

---

### 2.7 Scenarios & Use Cases

| Scenario | NautilusTrader | Backtrader | Backtesting.py |
|----------|---------------|------------|----------------|
| **Quick research / prototyping** | ⚠️ Heavy setup | ⚠️ Moderate setup | ✅ Best choice |
| **Multi-asset portfolio** | ✅ Best choice | ✅ Good | ❌ Single asset |
| **Multi-venue arbitrage** | ✅ Best choice | ❌ Not supported | ❌ Not supported |
| **HFT / tick-level** | ✅ Best choice (ns resolution) | ❌ Bar-level | ❌ Bar-level |
| **Crypto trading** | ✅ Many integrations | ⚠️ Community forks | ❌ Manual data |
| **Options/Futures** | ✅ Native types | ⚠️ Via IB | ❌ With workarounds |
| **Betting markets** | ✅ Betfair adapter | ❌ No | ❌ No |
| **Strategy optimization** | ⚠️ Manual loop | ✅ Built-in `optstrategy` with multiprocessing | ✅ Built-in `optimize()` with grid/skopt |
| **Interactive visualization** | ⚠️ Basic | ✅ Matplotlib plots | ✅ Excellent Bokeh interactive charts |
| **AI/RL training** | ✅ Engine fast enough for RL | ⚠️ Too slow | ⚠️ Too slow |
| **Production live trading** | ✅ First-class | ⚠️ IB/Oanda (outdated) | ❌ No |
| **DeFi / Prediction Markets** | ✅ dYdX, Hyperliquid, Polymarket | ❌ No | ❌ No |

---

### 2.8 Platform Support & Dependencies

| Aspect | NautilusTrader | Backtrader | Backtesting.py |
|--------|---------------|------------|----------------|
| **Python Versions** | 3.12-3.14 | 3.2+ (incl. PyPy) | 3.6+ |
| **Core Dependencies** | Rust toolchain, Cython, numpy, pandas, msgspec, fsspec, pyarrow | None (matplotlib optional) | numpy, pandas, bokeh |
| **Install Size** | Heavy (~100MB+ binary wheel) | Light (~1MB) | Light (~1MB) |
| **OS Support** | Linux, macOS, Windows | Linux, macOS, Windows | Linux, macOS, Windows |
| **Docker** | ✅ Official images | ❌ No | ❌ No |

---

### 2.9 Limitations

#### NautilusTrader Limitations
- 🔴 **Very steep learning curve** — extensive domain model to learn
- 🔴 **Heavy dependency** — Rust toolchain required for building from source
- 🔴 **No built-in optimization** — must write manual loops
- 🔴 **Limited visualization** — basic plotting, no interactive charts
- 🔴 **Complex configuration** — many config objects to wire together
- 🟡 **API still evolving** — breaking changes between releases

#### Backtrader Limitations
- 🔴 **Abandoned** — no updates for 3+ years, many unfixed bugs
- 🔴 **No multi-venue** — single broker per cerebro
- 🔴 **Outdated data feeds** — Yahoo, IB integrations broken
- 🔴 **No order book simulation** — bar-level execution only
- 🟡 **Metaclass complexity** — `with_metaclass()` magic makes debugging hard
- 🟡 **No nanosecond precision** — float-encoded datetimes lose precision

#### Backtesting.py Limitations
- 🔴 **Single instrument only** — no portfolio backtesting
- 🔴 **No live trading** — backtesting only
- 🔴 **No order book** — bar-level execution only
- 🔴 **No multi-timeframe** — single timeframe per test
- 🔴 **No risk management** — no pre-trade checks
- 🔴 **No partial fills** — all-or-nothing execution
- 🟡 **Memory-bound** — all data must fit in memory

---

## 3. Framework Structure Maps

### 3.1 NautilusTrader Structure

```
nautilus_trader/                          # Python package (~29.5% of codebase)
├── adapters/                            # Venue-specific integrations
│   ├── binance/                         # Binance CEX adapter
│   ├── betfair/                         # Betfair betting adapter
│   ├── bybit/                           # Bybit CEX adapter
│   ├── deribit/                         # Deribit adapter
│   ├── dydx/                            # dYdX DEX adapter
│   ├── hyperliquid/                     # Hyperliquid DEX adapter
│   ├── interactive_brokers/             # IB brokerage adapter
│   ├── polymarket/                      # Polymarket prediction market
│   └── ...                              # 15+ adapters total
├── backtest/
│   ├── engine.pyx                       # BacktestEngine (Cython)
│   ├── exchange.pyx                     # SimulatedExchange
│   ├── matching_engine.pyx              # OrderMatchingEngine
│   ├── data_client.pyx                  # BacktestDataClient
│   ├── execution_client.pyx             # BacktestExecClient
│   ├── config.py                        # Configuration classes
│   ├── node.py                          # BacktestNode (high-level)
│   ├── models.py                        # FillModel, FeeModel, LatencyModel
│   └── results.py                       # BacktestResult
├── common/
│   ├── actor.pyx                        # Actor base class
│   ├── component.pyx                    # Component base + Logger
│   └── config.py                        # Base configs
├── core/                                # Core utilities (time, UUID, etc.)
├── data/
│   ├── engine.pyx                       # DataEngine
│   └── client.pyx                       # DataClient base
├── execution/
│   ├── engine.pyx                       # ExecutionEngine
│   └── algorithm.pyx                    # ExecAlgorithm (TWAP, etc.)
├── indicators/                          # 50+ built-in indicators
├── model/
│   ├── data.pyx                         # Bar, QuoteTick, TradeTick, etc.
│   ├── enums.py                         # All domain enums
│   ├── events/                          # OrderFilled, PositionOpened, etc.
│   ├── identifiers.pyx                  # InstrumentId, Venue, TraderId, etc.
│   ├── instruments/                     # Equity, FuturesContract, etc.
│   ├── objects.pyx                      # Price, Quantity, Money
│   ├── orders/                          # All order types
│   └── position.pyx                     # Position
├── portfolio/                           # Portfolio management
├── risk/
│   └── engine.pyx                       # RiskEngine
├── trading/
│   └── strategy.pyx                     # Strategy base class
└── persistence/                         # ParquetDataCatalog

crates/                                  # Rust core (~61.2% of codebase)
├── backtest/src/
│   ├── engine.rs                        # BacktestEngine (Rust impl)
│   ├── exchange.rs                      # SimulatedExchange (Rust impl)
│   ├── matching_engine.rs               # OrderMatchingEngine (Rust impl)
│   └── config.rs                        # Configuration (Rust impl)
├── model/src/                           # Data model types
├── common/src/                          # Shared utilities
├── core/src/                            # Core primitives
├── data/src/                            # Data engine
├── execution/src/                       # Execution engine
├── portfolio/src/                       # Portfolio
└── system/src/                          # NautilusKernel
```

**Data Flow:**
```
Historical Data
    │
    ▼
DataWrangler (normalize) → ParquetDataCatalog (persist)
    │
    ▼
BacktestEngine.add_data()
    │
    ▼
DataIterator (chronological replay)
    │
    ▼
DataEngine (distribute via MessageBus)
    │
    ├──▶ Strategy.on_bar() / on_tick()
    │        │
    │        ▼
    │    OrderFactory.market() / .limit() / ...
    │        │
    │        ▼
    │    ExecutionEngine (route)
    │        │
    │        ▼
    │    RiskEngine (pre-trade check)
    │        │
    │        ▼
    │    SimulatedExchange.process_order()
    │        │
    │        ▼
    │    OrderMatchingEngine (fill simulation)
    │        │
    │        ▼
    │    Events: OrderFilled, PositionOpened, etc.
    │        │
    │        ▼
    │    Portfolio.update() → Cache.update()
    │
    └──▶ Actor (non-trading logic)
```

---

### 3.2 Backtrader Structure

```
backtrader/
├── cerebro.py              # Cerebro: the brain / orchestrator
├── strategy.py             # Strategy base class
├── broker.py               # Broker interface
├── brokers/
│   ├── bbroker.py          # BackBroker (simulated)
│   ├── ibbroker.py         # Interactive Brokers broker
│   └── oandabroker.py      # Oanda broker
├── feed.py                 # AbstractDataBase (data feed base)
├── feeds/
│   ├── csvgeneric.py       # Generic CSV feed
│   ├── ibdata.py           # IB data feed
│   ├── oandadata.py        # Oanda data feed
│   ├── pandafeed.py        # Pandas DataFrame feed
│   ├── yahoo.py            # Yahoo Finance feed
│   └── ...                 # ~15 feed types
├── indicator.py            # Indicator base
├── indicators/
│   ├── sma.py, ema.py      # Basic indicators
│   ├── macd.py, rsi.py     # Advanced indicators
│   ├── atr.py, bollingerbands.py
│   └── ...                 # 122+ built-in indicators
├── observer.py             # Observer base (visual tracking)
├── observers/
│   ├── broker.py           # Cash/Value observer
│   ├── buysell.py          # Buy/Sell marker observer
│   ├── drawdown.py         # Drawdown observer
│   └── trades.py           # Trades observer
├── analyzer.py             # Analyzer base (statistics)
├── analyzers/
│   ├── sharpe.py           # Sharpe ratio
│   ├── drawdown.py         # Drawdown analysis
│   ├── tradeanalyzer.py    # Trade statistics
│   ├── sqn.py              # System Quality Number
│   └── ...                 # ~15 analyzers
├── sizer.py                # Sizer base (position sizing)
├── sizers/
│   ├── fixedsize.py        # Fixed size
│   ├── percentsize.py      # Percentage of portfolio
│   └── ...
├── order.py                # Order class
├── trade.py                # Trade class
├── position.py             # Position class
├── comminfo.py             # Commission info
├── store.py                # Store base (connection management)
├── stores/
│   ├── ibstore.py          # IB store
│   └── oandastore.py       # Oanda store
├── linebuffer.py           # Line (array) buffer system
├── lineseries.py           # LineSeries (multi-line container)
├── lineiterator.py         # LineIterator (base for everything)
├── dataseries.py           # DataSeries (OHLCV lines)
├── resamplerfilter.py      # Data resampling/replaying
├── signal.py               # Signal-based strategies
├── writer.py               # Output writers
├── talib.py                # TA-Lib integration
└── metabase.py             # Metaclass framework
```

**Data Flow:**
```
Data Source (CSV, Yahoo, IB, ...)
    │
    ▼
DataFeed (extends AbstractDataBase)
    │
    ▼
Cerebro.adddata()
    │
    ▼
Cerebro.run()
    ├── Preload data (if preload=True)
    ├── For each bar:
    │   ├── Advance all data feeds
    │   ├── Advance all indicators (vectorized if runonce=True)
    │   ├── Call Strategy.next()
    │   │   ├── Read indicators / data lines
    │   │   ├── Call self.buy() / self.sell() / self.close()
    │   │   │       │
    │   │   │       ▼
    │   │   │   Broker.submit(order)
    │   │   │       │
    │   │   │       ▼
    │   │   │   Sizer.getsizing()
    │   │   │       │
    │   │   │       ▼
    │   │   │   CommissionInfo.getcommission()
    │   │   │       │
    │   │   │       ▼
    │   │   │   Order filled → Trade opened/closed
    │   │   │       │
    │   │   │       ▼
    │   │   │   Strategy.notify_order() / notify_trade()
    │   │   │
    │   │   └── Observers record (Cash, Value, BuySell, etc.)
    │   │
    │   └── Analyzers._next() (compute statistics)
    │
    ▼
Cerebro.plot()  (matplotlib)
```

---

### 3.3 Backtesting.py Structure

```
backtesting/
├── backtesting.py          # EVERYTHING: Strategy, Backtest, Broker, Order, Trade, Position
├── lib.py                  # Library of helper strategies and utilities
│   ├── SignalStrategy      # Signal-based strategy helper
│   ├── TrailingStrategy    # Trailing stop-loss helper
│   ├── FractionalBacktest  # Fractional shares support
│   ├── MultiBacktest       # Run multiple backtests
│   ├── crossover()         # Utility: detect crossovers
│   ├── resample_apply()    # Utility: multi-timeframe workaround
│   ├── random_ohlc_data()  # Utility: synthetic data generator
│   └── barssince()         # Utility: bars since condition
├── _plotting.py            # Bokeh interactive charts
├── _stats.py               # Statistics computation
├── _util.py                # Internal utilities (_Data, _Indicator, etc.)
└── test/
    ├── __init__.py          # Test data (GOOG) and utilities (SMA, GOOG)
    └── _test.py             # Unit tests
```

**Data Flow:**
```
pandas DataFrame (OHLCV)
    │
    ▼
Backtest(data, StrategyClass, cash=10000, ...)
    │
    ▼
Backtest.run()
    ├── Create _Broker(data, cash, spread, commission, ...)
    ├── Create Strategy(broker, data, params)
    ├── Strategy.init()
    │   ├── self.I(SMA, self.data.Close, 20)  → register indicators
    │   └── Precompute everything vectorized
    │
    ├── For i in range(warmup, len(data)):
    │   ├── data._set_length(i + 1)           → simulate bar revelation
    │   ├── Slice indicators to current length
    │   ├── broker.next()                      → process pending orders
    │   │   ├── Check limit/stop conditions against OHLC
    │   │   ├── Fill orders → create Trade
    │   │   └── Update equity
    │   ├── strategy.next()                    → user logic
    │   │   ├── Read self.data.Close[-1], self.sma[-1]
    │   │   └── self.buy() / self.sell() / self.position.close()
    │   │
    │   └── Record equity
    │
    ▼
compute_stats(trades, equity, data) → pd.Series
    │
    ▼
Backtest.plot() → interactive Bokeh chart
```

---

## 4. Availability, Scalability & Extensibility

### 4.1 Availability

| Aspect | NautilusTrader | Backtrader | Backtesting.py |
|--------|---------------|------------|----------------|
| **PyPI** | ✅ `pip install nautilus_trader` | ✅ `pip install backtrader` | ✅ `pip install backtesting` |
| **Documentation** | ✅ Extensive (nautilustrader.io) | ✅ Good (backtrader.com) | ✅ Good (auto-generated API docs) |
| **Examples** | ✅ Many (examples/ directory) | ✅ Many (samples/ directory) | ✅ Jupyter notebook tutorials |
| **Community** | Discord (active) | Community forum (dormant) | GitHub Discussions |
| **Books/Courses** | ❌ None known | ✅ Several community resources | ⚠️ YouTube tutorials |
| **Commercial Support** | ✅ Nautech Systems | ❌ No | ❌ No |
| **Contributors** | 125 | 52 | 42 |

---

### 4.2 Scalability

| Aspect | NautilusTrader | Backtrader | Backtesting.py |
|--------|---------------|------------|----------------|
| **Performance** | 🟢 Excellent (Rust core, ~50-100x faster than pure Python) | 🟡 Good with `runonce=True` (vectorized indicators) | 🟡 Good (vectorized init, but Python loop for next) |
| **Memory Efficiency** | 🟢 Streaming chunks, Rust memory management | 🟢 `exactbars` mode for memory savings | 🔴 All data in memory |
| **Large Datasets** | ✅ ParquetDataCatalog + chunked streaming | ⚠️ With `exactbars`, limited to recent bars | ❌ Limited by RAM |
| **Multi-Core** | ⚠️ Async via tokio (Rust), but mostly single-threaded backtest | ✅ `optstrategy` with `maxcpus` | ✅ `optimize()` uses multiprocessing |
| **Tick-Level Data** | ✅ Native QuoteTick/TradeTick support | ❌ Bar-level only | ❌ Bar-level only |
| **Benchmarks** | Can process millions of ticks in seconds | ~100k bars/sec (with preload) | ~50k-200k bars/sec |

---

### 4.3 Extensibility

| Aspect | NautilusTrader | Backtrader | Backtesting.py |
|--------|---------------|------------|----------------|
| **Custom Indicators** | Python or Cython, register with strategy | Subclass `bt.Indicator`, define `lines` and `next()` | Any callable via `self.I(func)` |
| **Custom Data Types** | ✅ Subclass `Data`, register via DataEngine | ✅ Add custom lines to DataSeries | ✅ Extra DataFrame columns |
| **Custom Order Types** | ✅ Possible but complex | ⚠️ Limited (must modify broker) | ❌ Not supported |
| **Custom Venues/Brokers** | ✅ Adapter pattern (`DataClient`, `ExecutionClient`) | ✅ Subclass `BackBroker` or `Store` | ❌ Not supported |
| **Custom Commission** | ✅ `FeeModel` interface | ✅ `CommissionInfo` subclass | ✅ Callable commission function |
| **Custom Analysis** | ✅ Via actors + message bus | ✅ `Analyzer` subclass | ❌ Post-hoc via stats Series |
| **Plugin Architecture** | ✅ `SimulationModule`, adapters, actors | ⚠️ Stores, filters | ❌ No |
| **Ease of Extension** | 🔴 Steep — Cython/Rust knowledge needed | 🟡 Moderate — metaclass magic can be confusing | 🟢 Easy — simple Python classes |

---

## 5. Side-by-Side Comparison Matrix

| Dimension | NautilusTrader | Backtrader | Backtesting.py |
|-----------|:---:|:---:|:---:|
| **Instrument Support** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Venue Support** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Order Types** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Data Handling** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Ease of Use** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Documentation** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Visualization** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Optimization** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Live Trading** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ☆ |
| **Extensibility** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Maintenance** | ⭐⭐⭐⭐⭐ | ☆ | ⭐⭐ |
| **Multi-Asset** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| **Risk Management** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Community** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## 6. Combined Advantages → Proposed Custom Framework

### 6.1 Key Strengths to Borrow

| From | What to Borrow | Why |
|------|---------------|-----|
| **NautilusTrader** | Event-driven architecture with MessageBus | Decouples components, enables extensibility |
| **NautilusTrader** | Strongly-typed instrument model | Essential for multi-venue, multi-asset |
| **NautilusTrader** | Multi-venue with independent OMS per venue | Enables arbitrage, cross-venue strategies |
| **NautilusTrader** | Dedicated engines (Data, Execution, Risk) | Separation of concerns |
| **NautilusTrader** | `Decimal`-based precision for financial math | Avoids floating-point errors |
| **NautilusTrader** | Order state machine with full lifecycle | Realistic execution simulation |
| **NautilusTrader** | Cache/state management pattern | Centralized, queryable state |
| **Backtrader** | `Cerebro` as simple entry point | Easy to set up a backtest |
| **Backtrader** | Auto-detected indicators via metaclass/registration | Reduce boilerplate |
| **Backtrader** | `Analyzer` pattern for post-hoc statistics | Pluggable analytics |
| **Backtrader** | `Observer` pattern for real-time visual tracking | Debugging aid |
| **Backtrader** | `Sizer` pattern for position sizing logic | Separates sizing from strategy |
| **Backtrader** | Built-in optimization with multiprocessing | Essential for parameter search |
| **Backtesting.py** | Simple `init()` + `next()` strategy API | Low barrier to entry |
| **Backtesting.py** | `self.I(func)` indicator wrapping | Library-agnostic indicators |
| **Backtesting.py** | Interactive Bokeh visualization | Superior to matplotlib |
| **Backtesting.py** | `optimize()` with grid/skopt methods | Easy parameter optimization |
| **Backtesting.py** | Clean `pd.Series` results with all statistics | Easy to consume/compare |
| **Backtesting.py** | Fractional position sizing (`size=0.95` for 95% of equity) | Intuitive API |

---

### 6.2 Proposed Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Custom Framework                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    BacktestRunner                         │   │
│  │  (Simple entry point — inspired by Cerebro + Backtest)    │   │
│  │  runner = BacktestRunner()                                │   │
│  │  runner.add_venue("BINANCE", oms=NETTING, ...)           │   │
│  │  runner.add_venue("NASDAQ", oms=HEDGING, ...)            │   │
│  │  runner.add_data(bars, instrument_id="BTC/USDT.BINANCE") │   │
│  │  runner.add_strategy(MyStrategy, param1=10)              │   │
│  │  results = runner.run()                                   │   │
│  │  runner.optimize(param1=range(5,50), maximize='sharpe')  │   │
│  │  runner.plot()  ← interactive Bokeh                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    BacktestEngine                         │   │
│  │  (Core — inspired by NautilusTrader kernel)               │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │  DataEngine   │  │  ExecEngine  │  │  RiskEngine  │   │   │
│  │  │  (subscribe,  │  │  (route to   │  │  (pre-trade  │   │   │
│  │  │   distribute) │  │   venues)    │  │   checks)    │   │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │   │
│  │         │                  │                  │           │   │
│  │         └──────────────────┼──────────────────┘           │   │
│  │                            │                              │   │
│  │                    ┌───────▼───────┐                      │   │
│  │                    │  MessageBus   │                      │   │
│  │                    │  (pub/sub)    │                      │   │
│  │                    └───────┬───────┘                      │   │
│  │                            │                              │   │
│  │              ┌─────────────┼─────────────┐               │   │
│  │              │             │             │                │   │
│  │        ┌─────▼────┐ ┌─────▼────┐ ┌─────▼────┐          │   │
│  │        │  Cache    │ │ Portfolio│ │  Clock   │          │   │
│  │        │  (state)  │ │  (PnL)  │ │  (time)  │          │   │
│  │        └──────────┘ └──────────┘ └──────────┘          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │ Venue:       │ │ Venue:       │ │ Venue:       │           │
│  │ BINANCE      │ │ NASDAQ       │ │ POLYMARKET   │           │
│  │ (SimExchange)│ │ (SimExchange)│ │ (SimExchange)│           │
│  │ OMS: NETTING │ │ OMS: HEDGING │ │ OMS: NETTING │           │
│  │ Acct: MARGIN │ │ Acct: CASH   │ │ Acct: CASH   │           │
│  │ Instruments: │ │ Instruments: │ │ Instruments: │           │
│  │ BTC/USDT     │ │ AAPL         │ │ YES/NO       │           │
│  │ ETH/USDT     │ │ MSFT         │ │ contracts    │           │
│  └──────────────┘ └──────────────┘ └──────────────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Strategy Layer                          │   │
│  │                                                           │   │
│  │  class MyStrategy(Strategy):     ← Simple API             │   │
│  │      class Config:               ← Params via Config      │   │
│  │          fast_period = 10                                 │   │
│  │          slow_period = 20                                 │   │
│  │                                                           │   │
│  │      def init(self):                                      │   │
│  │          self.fast = self.I(EMA, period=self.config.fast) │   │
│  │          self.slow = self.I(EMA, period=self.config.slow) │   │
│  │                                                           │   │
│  │      def next(self, bar):                                 │   │
│  │          if crossover(self.fast, self.slow):              │   │
│  │              self.buy(instrument_id, size=0.95)           │   │
│  │                                                           │   │
│  │      def on_order_filled(self, event):  ← Optional hooks  │   │
│  │          ...                                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Analysis Layer                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │ Analyzer │ │ Observer │ │  Sizer   │ │Visualizer│   │   │
│  │  │ (stats)  │ │ (track)  │ │ (sizing) │ │ (Bokeh)  │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

### 6.3 Proposed File Structure

```
custom_backtesting_framework/
│
├── core/                                # Foundation Layer
│   ├── __init__.py
│   ├── enums.py                         # All enums (from NautilusTrader pattern)
│   ├── identifiers.py                   # InstrumentId, Venue, StrategyId, etc.
│   ├── objects.py                       # Price, Quantity, Money (Decimal-based)
│   ├── clock.py                         # TestClock, LiveClock
│   ├── events.py                        # All event types (OrderFilled, etc.)
│   └── msgbus.py                        # MessageBus (pub/sub)
│
├── model/                               # Domain Model Layer
│   ├── __init__.py
│   ├── data.py                          # Bar, QuoteTick, TradeTick, OrderBookDelta
│   ├── instruments/
│   │   ├── __init__.py
│   │   ├── base.py                      # Instrument ABC
│   │   ├── equity.py                    # Equity
│   │   ├── crypto_perpetual.py          # CryptoPerpetual
│   │   ├── futures_contract.py          # FuturesContract
│   │   ├── options_contract.py          # OptionsContract
│   │   ├── currency_pair.py             # CurrencyPair (FX)
│   │   ├── betting_instrument.py        # BettingInstrument
│   │   └── prediction_market.py         # PredictionMarket (Polymarket-style)
│   ├── orders/
│   │   ├── __init__.py
│   │   ├── base.py                      # Order ABC + FSM
│   │   ├── market.py, limit.py, stop.py # Order types
│   │   └── factory.py                   # OrderFactory
│   └── position.py                      # Position tracking
│
├── engine/                              # Engine Layer
│   ├── __init__.py
│   ├── data_engine.py                   # DataEngine (subscribe/distribute)
│   ├── execution_engine.py              # ExecutionEngine (route orders)
│   ├── risk_engine.py                   # RiskEngine (pre-trade checks)
│   └── matching_engine.py               # OrderMatchingEngine (per venue)
│
├── venues/                              # Venue Layer (multi-venue support)
│   ├── __init__.py
│   ├── simulated_exchange.py            # SimulatedExchange (backtest)
│   ├── account.py                       # Account (Cash, Margin, Betting)
│   └── models.py                        # FillModel, FeeModel, LatencyModel, SlippageModel
│
├── state/                               # State Management
│   ├── __init__.py
│   ├── cache.py                         # Cache (centralized state)
│   └── portfolio.py                     # Portfolio (PnL, positions)
│
├── trading/                             # Trading Layer
│   ├── __init__.py
│   ├── strategy.py                      # Strategy base (init + next + event hooks)
│   ├── config.py                        # StrategyConfig base
│   └── actor.py                         # Actor (non-trading components)
│
├── indicators/                          # Indicator Layer
│   ├── __init__.py
│   ├── base.py                          # Indicator ABC
│   ├── sma.py, ema.py, atr.py          # Built-in indicators
│   └── wrapper.py                       # self.I() wrapper for any callable
│
├── data/                                # Data Layer
│   ├── __init__.py
│   ├── wranglers.py                     # DataWrangler for CSV, Parquet, APIs
│   ├── catalog.py                       # DataCatalog (Parquet persistence)
│   └── providers/                       # Data source adapters
│       ├── csv_provider.py
│       ├── parquet_provider.py
│       └── api_provider.py
│
├── analysis/                            # Analysis Layer
│   ├── __init__.py
│   ├── analyzer.py                      # Analyzer base (from Backtrader)
│   ├── analyzers/
│   │   ├── sharpe.py, drawdown.py       # Built-in analyzers
│   │   └── trade_analysis.py
│   ├── observer.py                      # Observer base (from Backtrader)
│   ├── sizer.py                         # Sizer base (from Backtrader)
│   └── stats.py                         # compute_stats() (from Backtesting.py)
│
├── visualization/                       # Visualization Layer
│   ├── __init__.py
│   ├── bokeh_plot.py                    # Interactive Bokeh charts (from Backtesting.py)
│   └── report.py                        # HTML report generation
│
├── optimization/                        # Optimization Layer
│   ├── __init__.py
│   ├── grid_search.py                   # Grid search (from Backtesting.py)
│   ├── bayesian.py                      # Bayesian optimization
│   └── walk_forward.py                  # Walk-forward analysis
│
├── backtest/                            # Backtest Orchestration
│   ├── __init__.py
│   ├── engine.py                        # BacktestEngine (core kernel)
│   ├── runner.py                        # BacktestRunner (simple entry point)
│   ├── config.py                        # BacktestConfig, VenueConfig, etc.
│   └── results.py                       # BacktestResult (pd.Series + extras)
│
├── live/                                # Live Trading (future)
│   ├── __init__.py
│   ├── trading_node.py                  # LiveTradingNode
│   └── adapters/                        # Venue adapters
│       ├── binance/
│       ├── interactive_brokers/
│       └── polymarket/
│
├── examples/
│   ├── quick_start.py                   # 10-line backtest
│   ├── multi_venue.py                   # Cross-venue strategy
│   ├── optimization.py                  # Parameter optimization
│   └── notebooks/
│       └── tutorial.ipynb
│
└── tests/
    ├── test_engine.py
    ├── test_strategy.py
    ├── test_venues.py
    └── ...
```

---

### 6.4 Design Principles

| Principle | Implementation | Inspired By |
|-----------|---------------|-------------|
| **10-second quickstart** | `runner.run()` with sensible defaults | Backtesting.py |
| **Infinite depth** | Full event hooks, custom engines, adapters | NautilusTrader |
| **Multi-venue native** | `runner.add_venue()` with independent OMS | NautilusTrader |
| **Multi-instrument native** | Strongly-typed instrument hierarchy | NautilusTrader |
| **Decimal precision** | `Price`, `Quantity`, `Money` using `decimal.Decimal` | NautilusTrader |
| **Event-driven core** | MessageBus pub/sub for all events | NautilusTrader |
| **Pluggable analysis** | Analyzer, Observer, Sizer patterns | Backtrader |
| **Library-agnostic indicators** | `self.I(any_function)` + built-in set | Backtesting.py |
| **Interactive visualization** | Bokeh-based charts | Backtesting.py |
| **Built-in optimization** | Grid search, Bayesian, walk-forward | Backtesting.py + Backtrader |
| **Backtest-live parity** | Same strategy code in both modes | NautilusTrader |
| **Pure Python** | No Rust/Cython compile step (use numpy for speed) | Backtrader + Backtesting.py |
| **Clean API** | Minimal boilerplate, Pythonic interfaces | Backtesting.py |

#### Usage Example (Proposed API):

```python
from framework import BacktestRunner, Strategy, EMA, crossover
from framework.venues import VenueConfig

class EmaCross(Strategy):
    class Config:
        fast_period: int = 10
        slow_period: int = 20

    def init(self):
        self.fast = self.I(EMA, self.data.Close, self.config.fast_period)
        self.slow = self.I(EMA, self.data.Close, self.config.slow_period)

    def next(self):
        if crossover(self.fast, self.slow):
            self.buy(size=0.95)          # 95% of equity
        elif crossover(self.slow, self.fast):
            self.sell(size=0.95)

# Quick backtest (Backtesting.py simplicity)
runner = BacktestRunner()
runner.add_venue("BINANCE", oms="NETTING", account="MARGIN", cash=100_000)
runner.add_data("BTC_USDT_1h.csv", instrument="BTC/USDT.BINANCE")
runner.add_strategy(EmaCross, fast_period=12, slow_period=26)
results = runner.run()
print(results)          # pd.Series with all stats
runner.plot()           # Interactive Bokeh chart

# Multi-venue (NautilusTrader power)
runner = BacktestRunner()
runner.add_venue("BINANCE", oms="NETTING", cash=50_000)
runner.add_venue("NASDAQ", oms="HEDGING", cash=50_000)
runner.add_data(crypto_bars, instrument="BTC/USDT.BINANCE")
runner.add_data(equity_bars, instrument="AAPL.NASDAQ")
runner.add_strategy(ArbitrageStrategy)
results = runner.run()

# Optimization (Backtesting.py + Backtrader convenience)
results, heatmap = runner.optimize(
    fast_period=range(5, 30),
    slow_period=range(20, 60),
    maximize='sharpe_ratio',
    method='grid',
    return_heatmap=True,
)
```

---

## Summary

| Best For | Choose |
|----------|--------|
| **Research & prototyping** | Backtesting.py |
| **Learning backtesting** | Backtesting.py → Backtrader |
| **Production trading system** | NautilusTrader |
| **Multi-venue / multi-asset** | NautilusTrader |
| **Custom framework** | Take the best from all three ✨ |

The proposed custom framework aims to achieve:
- **NautilusTrader's power** (multi-venue, typed instruments, event-driven, risk engine)
- **Backtrader's richness** (analyzers, observers, sizers, 122+ indicators)
- **Backtesting.py's simplicity** (10-line quickstart, interactive charts, easy optimization)

All in **pure Python** with no Rust/Cython compilation required, while supporting **more venues and instruments** than any single framework.

---

*Generated for the `backtesting_framework` project — a custom backtesting platform combining the best of open-source.*
