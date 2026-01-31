from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from nautilus_core.enums import AccountType, OmsType
from nautilus_core.objects import Currency, Money


@dataclass
class BacktestVenueConfig:
    venue_name: str
    oms_type: OmsType = OmsType.HEDGING
    account_type: AccountType = AccountType.CASH
    base_currency: Currency | None = None
    starting_balances: list[Money] = field(default_factory=list)
    default_leverage: Decimal = Decimal("1")


@dataclass
class BacktestEngineConfig:
    trader_id: str = "BACKTESTER-001"
