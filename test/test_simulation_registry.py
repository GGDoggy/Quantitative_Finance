import pytest

from src.simulation import list_algorithms
from src.simulation.registry import get_algorithm


def test_list_algorithms_returns_registered_names() -> None:
    assert list_algorithms() == [
        "time_averaged_random_cancellation",
        "event_balanced",
        "best_size_changed",
    ]


def test_get_algorithm_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown simulation algorithm"):
        get_algorithm("does_not_exist")
