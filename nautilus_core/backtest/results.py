from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class BacktestResult:
    start_time_ns: int = 0
    end_time_ns: int = 0
    total_orders: int = 0
    total_positions: int = 0
    total_fills: int = 0
    starting_balance: Decimal = Decimal("0")
    ending_balance: Decimal = Decimal("0")
    total_return: Decimal = Decimal("0")
    total_commissions: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    sharpe_ratio: Decimal = Decimal("0")
    win_rate: Decimal = Decimal("0")
    profit_factor: Decimal = Decimal("0")
    avg_win: Decimal = Decimal("0")
    avg_loss: Decimal = Decimal("0")
    balance_curve: list[tuple[int, Decimal]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_time_ns": self.start_time_ns,
            "end_time_ns": self.end_time_ns,
            "total_orders": self.total_orders,
            "total_positions": self.total_positions,
            "total_fills": self.total_fills,
            "starting_balance": float(self.starting_balance),
            "ending_balance": float(self.ending_balance),
            "total_return": float(self.total_return),
            "total_return_pct": float(self.total_return / self.starting_balance * 100) if self.starting_balance else 0,
            "total_commissions": float(self.total_commissions),
            "max_drawdown": float(self.max_drawdown),
            "max_drawdown_pct": float(self.max_drawdown / self.starting_balance * 100) if self.starting_balance else 0,
            "sharpe_ratio": float(self.sharpe_ratio),
            "win_rate": float(self.win_rate),
            "profit_factor": float(self.profit_factor),
            "avg_win": float(self.avg_win),
            "avg_loss": float(self.avg_loss),
        }

    def to_dataframe(self):
        import pandas as pd
        if self.balance_curve:
            timestamps, balances = zip(*self.balance_curve)
            return pd.DataFrame({
                "timestamp_ns": timestamps,
                "balance": [float(b) for b in balances],
            })
        return pd.DataFrame(columns=["timestamp_ns", "balance"])

    def __str__(self) -> str:
        d = self.to_dict()
        lines = ["=" * 50, "BACKTEST RESULTS", "=" * 50]
        for k, v in d.items():
            label = k.replace("_", " ").title()
            if isinstance(v, float):
                lines.append(f"  {label:30s}: {v:>12.4f}")
            else:
                lines.append(f"  {label:30s}: {v:>12}")
        lines.append("=" * 50)
        return "\n".join(lines)
