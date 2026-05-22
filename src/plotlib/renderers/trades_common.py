from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from src.plotlib.errors import PayloadSchemaVersionError
from src.plotlib.types import TradesPayloadV1


SIDE_LABELS = {-1.0: "buy taker", 1.0: "sell taker"}
SIDE_COLORS = {-1.0: "#0FB353", 1.0: "#E23E1E"}


def extract_trades(
    items: Sequence[TradesPayloadV1 | pd.DataFrame],
) -> tuple[pd.DataFrame, str]:
    frames: list[pd.DataFrame] = []
    product_ids = set()

    for item in items:
        if isinstance(item, pd.DataFrame):
            required_columns = {"Time", "Price", "Volume", "Side"}
            missing_columns = required_columns - set(item.columns)
            if missing_columns:
                raise KeyError(
                    f"Trade frame is missing required column(s): {', '.join(sorted(missing_columns))}"
                )
            trade_frame = item.copy()
        else:
            if item.get("schema_version") != "1":
                raise PayloadSchemaVersionError(
                    "trades payload", "1", item.get("schema_version")
                )
            trade_frame = pd.DataFrame(
                {
                    "Time": pd.to_datetime(item["trade_time"]),
                    "Price": np.asarray(item["trade_price"], dtype=float),
                    "Volume": np.asarray(item["trade_volume"], dtype=float),
                    "Side": np.asarray(item["trade_side"], dtype=float),
                }
            )
            trade_frame.attrs["product_id"] = item["product_id"]

        product_id = trade_frame.attrs.get("product_id")
        if product_id is None:
            raise ValueError("Loaded trade frames must include a product_id in DataFrame.attrs.")
        product_ids.add(str(product_id))
        frames.append(trade_frame)

    if not frames:
        raise ValueError("Selected datasets do not contain trade data.")
    if len(product_ids) != 1:
        raise ValueError("Trade views only support datasets from one product at a time.")

    trade_frame = pd.concat(frames, ignore_index=True).sort_values("Time")
    if trade_frame.empty:
        raise ValueError("Selected datasets do not contain trade rows.")
    return trade_frame, next(iter(product_ids))
