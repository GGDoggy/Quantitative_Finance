from __future__ import annotations

from typing import Literal, TypedDict

import numpy as np

SchemaVersionV1 = Literal["1"]


class OrderbookPayloadV1(TypedDict):
    schema_version: SchemaVersionV1
    product_id: str
    timestamp: str
    time_step: float
    price_axis: np.ndarray
    time_axis: np.ndarray
    data: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    mid: np.ndarray


class TradesPayloadV1(TypedDict):
    schema_version: SchemaVersionV1
    product_id: str
    timestamp: str
    time_step: float
    trade_time: np.ndarray
    trade_price: np.ndarray
    trade_volume: np.ndarray
    trade_side: np.ndarray


class SimulationArraysV1(TypedDict):
    schema_version: SchemaVersionV1
    bid_near_size: np.ndarray
    bid_opp_size: np.ndarray
    bid_result: np.ndarray
    ask_near_size: np.ndarray
    ask_opp_size: np.ndarray
    ask_result: np.ndarray
    bid_mid_profit: np.ndarray
    ask_mid_profit: np.ndarray
    bid_micro_profit: np.ndarray
    ask_micro_profit: np.ndarray


def normalize_orderbook_payload_to_v1(payload: dict[str, object]) -> OrderbookPayloadV1:
    bid = np.asarray(payload["bid"])
    ask = np.asarray(payload["ask"])
    mid_payload = payload.get("mid")
    mid = np.asarray(mid_payload) if mid_payload is not None else 0.5 * (bid + ask)

    return {
        "schema_version": "1",
        "product_id": str(payload["product_id"]),
        "timestamp": str(payload["timestamp"]),
        "time_step": float(payload["time_step"]),
        "price_axis": np.asarray(payload["price_axis"]),
        "time_axis": np.asarray(payload["time_axis"]),
        "data": np.asarray(payload["data"]),
        "bid": bid,
        "ask": ask,
        "mid": mid,
    }


def normalize_trades_payload_to_v1(payload: dict[str, object]) -> TradesPayloadV1:
    return {
        "schema_version": "1",
        "product_id": str(payload["product_id"]),
        "timestamp": str(payload["timestamp"]),
        "time_step": float(payload["time_step"]),
        "trade_time": np.asarray(payload["trade_time"]),
        "trade_price": np.asarray(payload["trade_price"]),
        "trade_volume": np.asarray(payload["trade_volume"]),
        "trade_side": np.asarray(payload["trade_side"]),
    }


def normalize_simulation_arrays_to_v1(payload: dict[str, np.ndarray]) -> SimulationArraysV1:
    normalized = {k: np.asarray(v) for k, v in payload.items()}
    normalized["schema_version"] = "1"
    return normalized  # type: ignore[return-value]
