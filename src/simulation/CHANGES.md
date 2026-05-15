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
