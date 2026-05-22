from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.preprocess import RawBatch
from src.preprocess.service import preprocess_batch


@dataclass(frozen=True)
class StubBuilderSpec:
    preprocess_builder: object
    required_payload_keys: tuple[str, ...]


def _make_batch(tmp_path: Path) -> RawBatch:
    timestamp = "20240101.000000"
    product_id = "ETH-USD"
    for name in (
        f"level2-{product_id}-init-{timestamp}.csv",
        f"level2-{product_id}-updates-{timestamp}.csv",
        f"trade-{product_id}-{timestamp}.csv",
    ):
        (tmp_path / name).write_text("header\n", encoding="utf-8")

    return RawBatch(
        product_id=product_id,
        timestamp=timestamp,
        init_path=tmp_path / f"level2-{product_id}-init-{timestamp}.csv",
        updates_path=tmp_path / f"level2-{product_id}-updates-{timestamp}.csv",
        trade_path=tmp_path / f"trade-{product_id}-{timestamp}.csv",
    )


def test_preprocess_batch_default_registry_output_is_unchanged(tmp_path, monkeypatch):
    batch = _make_batch(tmp_path)
    output_dir = tmp_path / "out"

    monkeypatch.setattr("src.preprocess.service.build_context", lambda *_args: object())

    default_registry = {
        "orderbook": StubBuilderSpec(
            preprocess_builder=lambda _context: {
                "price_axis": np.array([1.0]),
                "time_axis": np.array([2.0]),
                "data": np.array([[3.0]]),
                "bid": np.array([[4.0]]),
                "ask": np.array([[5.0]]),
            },
            required_payload_keys=("price_axis", "time_axis", "data", "bid", "ask"),
        ),
        "ignored": StubBuilderSpec(
            preprocess_builder=lambda _context: {"x": np.array([1.0])},
            required_payload_keys=("missing",),
        ),
    }
    monkeypatch.setattr(
        "src.preprocess.service.get_default_builder_registry",
        lambda: default_registry,
    )

    dataset = preprocess_batch(batch, output_dir=output_dir, time_step=0.01)

    assert dataset.path.name == "ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz"
    assert dataset.available_views == ("orderbook",)

    with np.load(dataset.path, allow_pickle=False) as data:
        assert tuple(data["available_views"].tolist()) == ("orderbook",)
        assert {"price_axis", "time_axis", "data", "bid", "ask"}.issubset(data.files)


def test_preprocess_batch_with_stub_registry_writes_available_views(tmp_path, monkeypatch):
    batch = _make_batch(tmp_path)
    output_dir = tmp_path / "out"

    monkeypatch.setattr("src.preprocess.service.build_context", lambda *_args: object())

    stub_registry = {
        "mini_view": StubBuilderSpec(
            preprocess_builder=lambda _context: {"k": np.array([42])},
            required_payload_keys=("k",),
        ),
    }

    dataset = preprocess_batch(
        batch,
        output_dir=output_dir,
        time_step=0.01,
        builder_registry=stub_registry,
    )

    assert dataset.available_views == ("mini_view",)
    with np.load(dataset.path, allow_pickle=False) as data:
        assert data["k"].tolist() == [42]
        assert tuple(data["available_views"].tolist()) == ("mini_view",)
