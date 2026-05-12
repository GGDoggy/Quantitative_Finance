import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SIMULATION_PATH = ROOT / "src" / "simulation" / "random_cancelation.py"
DATA_PATH = "data/v3/"
FILE_STEM = "ETH-USD-20260421.035228"
TIME_STEP = 0.01
BASE_TICK = 0.00000001
BINS = 20
RESOLVED_ONLY = True


def load_simulation_module():
    spec = importlib.util.spec_from_file_location("random_cancelation", SIMULATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compute_fill_probability_grid(near_size, opp_size, result, bins):
    near_size = np.asarray(near_size, dtype=float)
    opp_size = np.asarray(opp_size, dtype=float)
    result = np.asarray(result, dtype=int)

    finite_mask = np.isfinite(near_size) & np.isfinite(opp_size)
    if RESOLVED_ONLY:
        valid_mask = finite_mask & (result != -1)
    else:
        valid_mask = finite_mask

    near_size = near_size[valid_mask]
    opp_size = opp_size[valid_mask]
    result = result[valid_mask]

    if len(near_size) == 0:
        raise ValueError("No valid orders available for fill probability plotting.")

    near_edges = np.linspace(near_size.min(), near_size.max(), bins + 1)
    opp_edges = np.linspace(opp_size.min(), opp_size.max(), bins + 1)

    total_count, _, _ = np.histogram2d(near_size, opp_size, bins=[near_edges, opp_edges])
    fill_count, _, _ = np.histogram2d(
        near_size[result == 1],
        opp_size[result == 1],
        bins=[near_edges, opp_edges],
    )

    fill_probability = np.divide(
        fill_count,
        total_count,
        out=np.full_like(fill_count, np.nan, dtype=float),
        where=total_count > 0,
    )
    return near_edges, opp_edges, fill_probability, total_count


def plot_fill_probability(ax, near_size, opp_size, result, title, bins):
    near_edges, opp_edges, fill_probability, sample_count = compute_fill_probability_grid(
        near_size,
        opp_size,
        result,
        bins,
    )
    mesh = ax.pcolormesh(
        near_edges,
        opp_edges,
        fill_probability.T,
        shading="auto",
        cmap="viridis",
        vmin=0.0,
        vmax=1.0,
    )
    ax.set_title(title)
    ax.set_xlabel("Near Size")
    ax.set_ylabel("Opp Size")
    ax.text(
        0.02,
        0.98,
        f"valid bins: {np.sum(sample_count > 0)}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none"},
    )
    return mesh


if __name__ == "__main__":
    simulation = load_simulation_module()

    init = simulation.read_csv(
        f"{DATA_PATH}level2-{FILE_STEM.replace('-2026', '-init-2026')}.csv"
    )
    updates = simulation.read_csv(
        f"{DATA_PATH}level2-{FILE_STEM.replace('-2026', '-updates-2026')}.csv"
    )
    trades = simulation.read_csv(f"{DATA_PATH}trade-{FILE_STEM}.csv")
    start_time = simulation.file_time_to_unix(FILE_STEM.split("-")[-1])

    (
        bid_prices,
        bid_near_size,
        bid_opp_size,
        bid_survival_time,
        bid_ahead,
        bid_behind,
        bid_vorder_ratio,
        bid_result,
        ask_prices,
        ask_near_size,
        ask_opp_size,
        ask_survival_time,
        ask_ahead,
        ask_behind,
        ask_vorder_ratio,
        ask_result,
    ) = simulation.simulate_virtual_best_orders(
        init,
        updates,
        trades,
        start_time,
        time_step=TIME_STEP,
        base_tick=BASE_TICK,
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    bid_mesh = plot_fill_probability(
        axes[0],
        bid_near_size,
        bid_opp_size,
        bid_result,
        "Bid Fill Probability",
        BINS,
    )
    ask_mesh = plot_fill_probability(
        axes[1],
        ask_near_size,
        ask_opp_size,
        ask_result,
        "Ask Fill Probability",
        BINS,
    )

    fig.colorbar(bid_mesh, ax=axes[0], label="Fill Probability")
    fig.colorbar(ask_mesh, ax=axes[1], label="Fill Probability")
    plt.show()
