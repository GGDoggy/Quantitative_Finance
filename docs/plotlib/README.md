# `src.plotlib`

`src.plotlib` is the only plotting library entrypoint in the current repository.

Its responsibilities are intentionally narrow:

- expose a stable plotting public API
- accept already-preprocessed payloads or simulation arrays
- return view objects that the Panel dashboard can render directly
- stay decoupled from `gui` and `src.preprocess`

The old `src.plots` package has already been removed. See [src_plots_migration.md](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/src_plots_migration.md).

## Module map

```text
src/plotlib/
|-- __init__.py          # public exports
|-- views.py             # public builder facade
|-- types.py             # payload schema v1 and normalize helpers
|-- options.py           # render options and heatmap settings
|-- errors.py            # domain-specific exceptions
|-- discovery.py         # simulation filename parsing and lookup
|-- loaders/             # .npz -> payload loaders
`-- renderers/           # actual plotting implementations
```

## Boundary

`src.plotlib` should not depend on:

- `gui`
- `src.preprocess`

App-level integration lives in:

- [`src/app_plot_registry.py`](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/src/app_plot_registry.py)
- [`src/app_plot_adapters.py`](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/src/app_plot_adapters.py)

The flow is:

1. `src.preprocess` and `src.simulation` produce `.npz` outputs.
2. `src.app_plot_adapters` converts app datasets into `src.plotlib.loaders` inputs.
3. `src.plotlib` loads normalized payloads and builds plot views.

## Supported plots

Public builders exported by `src.plotlib`:

- `build_orderbook_view`
- `build_trades_scatter_view`
- `build_trade_volume_timeline_view`
- `build_fill_probability_view`
- `build_mid_profit_view`
- `build_micro_profit_view`
- `build_mid_cost_fill_probability_view`
- `build_micro_cost_fill_probability_view`

These fall into two groups:

- Market-data plots:
  - Orderbook
  - Trades Scatter
  - Trade Volume Timeline
- Simulation heatmaps:
  - Fill Probability
  - Mid Profit
  - Micro Profit
  - Cost-filtered Fill Probability

## Returned view types

`src.plotlib` returns native plotting objects instead of wrapping everything in a custom view class:

- orderbook returns a `holoviews` overlay / dynamic map
- trades and simulation plots return `plotly.graph_objects.Figure`

This keeps the dashboard side simple: the caller usually passes the returned object directly into Panel.

## Example

### Orderbook

```python
from pathlib import Path

from src.plotlib import build_orderbook_view
from src.plotlib.loaders import load_orderbook_payload

payload = load_orderbook_payload(
    Path("data/preprocessed/ETH-USD-20250521.120000-orderbook_for_plot.npz"),
    product_id="ETH-USD",
    timestamp="20250521.120000",
    time_step=0.01,
)

view = build_orderbook_view([payload])
```

### Simulation heatmap with render options

```python
from src.plotlib import (
    FillProbabilityPlotSettings,
    HeatmapAxisSettings,
    PlotRenderOptions,
    build_fill_probability_view,
)
from src.plotlib.loaders import load_simulation_arrays

arrays = load_simulation_arrays([
    "data/preprocessed/ETH-USD-20250521.120000-0.01-simulation-event_balanced.npz",
])

options = PlotRenderOptions(
    simulation_heatmap_settings=FillProbabilityPlotSettings(
        axis=HeatmapAxisSettings(
            size_min=1e-3,
            size_max=10.0,
            shared_bins=24,
            use_log_bins=True,
        )
    )
)

figure = build_fill_probability_view(arrays, render_options=options)
```

## Related docs

- [API Reference](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/plotlib/api.md)
- [Architecture](/C:/Users/tedhu/Desktop/prog/python/Quantitative_Finance/docs/plotlib/architecture.md)
