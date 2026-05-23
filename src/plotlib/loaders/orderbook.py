from __future__ import annotations

from pathlib import Path
import zipfile

import numpy as np

from src.plotlib.errors import PreprocessedDataError
from src.plotlib.types import OrderbookPayloadV1, normalize_orderbook_payload_to_v1


ORDERBOOK_REQUIRED_KEYS = ("price_axis", "time_axis", "data", "bid", "ask")
ORDERBOOK_OPTIONAL_KEYS = ("mid",)


def load_orderbook_payload(
    path: Path | str,
    *,
    product_id: str,
    timestamp: str,
    time_step: float,
) -> OrderbookPayloadV1:
    dataset_path = Path(path)
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Orderbook dataset file does not exist: {dataset_path}")

    try:
        with np.load(dataset_path, allow_pickle=False) as data:
            missing_keys = [key for key in ORDERBOOK_REQUIRED_KEYS if key not in data.files]
            if missing_keys:
                raise KeyError(
                    f"Orderbook dataset {dataset_path.name} is missing required key(s): "
                    f"{', '.join(missing_keys)}"
                )

            payload = {key: data[key] for key in ORDERBOOK_REQUIRED_KEYS}
            payload.update(
                {key: data[key] for key in ORDERBOOK_OPTIONAL_KEYS if key in data.files}
            )
    except KeyError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise PreprocessedDataError(
            f"Failed to load orderbook dataset {dataset_path.name}: {error}"
        ) from error

    payload["product_id"] = product_id
    payload["timestamp"] = timestamp
    payload["time_step"] = time_step
    return normalize_orderbook_payload_to_v1(payload)


def load_orderbook_payloads(
    datasets: list[tuple[Path | str, str, str, float]],
) -> list[OrderbookPayloadV1]:
    return [
        load_orderbook_payload(
            path,
            product_id=product_id,
            timestamp=timestamp,
            time_step=time_step,
        )
        for path, product_id, timestamp, time_step in datasets
    ]
