from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from nautilus_core.account import Account
from nautilus_core.backtest.exchange import SimulatedExchange
from nautilus_core.backtest.results import BacktestResult
from nautilus_core.cache import Cache
from nautilus_core.clock import TestClock
from nautilus_core.data import Bar, QuoteTick, TradeTick
from nautilus_core.data_engine import DataEngine
from nautilus_core.enums import AccountType, OmsType, OrderStatus
from nautilus_core.execution_engine import ExecutionEngine
from nautilus_core.identifiers import TraderId, Venue
from nautilus_core.instruments import Instrument
from nautilus_core.msgbus import MessageBus
from nautilus_core.objects import Currency, Money
from nautilus_core.order_factory import OrderFactory
from nautilus_core.portfolio import Portfolio
from nautilus_core.risk_engine import RiskEngine
from nautilus_core.trading.strategy import Strategy


class BacktestEngine:
    def __init__(self, trader_id: str = "BACKTESTER-001") -> None:
        self.trader_id = TraderId(trader_id)
        self.clock = TestClock()
        self.msgbus = MessageBus(trader_id=trader_id)
        self.cache = Cache()
        self.portfolio = Portfolio(self.cache)
        self.risk_engine = RiskEngine(self.portfolio, self.cache, self.msgbus)
        self.exec_engine = ExecutionEngine(self.cache, self.msgbus, self.risk_engine)
        self.data_engine = DataEngine(self.cache, self.msgbus)

        self._exchanges: dict[Venue, SimulatedExchange] = {}
        self._strategies: list[Strategy] = []
        self._data: list[Any] = []
        self._instruments: dict = {}
        self._starting_balances: dict[Venue, list[Money]] = {}
        self._result: BacktestResult | None = None

    def add_venue(
        self,
        venue_name: str,
        oms_type: OmsType = OmsType.HEDGING,
        account_type: AccountType = AccountType.CASH,
        base_currency: Currency | None = None,
        starting_balances: list[Money] | None = None,
        default_leverage: Decimal = Decimal("1"),
    ) -> None:
        venue = Venue(venue_name)
        balances = starting_balances or []

        if base_currency is None and balances:
            base_currency = balances[0].currency

        exchange = SimulatedExchange(
            venue=venue,
            oms_type=oms_type,
            account_type=account_type,
            base_currency=base_currency,
            starting_balances=balances,
            exec_engine=self.exec_engine,
            default_leverage=default_leverage,
        )
        self._exchanges[venue] = exchange
        self._starting_balances[venue] = balances
        self.exec_engine.register_venue(venue, exchange, oms_type)
        self.cache.add_account(exchange.account)

    def add_instrument(self, instrument: Instrument) -> None:
        self.cache.add_instrument(instrument)
        self._instruments[instrument.id] = instrument
        venue = instrument.venue
        exchange = self._exchanges.get(venue)
        if exchange:
            exchange.add_instrument(instrument)

    def add_data(self, data: list[Bar | QuoteTick | TradeTick]) -> None:
        self._data.extend(data)

    def add_strategy(self, strategy: Strategy) -> None:
        order_factory = OrderFactory(self.trader_id, strategy.id)
        strategy.register(
            clock=self.clock,
            cache=self.cache,
            portfolio=self.portfolio,
            msgbus=self.msgbus,
            order_factory=order_factory,
            exec_engine=self.exec_engine,
            data_engine=self.data_engine,
        )
        self._strategies.append(strategy)

    def run(self, start: int | None = None, end: int | None = None) -> None:
        # Sort data chronologically
        self._data.sort(key=lambda d: d.ts_event)

        # Filter by time range
        data = self._data
        if start is not None:
            data = [d for d in data if d.ts_event >= start]
        if end is not None:
            data = [d for d in data if d.ts_event <= end]

        # Start strategies
        for strategy in self._strategies:
            strategy.on_start()

        # Record starting balance
        balance_curve: list[tuple[int, Decimal]] = []
        starting_balance = self._get_total_balance()
        if data:
            balance_curve.append((data[0].ts_event, starting_balance))

        # Main event loop
        for datum in data:
            # Advance clock
            self.clock.set_time(datum.ts_event)

            # Process time events
            time_events = self.clock.advance_time(datum.ts_event)
            for te in time_events:
                if te.callback:
                    te.callback(te)

            # Route data to exchange first (for fills), then to data engine (for strategies)
            if isinstance(datum, Bar):
                # Process through exchange matching engine
                venue = datum.bar_type.instrument_id.venue
                exchange = self._exchanges.get(venue)
                if exchange:
                    exchange.process_bar(datum)
                # Then route through data engine to strategies
                self.data_engine.process_bar(datum)
                # Record balance
                balance_curve.append((datum.ts_event, self._get_total_balance()))

            elif isinstance(datum, QuoteTick):
                self.data_engine.process_quote_tick(datum)
            elif isinstance(datum, TradeTick):
                self.data_engine.process_trade_tick(datum)

        # Stop strategies
        for strategy in self._strategies:
            strategy.on_stop()

        # Build result
        self._result = self._build_result(starting_balance, balance_curve)

    def get_result(self) -> BacktestResult:
        if self._result is None:
            raise RuntimeError("No result available. Run the backtest first.")
        return self._result

    def reset(self) -> None:
        self._data.clear()
        self._result = None
        for strategy in self._strategies:
            strategy.on_reset()

    def dispose(self) -> None:
        self._data.clear()
        self._strategies.clear()
        self._exchanges.clear()
        self._result = None

    def _get_total_balance(self) -> Decimal:
        total = Decimal("0")
        for venue, exchange in self._exchanges.items():
            bal = exchange.account.balance_total(exchange.base_currency)
            if bal:
                total += bal.amount
        return total

    def _build_result(
        self,
        starting_balance: Decimal,
        balance_curve: list[tuple[int, Decimal]],
    ) -> BacktestResult:
        ending_balance = self._get_total_balance()
        total_return = ending_balance - starting_balance

        # Count orders and positions
        all_orders = self.cache.orders()
        all_positions = self.cache.positions()
        total_fills = sum(1 for o in all_orders if o.status == OrderStatus.FILLED)

        # Calculate commissions
        total_commissions = Decimal("0")
        for exchange in self._exchanges.values():
            for curr, amount in exchange.account.commissions.items():
                total_commissions += amount

        # Calculate max drawdown
        max_drawdown = Decimal("0")
        peak = starting_balance
        for ts, bal in balance_curve:
            if bal > peak:
                peak = bal
            dd = peak - bal
            if dd > max_drawdown:
                max_drawdown = dd

        # Calculate win/loss stats from closed positions
        wins = []
        losses = []
        for pos in all_positions:
            if pos.is_closed:
                pnl = pos.realized_pnl
                if pnl > 0:
                    wins.append(pnl)
                elif pnl < 0:
                    losses.append(pnl)

        total_closed = len(wins) + len(losses)
        win_rate = Decimal(len(wins)) / Decimal(total_closed) if total_closed > 0 else Decimal("0")
        avg_win = sum(wins) / Decimal(len(wins)) if wins else Decimal("0")
        avg_loss = sum(losses) / Decimal(len(losses)) if losses else Decimal("0")
        gross_profit = sum(wins) if wins else Decimal("0")
        gross_loss = abs(sum(losses)) if losses else Decimal("0")
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else Decimal("0")

        # Sharpe ratio (simplified: using balance returns)
        sharpe = Decimal("0")
        if len(balance_curve) > 2:
            returns = []
            for i in range(1, len(balance_curve)):
                prev_bal = balance_curve[i - 1][1]
                curr_bal = balance_curve[i][1]
                if prev_bal > 0:
                    ret = (curr_bal - prev_bal) / prev_bal
                    returns.append(float(ret))
            if returns and len(returns) > 1:
                mean_ret = sum(returns) / len(returns)
                variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
                std_ret = math.sqrt(variance) if variance > 0 else 0
                if std_ret > 0:
                    sharpe = Decimal(str(mean_ret / std_ret * math.sqrt(252)))

        start_ns = balance_curve[0][0] if balance_curve else 0
        end_ns = balance_curve[-1][0] if balance_curve else 0

        return BacktestResult(
            start_time_ns=start_ns,
            end_time_ns=end_ns,
            total_orders=len(all_orders),
            total_positions=len(all_positions),
            total_fills=total_fills,
            starting_balance=starting_balance,
            ending_balance=ending_balance,
            total_return=total_return,
            total_commissions=total_commissions,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            balance_curve=balance_curve,
        )
