"""Application bootstrap helpers and default paths for the dashboard package."""

from __future__ import annotations

from pathlib import Path

import holoviews as hv
import panel as pn

from .dashboard import OrderbookDashboard
from .styles import DASHBOARD_CSS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "v3"
PREPROCESSED_DIR = PROJECT_ROOT / "data" / "preprocessed"
DASHBOARD_SETTINGS_PATH = PROJECT_ROOT / "gui" / "dashboard_settings.json"


def build_app():
    """Initialize Panel extensions and build the dashboard template."""
    hv.extension("bokeh")
    pn.extension("plotly", raw_css=[DASHBOARD_CSS])
    dashboard = OrderbookDashboard(
        RAW_DATA_DIR,
        PREPROCESSED_DIR,
        DASHBOARD_SETTINGS_PATH,
        PROJECT_ROOT,
    )
    return dashboard.view()


def main() -> None:
    """Serve the dashboard as a local Panel application."""
    pn.serve(build_app, title="Orderbook Viewer", show=True)
