from __future__ import annotations

import pytest

from src.preprocess.exceptions import PreprocessValidationError
from src.preprocess.filenames import (
    format_time_step,
    is_preprocessed_filename,
    is_simulation_filename,
    match_preprocessed_filename,
    match_raw_level2_init_filename,
    match_raw_level2_updates_filename,
    match_raw_trade_filename,
    parse_simulation_filename,
    parse_timestamp,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (1, "1"),
        (0.01, "0.01"),
        ("1e-2", "0.01"),
        ("1.2300", "1.23"),
        ("1E-3", "0.001"),
    ),
)
def test_format_time_step_normalizes_supported_inputs(value, expected):
    assert format_time_step(value) == expected


@pytest.mark.parametrize("value", ("abc", 0, -1))
def test_format_time_step_rejects_invalid_inputs(value):
    with pytest.raises(PreprocessValidationError):
        format_time_step(value)


def test_parse_timestamp_accepts_valid_token():
    assert parse_timestamp("20240101.123456").strftime("%Y-%m-%d %H:%M:%S") == "2024-01-01 12:34:56"


def test_parse_timestamp_rejects_invalid_format():
    with pytest.raises(ValueError):
        parse_timestamp("2024-01-01 12:34:56")


def test_parse_simulation_filename_supports_resolved_token():
    metadata = parse_simulation_filename(
        "ETH-USD-20240101.000000-0.01-resolved-1e-2-simulation-event_balanced.npz"
    )

    assert metadata is not None
    assert metadata.resolved_time == 0.01
    assert metadata.resolved_time_token == "1e-2"
    assert metadata.algorithm_name == "event_balanced"


def test_parse_simulation_filename_supports_legacy_without_resolved_token():
    metadata = parse_simulation_filename(
        "ETH-USD-20240101.000000-0.01-simulation-event_balanced.npz"
    )

    assert metadata is not None
    assert metadata.resolved_time is None
    assert metadata.resolved_time_token is None


def test_filename_match_helpers_distinguish_supported_patterns():
    assert match_raw_level2_init_filename("level2-ETH-USD-init-20240101.000000.csv")
    assert match_raw_level2_updates_filename("level2-ETH-USD-updates-20240101.000000.csv")
    assert match_raw_trade_filename("trade-ETH-USD-20240101.000000.csv")
    assert match_preprocessed_filename("ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz")
    assert is_preprocessed_filename("ETH-USD-20240101.000000-0.01-orderbook_for_plot.npz")
    assert is_simulation_filename("ETH-USD-20240101.000000-0.01-simulation-event_balanced.npz")


def test_filename_match_helpers_reject_invalid_names():
    assert not match_raw_level2_init_filename("level2-ETH-USD-20240101.000000.csv")
    assert not match_raw_level2_updates_filename("level2-ETH-USD-init-20240101.000000.csv")
    assert not match_raw_trade_filename("trade-ETH-USD.csv")
    assert not match_preprocessed_filename("ETH-USD-20240101.000000-orderbook_for_plot.npz")
    assert not match_preprocessed_filename("ETH-USD-20240101.000000-0.01-other.npz")
    assert not is_preprocessed_filename("ETH-USD.txt")
    assert not is_simulation_filename("simulation-event_balanced.npz")
