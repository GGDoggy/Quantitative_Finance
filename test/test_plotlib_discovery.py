from __future__ import annotations

from pathlib import Path

from src.plotlib.discovery import (
    find_simulation_files,
    parse_simulation_filename,
)


def test_parse_simulation_filename_variants() -> None:
    metadata = parse_simulation_filename(
        "ETH-USD-20240101.000000-0.01-resolved-2.5-simulation-best_size_changed.npz"
    )

    assert metadata is not None
    assert metadata.product_id == "ETH-USD"
    assert metadata.time_step == 0.01
    assert metadata.resolved_time == 2.5
    assert metadata.algorithm_name == "best_size_changed"

    metadata_without_resolved = parse_simulation_filename(
        "ETH-USD-20240101.000000-0.01-simulation-event_balanced.npz"
    )
    assert metadata_without_resolved is not None
    assert metadata_without_resolved.resolved_time is None

    assert parse_simulation_filename("ETH-USD-invalid-simulation.npz") is None


def test_find_simulation_files_matches_time_step_resolved_time_and_algorithm(
    tmp_path: Path,
) -> None:
    matching = tmp_path / (
        "ETH-USD-20240101.000000-0.01-resolved-2.5-simulation-best_size_changed.npz"
    )
    wrong_algorithm = tmp_path / (
        "ETH-USD-20240101.000000-0.01-resolved-2.5-simulation-event_balanced.npz"
    )
    default_resolved = tmp_path / (
        "ETH-USD-20240101.000000-0.01-simulation-best_size_changed.npz"
    )
    other_time_step = tmp_path / (
        "ETH-USD-20240101.000000-0.02-resolved-2.5-simulation-best_size_changed.npz"
    )
    for path in (matching, wrong_algorithm, default_resolved, other_time_step):
        path.write_bytes(b"placeholder")

    found = find_simulation_files(
        tmp_path,
        "ETH-USD",
        "20240101.000000",
        0.01,
        resolved_time=2.5,
        algorithm_name="best_size_changed",
    )
    assert found == (matching,)

    found_without_resolved_filter = find_simulation_files(
        tmp_path,
        "ETH-USD",
        "20240101.000000",
        0.01,
        algorithm_name="best_size_changed",
    )
    assert found_without_resolved_filter == tuple(sorted((default_resolved, matching)))
