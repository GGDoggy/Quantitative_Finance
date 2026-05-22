from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


PreprocessBuilder = Callable[[object], dict[str, object]]


@dataclass(frozen=True)
class PreprocessPlotSpec:
    key: str
    preprocess_builder: PreprocessBuilder
    required_payload_keys: tuple[str, ...]


def build_orderbook_payload(context: object) -> dict[str, object]:
    from src.preprocess.orderbook import build_orderbook_payload as implementation

    return implementation(context)


def build_trades_scatter_payload(context: object) -> dict[str, object]:
    from src.preprocess.trades_scatter import build_trades_scatter_payload as implementation

    return implementation(context)


def build_trade_volume_timeline_payload(context: object) -> dict[str, object]:
    from src.preprocess.trade_volume_timeline import (
        build_trade_volume_timeline_payload as implementation,
    )

    return implementation(context)


PREPROCESS_PLOT_REGISTRY: dict[str, PreprocessPlotSpec] = {
    "orderbook": PreprocessPlotSpec(
        key="orderbook",
        preprocess_builder=build_orderbook_payload,
        required_payload_keys=("price_axis", "time_axis", "data", "bid", "ask"),
    ),
    "trades_scatter": PreprocessPlotSpec(
        key="trades_scatter",
        preprocess_builder=build_trades_scatter_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
    ),
    "trade_volume_timeline": PreprocessPlotSpec(
        key="trade_volume_timeline",
        preprocess_builder=build_trade_volume_timeline_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
    ),
}
