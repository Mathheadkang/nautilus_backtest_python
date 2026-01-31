from __future__ import annotations

from decimal import Decimal

from nautilus_core.enums import AccountType
from nautilus_core.events import AccountState
from nautilus_core.identifiers import AccountId
from nautilus_core.objects import AccountBalance, Currency, Money


class Account:
    def __init__(
        self,
        account_id: AccountId,
        account_type: AccountType,
        base_currency: Currency,
        balances: list[AccountBalance] | None = None,
    ) -> None:
        self.id = account_id
        self.account_type = account_type
        self.base_currency = base_currency
        self.balances: dict[Currency, AccountBalance] = {}
        self.commissions: dict[Currency, Decimal] = {}
        self._events: list[AccountState] = []

        if balances:
            for bal in balances:
                self.balances[bal.total.currency] = bal

    def balance_total(self, currency: Currency | None = None) -> Money | None:
        c = currency or self.base_currency
        bal = self.balances.get(c)
        return bal.total if bal else None

    def balance_free(self, currency: Currency | None = None) -> Money | None:
        c = currency or self.base_currency
        bal = self.balances.get(c)
        return bal.free if bal else None

    def balance_locked(self, currency: Currency | None = None) -> Money | None:
        c = currency or self.base_currency
        bal = self.balances.get(c)
        return bal.locked if bal else None

    def apply(self, event: AccountState) -> None:
        for bal in event.balances:
            self.balances[bal.total.currency] = bal
        self._events.append(event)

    def update_balance(self, currency: Currency, total: Decimal, locked: Decimal) -> None:
        free = total - locked
        self.balances[currency] = AccountBalance(
            total=Money(total, currency),
            locked=Money(locked, currency),
            free=Money(free, currency),
        )

    def update_commissions(self, currency: Currency, amount: Decimal) -> None:
        self.commissions[currency] = self.commissions.get(currency, Decimal("0")) + amount

    @property
    def events(self) -> list[AccountState]:
        return list(self._events)

    def __repr__(self) -> str:
        return f"Account(id={self.id}, type={self.account_type.name})"


class CashAccount(Account):
    def __init__(
        self,
        account_id: AccountId,
        base_currency: Currency,
        balances: list[AccountBalance] | None = None,
    ) -> None:
        super().__init__(account_id, AccountType.CASH, base_currency, balances)


class MarginAccount(Account):
    def __init__(
        self,
        account_id: AccountId,
        base_currency: Currency,
        balances: list[AccountBalance] | None = None,
        leverage: Decimal = Decimal("1"),
    ) -> None:
        super().__init__(account_id, AccountType.MARGIN, base_currency, balances)
        self.leverage = leverage
