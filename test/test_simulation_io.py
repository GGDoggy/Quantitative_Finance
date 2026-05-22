from pathlib import Path

import numpy as np

from src.simulation.io import (
    SIMULATION_METADATA_KEYS,
    SIMULATION_RESULT_KEYS,
    build_output_path,
    parse_dataset_groups,
    save_result_file,
)
from src.simulation.models import RawSimulationDataset, SimulationResult


def _build_result() -> SimulationResult:
    arrays = tuple(np.array([index], dtype=float) for index in range(len(SIMULATION_RESULT_KEYS)))
    return SimulationResult.from_algorithm_output(arrays)


def test_parse_dataset_groups_discovers_complete_batches(tmp_path: Path) -> None:
    (tmp_path / "level2-ETH-USD-init-20240101.010203.csv").write_text("1,2\n")
    (tmp_path / "level2-ETH-USD-updates-20240101.010203.csv").write_text("3,4\n")
    (tmp_path / "trade-ETH-USD-20240101.010203.csv").write_text("5,6\n")
    (tmp_path / "level2-ETH-USD-init-20240101.010204.csv").write_text("7,8\n")

    datasets = parse_dataset_groups(tmp_path)

    assert len(datasets) == 1
    assert datasets[0] == RawSimulationDataset(
        product_id="ETH-USD",
        timestamp="20240101.010203",
        file_stem="ETH-USD-20240101.010203",
        init=tmp_path / "level2-ETH-USD-init-20240101.010203.csv",
        updates=tmp_path / "level2-ETH-USD-updates-20240101.010203.csv",
        trade=tmp_path / "trade-ETH-USD-20240101.010203.csv",
    )


def test_build_output_path_matches_existing_filename_format(tmp_path: Path) -> None:
    output_file = build_output_path(
        tmp_path,
        "ETH-USD",
        "20240101.010203",
        0.01,
        "event_balanced",
        3.0,
    )
    assert output_file.name == "ETH-USD-20240101.010203-0.01-resolved-3.0-simulation-event_balanced.npz"


def test_save_result_file_preserves_metadata_and_payload_keys(tmp_path: Path) -> None:
    dataset = RawSimulationDataset(
        product_id="ETH-USD",
        timestamp="20240101.010203",
        file_stem="ETH-USD-20240101.010203",
        init=tmp_path / "level2-ETH-USD-init-20240101.010203.csv",
        updates=tmp_path / "level2-ETH-USD-updates-20240101.010203.csv",
        trade=tmp_path / "trade-ETH-USD-20240101.010203.csv",
    )
    output_file = tmp_path / "simulation.npz"

    save_result_file(
        output_file,
        algorithm_name="event_balanced",
        dataset=dataset,
        time_step=0.01,
        base_tick=1e-8,
        resolved_time=3.0,
        result=_build_result(),
    )

    with np.load(output_file, allow_pickle=False) as payload:
        assert set(SIMULATION_METADATA_KEYS).issubset(payload.files)
        assert set(SIMULATION_RESULT_KEYS).issubset(payload.files)
        assert payload["algorithm"] == "event_balanced"
        assert payload["product_id"] == "ETH-USD"
        assert payload["file_stem"] == "ETH-USD-20240101.010203"
