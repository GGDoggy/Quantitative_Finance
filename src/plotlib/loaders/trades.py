from __future__ import annotations

from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from src.plotlib.errors import PreprocessedDataError
from src.plotlib.types import TradesPayloadV1, normalize_trades_payload_to_v1


TRADE_REQUIRED_KEYS = ("trade_time", "trade_price", "trade_volume", "trade_side")


def load_trades_payload(
    path: Path | str,
    *,
    product_id: str,
    timestamp: str,
    time_step: float,
) -> TradesPayloadV1:
    dataset_path = Path(path)
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Trade dataset file does not exist: {dataset_path}")

    try:
        with np.load(dataset_path, allow_pickle=False) as data:
            missing_keys = [key for key in TRADE_REQUIRED_KEYS if key not in data.files]
            if missing_keys:
                raise KeyError(
                    f"Trade dataset {dataset_path.name} is missing required key(s): "
                    f"{', '.join(missing_keys)}"
                )
            trade_time = pd.to_datetime(np.asarray(data["trade_time"]))
            payload = {
                "trade_time": trade_time.to_numpy(),
                "trade_price": np.asarray(data["trade_price"], dtype=float),
                "trade_volume": np.asarray(data["trade_volume"], dtype=float),
                "trade_side": np.asarray(data["trade_side"], dtype=float),
            }
    except KeyError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise PreprocessedDataError(
            f"Failed to load trade dataset {dataset_path.name}: {error}"
        ) from error

    return normalize_trades_payload_to_v1(
        {
            "product_id": product_id,
            "timestamp": timestamp,
            "time_step": time_step,
            **payload,
        }
    )


def load_trades_payloads(
    datasets: list[tuple[Path | str, str, str, float]],
) -> list[TradesPayloadV1]:
    return [
        load_trades_payload(
            path,
            product_id=product_id,
            timestamp=timestamp,
            time_step=time_step,
        )
        for path, product_id, timestamp, time_step in datasets
    ]
