# `src.simulation` Internal Module

`src.simulation` is the only supported import surface for simulation code in this repo.

## Public API

- `list_algorithms()`: list registered algorithm names.
- `load_raw_dataset(dataset)`: load one raw CSV batch into memory.
- `simulate_loaded_data(...)`: run one algorithm against pre-loaded arrays.
- `simulate_batch(...)`: run one GUI-selected raw batch end to end.
- `simulate_batches(...)`: run multiple GUI-selected raw batches end to end.
- `save_result(...)`: serialize one simulation result to the standard `.npz` format.

## Internal Responsibilities

- `registry.py`: algorithm registration and lookup.
- `io.py`: filename construction, raw CSV loading, `.npz` serialization.
- `runner.py`: request execution and parallel batch orchestration.
- `service.py`: `RawBatch` adapter used by the dashboard.
- Algorithm modules: numeric logic only; no path handling or file output.

## GUI Usage

The dashboard should call only `src.simulation` exports. `service.py` handles
`RawBatch -> RawSimulationDataset` conversion internally so GUI code does not
need to import simulation internals.

## Unsupported Legacy Entrypoints

These are no longer supported and should not be reintroduced:

- `src.simulation.compat`
- `src.simulation.library`
- `python test/run_simulation.py`
