from pathlib import Path
import math
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.preprocess.catalog import PreprocessedDataset, RawBatch
from src.simulation.service import simulate_batch, simulate_batches
import gui.plot as dashboard_module


def _make_raw_batch(tmp_path: Path, *, timestamp: str = "20240101.000000") -> RawBatch:
    init_path = tmp_path / f"level2-BTC-USD-init-{timestamp}.csv"
    updates_path = tmp_path / f"level2-BTC-USD-updates-{timestamp}.csv"
    trade_path = tmp_path / f"trade-BTC-USD-{timestamp}.csv"
    for path in (init_path, updates_path, trade_path):
        path.write_text("placeholder", encoding="utf-8")
    return RawBatch(
        product_id="BTC-USD",
        timestamp=timestamp,
        init_path=init_path,
        updates_path=updates_path,
        trade_path=trade_path,
    )


def test_simulate_batch_uses_raw_batch_and_reports_overwrite(tmp_path, monkeypatch):
    raw_batch = _make_raw_batch(tmp_path)
    captured = {}

    def fake_run_dataset_simulation(dataset, algorithm_name, time_step, base_tick, resolved_time):
        captured["dataset"] = dataset
        captured["algorithm_name"] = algorithm_name
        captured["time_step"] = time_step
        captured["base_tick"] = base_tick
        captured["resolved_time"] = resolved_time
        return ("simulation-result",)

    output_path = tmp_path / "simulation.npz"

    def fake_save_simulation_npz(
        dataset,
        output_dir,
        algorithm_name,
        time_step,
        base_tick,
        result,
        resolved_time,
    ):
        output_path.write_text("saved", encoding="utf-8")
        return output_path

    monkeypatch.setattr(
        "src.simulation.service.run_dataset_simulation",
        fake_run_dataset_simulation,
    )
    monkeypatch.setattr(
        "src.simulation.service.save_simulation_npz",
        fake_save_simulation_npz,
    )
    monkeypatch.setattr(
        "src.simulation.service.build_output_path",
        lambda *args, **kwargs: output_path,
    )

    first_result = simulate_batch(
        raw_batch,
        output_dir=tmp_path,
        algorithm_name="event_balanced",
        time_step=0.1,
        resolved_time=1.0,
    )
    second_result = simulate_batch(
        raw_batch,
        output_dir=tmp_path,
        algorithm_name="event_balanced",
        time_step=0.1,
        resolved_time=1.0,
    )

    assert captured["dataset"]["product_id"] == raw_batch.product_id
    assert captured["dataset"]["timestamp"] == raw_batch.timestamp
    assert captured["dataset"]["init"] == raw_batch.init_path
    assert captured["algorithm_name"] == "event_balanced"
    assert captured["time_step"] == 0.1
    assert captured["resolved_time"] == 1.0
    assert first_result.overwritten is False
    assert second_result.overwritten is True


def test_simulate_batches_validates_parameters_and_emits_progress(tmp_path, monkeypatch):
    raw_batch = _make_raw_batch(tmp_path)
    output_path = tmp_path / "simulation.npz"
    progress_messages = []

    monkeypatch.setattr(
        "src.simulation.service.run_dataset_simulation",
        lambda *args, **kwargs: ("simulation-result",),
    )
    monkeypatch.setattr(
        "src.simulation.service.save_simulation_npz",
        lambda *args, **kwargs: output_path,
    )
    monkeypatch.setattr(
        "src.simulation.service.build_output_path",
        lambda *args, **kwargs: output_path,
    )

    results = simulate_batches(
        [raw_batch],
        output_dir=tmp_path,
        algorithm_name="event_balanced",
        time_step=0.1,
        resolved_time=0.0,
        progress_callback=progress_messages.append,
    )

    assert len(results) == 1
    assert progress_messages[0].startswith("[1/1] simulating BTC-USD")
    assert progress_messages[1].startswith("saved simulation.npz")
    assert progress_messages[-1] == "Finished simulation for 1 batch(es)."

    try:
        simulate_batches(
            [raw_batch],
            output_dir=tmp_path,
            algorithm_name="event_balanced",
            time_step=0.0,
            resolved_time=1.0,
        )
    except ValueError as exc:
        assert "time_step" in str(exc)
    else:
        raise AssertionError("Expected invalid time_step to raise ValueError.")

    try:
        simulate_batches(
            [raw_batch],
            output_dir=tmp_path,
            algorithm_name="event_balanced",
            time_step=0.1,
            resolved_time=-1.0,
        )
    except ValueError as exc:
        assert "resolved_time" in str(exc)
    else:
        raise AssertionError("Expected invalid resolved_time to raise ValueError.")

    for parameter_name, kwargs in (
        ("time_step", {"time_step": math.nan, "resolved_time": 1.0}),
        ("resolved_time", {"time_step": 0.1, "resolved_time": math.inf}),
    ):
        try:
            simulate_batches(
                [raw_batch],
                output_dir=tmp_path,
                algorithm_name="event_balanced",
                **kwargs,
            )
        except ValueError as exc:
            assert parameter_name in str(exc)
            assert "finite" in str(exc)
        else:
            raise AssertionError(
                f"Expected non-finite {parameter_name} to raise ValueError."
            )


def test_dashboard_reports_blank_simulation_parameters(tmp_path, monkeypatch):
    raw_batch = _make_raw_batch(tmp_path)

    monkeypatch.setattr(
        dashboard_module,
        "discover_raw_batches",
        lambda raw_dir, preprocessed_dir: [raw_batch],
    )
    monkeypatch.setattr(
        dashboard_module,
        "discover_preprocessed_datasets",
        lambda preprocessed_dir: [],
    )

    called = {"simulate": False}

    def fake_simulate_batches(*args, **kwargs):
        called["simulate"] = True
        return []

    monkeypatch.setattr(dashboard_module, "simulate_batches", fake_simulate_batches)

    dashboard = dashboard_module.OrderbookDashboard(tmp_path, tmp_path)
    dashboard.simulation_raw_select.value = [raw_batch.display_name]
    dashboard.simulation_algorithm_select.value = "event_balanced"
    dashboard.simulation_resolved_time_input.value = 1.0
    dashboard.simulation_time_step_input.value = None

    dashboard._handle_simulation(None)

    assert called["simulate"] is False
    assert dashboard.simulation_button.disabled is False
    assert dashboard.simulation_button.loading is False
    assert dashboard.status.alert_type == "danger"
    assert "Simulation time_step is required" in dashboard.status.object
    assert "Simulation time_step is required" in dashboard.simulation_progress.object


def test_dashboard_rejects_non_finite_simulation_parameters(tmp_path, monkeypatch):
    raw_batch = _make_raw_batch(tmp_path)

    monkeypatch.setattr(
        dashboard_module,
        "discover_raw_batches",
        lambda raw_dir, preprocessed_dir: [raw_batch],
    )
    monkeypatch.setattr(
        dashboard_module,
        "discover_preprocessed_datasets",
        lambda preprocessed_dir: [],
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("simulate_batches should not run")

    monkeypatch.setattr(dashboard_module, "simulate_batches", fail_if_called)

    dashboard = dashboard_module.OrderbookDashboard(tmp_path, tmp_path)
    dashboard.simulation_raw_select.value = [raw_batch.display_name]
    dashboard.simulation_resolved_time_input.value = math.nan
    dashboard.simulation_time_step_input.value = 0.1

    dashboard._handle_simulation(None)

    assert dashboard.status.alert_type == "danger"
    assert "Simulation resolved_time must be finite" in dashboard.status.object
    assert dashboard.simulation_button.disabled is False


def test_dashboard_refresh_and_run_simulation_use_all_raw_batches(tmp_path, monkeypatch):
    pending_batch = _make_raw_batch(tmp_path, timestamp="20240101.000000")
    preprocessed_batch = RawBatch(
        product_id="BTC-USD",
        timestamp="20240101.010000",
        init_path=tmp_path / "level2-BTC-USD-init-20240101.010000.csv",
        updates_path=tmp_path / "level2-BTC-USD-updates-20240101.010000.csv",
        trade_path=tmp_path / "trade-BTC-USD-20240101.010000.csv",
        is_preprocessed=True,
    )
    for path in (
        preprocessed_batch.init_path,
        preprocessed_batch.updates_path,
        preprocessed_batch.trade_path,
    ):
        path.write_text("placeholder", encoding="utf-8")

    discovered_datasets = [
        PreprocessedDataset(
            product_id="BTC-USD",
            timestamp="20240101.010000",
            time_step=0.01,
            path=tmp_path / "BTC-USD-20240101.010000-0.01-orderbook_for_plot.npz",
            available_views=("orderbook", "fill_probability"),
            time_step_token="0.01",
            resolved_time=1.0,
            resolved_time_token="1",
            algorithm_name="event_balanced",
            simulation_path=tmp_path
            / "BTC-USD-20240101.010000-0.01-resolved-1-simulation-event_balanced.npz",
        )
    ]

    monkeypatch.setattr(
        dashboard_module,
        "discover_raw_batches",
        lambda raw_dir, preprocessed_dir: [pending_batch, preprocessed_batch],
    )
    monkeypatch.setattr(
        dashboard_module,
        "discover_preprocessed_datasets",
        lambda preprocessed_dir: discovered_datasets,
    )

    called = {}

    def fake_simulate_batches(
        raw_batches,
        *,
        output_dir,
        algorithm_name,
        time_step,
        resolved_time,
        progress_callback,
    ):
        called["raw_batches"] = raw_batches
        called["output_dir"] = output_dir
        called["algorithm_name"] = algorithm_name
        called["time_step"] = time_step
        called["resolved_time"] = resolved_time
        progress_callback("saved fake-simulation.npz")
        return []

    monkeypatch.setattr(dashboard_module, "simulate_batches", fake_simulate_batches)

    dashboard = dashboard_module.OrderbookDashboard(tmp_path, tmp_path)
    assert len(dashboard.raw_select.options) == 1
    assert len(dashboard.simulation_raw_select.options) == 2
    assert dashboard.simulation_algorithm_select.visible is True

    dashboard.simulation_algorithm_select.value = "event_balanced"
    assert dashboard.simulation_time_step_input.visible is False

    dashboard.simulation_algorithm_select.value = (
        "time_averaged_random_cancellation"
    )
    assert dashboard.simulation_time_step_input.visible is True

    dashboard.simulation_raw_select.value = [preprocessed_batch.display_name]
    dashboard.simulation_algorithm_select.value = "event_balanced"
    assert dashboard.simulation_time_step_input.visible is False
    dashboard.simulation_time_step_input.value = 0.1
    dashboard.simulation_resolved_time_input.value = 5.0
    dashboard._handle_simulation(None)

    assert called["raw_batches"] == [preprocessed_batch]
    assert called["output_dir"] == tmp_path
    assert called["algorithm_name"] == "event_balanced"
    assert called["time_step"] == 0.1
    assert called["resolved_time"] == 5.0


def test_dashboard_can_focus_fill_probability_group(tmp_path, monkeypatch):
    simulation_path = (
        tmp_path / "BTC-USD-20240101.010000-0.01-resolved-1-simulation-event_balanced.npz"
    )
    dataset = PreprocessedDataset(
        product_id="BTC-USD",
        timestamp="20240101.010000",
        time_step=0.01,
        path=tmp_path / "BTC-USD-20240101.010000-0.01-orderbook_for_plot.npz",
        available_views=("orderbook", "fill_probability"),
        time_step_token="0.01",
        resolved_time=1.0,
        resolved_time_token="1",
        algorithm_name="event_balanced",
        simulation_path=simulation_path,
    )

    monkeypatch.setattr(
        dashboard_module,
        "discover_raw_batches",
        lambda raw_dir, preprocessed_dir: [],
    )
    monkeypatch.setattr(
        dashboard_module,
        "discover_preprocessed_datasets",
        lambda preprocessed_dir: [dataset],
    )

    dashboard = dashboard_module.OrderbookDashboard(tmp_path, tmp_path)
    dashboard._select_fill_probability_dataset(dataset)

    assert dashboard.product_select.value == "BTC-USD"
    assert dashboard.plot_select.value == dashboard._plot_label_for_type("fill_probability")
    assert dashboard.fill_group_select.value == dashboard._fill_probability_group_value(
        dashboard._fill_probability_group_key(dataset)
    )
