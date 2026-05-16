from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from gui.plot import OrderbookDashboard
from src.plots.profit_heatmap import compute_profit_grid, _shared_profit_limit
from src.preprocess.catalog import PreprocessedDataset


def test_compute_profit_grid_averages_only_finite_profit_samples():
    near_size = np.array([0.01, 0.02, 1.0, 2.0])
    opp_size = np.array([0.02, 0.03, 1.0, 2.0])
    profit = np.array([1.0, 3.0, np.nan, -2.0])

    _near_edges, _opp_edges, mean_profit, sample_count = compute_profit_grid(
        near_size,
        opp_size,
        profit,
        bins=2,
    )

    expected_mean_profit = np.array(
        [
            [2.0, np.nan],
            [np.nan, -2.0],
        ]
    )
    expected_sample_count = np.array(
        [
            [2.0, 0.0],
            [0.0, 1.0],
        ]
    )

    np.testing.assert_allclose(mean_profit, expected_mean_profit, equal_nan=True)
    np.testing.assert_allclose(sample_count, expected_sample_count, equal_nan=True)


def test_shared_profit_limit_uses_symmetric_absolute_maximum():
    bid_profit = np.array([[np.nan, -1.5], [0.0, 2.0]])
    ask_profit = np.array([[1.0, np.nan], [-3.5, 0.5]])

    assert _shared_profit_limit(bid_profit, ask_profit) == 3.5


def test_dashboard_selects_simulation_group_for_profit_plots(tmp_path):
    dataset = PreprocessedDataset(
        product_id="BTC-USD",
        timestamp="20240101.000000",
        time_step=0.1,
        path=tmp_path / "BTC-USD-20240101.000000-0.1-orderbook_for_plot.npz",
        available_views=("fill_probability", "mid_profit", "micro_profit"),
        time_step_token="0.1",
        resolved_time=5.0,
        resolved_time_token="5",
        algorithm_name="algo_a",
        simulation_path=tmp_path
        / "BTC-USD-20240101.000000-0.1-resolved-5-simulation-algo_a.npz",
    )

    dashboard = OrderbookDashboard(tmp_path / "raw", tmp_path / "preprocessed")
    dashboard.preprocessed_datasets = [dataset]

    dashboard.product_select.options = {"BTC-USD": "BTC-USD"}
    dashboard.product_select.value = "BTC-USD"
    dashboard.plot_select.options = {"Mid Profit": "Mid Profit"}
    dashboard.plot_select.value = "Mid Profit"

    dashboard._sync_timestamp_options(render=False)

    assert dashboard.timestamp_select.visible is False
    assert dashboard.timestamp_select.disabled is True
    assert dashboard.fill_group_select.visible is True
    assert dashboard.fill_group_select.disabled is False
    assert dashboard._selectable_option_values(dashboard.fill_group_select.options)
