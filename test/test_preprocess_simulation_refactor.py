from pathlib import Path

import numpy as np

from src.dataset_artifacts import build_simulation_output_path
from src.preprocess import PLOT_REGISTRY, preprocess_batch
from src.raw_batches import discover_raw_batches
from src.simulation import SimulationRequest, build_output_path, load_raw_dataset


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _make_raw_batch_dir(tmp_path: Path) -> Path:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write(raw_dir / "level2-ETH-USD-init-20260523.120000.csv", "100,1,-1\n101,1,1\n")
    _write(
        raw_dir / "level2-ETH-USD-updates-20260523.120000.csv",
        "43200,100,2,-1\n43200.01,101,2,1\n",
    )
    _write(raw_dir / "trade-ETH-USD-20260523.120000.csv", "43200,100,1,1\n")
    return raw_dir


def test_preprocess_batch_writes_preprocessed_artifact(tmp_path: Path) -> None:
    raw_dir = _make_raw_batch_dir(tmp_path)
    output_dir = tmp_path / "preprocessed"
    output_dir.mkdir()
    batch = discover_raw_batches(raw_dir)[0]

    dataset = preprocess_batch(
        batch,
        output_dir=output_dir,
        builder_registry=PLOT_REGISTRY,
    )

    assert dataset.path.exists()
    with np.load(dataset.path, allow_pickle=False) as payload:
        assert "price_axis" in payload.files
        assert "trade_time" in payload.files
        assert "available_views" in payload.files


def test_simulation_build_output_path_uses_dataset_artifacts_tokens(tmp_path: Path) -> None:
    simulation_path = build_output_path(
        tmp_path,
        "ETH-USD",
        "20260523.120000",
        1.0,
        "event_balanced",
        1.0,
    )

    expected = build_simulation_output_path(
        tmp_path,
        "ETH-USD",
        "20260523.120000",
        1.0,
        "event_balanced",
        1.0,
    )
    assert simulation_path == expected


def test_simulation_load_raw_dataset_accepts_raw_batch(tmp_path: Path) -> None:
    raw_dir = _make_raw_batch_dir(tmp_path)
    batch = discover_raw_batches(raw_dir)[0]
    request = SimulationRequest(
        algorithm="event_balanced",
        time_step=0.01,
        base_tick=1e-8,
        resolved_time=1.0,
    )

    loaded = load_raw_dataset(batch)

    assert loaded.init
    assert loaded.updates
    assert loaded.trades
    assert request.algorithm == "event_balanced"
