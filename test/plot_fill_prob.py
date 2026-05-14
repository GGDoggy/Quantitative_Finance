from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


PREPROCESSED_PATH = Path("data/preprocessed")
FILE_PATTERN = "*simulation*.npz"
BINS = 20
SIZE_RANGE = (1e-3, 10.0)
RESOLVED_ONLY = True
LOG_SPACED_BINS = True


def list_simulation_files(preprocessed_path, pattern):
    return sorted(Path(preprocessed_path).glob(pattern))


def parse_selection(selection, file_count):
    selection = selection.strip().lower()
    if selection == "all":
        return list(range(file_count))

    chosen = []
    for token in selection.split(","):
        token = token.strip()
        if not token:
            continue
        if not token.isdigit():
            raise ValueError(f"Invalid selection token: {token}")
        index = int(token) - 1
        if index < 0 or index >= file_count:
            raise ValueError(f"Selection out of range: {token}")
        chosen.append(index)

    if not chosen:
        raise ValueError("No file selected.")
    return sorted(set(chosen))


def prompt_file_selection(files):
    print("Available simulation files:")
    for index, path in enumerate(files, start=1):
        print(f"[{index}] {path.name}")
    print("Enter a number, comma-separated numbers, or 'all'.")

    while True:
        raw = input("Selection: ")
        try:
            selected_indices = parse_selection(raw, len(files))
            return [files[index] for index in selected_indices]
        except ValueError as exc:
            print(exc)


def load_simulation_arrays(paths):
    bid_near_size = []
    bid_opp_size = []
    bid_result = []
    ask_near_size = []
    ask_opp_size = []
    ask_result = []

    for path in paths:
        with np.load(path) as data:
            bid_near_size.append(np.asarray(data["bid_near_size"], dtype=float))
            bid_opp_size.append(np.asarray(data["bid_opp_size"], dtype=float))
            bid_result.append(np.asarray(data["bid_result"], dtype=int))
            ask_near_size.append(np.asarray(data["ask_near_size"], dtype=float))
            ask_opp_size.append(np.asarray(data["ask_opp_size"], dtype=float))
            ask_result.append(np.asarray(data["ask_result"], dtype=int))

    return (
        np.concatenate(bid_near_size) if bid_near_size else np.array([], dtype=float),
        np.concatenate(bid_opp_size) if bid_opp_size else np.array([], dtype=float),
        np.concatenate(bid_result) if bid_result else np.array([], dtype=int),
        np.concatenate(ask_near_size) if ask_near_size else np.array([], dtype=float),
        np.concatenate(ask_opp_size) if ask_opp_size else np.array([], dtype=float),
        np.concatenate(ask_result) if ask_result else np.array([], dtype=int),
    )


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

    if LOG_SPACED_BINS:
        if SIZE_RANGE[0] <= 0 or SIZE_RANGE[1] <= 0:
            raise ValueError("Log-spaced bins require a strictly positive SIZE_RANGE.")
        near_edges = np.geomspace(*SIZE_RANGE, bins + 1)
        opp_edges = np.geomspace(*SIZE_RANGE, bins + 1)
    else:
        near_edges = np.linspace(*SIZE_RANGE, bins + 1)
        opp_edges = np.linspace(*SIZE_RANGE, bins + 1)

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


def plot_heatmap(ax, near_edges, opp_edges, values, title, cmap, vmin=None, vmax=None):
    mesh = ax.pcolormesh(
        near_edges,
        opp_edges,
        values.T,
        shading="auto",
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
    )
    ax.set_title(title)
    ax.set_xlabel("Near Size")
    ax.set_ylabel("Opp Size")
    if LOG_SPACED_BINS:
        ax.set_xscale("log")
        ax.set_yscale("log")
    return mesh


def plot_fill_probability(ax, near_size, opp_size, result, title, bins):
    near_edges, opp_edges, fill_probability, sample_count = compute_fill_probability_grid(
        near_size,
        opp_size,
        result,
        bins,
    )
    mesh = plot_heatmap(
        ax,
        near_edges,
        opp_edges,
        fill_probability,
        title,
        "viridis",
        vmin=0.0,
        vmax=1.0,
    )
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
    return mesh, sample_count


def plot_sample_count(ax, near_size, opp_size, result, title, bins):
    near_edges, opp_edges, _, sample_count = compute_fill_probability_grid(
        near_size,
        opp_size,
        result,
        bins,
    )
    mesh = plot_heatmap(
        ax,
        near_edges,
        opp_edges,
        sample_count,
        title,
        "magma",
    )
    ax.text(
        0.02,
        0.98,
        f"total samples: {int(sample_count.sum())}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none"},
    )
    return mesh


if __name__ == "__main__":
    files = list_simulation_files(PREPROCESSED_PATH, FILE_PATTERN)
    if not files:
        raise FileNotFoundError(f"No simulation files found in {PREPROCESSED_PATH} matching {FILE_PATTERN}.")

    selected_files = prompt_file_selection(files)
    (
        bid_near_size,
        bid_opp_size,
        bid_result,
        ask_near_size,
        ask_opp_size,
        ask_result,
    ) = load_simulation_arrays(selected_files)

    fig, axes = plt.subplots(2, 2, figsize=(14, 12), constrained_layout=True)
    bid_prob_mesh, _ = plot_fill_probability(
        axes[0, 0],
        bid_near_size,
        bid_opp_size,
        bid_result,
        "Bid Fill Probability",
        BINS,
    )
    ask_prob_mesh, _ = plot_fill_probability(
        axes[0, 1],
        ask_near_size,
        ask_opp_size,
        ask_result,
        "Ask Fill Probability",
        BINS,
    )
    bid_count_mesh = plot_sample_count(
        axes[1, 0],
        bid_near_size,
        bid_opp_size,
        bid_result,
        "Bid Sample Count",
        BINS,
    )
    ask_count_mesh = plot_sample_count(
        axes[1, 1],
        ask_near_size,
        ask_opp_size,
        ask_result,
        "Ask Sample Count",
        BINS,
    )

    fig.colorbar(bid_prob_mesh, ax=axes[0, 0], label="Fill Probability")
    fig.colorbar(ask_prob_mesh, ax=axes[0, 1], label="Fill Probability")
    fig.colorbar(bid_count_mesh, ax=axes[1, 0], label="Sample Count")
    fig.colorbar(ask_count_mesh, ax=axes[1, 1], label="Sample Count")
    plt.show()
