from src.preprocess.catalog import find_simulation_files, has_simulation_file


def _touch(path):
    path.write_bytes(b"")


def test_find_simulation_files_matches_legacy_without_resolved_token(tmp_path):
    _touch(tmp_path / "ETH-USD-20240101.000000-0.01-simulation-event_balanced.npz")

    matches = find_simulation_files(
        tmp_path,
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
        resolved_time=1.0,
        algorithm_name="event_balanced",
    )

    assert len(matches) == 1


def test_find_simulation_files_resolved_fallback_can_be_injected(tmp_path):
    _touch(tmp_path / "ETH-USD-20240101.000000-0.01-simulation-event_balanced.npz")

    default_matches = find_simulation_files(
        tmp_path,
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
        resolved_time=2.0,
        algorithm_name="event_balanced",
    )
    injected_matches = find_simulation_files(
        tmp_path,
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
        resolved_time=2.0,
        algorithm_name="event_balanced",
        resolved_time_fallback=2.0,
    )

    assert default_matches == ()
    assert len(injected_matches) == 1
    assert has_simulation_file(
        tmp_path,
        "ETH-USD",
        "20240101.000000",
        0.01,
        resolved_time_fallback=2.0,
    )


def test_find_simulation_files_matches_equivalent_resolved_time_tokens(tmp_path):
    _touch(tmp_path / "ETH-USD-20240101.000000-0.01-resolved-1e-2-simulation-event_balanced.npz")

    matches = find_simulation_files(
        tmp_path,
        product_id="ETH-USD",
        timestamp="20240101.000000",
        time_step=0.01,
        resolved_time=0.01,
        resolved_time_token="0.01",
        algorithm_name="event_balanced",
    )

    assert len(matches) == 1
