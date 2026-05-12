from pathlib import Path

import numpy as np
import pytest

from gui.data_catalog import PreprocessedDataset, discover_preprocessed_datasets, format_time_step


def _write_dataset(path: Path) -> None:
    np.savez_compressed(path, available_views=np.array(["orderbook"]))


def test_format_time_step_expands_scientific_notation() -> None:
    assert format_time_step(1e-05) == "0.00001"
    assert format_time_step("1e-05") == "0.00001"


def test_format_time_step_preserves_distinct_small_steps() -> None:
    assert format_time_step(0.001) == "0.001"
    assert format_time_step(0.011) == "0.011"
    assert format_time_step(0.014) == "0.014"


@pytest.mark.parametrize("time_step", [0, -0.01, "nan"])
def test_format_time_step_rejects_non_positive_or_non_finite_values(time_step: float | str) -> None:
    with pytest.raises(ValueError):
        format_time_step(time_step)


def test_discover_preprocessed_datasets_accepts_decimal_and_legacy_scientific_names(tmp_path: Path) -> None:
    decimal_path = tmp_path / "ETH-USD-20260203.040506-0.00001-orderbook_for_plot.npz"
    legacy_scientific_path = tmp_path / "ETH-USD-20260203.040506-1e-05-orderbook_for_plot.npz"
    _write_dataset(decimal_path)
    _write_dataset(legacy_scientific_path)

    datasets = discover_preprocessed_datasets(tmp_path)

    assert [dataset.path for dataset in datasets] == [decimal_path, legacy_scientific_path]
    assert [dataset.time_step for dataset in datasets] == [1e-05, 1e-05]


def test_preprocessed_dataset_display_name_uses_precise_time_step() -> None:
    first = PreprocessedDataset(
        product_id="ETH-USD",
        timestamp="20260203.040506",
        time_step=0.011,
        path=Path("first.npz"),
        available_views=("orderbook",),
    )
    second = PreprocessedDataset(
        product_id="ETH-USD",
        timestamp="20260203.040506",
        time_step=0.014,
        path=Path("second.npz"),
        available_views=("orderbook",),
    )

    assert "0.011s" in first.display_name
    assert "0.014s" in second.display_name
    assert first.display_name != second.display_name


def test_preprocess_batch_writes_normalized_time_step_filename(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from types import SimpleNamespace

    import gui.preprocess_service as preprocess_service
    from gui.data_catalog import RawBatch

    batch = RawBatch(
        product_id="ETH-USD",
        timestamp="20260203.040506",
        init_path=tmp_path / "init.csv",
        updates_path=tmp_path / "updates.csv",
        trade_path=tmp_path / "trade.csv",
    )
    spec = SimpleNamespace(
        required_payload_keys=("time",),
        preprocess_builder=lambda context: {"time": np.array([1.0])},
    )
    monkeypatch.setattr(preprocess_service, "PLOT_REGISTRY", {"orderbook": spec})
    monkeypatch.setattr(preprocess_service, "build_context", lambda batch, time_step: object())

    dataset = preprocess_service.preprocess_batch(batch, output_dir=tmp_path, time_step=1e-05)

    assert dataset.path.name == "ETH-USD-20260203.040506-0.00001-orderbook_for_plot.npz"
    assert dataset.path.exists()
