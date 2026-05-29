"""Shared constants and visual settings for the Panel dashboard UI."""

from __future__ import annotations


DASHBOARD_CSS = """
:root {
  --qf-bg: #020617;
  --qf-surface: #0b1220;
  --qf-surface-elevated: #111827;
  --qf-border: rgba(148, 163, 184, 0.22);
  --qf-primary: #22d3ee;
  --qf-accent: #3b82f6;
  --qf-success: #22c55e;
  --qf-warning: #f59e0b;
  --qf-danger: #f43f5e;
  --qf-text: #e5eefb;
  --qf-muted: #94a3b8;
}

body, .bk, .pn-template {
  background: radial-gradient(circle at top left, rgba(34, 211, 238, 0.10), transparent 28rem),
    linear-gradient(135deg, #020617 0%, #07111f 45%, #030712 100%) !important;
  color: var(--qf-text) !important;
}

.pn-template .pn-wrapper, .pn-template .main {
  background: transparent !important;
}

.qf-dashboard-header {
  padding: 1rem 1.25rem;
  border: 1px solid var(--qf-border);
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(17, 24, 39, 0.88));
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.32);
}

.qf-eyebrow {
  margin: 0 0 0.35rem;
  color: var(--qf-primary);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.qf-title h1, .qf-section-title h2 {
  margin: 0;
  color: #f8fafc;
}

.qf-title p, .qf-section-subtitle {
  color: var(--qf-muted);
}

.qf-card {
  border: 1px solid var(--qf-border) !important;
  border-radius: 16px !important;
  background: rgba(15, 23, 42, 0.78) !important;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.24) !important;
  backdrop-filter: blur(14px);
  overflow: visible !important;
}

.qf-card .card-header {
  border-bottom: 1px solid var(--qf-border) !important;
  background: linear-gradient(90deg, rgba(34, 211, 238, 0.12), rgba(59, 130, 246, 0.08)) !important;
  color: #f8fafc !important;
  font-weight: 700;
}

.qf-card .card-body {
  padding: 1rem !important;
  overflow: visible !important;
}

.qf-plot-controls {
  position: relative;
  z-index: 30;
}

.qf-button-row {
  gap: 0.75rem;
  justify-content: flex-end;
}

.qf-plot-workspace {
  min-height: 620px;
  position: relative;
  z-index: 1;
}

.qf-main-plot-card {
  min-height: 620px;
}

.qf-plot-result {
  min-height: 560px;
  width: 100%;
}

.qf-fill-probability-card {
  min-height: 1660px;
}

.qf-fill-probability-result {
  min-height: 1560px;
}

.qf-plot-tabs {
  width: 100%;
}

.qf-status-card .alert-success {
  border-color: rgba(34, 197, 94, 0.45);
}

.qf-status-card .alert-warning {
  border-color: rgba(245, 158, 11, 0.55);
}

.qf-status-card .alert-danger {
  border-color: rgba(244, 63, 94, 0.55);
}

.qf-card button, .qf-dashboard-header button {
  border-radius: 999px !important;
  font-weight: 700 !important;
}

.qf-card label, .qf-card .bk-input-group label {
  color: var(--qf-muted) !important;
  font-weight: 650;
}

.qf-card .bk-input, .qf-card .bk-input-group, .qf-card select {
  color: var(--qf-text) !important;
}

@media (max-width: 900px) {
  .qf-dashboard-header {
    padding: 0.9rem;
  }

  .qf-responsive-row {
    flex-direction: column !important;
    align-items: stretch !important;
  }

  .qf-plot-workspace, .qf-main-plot-card {
    min-height: 460px;
  }

  .qf-plot-result {
    min-height: 420px;
  }

  .qf-fill-probability-card {
    min-height: 1320px;
  }

  .qf-fill-probability-result {
    min-height: 1240px;
  }
}
"""

PLOTLY_DARK_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(2, 6, 23, 0)",
    "plot_bgcolor": "rgba(15, 23, 42, 0.92)",
    "font": {"color": "#e5eefb"},
    "margin": {"l": 56, "r": 32, "t": 54, "b": 48},
}

PRODUCT_PLACEHOLDER = "Select a product..."
PLOT_PLACEHOLDER = "Select a plot..."
TIMESTAMP_PLACEHOLDER = "Select a timestamp..."
FILL_GROUP_PLACEHOLDER = "Select a simulation group..."
DEPTH_PLACEHOLDER = "Select a depth..."

SIMULATION_HEATMAP_PLOT_TYPES = {
    "fill_probability",
    "mid_profit",
    "micro_profit",
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
}

COST_FILTERED_PLOT_TYPES = {
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
}

SIMULATION_SETTINGS_GROUP_BY_PLOT = {
    "fill_probability": "fill_probability",
    "mid_profit": "profit",
    "micro_profit": "profit",
    "mid_fill_probability_cost": "conditional_fill_probability",
    "micro_fill_probability_cost": "conditional_fill_probability",
}
