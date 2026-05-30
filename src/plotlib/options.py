from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


DEFAULT_SIZE_MIN = 1e-3
DEFAULT_SIZE_MAX = 10.0
DEFAULT_SHARED_BINS = 20


@dataclass(frozen=True)
class HeatmapAxisSettings:
    size_min: float = DEFAULT_SIZE_MIN
    size_max: float = DEFAULT_SIZE_MAX
    shared_bins: int = DEFAULT_SHARED_BINS
    use_log_bins: bool = True


@dataclass(frozen=True)
class ManualColorRange:
    min: float
    max: float


@dataclass(frozen=True)
class OptionalColorRange:
    auto: bool = True
    min: float | None = None
    max: float | None = None
    use_log_color_scale: bool = False


@dataclass(frozen=True)
class OptionalSymmetricColorRange:
    auto: bool = True
    limit: float | None = None


@dataclass(frozen=True)
class FillProbabilityPlotSettings:
    axis: HeatmapAxisSettings = HeatmapAxisSettings()
    metric_range: ManualColorRange = ManualColorRange(min=0.0, max=1.0)
    sample_count_range: OptionalColorRange = OptionalColorRange()


@dataclass(frozen=True)
class ProfitPlotSettings:
    axis: HeatmapAxisSettings = HeatmapAxisSettings()
    metric_limit: OptionalSymmetricColorRange = OptionalSymmetricColorRange()
    sample_count_range: OptionalColorRange = OptionalColorRange()


@dataclass(frozen=True)
class ConditionalFillProbabilityPlotSettings:
    axis: HeatmapAxisSettings = HeatmapAxisSettings()
    metric_range: ManualColorRange = ManualColorRange(min=0.0, max=1.0)
    sample_count_range: OptionalColorRange = OptionalColorRange()


SimulationHeatmapSettings = (
    FillProbabilityPlotSettings
    | ProfitPlotSettings
    | ConditionalFillProbabilityPlotSettings
)


@dataclass(frozen=True)
class DashboardSimulationHeatmapSettings:
    fill_probability: FillProbabilityPlotSettings = FillProbabilityPlotSettings()
    profit: ProfitPlotSettings = ProfitPlotSettings()
    conditional_fill_probability: ConditionalFillProbabilityPlotSettings = (
        ConditionalFillProbabilityPlotSettings()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> DashboardSimulationHeatmapSettings:
        if not isinstance(payload, dict):
            return cls()
        return cls(
            fill_probability=_fill_probability_settings_from_dict(
                payload.get("fill_probability")
            ),
            profit=_profit_settings_from_dict(payload.get("profit")),
            conditional_fill_probability=_conditional_settings_from_dict(
                payload.get("conditional_fill_probability")
            ),
        )


@dataclass(frozen=True)
class PlotRenderOptions:
    cost: float | None = None
    simulation_heatmap_settings: SimulationHeatmapSettings | None = None
    simulation_depth: int | None = None


def _read_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _read_float(value: Any, default: float | None) -> float | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _axis_settings_from_dict(payload: Any) -> HeatmapAxisSettings:
    if not isinstance(payload, dict):
        return HeatmapAxisSettings()
    size_min = _read_float(payload.get("size_min"), DEFAULT_SIZE_MIN)
    size_max = _read_float(payload.get("size_max"), DEFAULT_SIZE_MAX)
    return HeatmapAxisSettings(
        size_min=DEFAULT_SIZE_MIN if size_min is None else size_min,
        size_max=DEFAULT_SIZE_MAX if size_max is None else size_max,
        shared_bins=_read_int(payload.get("shared_bins"), DEFAULT_SHARED_BINS),
        use_log_bins=_read_bool(payload.get("use_log_bins"), True),
    )


def _manual_range_from_dict(
    payload: Any, *, default_min: float, default_max: float
) -> ManualColorRange:
    if not isinstance(payload, dict):
        return ManualColorRange(min=default_min, max=default_max)
    min_value = _read_float(payload.get("min"), default_min)
    max_value = _read_float(payload.get("max"), default_max)
    return ManualColorRange(
        min=default_min if min_value is None else min_value,
        max=default_max if max_value is None else max_value,
    )


def _optional_range_from_dict(payload: Any) -> OptionalColorRange:
    if not isinstance(payload, dict):
        return OptionalColorRange()
    return OptionalColorRange(
        auto=_read_bool(payload.get("auto"), True),
        min=_read_float(payload.get("min"), None),
        max=_read_float(payload.get("max"), None),
        use_log_color_scale=_read_bool(payload.get("use_log_color_scale"), False),
    )


def _optional_symmetric_range_from_dict(payload: Any) -> OptionalSymmetricColorRange:
    if not isinstance(payload, dict):
        return OptionalSymmetricColorRange()
    return OptionalSymmetricColorRange(
        auto=_read_bool(payload.get("auto"), True),
        limit=_read_float(payload.get("limit"), None),
    )


def _fill_probability_settings_from_dict(payload: Any) -> FillProbabilityPlotSettings:
    if not isinstance(payload, dict):
        return FillProbabilityPlotSettings()
    return FillProbabilityPlotSettings(
        axis=_axis_settings_from_dict(payload.get("axis")),
        metric_range=_manual_range_from_dict(
            payload.get("metric_range"),
            default_min=0.0,
            default_max=1.0,
        ),
        sample_count_range=_optional_range_from_dict(payload.get("sample_count_range")),
    )


def _profit_settings_from_dict(payload: Any) -> ProfitPlotSettings:
    if not isinstance(payload, dict):
        return ProfitPlotSettings()
    return ProfitPlotSettings(
        axis=_axis_settings_from_dict(payload.get("axis")),
        metric_limit=_optional_symmetric_range_from_dict(payload.get("metric_limit")),
        sample_count_range=_optional_range_from_dict(payload.get("sample_count_range")),
    )


def _conditional_settings_from_dict(
    payload: Any,
) -> ConditionalFillProbabilityPlotSettings:
    if not isinstance(payload, dict):
        return ConditionalFillProbabilityPlotSettings()
    return ConditionalFillProbabilityPlotSettings(
        axis=_axis_settings_from_dict(payload.get("axis")),
        metric_range=_manual_range_from_dict(
            payload.get("metric_range"),
            default_min=0.0,
            default_max=1.0,
        ),
        sample_count_range=_optional_range_from_dict(payload.get("sample_count_range")),
    )
