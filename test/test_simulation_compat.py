from pathlib import Path

import numpy as np

from src.simulation.compat import (
    format_dataset_line,
    get_algorithm_names,
    is_processed,
    parse_dataset_groups,
    parse_selection,
    run_datasets_in_parallel,
    run_dataset_simulation,
    save_simulation_npz,
)
from src.simulation.models import RawSimulationDataset, SimulationWorkerPayload


def _legacy_dataset(tmp_path: Path, timestamp: str = "20240101.010203") -> dict[str, object]:
    return {
        "product_id": "ETH-USD",
        "timestamp": timestamp,
        "file_stem": f"ETH-USD-{timestamp}",
        "init": tmp_path / f"level2-ETH-USD-init-{timestamp}.csv",
        "updates": tmp_path / f"level2-ETH-USD-updates-{timestamp}.csv",
        "trade": tmp_path / f"trade-ETH-USD-{timestamp}.csv",
    }


def test_compat_parse_dataset_groups_returns_legacy_dicts(tmp_path: Path) -> None:
    (tmp_path / "level2-ETH-USD-init-20240101.010203.csv").write_text("1,2\n")
    (tmp_path / "level2-ETH-USD-updates-20240101.010203.csv").write_text("3,4\n")
    (tmp_path / "trade-ETH-USD-20240101.010203.csv").write_text("5,6\n")

    datasets = parse_dataset_groups(tmp_path)

    assert datasets == [_legacy_dataset(tmp_path)]


def test_compat_helpers_match_legacy_behavior(tmp_path: Path) -> None:
    dataset = _legacy_dataset(tmp_path)

    assert get_algorithm_names() == [
        "time_averaged_random_cancellation",
        "event_balanced",
        "best_size_changed",
    ]
    assert format_dataset_line(1, dataset, tmp_path, 0.01, "event_balanced").startswith("[1] ETH-USD-20240101.010203 -> ")
    assert parse_selection("1,2,2", 3) == [0, 1]
    assert is_processed(dataset, tmp_path, 0.01, "event_balanced") is False


def test_compat_run_dataset_simulation_accepts_dict_dataset(tmp_path: Path, monkeypatch) -> None:
    dataset = _legacy_dataset(tmp_path)

    def fake_load_raw_dataset(normalized):
        assert normalized.file_stem == "ETH-USD-20240101.010203"
        return type("Loaded", (), {"init": [[1.0]], "updates": [[2.0]], "trades": [[3.0]], "start_time": 0.0})()

    def fake_simulate_loaded_data(loaded_data, request):
        return type(
            "Result",
            (),
            {"as_tuple": lambda self: tuple(np.array([index], dtype=float) for index in range(26))},
        )()

    monkeypatch.setattr("src.simulation.compat.load_raw_dataset", fake_load_raw_dataset)
    monkeypatch.setattr("src.simulation.compat.simulate_loaded_data", fake_simulate_loaded_data)

    result = run_dataset_simulation(dataset, "event_balanced", 0.01, 1e-8)

    assert len(result) == 26


def test_compat_save_and_parallel_wrappers_accept_old_shapes(tmp_path: Path, monkeypatch) -> None:
    dataset = _legacy_dataset(tmp_path)
    arrays = tuple(np.array([index], dtype=float) for index in range(26))

    output_path = save_simulation_npz(
        dataset,
        tmp_path,
        "event_balanced",
        0.01,
        1e-8,
        arrays,
    )

    assert output_path.name == "ETH-USD-20240101.010203-0.01-resolved-1.0-simulation-event_balanced.npz"

    normalized = RawSimulationDataset(
        product_id="ETH-USD",
        timestamp="20240101.010203",
        file_stem="ETH-USD-20240101.010203",
        init_path=Path("init.csv"),
        updates_path=Path("updates.csv"),
        trade_path=Path("trade.csv"),
    )

    def fake_run_datasets_in_parallel(datasets, output_dir, request):
        assert datasets[0].file_stem == normalized.file_stem
        return [
            SimulationWorkerPayload(
                file_stem=normalized.file_stem,
                output_file=str(Path(output_dir) / "saved-file.npz"),
                overwritten=True,
            )
        ]

    monkeypatch.setattr("src.simulation.compat.run_dataset_jobs_in_parallel", fake_run_datasets_in_parallel)

    results = run_datasets_in_parallel([dataset], tmp_path, "event_balanced", 0.01, 1e-8)

    assert results == [
        {
            "file_stem": "ETH-USD-20240101.010203",
            "output_file": str(tmp_path / "saved-file.npz"),
            "overwritten": True,
        }
    ]
