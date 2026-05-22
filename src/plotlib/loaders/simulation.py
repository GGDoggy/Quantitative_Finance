from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

from src.plotlib.discovery import find_simulation_files
from src.plotlib.types import normalize_simulation_arrays_to_v1
from src.preprocess.catalog import PlotDatasetLocator

SIMULATION_REQUIRED_KEYS = (
    "bid_near_size",
    "bid_opp_size",
    "bid_result",
    "ask_near_size",
    "ask_opp_size",
    "ask_result",
)


def resolve_simulation_path(locator: PlotDatasetLocator) -> Path:
    if locator.simulation_path is not None:
        return locator.simulation_path

    candidates = find_simulation_files(
        locator.preprocessed_dir,
        locator.product_id,
        locator.timestamp,
        locator.time_step,
        locator.time_step_token,
        locator.resolved_time,
        locator.resolved_time_token,
        locator.algorithm_name,
    )
    if not candidates:
        raise FileNotFoundError(f"No fill probability simulation file found for {locator.base_id}")
    if len(candidates) > 1:
        candidate_names = ", ".join(path.name for path in candidates)
        raise FileExistsError(
            f"Multiple fill probability simulation files found for {locator.base_id}. "
            f"Specify resolved_time/algorithm metadata or choose an explicit file: {candidate_names}"
        )
    return candidates[0]


def load_simulation_arrays(paths: Iterable[Path | str]):
    chunks = {key: [] for key in SIMULATION_REQUIRED_KEYS}

    for path in paths:
        with np.load(path, allow_pickle=False) as data:
            missing_keys = [key for key in SIMULATION_REQUIRED_KEYS if key not in data.files]
            if missing_keys:
                raise KeyError(f"Simulation file {Path(path).name} is missing required key(s): {', '.join(missing_keys)}")
            chunks["bid_near_size"].append(np.asarray(data["bid_near_size"], dtype=float))
            chunks["bid_opp_size"].append(np.asarray(data["bid_opp_size"], dtype=float))
            chunks["bid_result"].append(np.asarray(data["bid_result"], dtype=int))
            chunks["ask_near_size"].append(np.asarray(data["ask_near_size"], dtype=float))
            chunks["ask_opp_size"].append(np.asarray(data["ask_opp_size"], dtype=float))
            chunks["ask_result"].append(np.asarray(data["ask_result"], dtype=int))

    return normalize_simulation_arrays_to_v1(
        {
            "bid_near_size": np.concatenate(chunks["bid_near_size"]) if chunks["bid_near_size"] else np.array([], dtype=float),
            "bid_opp_size": np.concatenate(chunks["bid_opp_size"]) if chunks["bid_opp_size"] else np.array([], dtype=float),
            "bid_result": np.concatenate(chunks["bid_result"]) if chunks["bid_result"] else np.array([], dtype=int),
            "ask_near_size": np.concatenate(chunks["ask_near_size"]) if chunks["ask_near_size"] else np.array([], dtype=float),
            "ask_opp_size": np.concatenate(chunks["ask_opp_size"]) if chunks["ask_opp_size"] else np.array([], dtype=float),
            "ask_result": np.concatenate(chunks["ask_result"]) if chunks["ask_result"] else np.array([], dtype=int),
            "bid_mid_profit": np.array([], dtype=float),
            "ask_mid_profit": np.array([], dtype=float),
            "bid_micro_profit": np.array([], dtype=float),
            "ask_micro_profit": np.array([], dtype=float),
        }
    )
