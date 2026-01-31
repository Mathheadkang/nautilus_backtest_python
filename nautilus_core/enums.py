from enum import Enum, auto


class OrderSide(Enum):
    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    MARKET = auto()
    LIMIT = auto()
    STOP_MARKET = auto()
    STOP_LIMIT = auto()


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


# Valid FSM transitions: from_status -> set of valid to_statuses
ORDER_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.INITIALIZED: {OrderStatus.DENIED, OrderStatus.SUBMITTED},
    OrderStatus.SUBMITTED: {OrderStatus.ACCEPTED, OrderStatus.REJECTED, OrderStatus.CANCELED},
    OrderStatus.ACCEPTED: {
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.TRIGGERED,
        OrderStatus.PENDING_UPDATE,
        OrderStatus.PENDING_CANCEL,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
    },
    OrderStatus.TRIGGERED: {
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.PENDING_UPDATE,
        OrderStatus.PENDING_CANCEL,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
    },
    OrderStatus.PENDING_UPDATE: {
        OrderStatus.ACCEPTED,
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.TRIGGERED,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
    },
    OrderStatus.PENDING_CANCEL: {
        OrderStatus.CANCELED,
        OrderStatus.ACCEPTED,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.PENDING_UPDATE,
        OrderStatus.PENDING_CANCEL,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
    },
}


class PositionSide(Enum):
    FLAT = auto()
    LONG = auto()
    SHORT = auto()


class AccountType(Enum):
    CASH = auto()
    MARGIN = auto()


class OmsType(Enum):
    HEDGING = auto()
    NETTING = auto()


class AssetClass(Enum):
    FX = auto()
    EQUITY = auto()
    COMMODITY = auto()
    CRYPTO = auto()
    BOND = auto()
    INDEX = auto()
    METAL = auto()


class CurrencyType(Enum):
    FIAT = auto()
    CRYPTO = auto()


class BookAction(Enum):
    ADD = auto()
    UPDATE = auto()
    DELETE = auto()
    CLEAR = auto()


class LiquiditySide(Enum):
    MAKER = auto()
    TAKER = auto()
    NO_LIQUIDITY_SIDE = auto()


class BarAggregation(Enum):
    TICK = auto()
    SECOND = auto()
    MINUTE = auto()
    HOUR = auto()
    DAY = auto()


class PriceType(Enum):
    BID = auto()
    ASK = auto()
    MID = auto()
    LAST = auto()


class TradingState(Enum):
    ACTIVE = auto()
    REDUCING = auto()
    HALTED = auto()
