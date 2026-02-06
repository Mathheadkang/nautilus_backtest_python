# 🏗️ Custom Backtesting Framework — Step-by-Step Build Plan

> **Audience:** You (the builder). This document is a teacher's guide: each step tells you *what* to build, *why* every design decision matters, *where* it will be used, and *whether C++/Rust optimization is worth it*.

---

## Table of Contents

1. [Build Order Overview](#build-order-overview)
2. [Phase 1 — Foundation Layer (core/)](#phase-1--foundation-layer-core)
3. [Phase 2 — Domain Model Layer (model/)](#phase-2--domain-model-layer-model)
4. [Phase 3 — State Management Layer (state/)](#phase-3--state-management-layer-state)
5. [Phase 4 — Engine Layer (engine/)](#phase-4--engine-layer-engine)
6. [Phase 5 — Venue Layer (venues/)](#phase-5--venue-layer-venues)
7. [Phase 6 — Trading Layer (trading/)](#phase-6--trading-layer-trading)
8. [Phase 7 — Indicator Layer (indicators/)](#phase-7--indicator-layer-indicators)
9. [Phase 8 — Data Layer (data/)](#phase-8--data-layer-data)
10. [Phase 9 — Analysis Layer (analysis/)](#phase-9--analysis-layer-analysis)
11. [Phase 10 — Backtest Orchestration (backtest/)](#phase-10--backtest-orchestration-backtest)
12. [Phase 11 — Visualization Layer (visualization/)](#phase-11--visualization-layer-visualization)
13. [Phase 12 — Optimization Layer (optimization/)](#phase-12--optimization-layer-optimization)
14. [Phase 13 — Live Trading Skeleton (live/)](#phase-13--live-trading-skeleton-live)
15. [Master Test Plan](#master-test-plan)
16. [Example Test Data Files](#example-test-data-files)
17. [C++/Rust Optimization Summary Table](#crust-optimization-summary-table)

---

## Build Order Overview

```
Phase 1: core/enums.py → core/identifiers.py → core/objects.py → core/events.py → core/clock.py → core/msgbus.py
              │
Phase 2: model/data.py → model/instruments/* → model/orders/* → model/position.py
              │
Phase 3: state/cache.py → state/portfolio.py
              │
Phase 4: engine/matching_engine.py → engine/data_engine.py → engine/execution_engine.py → engine/risk_engine.py
              │
Phase 5: venues/models.py → venues/account.py → venues/simulated_exchange.py
              │
Phase 6: trading/config.py → trading/strategy.py → trading/actor.py
              │
Phase 7: indicators/base.py → indicators/sma.py → indicators/ema.py → indicators/atr.py → indicators/wrapper.py
              │
Phase 8: data/wranglers.py → data/catalog.py → data/providers/*
              │
Phase 9: analysis/analyzer.py → analysis/analyzers/* → analysis/observer.py → analysis/sizer.py → analysis/stats.py
              │
Phase 10: backtest/config.py → backtest/engine.py → backtest/runner.py → backtest/results.py
              │
Phase 11: visualization/bokeh_plot.py → visualization/report.py
              │
Phase 12: optimization/grid_search.py → optimization/bayesian.py → optimization/walk_forward.py
              │
Phase 13: live/trading_node.py → live/adapters/*
```

**Rule:** Never start a phase until every file in the previous phase passes its unit tests.

---

## Phase 1 — Foundation Layer (`core/`)

The foundation layer has **zero external dependencies** (only Python stdlib). Every other module in the framework imports from `core/`. Build it first, test it exhaustively.

---

### Step 1.1: `core/enums.py`

**Where it will be used:**
Everywhere. Every module that needs to express order sides, order types, order statuses, OMS types, account types, asset classes, etc. will import from this file. It is the single source of truth for all categorical constants.

**What it should contain and the logic:**

```python
from enum import Enum, auto

class OrderSide(Enum):
    BUY = auto()
    SELL = auto()

class OrderType(Enum):
    MARKET = auto()
    LIMIT = auto()
    STOP_MARKET = auto()
    STOP_LIMIT = auto()
    TRAILING_STOP = auto()
    MARKET_IF_TOUCHED = auto()

class TimeInForce(Enum):
    GTC = auto()   # Good Till Cancel
    IOC = auto()   # Immediate or Cancel
    FOK = auto()   # Fill or Kill
    GTD = auto()   # Good Till Date
    DAY = auto()

class OrderStatus(Enum):
    INITIALIZED = auto()
    DENIED = auto()
    SUBMITTED = auto()
    ACCEPTED = auto()
    REJECTED = auto()
    CANCELED = auto()
    EXPIRED = auto()
    TRIGGERED = auto()
    PENDING_UPDATE = auto()
    PENDING_CANCEL = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()

class OmsType(Enum):
    UNSPECIFIED = auto()
    NETTING = auto()    # Single position per instrument (crypto, FX)
    HEDGING = auto()    # Multiple positions per instrument (equities, futures)

class AccountType(Enum):
    CASH = auto()
    MARGIN = auto()
    BETTING = auto()

class AssetClass(Enum):
    EQUITY = auto()
    FX = auto()
    CRYPTO = auto()
    COMMODITY = auto()
    INDEX = auto()
    BETTING = auto()

class CurrencyType(Enum):
    FIAT = auto()
    CRYPTO = auto()

class LiquiditySide(Enum):
    MAKER = auto()
    TAKER = auto()

class PositionSide(Enum):
    FLAT = auto()
    LONG = auto()
    SHORT = auto()

class BarAggregation(Enum):
    TICK = auto()
    SECOND = auto()
    MINUTE = auto()
    HOUR = auto()
    DAY = auto()
    WEEK = auto()
    MONTH = auto()

class PriceType(Enum):
    BID = auto()
    ASK = auto()
    MID = auto()
    LAST = auto()

# ── Finite State Machine transition table ──
ORDER_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.INITIALIZED: {OrderStatus.DENIED, OrderStatus.SUBMITTED},
    OrderStatus.SUBMITTED:   {OrderStatus.ACCEPTED, OrderStatus.REJECTED, OrderStatus.CANCELED},
    OrderStatus.ACCEPTED:    {OrderStatus.CANCELED, OrderStatus.EXPIRED, OrderStatus.TRIGGERED,
                              OrderStatus.PENDING_UPDATE, OrderStatus.PENDING_CANCEL,
                              OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED},
    OrderStatus.TRIGGERED:   {OrderStatus.CANCELED, OrderStatus.EXPIRED,
                              OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED},
    OrderStatus.PARTIALLY_FILLED: {OrderStatus.CANCELED, OrderStatus.PARTIALLY_FILLED,
                                    OrderStatus.FILLED},
    OrderStatus.PENDING_UPDATE: {OrderStatus.ACCEPTED, OrderStatus.CANCELED},
    OrderStatus.PENDING_CANCEL: {OrderStatus.ACCEPTED, OrderStatus.CANCELED},
    # Terminal states — no transitions out
    OrderStatus.DENIED:   set(),
    OrderStatus.REJECTED: set(),
    OrderStatus.CANCELED: set(),
    OrderStatus.EXPIRED:  set(),
    OrderStatus.FILLED:   set(),
}
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **`Enum` with `auto()`** | You never hard-code integer values. `auto()` auto-assigns, so insertion order doesn't matter. Enums are hashable, serializable, and IDE-friendly. |
| **Single file for all enums** | Avoids circular imports. Every module can `from core.enums import X` without pulling in heavy objects. |
| **`ORDER_STATUS_TRANSITIONS` dict** | This is a **Finite State Machine (FSM)** table. Instead of scattered `if/elif` chains in every order class, you have ONE authoritative table. The order class just checks `if new_status in ORDER_STATUS_TRANSITIONS[current_status]`. This prevents illegal transitions (e.g., `FILLED → SUBMITTED`), which is critical for simulation correctness. |
| **Separate `OmsType.NETTING` vs `HEDGING`** | Crypto exchanges (Binance) use NETTING (one position per instrument), while traditional brokers (Interactive Brokers) use HEDGING (multiple positions). You must model both to support multi-venue. |

**Instructions:**
1. Create the file `core/enums.py`.
2. Define every enum above. Add doc-strings to each member explaining what it means in a trading context.
3. Define the `ORDER_STATUS_TRANSITIONS` dictionary. Verify that terminal states have empty sets.
4. Create `core/__init__.py` and re-export all enums for convenience.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
Enums are used for comparisons and lookups. Python `Enum` is already fast enough. In Rust, enums are zero-cost abstractions, but the overhead of crossing the Python↔Rust FFI boundary (via PyO3) to compare an enum value would actually be *slower* than a native Python enum comparison. Leave this in pure Python.

---

### Step 1.2: `core/identifiers.py`

**Where it will be used:**
Every order, instrument, position, strategy, account, and venue is identified by a typed identifier. These objects are used as dictionary keys throughout the cache, portfolio, and execution engines.

**What it should contain and the logic:**

A base `_Identifier` class and typed subclasses: `TraderId`, `StrategyId`, `InstrumentId`, `Symbol`, `Venue`, `AccountId`, `ClientOrderId`, `VenueOrderId`, `TradeId`, `PositionId`.

```python
class _Identifier:
    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError(f"{type(self).__name__} value must be non-empty")
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._value))

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{self._value}')"

    def __str__(self) -> str:
        return self._value
```

`InstrumentId` is special — it's a composite of `Symbol` and `Venue`:

```python
class InstrumentId(_Identifier):
    """Format: SYMBOL.VENUE  e.g. 'BTC/USDT.BINANCE'"""
    __slots__ = ("_value", "_symbol", "_venue")

    def __init__(self, symbol: Symbol, venue: Venue) -> None:
        super().__init__(f"{symbol.value}.{venue.value}")
        self._symbol = symbol
        self._venue = venue

    @classmethod
    def from_str(cls, value: str) -> InstrumentId:
        parts = value.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid InstrumentId format: '{value}'")
        return cls(Symbol(parts[0]), Venue(parts[1]))
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **`__slots__`** | Identifiers are created in *massive* quantities (every order, every tick, every event has identifiers). `__slots__` eliminates the per-instance `__dict__` dictionary — this saves ~100 bytes per object and speeds up attribute access by 20-35%. When you process 1 million ticks, each carrying 3 identifiers, that's 3M identifier objects × 100 bytes = 300 MB saved. |
| **`__hash__` includes `type(self).__name__`** | Prevents collisions between different identifier types with the same string. `Venue("SIM")` and `Symbol("SIM")` must not hash to the same value when used as dictionary keys. |
| **`__eq__` checks `type(self)`** | A `Venue("BINANCE")` must NOT equal a `Symbol("BINANCE")`. Type safety prevents subtle bugs where you accidentally look up a symbol in a venue dictionary. |
| **`from_str` classmethod** | Parsing factory. Users write `"BTC/USDT.BINANCE"` in config files. This method splits and validates. |
| **Typed subclasses** | Instead of one generic `Identifier(type="venue", value="BINANCE")`, you have `Venue("BINANCE")`. This catches bugs at the type level — you cannot pass a `Venue` where a `StrategyId` is expected. Your IDE will warn you. |
| **Immutability** | The `_value` is set once in `__init__` and never changed. Combined with `__slots__`, there's no way to add attributes. This makes identifiers safe to use as dict keys (hashability contract). |

**Instructions:**
1. Create `core/identifiers.py`.
2. Implement `_Identifier` base class with `__slots__`, `__eq__`, `__hash__`, `__repr__`, `__str__`.
3. Implement subclasses: `TraderId`, `StrategyId`, `Symbol`, `Venue`, `AccountId`, `ClientOrderId`, `VenueOrderId`, `TradeId`, `PositionId` — all inherit `_Identifier` without modification.
4. Implement `InstrumentId` with composite `Symbol` + `Venue`, plus `from_str`.
5. **Test edge cases:** empty strings, `rsplit` with multiple dots (e.g., `"BTC/USDT.BINANCE"` must split as `("BTC/USDT", "BINANCE")`).

**🦀 C++/Rust Optimization Verdict: ⚠️ MAYBE (Phase 2+)**
Identifiers are tiny but created millions of times. In Rust (via PyO3), you could represent them as interned strings — store a global `HashMap<String, u32>` and use the integer ID internally. This reduces hash comparisons from string-to-string to int-to-int, which is ~10x faster. **Wait until profiling shows identifier hashing as a bottleneck** (it usually isn't until you hit >10M events/sec). For now, `__slots__` is sufficient.

---

### Step 1.3: `core/objects.py`

**Where it will be used:**
Every financial calculation: order prices, position sizes, account balances, PnL computations, commission fees. `Price`, `Quantity`, and `Money` are the three fundamental value types in the framework.

**What it should contain and the logic:**

1. **`Currency`** — a frozen dataclass with `code`, `precision`, `currency_type`. Pre-define common currencies (`USD`, `EUR`, `BTC`, `ETH`, `USDT`).
2. **`Price`** — wraps `Decimal` with fixed precision. Supports arithmetic (`+`, `-`, `*`, comparisons).
3. **`Quantity`** — wraps `Decimal` with fixed precision. Must be non-negative. Supports arithmetic.
4. **`Money`** — a `Decimal` amount + `Currency`. Supports arithmetic (must match currencies).
5. **`AccountBalance`** — tracks `total`, `locked`, `free` as `Money`.

```python
class Price:
    __slots__ = ("_value", "_precision")

    def __init__(self, value: Decimal | str | float, precision: int) -> None:
        self._precision = precision
        d = Decimal(str(value))
        self._value = d.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)

    # Full arithmetic: __add__, __sub__, __mul__, __neg__, __abs__
    # Full comparison: __eq__, __lt__, __le__, __gt__, __ge__
    # Utility: as_double(), __hash__, __repr__
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **`Decimal` instead of `float`** | `float(0.1 + 0.2) == 0.30000000000000004`. In finance, this causes incorrect PnL, position sizes, and balance computations. `Decimal("0.1") + Decimal("0.2") == Decimal("0.3")` exactly. A 1 cent rounding error on a $10M portfolio is $100K. |
| **`__slots__`** | Same reason as identifiers — Price/Quantity are created millions of times (every bar, every order, every fill). `__slots__` saves memory and speeds up access. |
| **Explicit `precision` parameter** | Different instruments have different price precisions: BTC/USDT uses 2 decimals, AAPL uses 2, JPY pairs use 3. The precision is set once and all arithmetic preserves it. This prevents bugs like submitting a price with 8 decimal places to an exchange that only accepts 2. |
| **`ROUND_HALF_UP`** | Standard rounding for financial calculations (0.5 rounds to 1, not "round half to even" like Python's default `ROUND_HALF_EVEN`). |
| **Quantity enforces non-negative** | You cannot have `-10` shares as a quantity. Negative positions are expressed via `PositionSide.SHORT`, not negative quantities. This prevents an entire class of sign bugs. |
| **Money requires matching currencies** | `Money("100", USD) + Money("50", EUR)` must raise a `ValueError`. Mixing currencies without explicit conversion is a bug. |

**Instructions:**
1. Create `core/objects.py`.
2. Implement `Currency` as a `@dataclass(frozen=True)`. Pre-define: `USD`, `EUR`, `GBP`, `JPY`, `BTC`, `ETH`, `USDT`, `SOL`.
3. Implement `Price` with `__slots__`, full arithmetic dunder methods, comparisons, `as_double()`, `__hash__`.
4. Implement `Quantity` — same as `Price` but with a non-negative check in `__init__`.
5. Implement `Money` — `Decimal` amount + `Currency`. Arithmetic checks currency match.
6. Implement `AccountBalance(total: Money, locked: Money, free: Money)`.
7. Write at least 25 unit tests covering arithmetic, rounding, edge cases (zero, negative, overflow).

**🦀 C++/Rust Optimization Verdict: ✅ HIGH VALUE (Phase 2+)**
This is the **#1 optimization target** in the entire framework. Every tick triggers Price/Quantity arithmetic. Python's `Decimal` is pure Python and ~100x slower than Rust's `rust_decimal` crate. NautilusTrader gained its 50-100x speedup primarily by moving Price/Quantity to Rust. **Plan:**
- Phase 1: Pure Python `Decimal` (correct first).
- Phase 2: Write Rust `Price`/`Quantity` structs with `rust_decimal`, expose via PyO3 with `#[pyclass]`. Keep the Python fallback for development.
- Expected speedup: 30-80x for arithmetic-heavy operations.

---

### Step 1.4: `core/events.py`

**Where it will be used:**
The MessageBus publishes events. Strategies subscribe to them. The execution engine emits them. Every state change in the system (order accepted, order filled, position opened) is an event.

**What it should contain and the logic:**

Define a hierarchy of event dataclasses:

```
Event (base)
├── OrderEvent
│   ├── OrderInitialized
│   ├── OrderDenied
│   ├── OrderSubmitted
│   ├── OrderAccepted
│   ├── OrderRejected
│   ├── OrderCanceled
│   ├── OrderUpdated
│   ├── OrderExpired
│   ├── OrderTriggered
│   └── OrderFilled
└── PositionEvent
    ├── PositionOpened
    ├── PositionChanged
    └── PositionClosed
```

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Event:
    ts_event: int    # nanosecond timestamp of when the event occurred
    ts_init: int     # nanosecond timestamp of when the event was initialized

@dataclass(frozen=True)
class OrderFilled(Event):
    trader_id: TraderId
    strategy_id: StrategyId
    instrument_id: InstrumentId
    client_order_id: ClientOrderId
    venue_order_id: VenueOrderId
    account_id: AccountId
    trade_id: TradeId
    order_side: OrderSide
    order_type: OrderType
    last_qty: Quantity
    last_px: Price
    currency: Currency
    commission: Money
    liquidity_side: LiquiditySide
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **`@dataclass(frozen=True)`** | Events are immutable facts. Once an order is filled, the fill event cannot change. `frozen=True` prevents accidental mutation, makes events hashable, and signals intent to other developers. |
| **Nanosecond timestamps (`int`)** | Using `int` nanoseconds (Unix epoch) instead of `datetime` because: (1) `int` comparisons are 5x faster than `datetime` comparisons, (2) nanosecond resolution is needed for tick-level simulations, (3) `int` is trivially serializable. You convert to `datetime` only for display. |
| **Event hierarchy** | Polymorphism. The execution engine processes any `OrderEvent` via `isinstance` checks. The strategy subscribes to specific types. This is the **Observer pattern** — events are the messages. |
| **All identifiers included** | Each event is self-contained. You can log it, replay it, or send it over a network and reconstruct full state. This is the foundation of **event sourcing**. |

**Instructions:**
1. Create `core/events.py`.
2. Define `Event` base dataclass with `ts_event` and `ts_init`.
3. Define all order event types as frozen dataclasses.
4. Define all position event types.
5. Consider adding an `AccountStateEvent` for balance changes.
6. Write tests: create each event type, verify immutability, verify field access.

**🦀 C++/Rust Optimization Verdict: ⚠️ MAYBE (Phase 3)**
Events are created frequently but are short-lived (created, published via msgbus, consumed, garbage collected). The bottleneck is not event creation but message dispatch. If profiling shows `dataclass.__init__` as hot, convert to Rust `#[pyclass]` structs. Typically not the bottleneck.

---

### Step 1.5: `core/clock.py`

**Where it will be used:**
The backtest engine uses `TestClock` to step through simulated time. Strategies query the clock for the current timestamp. Live trading uses `LiveClock` wrapping real system time. Timers and scheduled callbacks depend on this.

**What it should contain and the logic:**

```python
from abc import ABC, abstractmethod
import time

class Clock(ABC):
    @abstractmethod
    def timestamp_ns(self) -> int:
        """Current time in nanoseconds since Unix epoch."""
        ...

    @abstractmethod
    def set_timer(self, name: str, interval_ns: int, callback: Callable) -> None: ...

    @abstractmethod
    def cancel_timer(self, name: str) -> None: ...

class TestClock(Clock):
    """Deterministic clock for backtesting — time only advances when you tell it to."""
    def __init__(self, initial_ns: int = 0):
        self._time_ns = initial_ns
        self._timers: dict[str, tuple[int, int, Callable]] = {}  # name -> (next_fire, interval, callback)

    def set_time(self, ns: int) -> None:
        self._time_ns = ns

    def advance_time(self, to_ns: int) -> list[Event]:
        """Advance clock to `to_ns`, firing any timers that trigger along the way."""
        events = []
        for name, (next_fire, interval, callback) in list(self._timers.items()):
            while next_fire <= to_ns:
                events.append(callback(next_fire))
                next_fire += interval
                self._timers[name] = (next_fire, interval, callback)
        self._time_ns = to_ns
        return events

class LiveClock(Clock):
    """Real-time clock for live trading."""
    def timestamp_ns(self) -> int:
        return int(time.time_ns())
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Abstract `Clock` base class** | The **Strategy pattern** — strategies depend on `Clock` (the interface), not `TestClock` or `LiveClock`. Same strategy code works in both backtest and live. This is how NautilusTrader achieves backtest-live parity. |
| **`TestClock.advance_time()`** | In backtesting, you don't want real time. You want to jump from bar to bar. `advance_time()` moves the clock and fires any timers that would have triggered in between. This is deterministic and reproducible. |
| **Nanosecond integers** | Matches event timestamps. No `datetime` objects in the hot path. |
| **Timer support** | Strategies may need periodic actions (e.g., rebalance every hour). Timers fire automatically during `advance_time()`. |

**Instructions:**
1. Create `core/clock.py`.
2. Define `Clock` ABC with `timestamp_ns`, `set_timer`, `cancel_timer`.
3. Implement `TestClock` with `set_time`, `advance_time`, timer management.
4. Implement `LiveClock` using `time.time_ns()`.
5. Test: advance time, verify timer callbacks fire in correct order.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
The clock's `advance_time` is called once per bar (low frequency). The timer loop iterates over a handful of timers. Pure Python is fine.

---

### Step 1.6: `core/msgbus.py`

**Where it will be used:**
The central nervous system. DataEngine publishes bars/ticks → strategies receive them. ExecutionEngine publishes order events → strategies receive them. RiskEngine intercepts order submissions. Every inter-component communication flows through the MessageBus.

**What it should contain and the logic:**

```python
from collections import defaultdict
from typing import Any, Callable

class MessageBus:
    def __init__(self, trader_id: str | None = None):
        self.trader_id = trader_id
        self._subscriptions: dict[str, list[Callable]] = defaultdict(list)
        self._endpoints: dict[str, Callable] = {}

    # ── Pub/Sub (1-to-many) ──
    def subscribe(self, topic: str, handler: Callable) -> None: ...
    def unsubscribe(self, topic: str, handler: Callable) -> None: ...
    def publish(self, topic: str, msg: Any) -> None:
        for handler in self._subscriptions.get(topic, []):
            handler(msg)

    # ── Request/Response (1-to-1) ──
    def register(self, endpoint: str, handler: Callable) -> None: ...
    def send(self, endpoint: str, msg: Any) -> None: ...

    # ── Introspection ──
    def has_subscribers(self, topic: str) -> bool: ...
    def topics(self) -> list[str]: ...
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Pub/Sub pattern** | Decouples producers from consumers. The DataEngine doesn't need to know which strategies exist — it just `publish("data.bars.BTC/USDT.BINANCE", bar)`. Any strategy that subscribed gets it. You can add/remove strategies without changing the engine. |
| **Separate `publish` (1-to-many) vs `send` (1-to-1)** | `publish` is for broadcasting (data, events). `send` is for commands (submit order → execution engine). Having both patterns prevents architectural confusion. |
| **String-based topics** | Topics are hierarchical strings like `"data.bars.BTC/USDT.BINANCE"` or `"events.order.MyStrategy"`. This allows pattern matching in future versions (e.g., subscribe to `"data.bars.*"`). |
| **`defaultdict(list)`** | No need to check if a topic exists before appending. Clean code. |
| **No async** | In backtesting, everything is synchronous and deterministic. The handler is called *immediately* during `publish()`. This ensures events are processed in deterministic order. Async would introduce non-determinism. |

**Instructions:**
1. Create `core/msgbus.py`.
2. Implement `subscribe`, `unsubscribe`, `publish` for pub/sub.
3. Implement `register`, `deregister`, `send` for request/response.
4. Implement `has_subscribers`, `topics`, `endpoints` for introspection.
5. Test: subscribe two handlers, publish, verify both called in order. Unsubscribe one, publish again, verify only the remaining one is called.

**🦀 C++/Rust Optimization Verdict: ⚠️ MAYBE (Phase 3)**
The MessageBus `publish()` is called on every single tick/bar and calls all subscribers. For backtesting with millions of ticks, this can become a bottleneck. Rust could optimize with a pre-compiled dispatch table using function pointer arrays. **But first:** profile. The Python overhead is usually in the *handler functions*, not in the dispatch itself.

---

## Phase 2 — Domain Model Layer (`model/`)

These are your data types — the "nouns" of the system. They depend only on `core/`.

---

### Step 2.1: `model/data.py`

**Where it will be used:**
Every piece of market data flows through this: bars (OHLCV), quote ticks (bid/ask), trade ticks (last price). The DataEngine distributes these. Strategies consume them. The backtest engine iterates over them.

**What it should contain and the logic:**

```python
@dataclass(frozen=True)
class BarSpecification:
    step: int                    # e.g. 1
    aggregation: BarAggregation  # e.g. MINUTE
    price_type: PriceType        # e.g. LAST

@dataclass(frozen=True)
class BarType:
    instrument_id: InstrumentId
    bar_spec: BarSpecification

class Bar:
    __slots__ = ("bar_type", "open", "high", "low", "close", "volume", "ts_event", "ts_init")

    def __init__(self, bar_type: BarType, open: Price, high: Price, low: Price,
                 close: Price, volume: Quantity, ts_event: int, ts_init: int) -> None:
        ...

@dataclass(frozen=True)
class QuoteTick:
    instrument_id: InstrumentId
    bid_price: Price
    ask_price: Price
    bid_size: Quantity
    ask_size: Quantity
    ts_event: int
    ts_init: int

@dataclass(frozen=True)
class TradeTick:
    instrument_id: InstrumentId
    price: Price
    size: Quantity
    aggressor_side: OrderSide
    trade_id: TradeId
    ts_event: int
    ts_init: int
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **`Bar` uses `__slots__`** | Bars are the most numerous object in backtesting. A 5-year, 1-minute dataset of 1 instrument = ~1.3M bars. With `__slots__`, each bar is ~200 bytes instead of ~400 bytes. That's 260MB vs 520MB for one instrument. |
| **`BarType` as frozen dataclass** | `BarType` identifies which bar stream a bar belongs to (e.g., `BTC/USDT.BINANCE-1-MINUTE-LAST`). It's immutable and hashable so it can be used as a dictionary key for subscriptions. |
| **Separate `QuoteTick` and `TradeTick`** | They represent different market data. QuoteTick = current bid/ask spread (Level 1). TradeTick = actual executed trades on the exchange. Some strategies need one, some need both. |
| **`ts_event` vs `ts_init`** | `ts_event` = when the event *actually happened* (exchange timestamp). `ts_init` = when your system *received* it. In backtesting they're the same, but in live trading the difference is your latency. Track both for accurate analysis. |
| **`Bar` NOT as dataclass** | Although `QuoteTick` and `TradeTick` use `@dataclass(frozen=True)`, `Bar` uses `__slots__` manually for maximum performance because bars are more numerous and accessed more frequently. You *could* use dataclass for consistency, but the `__slots__` manual approach gives you more control over the constructor. |

**Instructions:**
1. Create `model/__init__.py` and `model/data.py`.
2. Implement `BarSpecification`, `BarType` as frozen dataclasses.
3. Implement `Bar` with `__slots__` and full `__eq__`, `__repr__`.
4. Implement `QuoteTick`, `TradeTick` as frozen dataclasses.
5. Add a `bar_to_quote_tick()` helper that converts a bar to a synthetic quote tick (useful for simulated exchanges).
6. Test: create bars, verify OHLCV values, test sorting by `ts_event`.

**🦀 C++/Rust Optimization Verdict: ✅ HIGH VALUE (Phase 2)**
Bar and tick data are the **#2 optimization target**. In Rust, you can use `#[repr(C)]` structs with fixed-size fields, store them in contiguous memory (like a Rust `Vec<Bar>`), and iterate over them with zero Python overhead. Combined with Rust Price/Quantity from Step 1.3, this could make the main backtest loop 50-100x faster. Use Apache Arrow / Polars-compatible layouts for zero-copy data access.

---

### Step 2.2: `model/instruments/` (Instrument Hierarchy)

**Where it will be used:**
Every venue registers instruments. Every order targets an instrument. The matching engine uses instrument specs (tick size, lot size, fees) to validate and fill orders. Different instrument types have different margin rules, settlement methods, and expiry logic.

**What it should contain and the logic:**

```
model/instruments/
├── __init__.py
├── base.py              # Instrument ABC
├── equity.py            # Equity (stocks)
├── crypto_perpetual.py  # CryptoPerpetual (BTC/USDT perps)
├── currency_pair.py     # CurrencyPair (FX — EUR/USD)
├── futures_contract.py  # FuturesContract (ES, NQ)
├── options_contract.py  # OptionsContract (AAPL calls/puts)
├── betting_instrument.py # BettingInstrument (Betfair)
└── prediction_market.py  # PredictionMarket (Polymarket YES/NO)
```

```python
from abc import ABC, abstractmethod

class Instrument(ABC):
    __slots__ = (
        "_id", "_venue", "_quote_currency", "_asset_class",
        "_price_precision", "_size_precision",
        "_tick_size", "_lot_size",
        "_maker_fee", "_taker_fee",
        "_min_quantity", "_max_quantity",
        "_margin_init", "_margin_maint",
    )

    def __init__(self, instrument_id: InstrumentId, ...) -> None: ...

    @property
    def id(self) -> InstrumentId: return self._id

    @abstractmethod
    def calculate_notional(self, quantity: Quantity, price: Price) -> Money: ...

    def make_price(self, value) -> Price:
        return Price(value, self._price_precision)

    def make_qty(self, value) -> Quantity:
        return Quantity(value, self._size_precision)
```

```python
class CryptoPerpetual(Instrument):
    """A crypto perpetual futures contract (e.g., BTC/USDT on Binance)."""
    __slots__ = Instrument.__slots__ + ("_settlement_currency", "_is_inverse")

    def calculate_notional(self, quantity, price):
        if self._is_inverse:
            return Money(quantity.value / price.value, self._settlement_currency)
        return Money(quantity.value * price.value, self._settlement_currency)
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **ABC with `@abstractmethod`** | Forces every instrument subclass to implement `calculate_notional`. Without this, you'd forget for some instrument type and get a runtime crash weeks later. |
| **`__slots__` inheritance** | Each subclass extends slots: `__slots__ = Instrument.__slots__ + (...)`. This maintains memory efficiency across the hierarchy. Note: each level in the hierarchy adds its OWN new slots; you don't repeat parent slots in the child's `__slots__` tuple. Actually, with `__slots__` inheritance, each class defines only its *new* slots. |
| **`make_price` / `make_qty`** | Factory methods that automatically apply the instrument's precision. Instead of `Price(100.50, 2)`, you write `instrument.make_price(100.50)`. The instrument knows its own precision. This prevents precision mismatch bugs. |
| **`is_inverse` for CryptoPerpetual** | Some perps (like BitMEX BTC/USD) are inverse — PnL is in BTC, not USD. Notional calculation is `qty / price` instead of `qty * price`. You must model this correctly or your PnL is completely wrong. |
| **Separate classes per instrument type** | An equity has `sector`, a futures contract has `expiry_date`, an option has `strike_price` and `option_type`. Cramming all into one class would be a mess. Polymorphism lets the matching engine handle each type correctly. |

**Instructions:**
1. Create `model/instruments/__init__.py` — re-export all instrument classes.
2. Create `base.py` with `Instrument` ABC. Define all `__slots__`, all common properties, `make_price`, `make_qty`, `calculate_notional`.
3. Implement `Equity` — add `sector: str | None`. Notional = `quantity * price`.
4. Implement `CryptoPerpetual` — add `settlement_currency`, `is_inverse`. Notional varies.
5. Implement `CurrencyPair` — add `base_currency`, `quote_currency`, `pip_size`.
6. Implement `FuturesContract` — add `underlying`, `expiry_date`, `multiplier`.
7. Implement `OptionsContract` — add `underlying`, `strike_price`, `expiry_date`, `option_type` (CALL/PUT).
8. Implement `BettingInstrument` and `PredictionMarket` — add `outcome`, `event_id`.
9. Test: create each instrument type, verify `make_price`, `make_qty`, `calculate_notional`.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
Instruments are few in number (tens to hundreds, not millions). Created once and reused. No hot loop touches instrument creation. Pure Python is fine.

---

### Step 2.3: `model/orders/` (Order Types & FSM)

**Where it will be used:**
Strategies create orders. The execution engine routes them. The matching engine fills them. Every order follows a state machine from `INITIALIZED` → `SUBMITTED` → `ACCEPTED` → `FILLED` (or `CANCELED`, `REJECTED`, etc.).

**What it should contain and the logic:**

```
model/orders/
├── __init__.py
├── base.py        # Order ABC + FSM logic
├── market.py      # MarketOrder
├── limit.py       # LimitOrder
├── stop_market.py # StopMarketOrder
├── stop_limit.py  # StopLimitOrder
└── factory.py     # OrderFactory
```

```python
class Order(ABC):
    __slots__ = (
        "_trader_id", "_strategy_id", "_instrument_id",
        "_client_order_id", "_venue_order_id", "_account_id",
        "_order_side", "_order_type", "_quantity", "_filled_qty",
        "_time_in_force", "_status",
        "_ts_init", "_ts_last",
        "_avg_px", "_events",
    )

    def __init__(self, ...):
        self._status = OrderStatus.INITIALIZED
        self._filled_qty = Quantity(0, quantity.precision)
        self._events: list[Event] = []

    def apply(self, event: OrderEvent) -> None:
        """Apply an event to transition the order's state (FSM)."""
        new_status = self._STATUS_MAP[type(event)]
        if new_status not in ORDER_STATUS_TRANSITIONS[self._status]:
            raise InvalidStateTransition(f"{self._status} → {new_status}")
        self._status = new_status
        self._events.append(event)
        self._apply_event(event)  # update fields (avg_px, filled_qty, etc.)

    _STATUS_MAP = {
        OrderSubmitted: OrderStatus.SUBMITTED,
        OrderAccepted: OrderStatus.ACCEPTED,
        OrderFilled: OrderStatus.FILLED,
        OrderCanceled: OrderStatus.CANCELED,
        ...
    }
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Finite State Machine (FSM)** | Orders have a lifecycle: they can't go from `FILLED` back to `INITIALIZED`. The FSM table in `core/enums.py` + the `apply()` method guarantee only valid transitions occur. This catches bugs like "trying to cancel an already-filled order" at the framework level, not in user strategy code. |
| **`apply(event)` pattern** | This is **event sourcing**. Instead of `order.status = FILLED`, you `order.apply(OrderFilled(...))`. The event is recorded in `_events`. You can reconstruct the full order history by replaying events. This is invaluable for debugging ("why was this order canceled?"). |
| **`__slots__`** | Orders are numerous (thousands in a long backtest). Memory matters. |
| **`_filled_qty` separate from `_quantity`** | Orders can be partially filled. `_quantity` is the requested quantity, `_filled_qty` is how much has actually been filled. The remaining quantity is `_quantity - _filled_qty`. |
| **`_avg_px` tracking** | For partial fills, the average fill price must be computed incrementally: `new_avg = (old_avg * old_qty + fill_px * fill_qty) / new_total_qty`. |
| **ABC with concrete subclasses** | `MarketOrder` has no price field. `LimitOrder` has a `price`. `StopMarketOrder` has a `trigger_price`. `StopLimitOrder` has both. Using separate classes instead of optional fields makes the API type-safe. |

**`OrderFactory`:**
```python
class OrderFactory:
    def __init__(self, trader_id: TraderId, strategy_id: StrategyId):
        self._trader_id = trader_id
        self._strategy_id = strategy_id
        self._counter = 0

    def market(self, instrument_id, side, quantity, ts_init) -> MarketOrder:
        self._counter += 1
        client_order_id = ClientOrderId(f"O-{self._strategy_id}-{self._counter}")
        return MarketOrder(...)
```

**Instructions:**
1. Create `model/orders/__init__.py`.
2. Implement `Order` ABC in `base.py` with `__slots__`, `apply()` method, FSM validation, event recording.
3. Implement `MarketOrder(Order)` in `market.py` — no price field.
4. Implement `LimitOrder(Order)` in `limit.py` — adds `_price` slot.
5. Implement `StopMarketOrder` in `stop_market.py` — adds `_trigger_price`.
6. Implement `StopLimitOrder` in `stop_limit.py` — adds `_trigger_price` and `_price`.
7. Implement `OrderFactory` in `factory.py` — generates unique `ClientOrderId`s.
8. Test FSM: verify every valid transition works, every invalid transition raises.

**🦀 C++/Rust Optimization Verdict: ⚠️ MAYBE (Phase 3)**
The FSM `apply()` method is called on every order event. If you have thousands of concurrent orders with frequent partial fills, this can add up. But typically orders are fewer than ticks by orders of magnitude. Optimize only if profiling shows it.

---

### Step 2.4: `model/position.py`

**Where it will be used:**
The portfolio tracks positions. PnL is computed per position. Risk engine checks position limits. Strategies query open positions.

**What it should contain and the logic:**

```python
class Position:
    __slots__ = (
        "_id", "_instrument_id", "_strategy_id", "_account_id",
        "_side", "_quantity", "_signed_qty",
        "_avg_entry_price", "_avg_close_price",
        "_realized_pnl", "_commission_total",
        "_ts_opened", "_ts_closed",
        "_events",
    )

    def apply(self, fill: OrderFilled) -> None:
        """Apply a fill event to update the position."""
        if self.is_closed:
            raise PositionError("Cannot apply fill to closed position")

        if fill.order_side == OrderSide.BUY:
            new_signed_qty = self._signed_qty + fill.last_qty.value
        else:
            new_signed_qty = self._signed_qty - fill.last_qty.value

        # If sign changes → close existing + open reverse
        # If zero → position closed
        # Compute realized PnL for closing portion
        ...
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Event-sourced (same as Order)** | `position.apply(fill)` updates the position state. You can reconstruct position history by replaying fills. |
| **`_signed_qty`** | Positive = LONG, negative = SHORT. This simplifies PnL calculation: `unrealized_pnl = signed_qty * (current_price - avg_entry_price)`. One formula works for both sides. |
| **Realized vs unrealized PnL** | Realized = profit from closed portions. Unrealized = paper profit from open portion. Total PnL = realized + unrealized. You need both for accurate portfolio accounting. |
| **NETTING vs HEDGING** | Under NETTING, one position per instrument. Under HEDGING, each order opens a separate position. Your `Position` class handles NETTING (net quantity). For HEDGING, the portfolio manages multiple `Position` objects per instrument. |

**Instructions:**
1. Create `model/position.py`.
2. Implement `Position` with `__slots__`, `apply(fill)`, PnL computation.
3. Properties: `is_open`, `is_closed`, `side`, `quantity`, `unrealized_pnl(current_price)`, `realized_pnl`, `total_pnl(current_price)`.
4. Test: open long, fill partially, close remaining. Verify PnL at each step.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
Positions are few (one per instrument per strategy in NETTING mode). Not a hot path.

---

## Phase 3 — State Management Layer (`state/`)

---

### Step 3.1: `state/cache.py`

**Where it will be used:**
Everything queries the cache: strategies ask "what instruments exist?", the execution engine asks "what account is this venue using?", the portfolio asks "what are the open positions?". It's the single source of truth for all state.

**What it should contain and the logic:**

```python
class Cache:
    def __init__(self):
        self._instruments: dict[InstrumentId, Instrument] = {}
        self._orders: dict[ClientOrderId, Order] = {}
        self._positions: dict[PositionId, Position] = {}
        self._accounts: dict[AccountId, Account] = {}
        self._bars: dict[BarType, list[Bar]] = defaultdict(list)

    # ── Add ──
    def add_instrument(self, instrument: Instrument) -> None: ...
    def add_order(self, order: Order) -> None: ...
    def add_position(self, position: Position) -> None: ...
    def add_account(self, account: Account) -> None: ...
    def add_bar(self, bar: Bar) -> None: ...

    # ── Query ──
    def instrument(self, instrument_id: InstrumentId) -> Instrument | None: ...
    def order(self, client_order_id: ClientOrderId) -> Order | None: ...
    def orders(self, instrument_id: InstrumentId = None, strategy_id: StrategyId = None) -> list[Order]: ...
    def open_orders(self, ...) -> list[Order]: ...
    def positions(self, instrument_id: InstrumentId = None) -> list[Position]: ...
    def open_positions(self, ...) -> list[Position]: ...
    def bars(self, bar_type: BarType) -> list[Bar]: ...
    def bar_count(self, bar_type: BarType) -> int: ...
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Centralized cache** | Without a cache, every component would need to know about every other component's internal data structures. The cache is the **Repository pattern** — a single interface for all state queries. |
| **Dictionary-based** | `O(1)` lookup by identifier. When the matching engine needs to find an order by `ClientOrderId`, it's one hash lookup, not a list scan. |
| **Filtered query methods** | `open_orders(instrument_id=..., strategy_id=...)` lets you ask "what are strategy X's open orders on instrument Y?" without scanning everything. |
| **No setter methods — only `add_*`** | The cache doesn't modify objects. It stores them. The objects themselves are updated via their `apply()` methods. This prevents the cache from becoming a "God object". |

**Instructions:**
1. Create `state/__init__.py` and `state/cache.py`.
2. Implement all `add_*` methods with validation (no duplicates).
3. Implement all query methods with optional filters.
4. Test: add instruments, orders, positions. Query with various filter combinations.

**🦀 C++/Rust Optimization Verdict: ⚠️ MAYBE (Phase 3)**
If you have tens of thousands of orders/positions (e.g., high-frequency strategies), the dictionary lookups and filtered queries can become slow. Rust `HashMap` is faster than Python `dict` for large collections. But for typical backtesting (hundreds to thousands of orders), Python is fine.

---

### Step 3.2: `state/portfolio.py`

**Where it will be used:**
Strategies query `portfolio.net_exposure(venue)`, `portfolio.unrealized_pnl(instrument_id)`. The risk engine queries total exposure to enforce limits. The results module queries final PnL.

**What it should contain and the logic:**

```python
class Portfolio:
    def __init__(self, cache: Cache):
        self._cache = cache

    def net_position(self, instrument_id: InstrumentId) -> Decimal: ...
    def net_exposure(self, instrument_id: InstrumentId, current_price: Price) -> Money: ...
    def unrealized_pnl(self, instrument_id: InstrumentId, current_price: Price) -> Money: ...
    def realized_pnl(self, instrument_id: InstrumentId) -> Money: ...
    def total_pnl(self, instrument_id: InstrumentId, current_price: Price) -> Money: ...
    def account(self, venue: Venue) -> Account: ...
    def balances(self, venue: Venue) -> dict[Currency, AccountBalance]: ...
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Depends on Cache, not on raw data** | The Portfolio doesn't own positions — it queries them from the Cache. This means the Cache is always the authoritative source. |
| **Per-instrument PnL** | You need to see PnL broken down by instrument for analysis. "Did BTC or ETH lose money?" |
| **Per-venue balances** | Each venue has its own account. `portfolio.balances(Venue("BINANCE"))` shows your Binance balance. |

**Instructions:**
1. Create `state/portfolio.py`.
2. Implement PnL computations using positions from cache.
3. Implement exposure calculations.
4. Test: set up cache with positions at known prices, verify PnL calculations.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
Portfolio queries are low-frequency (once per bar, not per tick).

---

## Phase 4 — Engine Layer (`engine/`)

The engines are the "verbs" — they *do things*. Each engine has a single responsibility.

---

### Step 4.1: `engine/matching_engine.py`

**Where it will be used:**
Each simulated exchange has a matching engine. When a bar/tick arrives, the matching engine checks all open orders against it to determine which should be filled. This is the heart of order simulation.

**What it should contain and the logic:**

```python
class OrderMatchingEngine:
    def __init__(self, instrument: Instrument, fill_model: FillModel):
        self._instrument = instrument
        self._fill_model = fill_model
        self._open_orders: list[Order] = []
        self._last_bid: Price | None = None
        self._last_ask: Price | None = None

    def process_bar(self, bar: Bar) -> list[OrderFilled]:
        """Check all open orders against this bar's OHLC range."""
        fills = []
        for order in self._open_orders[:]:  # iterate copy
            fill = self._try_fill(order, bar)
            if fill:
                fills.append(fill)
                self._open_orders.remove(order)
        return fills

    def _try_fill(self, order: Order, bar: Bar) -> OrderFilled | None:
        if isinstance(order, MarketOrder):
            fill_price = self._fill_model.market_fill_price(bar, order.order_side)
            return self._create_fill(order, fill_price, order.quantity)

        elif isinstance(order, LimitOrder):
            if order.order_side == OrderSide.BUY and bar.low.value <= order.price.value:
                return self._create_fill(order, order.price, order.quantity)
            elif order.order_side == OrderSide.SELL and bar.high.value >= order.price.value:
                return self._create_fill(order, order.price, order.quantity)

        elif isinstance(order, StopMarketOrder):
            if order.order_side == OrderSide.BUY and bar.high.value >= order.trigger_price.value:
                fill_price = self._fill_model.stop_fill_price(bar, order)
                return self._create_fill(order, fill_price, order.quantity)
            elif order.order_side == OrderSide.SELL and bar.low.value <= order.trigger_price.value:
                fill_price = self._fill_model.stop_fill_price(bar, order)
                return self._create_fill(order, fill_price, order.quantity)
        return None
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Separate `MatchingEngine` from `SimulatedExchange`** | The exchange handles connection, account management, order routing. The matching engine handles ONLY price matching. Separation of concerns. You can swap matching engines (e.g., realistic vs optimistic) without changing the exchange. |
| **`FillModel` injection** | Different fill models: `MidFill` (fill at bar midpoint), `WorstFill` (fill at worst price in bar range — pessimistic), `SlippageFill` (add random slippage). Inject via constructor for easy testing and swapping. |
| **Iterate copy of `_open_orders`** | You're removing from the list while iterating. Iterating `self._open_orders[:]` (a shallow copy) prevents `RuntimeError: list modified during iteration`. |
| **Bar-based matching** | For each bar, check: did the price range [low, high] touch the order's trigger/limit price? If yes → fill. This is the standard bar-level simulation approach. |

**Instructions:**
1. Create `engine/__init__.py` and `engine/matching_engine.py`.
2. Implement `OrderMatchingEngine` with `process_bar`, `process_quote_tick`, `add_order`, `cancel_order`.
3. Implement fill logic for each order type (market, limit, stop_market, stop_limit).
4. Inject `FillModel` (implement in Phase 5, Step 5.1).
5. Test: create a limit buy at $100, feed a bar with low=$99, verify fill at $100. Create a limit buy at $100, feed a bar with low=$101, verify NO fill.

**🦀 C++/Rust Optimization Verdict: ✅ HIGHEST VALUE**
The matching engine is the **#1 hot loop** in the entire system. For every bar, it iterates all open orders and does price comparisons. For strategies with many pending orders (e.g., market making with 50 limit orders), this runs 50+ comparisons per bar × millions of bars = billions of comparisons. Rust implementation with:
- `Vec<Order>` in contiguous memory
- `Decimal` comparisons via `rust_decimal`
- Zero Python overhead in the inner loop
Expected speedup: **50-200x** for order-heavy strategies.

---

### Step 4.2: `engine/data_engine.py`

**Where it will be used:**
The backtest engine feeds bars/ticks into the DataEngine. The DataEngine distributes them to subscribed strategies via the MessageBus. It also stores them in the Cache for historical lookups.

**What it should contain and the logic:**

```python
class DataEngine:
    def __init__(self, cache: Cache, msgbus: MessageBus):
        self._cache = cache
        self._msgbus = msgbus
        self._bar_subscriptions: dict[BarType, list[Callable]] = defaultdict(list)

    def process_bar(self, bar: Bar) -> None:
        self._cache.add_bar(bar)
        topic = f"data.bars.{bar.bar_type.instrument_id}"
        self._msgbus.publish(topic, bar)

    def subscribe_bars(self, bar_type: BarType, handler: Callable) -> None:
        self._bar_subscriptions[bar_type].append(handler)
        topic = f"data.bars.{bar_type.instrument_id}"
        self._msgbus.subscribe(topic, handler)
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **MessageBus for distribution** | The DataEngine doesn't need to know which strategies exist. It publishes to topics. Strategies subscribe to the topics they care about. Adding a new strategy requires zero changes to the DataEngine. |
| **Cache storage** | Strategies may need historical bars (e.g., "give me the last 20 bars for SMA calculation"). The cache stores them. |
| **Topic naming convention** | `"data.bars.BTC/USDT.BINANCE"` — hierarchical, human-readable, filterable. |

**Instructions:**
1. Create `engine/data_engine.py`.
2. Implement `process_bar`, `process_quote_tick`, `process_trade_tick`.
3. Implement `subscribe_bars`, `subscribe_quote_ticks`, `subscribe_trade_ticks`.
4. Test: subscribe a mock handler, process a bar, verify handler was called with the bar.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
The DataEngine is a thin routing layer. The bottleneck is in handlers (strategies, matching engines), not in dispatch.

---

### Step 4.3: `engine/execution_engine.py`

**Where it will be used:**
Strategies submit orders → Execution Engine routes them to the correct venue's matching engine. Fill events come back from the matching engine → Execution Engine updates orders in cache and publishes events.

**What it should contain and the logic:**

```python
class ExecutionEngine:
    def __init__(self, cache: Cache, msgbus: MessageBus, risk_engine: RiskEngine):
        self._cache = cache
        self._msgbus = msgbus
        self._risk_engine = risk_engine
        self._venues: dict[Venue, SimulatedExchange] = {}
        self._oms_types: dict[Venue, OmsType] = {}

    def register_venue(self, venue: Venue, exchange: SimulatedExchange, oms_type: OmsType): ...

    def submit_order(self, order: Order) -> None:
        # 1. Pre-trade risk check
        if not self._risk_engine.check_order(order):
            self._deny_order(order, "Risk check failed")
            return
        # 2. Add to cache
        self._cache.add_order(order)
        # 3. Route to correct venue
        venue = order.instrument_id.venue
        exchange = self._venues[venue]
        exchange.process_order(order)

    def process_event(self, event: OrderEvent) -> None:
        """Handle events coming back from the venue."""
        order = self._cache.order(event.client_order_id)
        order.apply(event)
        # Publish to strategy via msgbus
        self._msgbus.publish(f"events.order.{event.strategy_id}", event)
        # If filled, update/create position
        if isinstance(event, OrderFilled):
            self._update_position(event)
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Risk check before routing** | Pre-trade risk controls prevent disasters: max order size, max position, insufficient balance. The risk engine has veto power. |
| **Venue routing by `instrument_id.venue`** | `InstrumentId` contains the venue. `BTC/USDT.BINANCE` → routes to the BINANCE exchange. `AAPL.NASDAQ` → routes to NASDAQ. Automatic, no manual mapping needed. |
| **Event processing updates cache + publishes** | When a fill comes back, the execution engine (1) updates the order state, (2) updates/creates positions, (3) publishes the event so the strategy can react. |
| **Position management by OMS type** | Under NETTING: one position per instrument, fills aggregate. Under HEDGING: each order's fill creates a new position. The OMS type determines the logic. |

**Instructions:**
1. Create `engine/execution_engine.py`.
2. Implement `submit_order`, `cancel_order`, `modify_order`.
3. Implement `process_event` for all event types.
4. Implement `_update_position` with NETTING and HEDGING logic.
5. Test: submit a market order, verify it reaches the exchange. Simulate a fill event, verify position is created.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
Execution events are order-frequency (hundreds to thousands), not tick-frequency.

---

### Step 4.4: `engine/risk_engine.py`

**Where it will be used:**
Called by the execution engine before every order submission. Can also be called by the portfolio for continuous monitoring.

**What it should contain and the logic:**

```python
class RiskEngine:
    def __init__(self, portfolio: Portfolio, cache: Cache, msgbus: MessageBus):
        self._portfolio = portfolio
        self._cache = cache
        self._msgbus = msgbus
        self._max_order_size: dict[InstrumentId, Quantity] = {}
        self._max_position_size: dict[InstrumentId, Quantity] = {}
        self._max_notional: dict[Venue, Money] = {}

    def check_order(self, order: Order) -> bool:
        """Return True if order passes all risk checks."""
        if not self._check_order_size(order): return False
        if not self._check_position_limit(order): return False
        if not self._check_sufficient_balance(order): return False
        return True

    def set_max_order_size(self, instrument_id: InstrumentId, max_qty: Quantity): ...
    def set_max_position_size(self, instrument_id: InstrumentId, max_qty: Quantity): ...
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Centralized risk checks** | Without this, every strategy would need to check its own risk limits. That's error-prone and violates separation of concerns. A single risk engine enforces limits globally. |
| **Per-instrument limits** | BTC might have a max position of 10 coins; AAPL might have 10000 shares. Different instruments, different limits. |
| **Returns `bool`, doesn't raise** | The risk engine advises; it doesn't crash the system. A denied order generates a `OrderDenied` event, not an exception. |

**Instructions:**
1. Create `engine/risk_engine.py`.
2. Implement `check_order` with configurable limits.
3. Implement balance checks (query portfolio + cache for account balances).
4. Test: set max order size to 100, submit order for 200, verify denied.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
Risk checks are order-frequency and simple comparisons.

---

## Phase 5 — Venue Layer (`venues/`)

---

### Step 5.1: `venues/models.py`

**Where it will be used:**
The matching engine and simulated exchange use these models to compute realistic fills, fees, slippage, and latency.

**What it should contain and the logic:**

```python
from abc import ABC, abstractmethod

class FillModel(ABC):
    @abstractmethod
    def market_fill_price(self, bar: Bar, side: OrderSide) -> Price: ...
    @abstractmethod
    def stop_fill_price(self, bar: Bar, order: StopMarketOrder) -> Price: ...

class MidFillModel(FillModel):
    """Fill at midpoint of bar's range."""
    def market_fill_price(self, bar, side):
        mid = (bar.high.value + bar.low.value) / 2
        return Price(mid, bar.open.precision)

class WorstFillModel(FillModel):
    """Fill at worst price (pessimistic)."""
    def market_fill_price(self, bar, side):
        if side == OrderSide.BUY:
            return bar.high   # you buy at the highest price
        return bar.low        # you sell at the lowest price

class FeeModel(ABC):
    @abstractmethod
    def compute_fee(self, order: Order, fill_price: Price, fill_qty: Quantity,
                    instrument: Instrument, liquidity_side: LiquiditySide) -> Money: ...

class PercentageFeeModel(FeeModel):
    def __init__(self, maker_fee: Decimal, taker_fee: Decimal): ...
    def compute_fee(self, ...):
        rate = self._maker_fee if liquidity_side == LiquiditySide.MAKER else self._taker_fee
        notional = fill_qty.value * fill_price.value
        return Money(notional * rate, instrument.quote_currency)

class SlippageModel(ABC):
    @abstractmethod
    def apply_slippage(self, price: Price, side: OrderSide) -> Price: ...

class FixedSlippageModel(SlippageModel):
    def __init__(self, slippage_ticks: int = 1): ...

class LatencyModel:
    def __init__(self, base_latency_ns: int = 0, jitter_ns: int = 0): ...
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **ABC + concrete implementations** | The **Strategy pattern** (the design pattern, not a trading strategy). You define the interface, then provide multiple implementations. The exchange doesn't care *which* fill model it uses — it just calls `fill_model.market_fill_price()`. |
| **Worst-case fill model** | Backtesting often over-estimates performance because it fills at unrealistic prices. The `WorstFillModel` gives you a pessimistic lower bound. If your strategy is profitable with worst-case fills, it's likely profitable in reality. |
| **Slippage model** | Real exchanges have slippage — your fill price is worse than expected because of order book dynamics. Modeling this prevents overoptimistic backtests. |
| **Latency model** | In live trading, orders take time to reach the exchange. Simulating latency prevents strategies that depend on impossible execution speed. |

**Instructions:**
1. Create `venues/__init__.py` and `venues/models.py`.
2. Implement `FillModel` ABC + `MidFillModel`, `WorstFillModel`.
3. Implement `FeeModel` ABC + `PercentageFeeModel`, `FlatFeeModel`.
4. Implement `SlippageModel` ABC + `FixedSlippageModel`, `VolumeSlippageModel`.
5. Implement `LatencyModel` with configurable base + jitter.
6. Test: verify MidFill computes correct midpoint, WorstFill returns high/low, fees are correct.

**🦀 C++/Rust Optimization Verdict: ⚠️ MAYBE**
Fill models are called per-order, not per-tick. Usually not a bottleneck, unless you have a market-making strategy with thousands of orders per bar.

---

### Step 5.2: `venues/account.py`

**Where it will be used:**
Each venue has an account tracking balances, margin, and leverage. The execution engine updates it on fills. The portfolio queries it.

**What it should contain and the logic:**

```python
class Account(ABC):
    __slots__ = ("_id", "_base_currency", "_balances", "_events")

    def __init__(self, account_id: AccountId, base_currency: Currency):
        self._id = account_id
        self._base_currency = base_currency
        self._balances: dict[Currency, AccountBalance] = {}
        self._events: list = []

    def update_balance(self, currency: Currency, total: Decimal, locked: Decimal): ...
    def balance(self, currency: Currency) -> AccountBalance | None: ...
    def total_balance(self, currency: Currency) -> Money: ...
    def free_balance(self, currency: Currency) -> Money: ...

class CashAccount(Account):
    """No leverage. Balance = what you have."""
    def sufficient_balance(self, order: Order, price: Price) -> bool:
        required = order.quantity.value * price.value
        free = self.free_balance(order_currency).amount
        return free >= required

class MarginAccount(Account):
    """Leveraged trading. Margin = collateral."""
    __slots__ = Account.__slots__ + ("_leverage",)

    def __init__(self, account_id, base_currency, leverage: Decimal = Decimal("1")): ...
    def margin_required(self, quantity: Quantity, price: Price) -> Money:
        notional = quantity.value * price.value
        return Money(notional / self._leverage, self._base_currency)
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Separate Cash and Margin accounts** | A cash account (equities) and margin account (crypto perps, FX) have completely different balance logic. Cash: you need the full amount. Margin: you need only `notional / leverage`. |
| **Multi-currency balances** | A Binance account might hold USD, BTC, ETH simultaneously. The `_balances` dict maps `Currency → AccountBalance`. |
| **`AccountBalance` with total/locked/free** | When you place a limit buy order, the required funds are *locked* (reserved). `free = total - locked`. This prevents over-spending. |

**Instructions:**
1. Create `venues/account.py`.
2. Implement `Account` ABC, `CashAccount`, `MarginAccount`.
3. Implement `BettingAccount` for prediction markets (balance is number of contracts).
4. Test: update balance, lock funds, verify free balance decreases.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
Account operations are order-frequency.

---

### Step 5.3: `venues/simulated_exchange.py`

**Where it will be used:**
Each venue in the backtest has a `SimulatedExchange`. It receives orders from the execution engine, passes them to its matching engine, and returns fill events.

**What it should contain and the logic:**

```python
class SimulatedExchange:
    def __init__(self, venue, oms_type, account_type, base_currency,
                 starting_balances, exec_engine, default_leverage,
                 fill_model=None, fee_model=None, slippage_model=None):
        self.venue = venue
        self.oms_type = oms_type
        self.account = self._create_account(...)
        self._matching_engines: dict[InstrumentId, OrderMatchingEngine] = {}
        self._fill_model = fill_model or MidFillModel()
        self._fee_model = fee_model or PercentageFeeModel(Decimal("0.001"), Decimal("0.001"))

    def add_instrument(self, instrument: Instrument) -> None:
        self._matching_engines[instrument.id] = OrderMatchingEngine(instrument, self._fill_model)

    def process_order(self, order: Order) -> None:
        engine = self._matching_engines[order.instrument_id]
        engine.add_order(order)
        # Accept event
        ...

    def process_bar(self, bar: Bar) -> None:
        engine = self._matching_engines.get(bar.bar_type.instrument_id)
        if engine:
            fills = engine.process_bar(bar)
            for fill in fills:
                fee = self._fee_model.compute_fee(...)
                self.account.update_balance(...)
                self._exec_engine.process_event(fill)
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **One `OrderMatchingEngine` per instrument** | Each instrument has its own order book in reality. Separating matching engines per instrument prevents cross-contamination and makes the code cleaner. |
| **Composable models** | `fill_model`, `fee_model`, `slippage_model` are injected. You can configure each venue independently: Binance with 0.1% fees, NASDAQ with 0.01% fees. |
| **`process_bar` on the exchange** | The backtest engine calls `exchange.process_bar(bar)` on every bar. The exchange delegates to the matching engine. This keeps the backtest loop clean. |

**Instructions:**
1. Create `venues/simulated_exchange.py`.
2. Wire together `Account`, `OrderMatchingEngine`, `FillModel`, `FeeModel`.
3. Implement `process_order`, `process_bar`, `cancel_order`.
4. Handle account balance updates on fills.
5. Test: add instrument, submit order, process bar, verify fill + balance update.

**🦀 C++/Rust Optimization Verdict: ⚠️ MAYBE**
The exchange orchestrates but doesn't do heavy computation itself. The matching engine inside it is the hot spot (covered in Step 4.1).

---

## Phase 6 — Trading Layer (`trading/`)

---

### Step 6.1: `trading/config.py`

**Where it will be used:**
Every strategy has a `Config` inner class for parameters. The optimization layer iterates over config permutations.

```python
class StrategyConfig:
    """Base config. Users extend with their own parameters."""
    strategy_id: str | None = None
    order_id_tag: str = ""

    def __init_subclass__(cls, **kwargs):
        """Auto-register all config fields for serialization/optimization."""
        super().__init_subclass__(**kwargs)
```

**Instructions:**
1. Create `trading/config.py`.
2. Use `dataclass` or plain class with `__init_subclass__` for auto-discovery of parameters.
3. Support serialization to/from dict (for optimization parameter sweeps).

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**

---

### Step 6.2: `trading/strategy.py`

**Where it will be used:**
This is the class users subclass to write their trading logic. The most important API in the framework.

**What it should contain and the logic:**

```python
class Strategy:
    def __init__(self, config: StrategyConfig | None = None):
        self.config = config or StrategyConfig()
        self.id = StrategyId(self.config.strategy_id or type(self).__name__)
        self.clock = None
        self.cache = None
        self.portfolio = None
        self._indicators: list = []

    def register(self, clock, cache, portfolio, msgbus, order_factory, exec_engine, data_engine): ...

    # ── User overrides ──
    def on_start(self) -> None: ...
    def on_bar(self, bar: Bar) -> None: ...
    def on_quote_tick(self, tick: QuoteTick) -> None: ...
    def on_trade_tick(self, tick: TradeTick) -> None: ...
    def on_order_filled(self, event: OrderFilled) -> None: ...
    def on_position_opened(self, event: PositionOpened) -> None: ...
    def on_position_closed(self, event: PositionClosed) -> None: ...
    def on_stop(self) -> None: ...

    # ── Convenience methods ──
    def buy(self, instrument_id, quantity=None, size=None, price=None) -> Order: ...
    def sell(self, instrument_id, quantity=None, size=None, price=None) -> Order: ...
    def close_position(self, instrument_id) -> None: ...
    def close_all_positions(self) -> None: ...

    # ── Indicator registration (Backtesting.py-style) ──
    def I(self, func_or_indicator, *args, **kwargs):
        """Register an indicator. Works with built-in Indicator classes or any callable."""
        ...
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **`register()` injection** | The strategy doesn't create its own clock, cache, etc. The engine injects them. This is **Dependency Injection** — the strategy is decoupled from infrastructure. Same strategy code works in backtest and live. |
| **`on_bar` / `on_quote_tick` / `on_trade_tick`** | Three different data granularities. A strategy can override whichever it needs. Most strategies use `on_bar`. HFT strategies use `on_quote_tick`. |
| **`on_order_filled` / `on_position_opened`** | Event hooks. Strategies can react to execution events. E.g., "when my entry order is filled, place a stop loss." |
| **`buy()` / `sell()` convenience** | Instead of manually creating `MarketOrder` objects, users call `self.buy(instrument_id, size=0.95)`. The method handles order creation, quantity calculation (95% of equity), and submission. This is the **Backtesting.py simplicity**. |
| **`self.I()` for indicators** | Borrowed from Backtesting.py. `self.I(SMA, self.data.Close, 20)` registers an SMA indicator. The framework auto-feeds bars to it. Users don't need to manually call `indicator.handle_bar()`. |
| **`size` parameter (fractional)** | `size=0.95` means "use 95% of available equity". The framework computes the actual quantity based on current price and account balance. Intuitive API. |

**Instructions:**
1. Create `trading/strategy.py`.
2. Implement `register()` — store all dependencies, subscribe to events via msgbus.
3. Implement all `on_*` lifecycle methods as no-ops (users override them).
4. Implement `buy()`, `sell()` with both `quantity` (exact) and `size` (fractional) modes.
5. Implement `self.I()` — accepts `Indicator` instances or callables.
6. Implement `submit_order()`, `cancel_order()` that delegate to the execution engine.
7. Implement `subscribe_bars()`, `subscribe_quote_ticks()` that delegate to the data engine.
8. Test: create a mock strategy, verify `on_bar` is called when engine publishes a bar.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
Strategy logic is user-written Python. You can't optimize it without forcing users to write Rust.

---

### Step 6.3: `trading/actor.py`

**Where it will be used:**
Actors are non-trading components that participate in the event system. Examples: a logging actor, a data recording actor, a signal-generating actor. They receive events but don't place orders.

**What it should contain:**
A stripped-down version of `Strategy` without order-related methods.

**Instructions:**
1. Create `trading/actor.py`.
2. Implement `Actor` with `register()`, `on_bar()`, `on_data()`, but no `buy()`/`sell()`.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**

---

## Phase 7 — Indicator Layer (`indicators/`)

---

### Step 7.1: `indicators/base.py`

**What it should contain:**

```python
class Indicator(ABC):
    __slots__ = ("_name", "_initialized", "_count", "_values")

    def __init__(self, name: str, period: int = 0):
        self._name = name
        self._initialized = False
        self._count = 0
        self._values: list[float] = []  # use float for speed in indicator math

    @abstractmethod
    def handle_bar(self, bar: Bar) -> None: ...

    @property
    def value(self) -> float:
        """Most recent value."""
        return self._values[-1] if self._values else 0.0

    def __getitem__(self, index: int) -> float:
        """Negative indexing: self[-1] = most recent, self[-2] = previous."""
        return self._values[index]
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **`float` instead of `Decimal` for indicator values** | Indicators compute averages, exponential smoothing, etc. Exact decimal precision is NOT needed here (unlike prices). Using `float` makes indicator computation 10-50x faster than `Decimal` and enables numpy vectorization. |
| **`__getitem__` with negative indexing** | Strategies write `if self.ema[-1] > self.sma[-1]`. This is the Backtesting.py convention. Negative indices access from the end of the values list. |
| **`_values` list** | Store all computed values so you can do lookups like "EMA value 5 bars ago". The alternative (only storing current value) prevents multi-bar conditions like "EMA rising for 3 consecutive bars". |

**Instructions:**
1. Create `indicators/__init__.py` and `indicators/base.py`.
2. Implement `Indicator` ABC with `handle_bar`, `value`, `__getitem__`, `reset`.
3. Implement `indicators/sma.py` — Simple Moving Average.
4. Implement `indicators/ema.py` — Exponential Moving Average.
5. Implement `indicators/atr.py` — Average True Range.
6. Test each indicator against known correct values (compute by hand or compare with `pandas`/`talib`).

### Step 7.2: `indicators/wrapper.py`

**What it should contain:**

```python
class IndicatorWrapper:
    """Wraps any callable as an indicator, for self.I() support."""
    def __init__(self, func: Callable, *args, **kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._values: np.ndarray | None = None

    def compute(self, data: pd.Series) -> np.ndarray:
        self._values = self._func(data, *self._args, **self._kwargs)
        return self._values
```

**Why this design:**
Supports `self.I(talib.SMA, self.data.Close, 20)` — any function that takes a series and returns a series. Library-agnostic.

**🦀 C++/Rust Optimization Verdict: ✅ HIGH VALUE for built-in indicators**
Built-in indicators (SMA, EMA, ATR, Bollinger Bands, RSI, MACD) are computed on every bar. For 1M bars × 5 indicators = 5M computations. Rust implementations using `rust_decimal` or just `f64` in tight loops would be 20-50x faster. Expose via PyO3. TA-Lib already does this in C — consider wrapping TA-Lib via FFI as an alternative.

---

## Phase 8 — Data Layer (`data/`)

---

### Step 8.1: `data/wranglers.py`

**Where it will be used:**
Users load CSV/Parquet files and convert them to `Bar`, `QuoteTick`, `TradeTick` objects.

```python
class BarDataWrangler:
    def __init__(self, bar_type: BarType, price_precision: int = 2, size_precision: int = 0):
        self._bar_type = bar_type
        self._price_precision = price_precision
        self._size_precision = size_precision

    def from_pandas(self, df: pd.DataFrame) -> list[Bar]:
        """Convert a DataFrame with columns [open, high, low, close, volume, timestamp] to Bars."""
        bars = []
        for _, row in df.iterrows():
            bar = Bar(
                bar_type=self._bar_type,
                open=Price(row["open"], self._price_precision),
                high=Price(row["high"], self._price_precision),
                close=Price(row["close"], self._price_precision),
                low=Price(row["low"], self._price_precision),
                volume=Quantity(row["volume"], self._size_precision),
                ts_event=int(row["timestamp"]),
                ts_init=int(row["timestamp"]),
            )
            bars.append(bar)
        return bars
```

**Why this design:**

| Decision | Reason |
|----------|--------|
| **Wranglers separate from data classes** | `Bar` is a domain object. How you *load* data is a separate concern. You might load from CSV today and from a REST API tomorrow. The wrangler adapts. |
| **`from_pandas`** | Most users have data in DataFrames. This is the easiest on-ramp. |

**Instructions:**
1. Create `data/__init__.py` and `data/wranglers.py`.
2. Implement `BarDataWrangler.from_pandas()` and `from_csv()`.
3. Implement `QuoteTickDataWrangler` and `TradeTickDataWrangler`.
4. Test: create a small DataFrame, wrangle to bars, verify values match.

### Step 8.2: `data/catalog.py`

Implement a `DataCatalog` that stores and retrieves data from Parquet files for fast re-use.

### Step 8.3: `data/providers/`

Implement `CSVProvider`, `ParquetProvider`, `APIProvider` for different data sources.

**🦀 C++/Rust Optimization Verdict: ✅ HIGH VALUE for wranglers**
Converting 1M rows from DataFrame to Bar objects is slow in Python (`iterrows` is notoriously slow). Rust with Polars (or Arrow2) can do zero-copy reads from Parquet and construct Bar objects 50-100x faster. This is a great optimization target.

---

## Phase 9 — Analysis Layer (`analysis/`)

---

### Step 9.1: `analysis/analyzer.py` + `analysis/analyzers/`

**Where it will be used:**
After a backtest, analyzers compute statistics like Sharpe ratio, max drawdown, win rate, etc.

```python
class Analyzer(ABC):
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def on_order_filled(self, event: OrderFilled) -> None: ...
    @abstractmethod
    def result(self) -> dict: ...

class SharpeRatioAnalyzer(Analyzer):
    def __init__(self, risk_free_rate: float = 0.0):
        self._returns: list[float] = []
        self._risk_free_rate = risk_free_rate

    def on_order_filled(self, event):
        ...  # track returns

    def result(self):
        returns = np.array(self._returns)
        excess = returns - self._risk_free_rate / 252
        return {"sharpe_ratio": np.mean(excess) / np.std(excess) * np.sqrt(252)}

class DrawdownAnalyzer(Analyzer):
    """Tracks equity curve and computes max drawdown."""
    ...

class TradeAnalyzer(Analyzer):
    """Computes win rate, avg win, avg loss, profit factor, etc."""
    ...
```

**Why this design (Backtrader pattern):**
- **Pluggable:** Add any analyzer without changing the engine.
- **Decoupled:** Analyzers subscribe to events; they don't need to understand engine internals.
- **Composable:** Run multiple analyzers simultaneously.

**Instructions:**
1. Create `analysis/__init__.py`, `analysis/analyzer.py`.
2. Create `analysis/analyzers/sharpe.py`, `analysis/analyzers/drawdown.py`, `analysis/analyzers/trade_analysis.py`.
3. Each analyzer subscribes to relevant events and computes its metric.
4. Test: feed known fill events, verify Sharpe ratio matches manual calculation.

### Step 9.2: `analysis/observer.py`

Observers track values over time (equity curve, cash balance, position count). Used for visualization.

### Step 9.3: `analysis/sizer.py`

Position sizing logic: `FixedSizer`, `PercentSizer`, `KellySizer`, `VolatilitySizer`.

### Step 9.4: `analysis/stats.py`

A `compute_stats()` function (Backtesting.py-style) that returns a `pd.Series` with all statistics.

```python
def compute_stats(equity_curve: pd.Series, trades: list, starting_balance: Decimal) -> pd.Series:
    return pd.Series({
        "Start": equity_curve.index[0],
        "End": equity_curve.index[-1],
        "Duration": ...,
        "Starting Balance": starting_balance,
        "Ending Balance": equity_curve.iloc[-1],
        "Return [%]": ...,
        "Sharpe Ratio": ...,
        "Max Drawdown [%]": ...,
        "Win Rate [%]": ...,
        "# Trades": len(trades),
        ...
    })
```

**🦀 C++/Rust Optimization Verdict: ⚠️ MAYBE for stats computation**
If you compute stats on millions of equity data points (tick-level), Rust/numpy vectorization helps. For bar-level (thousands of points), Python is fine.

---

## Phase 10 — Backtest Orchestration (`backtest/`)

---

### Step 10.1: `backtest/config.py`

```python
@dataclass
class VenueConfig:
    venue_name: str
    oms_type: OmsType = OmsType.NETTING
    account_type: AccountType = AccountType.CASH
    base_currency: Currency = USD
    starting_balances: list[Money] = field(default_factory=list)
    leverage: Decimal = Decimal("1")
    fill_model: FillModel | None = None
    fee_model: FeeModel | None = None

@dataclass
class BacktestConfig:
    venues: list[VenueConfig] = field(default_factory=list)
    strategies: list[tuple[type, dict]] = field(default_factory=list)
    data: list = field(default_factory=list)
    analyzers: list[type] = field(default_factory=list)
```

### Step 10.2: `backtest/engine.py`

The core kernel that wires everything together and runs the simulation loop.

```python
class BacktestEngine:
    def __init__(self, config: BacktestConfig | None = None):
        # Create all core components
        self.clock = TestClock()
        self.msgbus = MessageBus()
        self.cache = Cache()
        self.portfolio = Portfolio(self.cache)
        self.risk_engine = RiskEngine(self.portfolio, self.cache, self.msgbus)
        self.exec_engine = ExecutionEngine(self.cache, self.msgbus, self.risk_engine)
        self.data_engine = DataEngine(self.cache, self.msgbus)

        self._exchanges = {}
        self._strategies = []
        self._data = []

    def run(self) -> BacktestResult:
        # Sort all data by timestamp
        self._data.sort(key=lambda d: d.ts_event)

        # Start strategies
        for strategy in self._strategies:
            strategy.on_start()

        # Main loop: iterate through every data point chronologically
        for data_point in self._data:
            self.clock.set_time(data_point.ts_event)

            if isinstance(data_point, Bar):
                # 1. Feed bar to matching engines (fill pending orders)
                venue = data_point.bar_type.instrument_id.venue
                exchange = self._exchanges.get(venue)
                if exchange:
                    exchange.process_bar(data_point)

                # 2. Feed bar to data engine (distribute to strategies)
                self.data_engine.process_bar(data_point)

        # Stop strategies
        for strategy in self._strategies:
            strategy.on_stop()

        return self._build_result()
```

**Why the data processing order matters:**

| Step | Why this order |
|------|---------------|
| **1. Process bar in matching engine FIRST** | Pending orders from the *previous* bar must be checked against the *current* bar's OHLC range. If you distribute the bar to strategies first, a strategy might submit a new order and it would be checked against the SAME bar — unrealistic. |
| **2. Distribute bar to strategies SECOND** | Strategies see the bar AFTER pending orders are processed. This simulates reality: you can't act on data you haven't received yet. |

**Instructions:**
1. Create `backtest/__init__.py`, `backtest/config.py`, `backtest/engine.py`.
2. Implement the full wiring in `__init__`.
3. Implement `add_venue`, `add_instrument`, `add_data`, `add_strategy`.
4. Implement `run()` with the correct processing order.
5. Implement `_build_result()` using analyzers and stats.
6. Test: full end-to-end backtest with a simple buy-and-hold strategy.

### Step 10.3: `backtest/runner.py`

The simple entry point (Cerebro + Backtesting.py hybrid):

```python
class BacktestRunner:
    """High-level API for running backtests with minimal setup."""

    def __init__(self):
        self._config = BacktestConfig()
        self._engine: BacktestEngine | None = None

    def add_venue(self, name, oms="NETTING", account="CASH", cash=100_000, currency=USD, **kwargs):
        """One-liner venue setup with sensible defaults."""
        ...

    def add_data(self, data, instrument=None):
        """Accept DataFrame, CSV path, or list of Bars."""
        ...

    def add_strategy(self, strategy_cls, **params):
        """Accept strategy class + keyword params."""
        ...

    def run(self) -> BacktestResult:
        self._engine = BacktestEngine(self._config)
        return self._engine.run()

    def optimize(self, maximize="sharpe_ratio", method="grid", **param_ranges) -> pd.DataFrame:
        """Grid/Bayesian optimization over strategy parameters."""
        ...

    def plot(self):
        """Interactive Bokeh chart."""
        ...
```

### Step 10.4: `backtest/results.py`

```python
class BacktestResult:
    def __init__(self, stats: pd.Series, equity_curve: pd.Series,
                 trades: list, orders: list, positions: list):
        self.stats = stats
        self.equity_curve = equity_curve
        self.trades = trades
        self.orders = orders
        self.positions = positions

    def __repr__(self):
        return str(self.stats)

    def to_dataframe(self) -> pd.DataFrame: ...
```

**🦀 C++/Rust Optimization Verdict: ✅ HIGH VALUE for the main loop**
The `BacktestEngine.run()` main loop iterates over all data points and calls Python functions for each one. If the entire loop (data iteration + matching + event dispatch) is in Rust, you eliminate the Python per-iteration overhead. This is how NautilusTrader achieves its speed — the entire backtest loop runs in Rust. **Plan:** Keep the Python version as the "reference implementation" and add a Rust fast path in Phase 2.

---

## Phase 11 — Visualization Layer (`visualization/`)

---

### Step 11.1: `visualization/bokeh_plot.py`

Interactive candlestick chart with equity curve, trade markers, and indicator overlays using Bokeh.

### Step 11.2: `visualization/report.py`

HTML report generation combining charts + statistics table.

**🦀 C++/Rust Optimization Verdict: ❌ NOT WORTH IT**
Visualization is inherently a Python/JS domain.

---

## Phase 12 — Optimization Layer (`optimization/`)

---

### Step 12.1: `optimization/grid_search.py`

```python
def grid_search(runner: BacktestRunner, param_ranges: dict, maximize: str,
                n_jobs: int = -1) -> pd.DataFrame:
    """Exhaustive parameter grid search using multiprocessing."""
    from itertools import product
    import multiprocessing

    combos = list(product(*param_ranges.values()))
    keys = list(param_ranges.keys())

    with multiprocessing.Pool(n_jobs if n_jobs > 0 else multiprocessing.cpu_count()) as pool:
        results = pool.map(_run_single, [(runner, dict(zip(keys, c))) for c in combos])

    return pd.DataFrame(results).sort_values(maximize, ascending=False)
```

### Step 12.2: `optimization/bayesian.py`

Use `scikit-optimize` for Bayesian optimization.

### Step 12.3: `optimization/walk_forward.py`

Walk-forward analysis: split data into in-sample/out-of-sample windows, optimize on in-sample, validate on out-of-sample.

**🦀 C++/Rust Optimization Verdict: ✅ HIGH VALUE**
Optimization runs the backtest engine N times (hundreds to thousands). If each backtest run is in Rust (Phase 10 optimization), the entire optimization finishes 50-100x faster. Also, Rust's `rayon` crate provides effortless data parallelism across CPU cores, which is more efficient than Python's `multiprocessing` (no serialization overhead).

---

## Phase 13 — Live Trading Skeleton (`live/`)

Build a `LiveTradingNode` that uses `LiveClock` instead of `TestClock` and connects to real exchange APIs via adapter classes. This is a future phase — build the skeleton now, implement adapters later.

**🦀 C++/Rust Optimization Verdict: ⚠️ FOR LATENCY**
Live trading benefits from Rust for latency-critical paths: WebSocket message parsing, order submission. Use `tokio` for async I/O.

---

---

# Master Test Plan

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── data/                          # Test data files
│   ├── btc_usdt_1h_100bars.csv
│   ├── aapl_1d_252bars.csv
│   └── multi_asset_bars.parquet
│
├── unit/                          # Unit tests (one per module)
│   ├── core/
│   │   ├── test_enums.py
│   │   ├── test_identifiers.py
│   │   ├── test_objects.py
│   │   ├── test_events.py
│   │   ├── test_clock.py
│   │   └── test_msgbus.py
│   ├── model/
│   │   ├── test_data.py
│   │   ├── test_instruments.py
│   │   ├── test_orders.py
│   │   └── test_position.py
│   ├── state/
│   │   ├── test_cache.py
│   │   └── test_portfolio.py
│   ├── engine/
│   │   ├── test_matching_engine.py
│   │   ├── test_data_engine.py
│   │   ├── test_execution_engine.py
│   │   └── test_risk_engine.py
│   ├── venues/
│   │   ├── test_models.py
│   │   ├── test_account.py
│   │   └── test_simulated_exchange.py
│   ├── trading/
│   │   ├── test_strategy.py
│   │   └── test_actor.py
│   ├── indicators/
│   │   ├── test_sma.py
│   │   ├── test_ema.py
│   │   ├── test_atr.py
│   │   └── test_wrapper.py
│   ├── data/
│   │   ├── test_wranglers.py
│   │   └── test_catalog.py
│   └── analysis/
│       ├── test_sharpe.py
│       ├── test_drawdown.py
│       ├── test_trade_analysis.py
│       ├── test_sizer.py
│       └── test_stats.py
│
├── integration/                   # Integration tests (multi-component)
│   ├── test_order_lifecycle.py
│   ├── test_position_lifecycle.py
│   ├── test_multi_venue.py
│   ├── test_multi_instrument.py
│   ├── test_data_to_strategy_flow.py
│   └── test_full_backtest.py
│
├── pipeline/                      # End-to-end pipeline tests
│   ├── test_buy_and_hold.py
│   ├── test_ema_crossover.py
│   ├── test_multi_venue_arb.py
│   ├── test_optimization_grid.py
│   └── test_results_consistency.py
│
└── performance/                   # Performance benchmarks
    ├── bench_bar_processing.py
    ├── bench_matching_engine.py
    ├── bench_1m_bars.py
    └── bench_memory_usage.py
```

---

## Detailed Unit Test Specifications

### `tests/conftest.py` — Shared Fixtures

```python
import pytest
from decimal import Decimal

@pytest.fixture
def instrument_id():
    return InstrumentId(Symbol("BTC/USDT"), Venue("BINANCE"))

@pytest.fixture
def equity_instrument():
    return Equity(
        instrument_id=InstrumentId(Symbol("AAPL"), Venue("NASDAQ")),
        quote_currency=USD,
        price_precision=2,
        size_precision=0,
        taker_fee=Decimal("0.0001"),
    )

@pytest.fixture
def crypto_instrument():
    return CryptoPerpetual(
        instrument_id=InstrumentId(Symbol("BTC/USDT"), Venue("BINANCE")),
        quote_currency=USDT,
        settlement_currency=USDT,
        price_precision=2,
        size_precision=3,
        taker_fee=Decimal("0.0004"),
        maker_fee=Decimal("0.0002"),
        is_inverse=False,
    )

@pytest.fixture
def sample_bars(instrument_id):
    """Generate 100 bars with realistic price movement."""
    bar_spec = BarSpecification(1, BarAggregation.HOUR, PriceType.LAST)
    bar_type = BarType(instrument_id, bar_spec)
    bars = []
    price = 50000.0
    for i in range(100):
        import random
        change = random.gauss(0, 0.01)  # 1% daily volatility
        price *= (1 + change)
        ts = (i + 1) * 3_600_000_000_000  # hourly
        bars.append(Bar(
            bar_type=bar_type,
            open=Price(price, 2),
            high=Price(price * 1.005, 2),
            low=Price(price * 0.995, 2),
            close=Price(price * (1 + change/2), 2),
            volume=Quantity(100, 0),
            ts_event=ts,
            ts_init=ts,
        ))
    return bars, bar_type

@pytest.fixture
def msgbus():
    return MessageBus(trader_id="TESTER-001")

@pytest.fixture
def cache():
    return Cache()

@pytest.fixture
def engine():
    """Fully wired BacktestEngine with default venue."""
    engine = BacktestEngine()
    engine.add_venue("SIM", oms_type=OmsType.NETTING, starting_balances=[Money("100000", USD)])
    return engine
```

---

### `tests/unit/core/test_enums.py`

```
Test cases:
- test_order_side_values: Verify BUY and SELL exist
- test_order_type_values: Verify all 6 order types exist
- test_order_status_values: Verify all 12 statuses exist
- test_fsm_terminal_states_have_no_transitions: FILLED, CANCELED, REJECTED, DENIED, EXPIRED → set()
- test_fsm_initialized_can_only_go_to_denied_or_submitted
- test_fsm_submitted_can_go_to_accepted_rejected_canceled
- test_fsm_all_transitions_are_to_valid_statuses: no transition points to a nonexistent status
- test_enum_str_representation: str(OrderSide.BUY) outputs readable string
- test_enum_hashable: can be used as dict keys
```

---

### `tests/unit/core/test_identifiers.py`

```
Test cases:
- test_creation_valid: Venue("BINANCE").value == "BINANCE"
- test_creation_empty_raises: Venue("") → ValueError
- test_equality_same_type: Venue("X") == Venue("X") → True
- test_equality_different_type: Venue("X") != Symbol("X") → True (different types)
- test_hash_same_value: hash(Venue("X")) == hash(Venue("X"))
- test_hash_different_type: hash(Venue("X")) != hash(Symbol("X"))
- test_repr: repr(Venue("BINANCE")) == "Venue('BINANCE')"
- test_instrument_id_composite: InstrumentId(Symbol("BTC/USDT"), Venue("BINANCE")).value == "BTC/USDT.BINANCE"
- test_instrument_id_from_str: InstrumentId.from_str("BTC/USDT.BINANCE").symbol.value == "BTC/USDT"
- test_instrument_id_from_str_invalid: InstrumentId.from_str("NO_DOT") → ValueError
- test_instrument_id_venue_property: .venue == Venue("BINANCE")
- test_can_use_as_dict_key: {Venue("X"): 1}[Venue("X")] == 1
```

---

### `tests/unit/core/test_objects.py`

```
Test cases for Price:
- test_creation: Price("100.50", 2).value == Decimal("100.50")
- test_rounding: Price("100.555", 2).value == Decimal("100.56")
- test_add: Price("100", 2) + Price("50.25", 2) → Price("150.25", 2)
- test_sub: Price("100", 2) - Price("50.25", 2) → Price("49.75", 2)
- test_mul_scalar: Price("100", 2) * 2 → Price("200.00", 2)
- test_neg: -Price("100", 2) → Price("-100.00", 2)
- test_comparisons: <, <=, >, >=, ==, !=
- test_comparison_with_float: Price("100", 2) == 100.0
- test_as_double: Price("100.50", 2).as_double() == 100.5
- test_hash: can be used as dict key

Test cases for Quantity:
- test_creation: Quantity("10.5", 1).value == Decimal("10.5")
- test_non_negative: Quantity("-1", 0) → ValueError
- test_zero_allowed: Quantity("0", 0).value == Decimal("0")
- test_bool_zero: bool(Quantity("0", 0)) == False
- test_bool_nonzero: bool(Quantity("10", 0)) == True
- test_add, test_sub, test_mul

Test cases for Money:
- test_creation: Money("1000", USD).amount == Decimal("1000.00")
- test_add_same_currency: Money("100", USD) + Money("50", USD) → Money("150", USD)
- test_add_different_currency_raises: Money("100", USD) + Money("50", EUR) → ValueError
- test_neg: -Money("100", USD) → Money("-100", USD)
- test_repr: "1000.00 USD"

Test cases for AccountBalance:
- test_free_balance: AccountBalance(total=100, locked=30, free=70)
```

---

### `tests/unit/core/test_events.py`

```
Test cases:
- test_order_filled_creation: all fields accessible
- test_event_immutable: setting attribute → FrozenInstanceError
- test_order_filled_has_timestamps: ts_event and ts_init are ints
- test_event_repr: readable string
- test_position_opened_creation
- test_position_closed_creation
```

---

### `tests/unit/core/test_clock.py`

```
Test cases:
- test_test_clock_initial_time: TestClock(0).timestamp_ns() == 0
- test_test_clock_set_time: set_time(1000), timestamp_ns() == 1000
- test_test_clock_advance_time: advance from 0 to 5000
- test_timer_fires_at_correct_time: set timer every 1000ns, advance to 3500, verify 3 fires
- test_timer_cancel: set timer, cancel, advance, verify no fires
- test_live_clock_returns_real_time: LiveClock().timestamp_ns() > 0
```

---

### `tests/unit/core/test_msgbus.py`

```
Test cases:
- test_subscribe_and_publish: handler receives message
- test_multiple_subscribers: both handlers called
- test_unsubscribe: after unsubscribe, handler not called
- test_publish_no_subscribers: no error
- test_register_endpoint: send() delivers to registered handler
- test_send_unregistered: no error (silent)
- test_has_subscribers_true: after subscribe
- test_has_subscribers_false: before subscribe
- test_topics_list: returns list of active topics
- test_handler_called_in_order: first subscriber called before second
```

---

### `tests/unit/model/test_orders.py`

```
Test cases:
- test_market_order_creation: status == INITIALIZED
- test_limit_order_creation: has price field
- test_stop_market_order_creation: has trigger_price field
- test_order_fsm_valid_transition: INITIALIZED → apply(Submitted) → SUBMITTED
- test_order_fsm_invalid_transition: INITIALIZED → apply(Filled) → InvalidStateTransition
- test_order_fsm_full_lifecycle: INITIALIZED → SUBMITTED → ACCEPTED → FILLED
- test_order_filled_updates_avg_px: after fill, avg_px is set
- test_order_partially_filled: filled_qty < quantity, status == PARTIALLY_FILLED
- test_order_partial_then_full: two fills, final status == FILLED
- test_order_cancel_after_accepted: ACCEPTED → apply(Canceled) → CANCELED
- test_order_cannot_cancel_after_filled: FILLED → apply(Canceled) → raises
- test_order_events_recorded: order._events has all applied events
```

---

### `tests/unit/engine/test_matching_engine.py`

```
Test cases:
- test_market_order_fills_on_bar: submit market buy, process bar → fill at open price
- test_limit_buy_fills_when_price_drops: limit buy at $100, bar low=$99 → fills at $100
- test_limit_buy_no_fill_when_price_above: limit buy at $100, bar low=$101 → no fill
- test_limit_sell_fills_when_price_rises: limit sell at $100, bar high=$101 → fills at $100
- test_stop_buy_triggers_above: stop buy at $105, bar high=$106 → fills
- test_stop_buy_no_trigger_below: stop buy at $105, bar high=$104 → no fill
- test_stop_sell_triggers_below: stop sell at $95, bar low=$94 → fills
- test_multiple_orders_on_same_bar: 3 limits, 1 fills, 2 don't → verify correct
- test_fill_model_mid: MidFillModel fills at (high+low)/2
- test_fill_model_worst: WorstFillModel fills at high for buy, low for sell
- test_order_removed_after_fill: filled order no longer in open orders
```

---

### `tests/unit/model/test_position.py`

```
Test cases:
- test_open_long_position: after buy fill, side==LONG, qty==fill_qty
- test_open_short_position: after sell fill, side==SHORT
- test_close_long_position: buy fill + sell fill of same qty → is_closed
- test_partial_close: buy 100, sell 50 → qty==50, side==LONG
- test_realized_pnl_profit: buy at $100, sell at $110, qty=10 → pnl=$100
- test_realized_pnl_loss: buy at $100, sell at $90, qty=10 → pnl=-$100
- test_unrealized_pnl: buy at $100, current=$110, qty=10 → unrealized=$100
- test_netting_add_to_position: buy 100, buy 50 → qty==150
- test_netting_reduce_position: buy 100, sell 30 → qty==70
- test_reverse_position: buy 100, sell 150 → side==SHORT, qty==50
```

---

## Detailed Integration Test Specifications

### `tests/integration/test_order_lifecycle.py`

```
Test: Order flows through the full system
1. Create BacktestEngine with venue + instrument
2. Create strategy that submits a market buy on bar 1
3. Run engine with 5 bars
4. Verify: order was INITIALIZED → SUBMITTED → ACCEPTED → FILLED
5. Verify: order.events has 4 events
6. Verify: cache has the order
7. Verify: account balance decreased by fill amount + commission
```

---

### `tests/integration/test_position_lifecycle.py`

```
Test: Position opens and closes correctly
1. Strategy buys on bar 1, sells on bar 5
2. After bar 1: position is LONG, cache has 1 open position
3. After bar 5: position is CLOSED, cache has 0 open positions
4. Verify realized PnL matches (close_price - open_price) * quantity - commissions
```

---

### `tests/integration/test_multi_venue.py`

```
Test: Two venues, two instruments, one strategy
1. Add venue BINANCE (NETTING, MARGIN) and NASDAQ (HEDGING, CASH)
2. Add BTC/USDT.BINANCE and AAPL.NASDAQ
3. Strategy buys BTC on bar 1, buys AAPL on bar 2
4. Verify: BINANCE account balance changed, NASDAQ account balance changed
5. Verify: two separate positions exist
6. Verify: portfolio.net_position for each instrument is correct
```

---

### `tests/integration/test_data_to_strategy_flow.py`

```
Test: Data flows from engine → DataEngine → MessageBus → Strategy
1. Create strategy that records all received bars in a list
2. Run with 10 bars
3. Verify: strategy received exactly 10 bars in chronological order
```

---

## Detailed Pipeline Test Specifications

### `tests/pipeline/test_buy_and_hold.py`

```
Test: Known-result end-to-end test
1. Load 252 bars of AAPL (from test data CSV)
2. Strategy: buy on first bar, hold until end
3. Run backtest
4. Verify: result.total_orders == 1
5. Verify: result.ending_balance ≈ starting_balance * (last_close / first_open) - commissions
6. Verify: result.stats["Return [%]"] matches manual calculation
7. Verify: result.equity_curve has 252 points
8. Verify: result.equity_curve is monotonically changing (no gaps)
```

---

### `tests/pipeline/test_ema_crossover.py`

```
Test: EMA crossover strategy produces expected trades
1. Load 100 bars with known trend (first 50 up, last 50 down)
2. EMA(10) / EMA(30) crossover strategy
3. Run backtest
4. Verify: at least 1 buy signal (EMA10 crosses above EMA30 during uptrend)
5. Verify: at least 1 sell signal (EMA10 crosses below EMA30 during downtrend)
6. Verify: no trades during first 30 bars (indicators warming up)
```

---

### `tests/pipeline/test_results_consistency.py`

```
Test: Run same backtest twice, get identical results (determinism)
1. Run backtest with fixed seed
2. Run identical backtest again
3. Assert: result1.stats == result2.stats (exact match)
4. Assert: result1.equity_curve == result2.equity_curve
```

---

### `tests/pipeline/test_optimization_grid.py`

```
Test: Grid optimization returns parameter combinations
1. EMA crossover strategy with fast_period=[5,10,15], slow_period=[20,30]
2. Run grid search (6 combinations)
3. Verify: result has 6 rows
4. Verify: best result has highest Sharpe ratio
5. Verify: all combinations were actually run (no duplicates, no missing)
```

---

## Performance Benchmarks

### `tests/performance/bench_bar_processing.py`

```python
import time

def bench_100k_bars():
    """Benchmark: process 100,000 bars through the engine."""
    engine = BacktestEngine()
    engine.add_venue("SIM", starting_balances=[Money("1000000", USD)])
    engine.add_instrument(equity)
    engine.add_data(generate_bars(100_000))
    engine.add_strategy(BuyAndHoldStrategy())

    start = time.perf_counter()
    engine.run()
    elapsed = time.perf_counter() - start

    bars_per_sec = 100_000 / elapsed
    print(f"100K bars: {elapsed:.2f}s ({bars_per_sec:.0f} bars/sec)")
    assert bars_per_sec > 10_000, "Performance regression: below 10K bars/sec"
```

### `tests/performance/bench_matching_engine.py`

```python
def bench_matching_with_100_orders():
    """Benchmark: 100 pending orders checked against 100K bars."""
    # This tests the O(orders × bars) inner loop
    ...
    assert bars_per_sec > 5_000
```

---

## Example Test Data Files

### `tests/data/btc_usdt_1h_100bars.csv`

```csv
timestamp,open,high,low,close,volume
1704067200000000000,42000.00,42150.00,41850.00,42100.00,1500
1704070800000000000,42100.00,42300.00,42050.00,42250.00,1200
1704074400000000000,42250.00,42400.00,42100.00,42350.00,1800
...
```

Generate this with a script:

```python
# tests/generate_test_data.py
import csv
import random

def generate_ohlcv_csv(filename, n_bars=100, start_price=42000.0, start_ts=1704067200000000000):
    random.seed(42)  # deterministic
    price = start_price
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        for i in range(n_bars):
            ts = start_ts + i * 3_600_000_000_000
            open_p = round(price, 2)
            change = random.gauss(0, 0.005)
            close_p = round(price * (1 + change), 2)
            high_p = round(max(open_p, close_p) * (1 + abs(random.gauss(0, 0.002))), 2)
            low_p = round(min(open_p, close_p) * (1 - abs(random.gauss(0, 0.002))), 2)
            volume = random.randint(500, 3000)
            writer.writerow([ts, open_p, high_p, low_p, close_p, volume])
            price = close_p

if __name__ == "__main__":
    generate_ohlcv_csv("tests/data/btc_usdt_1h_100bars.csv", n_bars=100)
    generate_ohlcv_csv("tests/data/aapl_1d_252bars.csv", n_bars=252, start_price=150.0)
```

### `tests/data/aapl_1d_252bars.csv`

Same format as above, 252 bars (1 trading year), starting price $150.

---

# C++/Rust Optimization Summary Table

| Module | File | Optimization Value | Reason | Expected Speedup |
|--------|------|:-:|--------|:-:|
| `core/enums.py` | ❌ Not worth it | Python Enum is fast enough | — |
| `core/identifiers.py` | ⚠️ Maybe | Could use interned strings | 2-5x |
| **`core/objects.py`** | **✅ HIGH** | **Price/Quantity Decimal arithmetic is the #1 CPU consumer** | **30-80x** |
| `core/events.py` | ⚠️ Maybe | Event creation is frequent but short-lived | 2-5x |
| `core/clock.py` | ❌ Not worth it | Called once per bar | — |
| `core/msgbus.py` | ⚠️ Maybe | Dispatch loop on every tick | 5-10x |
| `model/data.py` | **✅ HIGH** | Bar/tick objects created millions of times | **20-50x** |
| `model/instruments/` | ❌ Not worth it | Few objects, created once | — |
| `model/orders/` | ⚠️ Maybe | FSM apply() called per order event | 2-5x |
| `model/position.py` | ❌ Not worth it | Few objects | — |
| `state/cache.py` | ⚠️ Maybe | Dictionary lookups at scale | 3-10x |
| **`engine/matching_engine.py`** | **✅ HIGHEST** | **The inner loop: O(orders × bars) price comparisons** | **50-200x** |
| `engine/data_engine.py` | ❌ Not worth it | Thin routing layer | — |
| `engine/execution_engine.py` | ❌ Not worth it | Order-frequency | — |
| `engine/risk_engine.py` | ❌ Not worth it | Order-frequency | — |
| `venues/models.py` | ⚠️ Maybe | Fill model called per order | 2-5x |
| `venues/account.py` | ❌ Not worth it | Order-frequency | — |
| `venues/simulated_exchange.py` | ⚠️ Maybe | Orchestration layer | — |
| `trading/strategy.py` | ❌ Not worth it | User-written Python | — |
| **`indicators/`** | **✅ HIGH** | **Computed every bar × N indicators** | **20-50x** |
| **`data/wranglers.py`** | **✅ HIGH** | **Converting millions of rows to objects** | **50-100x** |
| `analysis/` | ⚠️ Maybe | Stats on large equity curves | 5-10x |
| **`backtest/engine.py`** | **✅ HIGH** | **The main simulation loop** | **50-100x** |
| **`optimization/`** | **✅ HIGH** | **Runs engine N times** | **Multiplicative** |
| `visualization/` | ❌ Not worth it | Python/JS domain | — |

### Recommended Rust Optimization Order:

1. **`core/objects.py`** → Rust `Price`, `Quantity`, `Money` with `rust_decimal` crate
2. **`engine/matching_engine.py`** → Rust matching loop with `Vec<Order>`
3. **`model/data.py`** → Rust `Bar`, `QuoteTick`, `TradeTick` structs
4. **`indicators/`** → Rust indicator implementations (SMA, EMA, ATR, etc.)
5. **`data/wranglers.py`** → Rust Parquet reader via Polars/Arrow2
6. **`backtest/engine.py`** → Rust main loop orchestrating all of the above

Use **PyO3** to expose Rust types to Python. Keep pure-Python fallbacks for development/debugging. Use **maturin** for build/packaging.

---

## Final Checklist

- [ ] Phase 1: All 6 core files pass unit tests
- [ ] Phase 2: All 4 model modules pass unit tests
- [ ] Phase 3: Cache + Portfolio pass unit tests
- [ ] Phase 4: All 4 engines pass unit tests
- [ ] Phase 5: Venue layer passes unit tests
- [ ] Phase 6: Strategy layer passes unit tests
- [ ] Phase 7: All indicators match known-correct values
- [ ] Phase 8: Data wranglers correctly parse CSV/Parquet
- [ ] Phase 9: Analyzers produce correct statistics
- [ ] Phase 10: Full backtest engine passes integration tests
- [ ] Phase 11: Visualization renders without errors
- [ ] Phase 12: Optimization returns valid results
- [ ] Pipeline: All pipeline tests pass (buy-and-hold, EMA crossover, determinism)
- [ ] Performance: >10K bars/sec for simple strategy on 100K bars
- [ ] Rust Phase 1: Price/Quantity in Rust, Python fallback maintained
- [ ] Rust Phase 2: Matching engine in Rust
- [ ] Rust Phase 3: Main loop in Rust

---

*This document is your roadmap. Follow the phases in order. Test before you move on. Build it right, then make it fast.*
