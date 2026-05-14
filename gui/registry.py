from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from gui.data_catalog import PlotDatasetLocator


PlotBuilder = Callable[[list["PlotDatasetLocator"]], object]
PreprocessBuilder = Callable[[object], dict[str, object]]


@dataclass(frozen=True)
class PlotSpec:
    key: str
    label: str
    plot_builder: PlotBuilder
    preprocess_builder: PreprocessBuilder
    required_payload_keys: tuple[str, ...]


def build_orderbook_view(locators: list["PlotDatasetLocator"]):
    from gui.plots.orderbook import build_orderbook_view as implementation
    return implementation(locators)


def build_trades_scatter_view(locators: list["PlotDatasetLocator"]):
    from gui.plots.trades_scatter import build_trades_scatter_view as implementation
    return implementation(locators)


def build_trade_volume_timeline_view(locators: list["PlotDatasetLocator"]):
    from gui.plots.trade_volume_timeline import build_trade_volume_timeline_view as implementation
    return implementation(locators)


def build_fill_probability_view(locators: list["PlotDatasetLocator"]):
    from gui.plots.fill_probability import build_fill_probability_view as implementation
    return implementation(locators)


def build_orderbook_payload(context: object) -> dict[str, object]:
    from gui.preprocess.orderbook import build_orderbook_payload as implementation
    return implementation(context)


def build_trades_scatter_payload(context: object) -> dict[str, object]:
    from gui.preprocess.trades_scatter import build_trades_scatter_payload as implementation
    return implementation(context)


def build_trade_volume_timeline_payload(context: object) -> dict[str, object]:
    from gui.preprocess.trade_volume_timeline import build_trade_volume_timeline_payload as implementation
    return implementation(context)


def build_fill_probability_payload(_context: object) -> dict[str, object]:
    return {}


PLOT_REGISTRY: dict[str, PlotSpec] = {
    "orderbook": PlotSpec(
        key="orderbook",
        label="Orderbook",
        plot_builder=build_orderbook_view,
        preprocess_builder=build_orderbook_payload,
        required_payload_keys=("price_axis", "time_axis", "data", "bid", "ask"),
    ),
    "trades_scatter": PlotSpec(
        key="trades_scatter",
        label="Trades Scatter",
        plot_builder=build_trades_scatter_view,
        preprocess_builder=build_trades_scatter_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
    ),
    "trade_volume_timeline": PlotSpec(
        key="trade_volume_timeline",
        label="Trade Volume Timeline",
        plot_builder=build_trade_volume_timeline_view,
        preprocess_builder=build_trade_volume_timeline_payload,
        required_payload_keys=("trade_time", "trade_price", "trade_volume", "trade_side"),
    ),
    "fill_probability": PlotSpec(
        key="fill_probability",
        label="Fill Probability",
        plot_builder=build_fill_probability_view,
        preprocess_builder=build_fill_probability_payload,
        required_payload_keys=("__simulation_npz__",),
    ),
}

PLOT_LABELS = {key: spec.label for key, spec in PLOT_REGISTRY.items()}
