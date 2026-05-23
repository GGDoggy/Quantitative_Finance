# `src.simulation` Internal Module

`src.simulation` is the preferred import surface for simulation code in this repo.
New code should import only from `src.simulation`. Compatibility wrappers remain
available only for legacy scripts that have not migrated yet.

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
- `compat.py`: legacy wrappers for the old dict-based API. Do not add new imports.
- `library.py`: transitional facade for legacy imports. Do not add new imports.

## GUI Usage

The dashboard should call only `src.simulation` exports. `service.py` handles
`RawBatch -> RawSimulationDataset` conversion internally so GUI code does not
need to import simulation internals.

## Packaging

Use editable install when working inside this repo:

```bash
pip install -e .
```

Example preferred imports:

```python
from src.simulation import SimulationRequest, list_algorithms, simulate_batch
```

## Legacy Entrypoints

These remain available during the migration:

- `src.simulation.compat`
- `src.simulation.library`
- `python test/run_simulation.py`
