from pathlib import Path

import pytest

from src.preprocess.catalog import RawBatch
from src.simulation import simulate_raw_batch, simulate_raw_batches
from src.simulation.models import (
    LoadedMarketData,
    RawSimulationDataset,
    SimulationRequest,
    SimulationResult,
    SimulationWorkerPayload,
)
from src.simulation.runner import simulate_batch, simulate_batches, simulate_loaded_data


def _raw_batch(tmp_path: Path, timestamp: str = "20240101.010203") -> RawBatch:
    return RawBatch(
        product_id="ETH-USD",
        timestamp=timestamp,
        init_path=tmp_path / f"level2-ETH-USD-init-{timestamp}.csv",
        updates_path=tmp_path / f"level2-ETH-USD-updates-{timestamp}.csv",
        trade_path=tmp_path / f"trade-ETH-USD-{timestamp}.csv",
    )


def _loaded_data() -> LoadedMarketData:
    return LoadedMarketData(init=[[1.0]], updates=[[2.0]], trades=[[3.0]], start_time=0.0)


def _result() -> SimulationResult:
    values = tuple([float(index)] for index in range(26))
    return SimulationResult.from_algorithm_output(values)  # type: ignore[arg-type]


def test_simulate_loaded_data_accepts_request(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded_data = _loaded_data()
    request = SimulationRequest(
        algorithm="event_balanced",
        time_step=0.01,
        base_tick=1e-8,
        resolved_time=1.0,
    )

    monkeypatch.setattr(
        "src.simulation.runner.run_simulation_request",
        lambda request, data: _result(),
    )
    result = simulate_loaded_data(loaded_data, request)
    assert isinstance(result, SimulationResult)


def test_simulation_request_validates_numeric_fields() -> None:
    with pytest.raises(ValueError, match="time_step must be a positive finite value"):
        SimulationRequest(algorithm="event_balanced", time_step=0.0, base_tick=1e-8, resolved_time=1.0)

    with pytest.raises(ValueError, match="resolved_time must be a non-negative finite value"):
        SimulationRequest(algorithm="event_balanced", time_step=0.01, base_tick=1e-8, resolved_time=-1.0)


def test_runner_simulate_batch_runs_load_simulate_save_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_batch = _raw_batch(tmp_path)
    calls: list[str] = []

    def fake_load_raw_dataset(dataset):
        calls.append(f"load:{dataset.file_stem}")
        return _loaded_data()

    def fake_run_simulation_request(request, loaded_data):
        calls.append(f"simulate:{request.algorithm}")
        return _result()

    def fake_save_result(result, dataset, request, output_dir):
        calls.append(f"save:{dataset.file_stem}")
        return Path(output_dir) / "saved-file.npz"

    monkeypatch.setattr("src.simulation.runner.load_raw_dataset", fake_load_raw_dataset)
    monkeypatch.setattr("src.simulation.runner.run_simulation_request", fake_run_simulation_request)
    monkeypatch.setattr("src.simulation.runner.save_result", fake_save_result)

    request = SimulationRequest(
        algorithm="event_balanced",
        time_step=0.01,
        base_tick=1e-8,
        resolved_time=1.0,
    )
    result = simulate_batch(
        RawSimulationDataset(
            product_id=raw_batch.product_id,
            timestamp=raw_batch.timestamp,
            file_stem=f"{raw_batch.product_id}-{raw_batch.timestamp}",
            init_path=raw_batch.init_path,
            updates_path=raw_batch.updates_path,
            trade_path=raw_batch.trade_path,
        ),
        request,
        tmp_path,
    )

    assert result.output_path == tmp_path / "saved-file.npz"
    assert result.overwritten is False
    assert calls == [
        "load:ETH-USD-20240101.010203",
        "simulate:event_balanced",
        "save:ETH-USD-20240101.010203",
    ]
    assert result.dataset.file_stem == "ETH-USD-20240101.010203"


def test_runner_simulate_batches_preserves_input_order_for_parallel_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first_raw = _raw_batch(tmp_path, "20240101.010203")
    second_raw = _raw_batch(tmp_path, "20240101.010204")

    def fake_run_datasets_in_parallel(datasets, output_dir, request):
        assert request.algorithm == "event_balanced"
        return [
            SimulationWorkerPayload(
                file_stem=f"{second_raw.product_id}-{second_raw.timestamp}",
                output_file=str(output_dir / "second.npz"),
                overwritten=True,
            ),
            SimulationWorkerPayload(
                file_stem=f"{first_raw.product_id}-{first_raw.timestamp}",
                output_file=str(output_dir / "first.npz"),
                overwritten=False,
            ),
        ]

    monkeypatch.setattr("src.simulation.runner.run_datasets_in_parallel", fake_run_datasets_in_parallel)

    request = SimulationRequest(
        algorithm="event_balanced",
        time_step=0.01,
        base_tick=1e-8,
        resolved_time=1.0,
    )
    first = RawSimulationDataset(
        product_id=first_raw.product_id,
        timestamp=first_raw.timestamp,
        file_stem=f"{first_raw.product_id}-{first_raw.timestamp}",
        init_path=first_raw.init_path,
        updates_path=first_raw.updates_path,
        trade_path=first_raw.trade_path,
    )
    second = RawSimulationDataset(
        product_id=second_raw.product_id,
        timestamp=second_raw.timestamp,
        file_stem=f"{second_raw.product_id}-{second_raw.timestamp}",
        init_path=second_raw.init_path,
        updates_path=second_raw.updates_path,
        trade_path=second_raw.trade_path,
    )

    results = simulate_batches(
        [first, second],
        request,
        tmp_path,
    )

    assert [result.dataset.timestamp for result in results] == [
        "20240101.010203",
        "20240101.010204",
    ]
    assert [result.overwritten for result in results] == [False, True]


def test_service_simulate_raw_batch_runs_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_batch = _raw_batch(tmp_path)

    def fake_simulate_dataset_batch(dataset, request, output_dir):
        assert dataset.file_stem == "ETH-USD-20240101.010203"
        assert request.algorithm == "event_balanced"
        assert output_dir == tmp_path
        return SimulationWorkerPayload(
            file_stem=dataset.file_stem,
            output_file=str(tmp_path / "saved-file.npz"),
            overwritten=False,
        ).to_job_result(dataset)

    monkeypatch.setattr("src.simulation.service.simulate_dataset_batch", fake_simulate_dataset_batch)

    result = simulate_raw_batch(
        raw_batch,
        output_dir=tmp_path,
        algorithm_name="event_balanced",
        time_step=0.01,
    )

    assert result.output_path == tmp_path / "saved-file.npz"
    assert result.dataset.file_stem == "ETH-USD-20240101.010203"


def test_service_simulate_raw_batches_preserves_input_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = _raw_batch(tmp_path, "20240101.010203")
    second = _raw_batch(tmp_path, "20240101.010204")

    def fake_simulate_dataset_batches(datasets, request, output_dir):
        return [
            SimulationWorkerPayload(
                file_stem=datasets[1].file_stem,
                output_file=str(output_dir / "second.npz"),
                overwritten=True,
            ).to_job_result(datasets[1]),
            SimulationWorkerPayload(
                file_stem=datasets[0].file_stem,
                output_file=str(output_dir / "first.npz"),
                overwritten=False,
            ).to_job_result(datasets[0]),
        ]

    monkeypatch.setattr("src.simulation.service.simulate_dataset_batches", fake_simulate_dataset_batches)

    results = simulate_raw_batches(
        [first, second],
        output_dir=tmp_path,
        algorithm_name="event_balanced",
        time_step=0.01,
    )

    assert [result.dataset.timestamp for result in results] == [
        "20240101.010203",
        "20240101.010204",
    ]
