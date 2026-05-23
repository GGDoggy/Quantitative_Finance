from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import src.simulation as simulation
import src.simulation.compat as compat
import src.simulation.library as library


def test_cli_and_compat_modules_import() -> None:
    wrapper_path = Path(__file__).resolve().parents[1] / "test" / "run_simulation.py"
    spec = spec_from_file_location("run_simulation_wrapper", wrapper_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.main)
    assert callable(compat.parse_selection)
    assert callable(library.run_dataset_simulation)
    assert callable(simulation.simulate_raw_batches)


def test_top_level_simulation_exports_only_official_api() -> None:
    assert callable(simulation.list_algorithms)
    assert callable(simulation.load_raw_dataset)
    assert callable(simulation.simulate_batch)
    assert callable(simulation.simulate_batches)
    assert callable(simulation.save_result)
    assert not hasattr(simulation, "run_dataset_simulation")
    assert not hasattr(simulation, "run_datasets_in_parallel")
    assert not hasattr(simulation, "save_simulation_npz")
    assert not hasattr(simulation, "parse_dataset_groups")
    assert not hasattr(simulation, "get_algorithm_names")
