from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .builders import build_orderbook_payload, build_trade_payload
from .models import PreprocessContext


@dataclass(frozen=True)
class PreprocessBuilderSpec:
    preprocess_builder: Callable[[PreprocessContext], dict[str, object]] | None
    required_payload_keys: tuple[str, ...]


PLOT_REGISTRY: dict[str, PreprocessBuilderSpec] = {
    "orderbook": PreprocessBuilderSpec(
        preprocess_builder=build_orderbook_payload,
        required_payload_keys=("price_axis", "time_axis", "data", "bid", "ask"),
    ),
    "trades_scatter": PreprocessBuilderSpec(
        preprocess_builder=build_trade_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
    ),
    "trade_volume_timeline": PreprocessBuilderSpec(
        preprocess_builder=build_trade_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
    ),
}

__all__ = ["PLOT_REGISTRY", "PreprocessBuilderSpec"]
