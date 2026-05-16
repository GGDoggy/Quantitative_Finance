# CHANGES

## Upcoming simulation output changes

The simulation output is extended with evolved quote prices and profit metrics.

### New simulation parameter

Simulation callers can pass a new `resolved_time` parameter to `run_dataset_simulation(...)` or directly to a simulation algorithm.
If omitted, simulations use `DEFAULT_RESOLVED_TIME`.

`resolved_time` is the fixed number of seconds after an order is filled.
For each filled virtual order, the simulation looks up the best quote at:

```text
order_fill_time + resolved_time
```

### New output fields

Filled orders include evolved mid/micro prices and mid/micro profit metrics when a complete quote is available at or before the target time.
Unfilled, canceled, unresolved, incomplete-quote, or out-of-range records are emitted as `np.nan` for these new fields.

### Saved output identity

Saved simulation `.npz` filenames and metadata now include `resolved_time` so runs with different evolved-quote horizons do not overwrite or mask one another.

When callers save both the default horizon and any non-default `resolved_time` for the same dataset, time step, and algorithm, the additional filename component can create multiple `.npz` files that still match `src/plots/discovery.py`'s `find_simulation_files(...)` filter when discovery only checks product, timestamp, and time step. In that scenario, `src/plots/fill_probability.py` can raise `FileExistsError` before plotting, so multi-horizon simulation outputs require discovery to parse or filter by `resolved_time` and likely `algorithm`.
