from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

from src.plotlib.types import normalize_simulation_arrays_to_v1

SIMULATION_REQUIRED_KEYS = (
    "bid_near_size",
    "bid_opp_size",
    "bid_mid_profit",
    "bid_micro_profit",
    "bid_result",
    "ask_near_size",
    "ask_opp_size",
    "ask_mid_profit",
    "ask_micro_profit",
    "ask_result",
)


def load_simulation_arrays(paths: Iterable[Path | str]):
    chunks = {key: [] for key in SIMULATION_REQUIRED_KEYS}

    for path in paths:
        with np.load(path, allow_pickle=False) as data:
            missing_keys = [key for key in SIMULATION_REQUIRED_KEYS if key not in data.files]
            if missing_keys:
                raise KeyError(f"Simulation file {Path(path).name} is missing required key(s): {', '.join(missing_keys)}")
            chunks["bid_near_size"].append(np.asarray(data["bid_near_size"], dtype=float))
            chunks["bid_opp_size"].append(np.asarray(data["bid_opp_size"], dtype=float))
            chunks["bid_mid_profit"].append(np.asarray(data["bid_mid_profit"], dtype=float))
            chunks["bid_micro_profit"].append(np.asarray(data["bid_micro_profit"], dtype=float))
            chunks["bid_result"].append(np.asarray(data["bid_result"], dtype=int))
            chunks["ask_near_size"].append(np.asarray(data["ask_near_size"], dtype=float))
            chunks["ask_opp_size"].append(np.asarray(data["ask_opp_size"], dtype=float))
            chunks["ask_mid_profit"].append(np.asarray(data["ask_mid_profit"], dtype=float))
            chunks["ask_micro_profit"].append(np.asarray(data["ask_micro_profit"], dtype=float))
            chunks["ask_result"].append(np.asarray(data["ask_result"], dtype=int))

    return normalize_simulation_arrays_to_v1(
        {
            "bid_near_size": np.concatenate(chunks["bid_near_size"]) if chunks["bid_near_size"] else np.array([], dtype=float),
            "bid_opp_size": np.concatenate(chunks["bid_opp_size"]) if chunks["bid_opp_size"] else np.array([], dtype=float),
            "bid_mid_profit": np.concatenate(chunks["bid_mid_profit"]) if chunks["bid_mid_profit"] else np.array([], dtype=float),
            "bid_micro_profit": np.concatenate(chunks["bid_micro_profit"]) if chunks["bid_micro_profit"] else np.array([], dtype=float),
            "bid_result": np.concatenate(chunks["bid_result"]) if chunks["bid_result"] else np.array([], dtype=int),
            "ask_near_size": np.concatenate(chunks["ask_near_size"]) if chunks["ask_near_size"] else np.array([], dtype=float),
            "ask_opp_size": np.concatenate(chunks["ask_opp_size"]) if chunks["ask_opp_size"] else np.array([], dtype=float),
            "ask_mid_profit": np.concatenate(chunks["ask_mid_profit"]) if chunks["ask_mid_profit"] else np.array([], dtype=float),
            "ask_micro_profit": np.concatenate(chunks["ask_micro_profit"]) if chunks["ask_micro_profit"] else np.array([], dtype=float),
            "ask_result": np.concatenate(chunks["ask_result"]) if chunks["ask_result"] else np.array([], dtype=int),
        }
    )


def load_simulation_arrays_from_metadata(
    simulation_paths: Iterable[Path | str],
):
    return load_simulation_arrays(simulation_paths)
