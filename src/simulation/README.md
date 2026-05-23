# `src.simulation` Internal Module

`src.simulation` is the preferred import surface for simulation code in this repo.
Compatibility wrappers remain available while the rest of the repo finishes
moving off the old API.

## Public API

- `list_algorithms()`: list registered algorithm names.
- `load_raw_dataset(dataset)`: load one raw CSV batch into memory.
- `simulate_loaded_data(data, request)`: run one algorithm against pre-loaded arrays.
- `simulate_batch(dataset, request, output_dir)`: run one raw dataset end to end.
- `simulate_batches(datasets, request, output_dir)`: run multiple raw datasets end to end.
- `save_result(result, dataset, request, output_dir)`: serialize one simulation result to the standard `.npz` format.
- `simulate_raw_batch(...)` / `simulate_raw_batches(...)`: GUI adapters from `RawBatch`.

## Internal Responsibilities

- `registry.py`: algorithm registration and lookup.
- `io.py`: filename construction, raw CSV loading, `.npz` serialization.
- `runner.py`: request execution and parallel batch orchestration.
- `service.py`: `RawBatch` adapter used by the dashboard.
- Algorithm modules: numeric logic only; no path handling or file output.
- `compat.py`: temporary wrappers for the old dict-based API.
- `library.py`: transitional facade for legacy imports.

## GUI Usage

The dashboard should call only `src.simulation` exports. `service.py` handles
`RawBatch -> RawSimulationDataset` conversion internally so GUI code does not
need to import simulation internals.

## Legacy Entrypoints

These remain available during the migration:

- `src.simulation.compat`
- `src.simulation.library`
- `python test/run_simulation.py`
