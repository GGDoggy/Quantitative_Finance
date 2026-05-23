from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal


PreprocessBuilder = Callable[[object], dict[str, object]]
PayloadKind = Literal["orderbook", "trades"]


@dataclass(frozen=True)
class PreprocessPlotSpec:
    key: str
    preprocess_builder: PreprocessBuilder
    payload_kind: PayloadKind


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
        payload_kind="orderbook",
    ),
    "trades_scatter": PreprocessPlotSpec(
        key="trades_scatter",
        preprocess_builder=build_trades_scatter_payload,
        payload_kind="trades",
    ),
    "trade_volume_timeline": PreprocessPlotSpec(
        key="trade_volume_timeline",
        preprocess_builder=build_trade_volume_timeline_payload,
        payload_kind="trades",
    ),
}
