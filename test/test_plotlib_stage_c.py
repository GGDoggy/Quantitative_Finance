from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.plotlib import (
    PlotRenderOptions,
    build_fill_probability_view,
    build_micro_cost_fill_probability_view,
    build_mid_profit_view,
    build_trade_volume_timeline_view,
    build_trades_scatter_view,
    load_orderbook_payload,
    load_simulation_arrays,
    load_trades_payload,
)


def _write_orderbook_dataset(path: Path) -> None:
    np.savez(
        path,
        price_axis=np.array([100.0, 101.0]),
        time_axis=np.array(
            ["2024-01-01T00:00:00", "2024-01-01T00:00:01"], dtype="datetime64[ns]"
        ),
        data=np.array([[1.0, -1.0], [2.0, -2.0]]),
        bid=np.array([100.0, 100.1]),
        ask=np.array([100.2, 100.3]),
        mid=np.array([100.1, 100.2]),
        trade_time=np.array(
            ["2024-01-01T00:00:00", "2024-01-01T00:00:01"], dtype="datetime64[ns]"
        ),
        trade_price=np.array([100.15, 100.25]),
        trade_volume=np.array([1.5, 2.0]),
        trade_side=np.array([-1.0, 1.0]),
    )


def _write_simulation_dataset(path: Path) -> None:
    np.savez(
        path,
        bid_near_size=np.array([1.0, 2.0, 3.0]),
        bid_opp_size=np.array([1.5, 2.5, 3.5]),
        bid_result=np.array([1, 0, 1]),
        ask_near_size=np.array([1.1, 2.1, 3.1]),
        ask_opp_size=np.array([1.6, 2.6, 3.6]),
        ask_result=np.array([1, 1, 0]),
        bid_mid_profit=np.array([0.3, 0.1, 0.4]),
        ask_mid_profit=np.array([0.2, 0.5, 0.1]),
        bid_micro_profit=np.array([0.25, 0.05, 0.2]),
        ask_micro_profit=np.array([0.15, 0.35, 0.05]),
    )


def test_orderbook_loader(tmp_path: Path) -> None:
    dataset_path = tmp_path / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    _write_orderbook_dataset(dataset_path)

    payload = load_orderbook_payload(
        dataset_path,
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
    )

    assert payload["schema_version"] == "1"
    assert payload["product_id"] == "ETH-USD"


def test_trades_loader_and_renderers(tmp_path: Path) -> None:
    dataset_path = tmp_path / "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    _write_orderbook_dataset(dataset_path)

    payload = load_trades_payload(
        dataset_path,
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
    )
    scatter = build_trades_scatter_view([payload])
    timeline = build_trade_volume_timeline_view([payload])

    assert isinstance(scatter, go.Figure)
    assert isinstance(timeline, go.Figure)
    assert len(scatter.data) > 0
    assert len(timeline.data) > 0


def test_simulation_loader_and_renderers(tmp_path: Path) -> None:
    dataset_path = (
        tmp_path / "ETH-USD-20240101.000000-0.01-simulation-best_size_changed.npz"
    )
    _write_simulation_dataset(dataset_path)

    arrays = load_simulation_arrays([dataset_path])
    fill_probability = build_fill_probability_view(arrays)
    mid_profit = build_mid_profit_view(arrays)
    micro_cost = build_micro_cost_fill_probability_view(
        arrays,
        render_options=PlotRenderOptions(cost=0.1),
    )

    assert arrays["schema_version"] == "1"
    assert isinstance(fill_probability, go.Figure)
    assert isinstance(mid_profit, go.Figure)
    assert isinstance(micro_cost, go.Figure)


def test_trades_renderer_accepts_dataframe() -> None:
    trade_frame = pd.DataFrame(
        {
            "Time": pd.to_datetime(["2024-01-01T00:00:00", "2024-01-01T00:00:01"]),
            "Price": [100.1, 100.2],
            "Volume": [1.0, 2.0],
            "Side": [-1.0, 1.0],
        }
    )
    trade_frame.attrs["product_id"] = "ETH-USD"

    figure = build_trades_scatter_view([trade_frame])
    assert isinstance(figure, go.Figure)
