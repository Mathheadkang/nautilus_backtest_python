from __future__ import annotations

from decimal import Decimal

from nautilus_core.enums import AssetClass
from nautilus_core.identifiers import InstrumentId, Symbol, Venue
from nautilus_core.objects import Currency, Price, Quantity


class Instrument:
    def __init__(
        self,
        instrument_id: InstrumentId,
        asset_class: AssetClass,
        quote_currency: Currency,
        price_precision: int,
        size_precision: int,
        price_increment: Price,
        size_increment: Quantity,
        multiplier: Decimal = Decimal("1"),
        lot_size: Quantity | None = None,
        maker_fee: Decimal = Decimal("0"),
        taker_fee: Decimal = Decimal("0"),
        min_quantity: Quantity | None = None,
        max_quantity: Quantity | None = None,
        min_price: Price | None = None,
        max_price: Price | None = None,
        base_currency: Currency | None = None,
        ts_event: int = 0,
        ts_init: int = 0,
    ) -> None:
        self.id = instrument_id
        self.symbol = instrument_id.symbol
        self.venue = instrument_id.venue
        self.asset_class = asset_class
        self.quote_currency = quote_currency
        self.base_currency = base_currency
        self.price_precision = price_precision
        self.size_precision = size_precision
        self.price_increment = price_increment
        self.size_increment = size_increment
        self.multiplier = multiplier
        self.lot_size = lot_size
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.min_quantity = min_quantity
        self.max_quantity = max_quantity
        self.min_price = min_price
        self.max_price = max_price
        self.ts_event = ts_event
        self.ts_init = ts_init

    def make_price(self, value: float | Decimal | str) -> Price:
        return Price(value, self.price_precision)

    def make_qty(self, value: float | Decimal | str) -> Quantity:
        return Quantity(value, self.size_precision)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Instrument):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class CurrencyPair(Instrument):
    def __init__(
        self,
        instrument_id: InstrumentId,
        base_currency: Currency,
        quote_currency: Currency,
        price_precision: int,
        size_precision: int,
        price_increment: Price | None = None,
        size_increment: Quantity | None = None,
        maker_fee: Decimal = Decimal("0"),
        taker_fee: Decimal = Decimal("0"),
        min_quantity: Quantity | None = None,
        max_quantity: Quantity | None = None,
        min_price: Price | None = None,
        max_price: Price | None = None,
        ts_event: int = 0,
        ts_init: int = 0,
    ) -> None:
        super().__init__(
            instrument_id=instrument_id,
            asset_class=AssetClass.FX,
            quote_currency=quote_currency,
            price_precision=price_precision,
            size_precision=size_precision,
            price_increment=price_increment or Price(Decimal(10) ** -price_precision, price_precision),
            size_increment=size_increment or Quantity(Decimal(10) ** -size_precision, size_precision),
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            min_price=min_price,
            max_price=max_price,
            base_currency=base_currency,
            ts_event=ts_event,
            ts_init=ts_init,
        )


class Equity(Instrument):
    def __init__(
        self,
        instrument_id: InstrumentId,
        quote_currency: Currency,
        price_precision: int = 2,
        size_precision: int = 0,
        price_increment: Price | None = None,
        size_increment: Quantity | None = None,
        lot_size: Quantity | None = None,
        maker_fee: Decimal = Decimal("0"),
        taker_fee: Decimal = Decimal("0"),
        min_quantity: Quantity | None = None,
        max_quantity: Quantity | None = None,
        min_price: Price | None = None,
        max_price: Price | None = None,
        ts_event: int = 0,
        ts_init: int = 0,
    ) -> None:
        super().__init__(
            instrument_id=instrument_id,
            asset_class=AssetClass.EQUITY,
            quote_currency=quote_currency,
            price_precision=price_precision,
            size_precision=size_precision,
            price_increment=price_increment or Price(Decimal(10) ** -price_precision, price_precision),
            size_increment=size_increment or Quantity(1, size_precision),
            lot_size=lot_size or Quantity(1, 0),
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            min_price=min_price,
            max_price=max_price,
            ts_event=ts_event,
            ts_init=ts_init,
        )


class CryptoPerpetual(Instrument):
    def __init__(
        self,
        instrument_id: InstrumentId,
        base_currency: Currency,
        quote_currency: Currency,
        settlement_currency: Currency,
        price_precision: int,
        size_precision: int,
        price_increment: Price | None = None,
        size_increment: Quantity | None = None,
        multiplier: Decimal = Decimal("1"),
        maker_fee: Decimal = Decimal("0"),
        taker_fee: Decimal = Decimal("0"),
        min_quantity: Quantity | None = None,
        max_quantity: Quantity | None = None,
        min_price: Price | None = None,
        max_price: Price | None = None,
        ts_event: int = 0,
        ts_init: int = 0,
    ) -> None:
        super().__init__(
            instrument_id=instrument_id,
            asset_class=AssetClass.CRYPTO,
            quote_currency=quote_currency,
            price_precision=price_precision,
            size_precision=size_precision,
            price_increment=price_increment or Price(Decimal(10) ** -price_precision, price_precision),
            size_increment=size_increment or Quantity(Decimal(10) ** -size_precision, size_precision),
            multiplier=multiplier,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            min_price=min_price,
            max_price=max_price,
            base_currency=base_currency,
            ts_event=ts_event,
            ts_init=ts_init,
        )
        self.settlement_currency = settlement_currency


class FuturesContract(Instrument):
    def __init__(
        self,
        instrument_id: InstrumentId,
        quote_currency: Currency,
        asset_class: AssetClass,
        price_precision: int,
        size_precision: int,
        expiry_date: str,
        multiplier: Decimal = Decimal("1"),
        price_increment: Price | None = None,
        size_increment: Quantity | None = None,
        lot_size: Quantity | None = None,
        maker_fee: Decimal = Decimal("0"),
        taker_fee: Decimal = Decimal("0"),
        min_quantity: Quantity | None = None,
        max_quantity: Quantity | None = None,
        min_price: Price | None = None,
        max_price: Price | None = None,
        ts_event: int = 0,
        ts_init: int = 0,
    ) -> None:
        super().__init__(
            instrument_id=instrument_id,
            asset_class=asset_class,
            quote_currency=quote_currency,
            price_precision=price_precision,
            size_precision=size_precision,
            price_increment=price_increment or Price(Decimal(10) ** -price_precision, price_precision),
            size_increment=size_increment or Quantity(Decimal(10) ** -size_precision, size_precision),
            multiplier=multiplier,
            lot_size=lot_size,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            min_price=min_price,
            max_price=max_price,
            ts_event=ts_event,
            ts_init=ts_init,
        )
        self.expiry_date = expiry_date
