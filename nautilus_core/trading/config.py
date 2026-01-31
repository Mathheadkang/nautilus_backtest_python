from __future__ import annotations

from dataclasses import dataclass

from nautilus_core.enums import OmsType


@dataclass(frozen=True)
class StrategyConfig:
    strategy_id: str = ""
    oms_type: OmsType = OmsType.HEDGING
