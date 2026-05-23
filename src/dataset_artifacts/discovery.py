from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
import zipfile

import numpy as np

from .models import PreprocessedArtifact, SimulationArtifact
from .naming import (
    SimulationFilenameMetadata,
    format_resolved_time,
    format_time_step,
    parse_preprocessed_filename,
    parse_simulation_filename,
)


DEFAULT_RESOLVED_TIME_FALLBACK = 1.0
DEFAULT_VIEW_ORDER = (
    "orderbook",
    "trades_scatter",
    "trade_volume_timeline",
    "fill_probability",
    "mid_profit",
    "micro_profit",
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
)
DEFAULT_VIEW_SPECS: tuple[tuple[str, frozenset[str]], ...] = (
    ("orderbook", frozenset(("price_axis", "time_axis", "data", "bid", "ask"))),
    (
        "trades_scatter",
        frozenset(("trade_time", "trade_price", "trade_volume", "trade_side")),
    ),
    (
        "trade_volume_timeline",
        frozenset(("trade_time", "trade_price", "trade_volume", "trade_side")),
    ),
)
SIMULATION_VIEW_KEYS = (
    "fill_probability",
    "mid_profit",
    "micro_profit",
    "mid_fill_probability_cost",
    "micro_fill_probability_cost",
)
ViewSpecs = Sequence[tuple[str, Iterable[str]]]


def _iter_files(path: Path, suffix: str) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(entry for entry in path.iterdir() if entry.is_file() and entry.suffix == suffix)


def _normalized_view_specs(
    view_specs: ViewSpecs | None,
) -> tuple[tuple[str, frozenset[str]], ...]:
    if view_specs is None:
        return DEFAULT_VIEW_SPECS
    return tuple((view_key, frozenset(required_keys)) for view_key, required_keys in view_specs)


def detect_available_views(
    path: Path,
    view_specs: ViewSpecs | None = None,
) -> tuple[str, ...]:
    try:
        with np.load(path, allow_pickle=False) as data:
            if "available_views" in data.files:
                available_views = tuple(str(view) for view in data["available_views"].tolist())
            else:
                data_keys = set(data.files)
                available_views = tuple(
                    view_key
                    for view_key, required_keys in _normalized_view_specs(view_specs)
                    if required_keys.issubset(data_keys)
                )
    except (OSError, ValueError, zipfile.BadZipFile):
        return ("orderbook",)
    return available_views or ("orderbook",)


def _union_available_views(
    *view_groups: Iterable[str],
    preferred_order: Sequence[str] = DEFAULT_VIEW_ORDER,
) -> tuple[str, ...]:
    seen: set[str] = set()
    encountered: list[str] = []
    for view_group in view_groups:
        for view in view_group:
            if view in seen:
                continue
            seen.add(view)
            encountered.append(view)

    ordered_views = [view for view in preferred_order if view in seen]
    ordered_views.extend(view for view in encountered if view not in preferred_order)
    return tuple(ordered_views)


def _matches_numeric_token(
    actual_value: float,
    actual_token: str,
    expected_value: float,
    explicit_token: str | None = None,
) -> bool:
    expected_tokens = {format_time_step(expected_value), str(expected_value)}
    if explicit_token is not None:
        expected_tokens.add(explicit_token)
    return actual_token in expected_tokens or actual_value == expected_value


def _matches_resolved_time(
    metadata: SimulationFilenameMetadata,
    resolved_time: float | None,
    resolved_time_token: str | None,
) -> bool:
    if resolved_time is None:
        return True
    if metadata.resolved_time is None:
        return resolved_time == DEFAULT_RESOLVED_TIME_FALLBACK
    expected_tokens = {format_resolved_time(resolved_time), str(resolved_time)}
    if resolved_time_token is not None:
        expected_tokens.add(resolved_time_token)
    return (
        metadata.resolved_time_token in expected_tokens
        or metadata.resolved_time == resolved_time
    )


def discover_simulation_artifacts(
    preprocessed_dir: Path | str,
    *,
    product_id: str | None = None,
    timestamp: str | None = None,
    time_step: float | None = None,
    time_step_token: str | None = None,
    resolved_time: float | None = None,
    resolved_time_token: str | None = None,
    algorithm_name: str | None = None,
) -> tuple[SimulationArtifact, ...]:
    artifacts: list[SimulationArtifact] = []
    for path in _iter_files(Path(preprocessed_dir), ".npz"):
        metadata = parse_simulation_filename(path.name)
        if metadata is None:
            continue
        if product_id is not None and metadata.product_id != product_id:
            continue
        if timestamp is not None and metadata.timestamp != timestamp:
            continue
        if time_step is not None and not _matches_numeric_token(
            metadata.time_step,
            metadata.time_step_token,
            time_step,
            explicit_token=time_step_token,
        ):
            continue
        if algorithm_name is not None and metadata.algorithm_name != algorithm_name:
            continue
        if not _matches_resolved_time(metadata, resolved_time, resolved_time_token):
            continue
        artifacts.append(
            SimulationArtifact(
                product_id=metadata.product_id,
                timestamp=metadata.timestamp,
                time_step=metadata.time_step,
                algorithm_name=metadata.algorithm_name,
                path=path,
                time_step_token=metadata.time_step_token,
                resolved_time=metadata.resolved_time,
                resolved_time_token=metadata.resolved_time_token,
            )
        )
    return tuple(sorted(artifacts, key=lambda artifact: artifact.path.name))


def discover_preprocessed_artifacts(
    preprocessed_dir: Path | str,
    view_specs: ViewSpecs | None = None,
    simulation_view_keys: tuple[str, ...] = SIMULATION_VIEW_KEYS,
) -> list[PreprocessedArtifact]:
    directory = Path(preprocessed_dir)
    entries: dict[tuple[str, str, float], dict[str, object]] = {}

    for path in _iter_files(directory, ".npz"):
        preprocessed_metadata = parse_preprocessed_filename(path.name)
        simulation_metadata = parse_simulation_filename(path.name)
        if preprocessed_metadata is None and simulation_metadata is None:
            continue

        if preprocessed_metadata is not None:
            key = (
                preprocessed_metadata.product_id,
                preprocessed_metadata.timestamp,
                preprocessed_metadata.time_step,
            )
            entry = entries.setdefault(
                key,
                {
                    "product_id": preprocessed_metadata.product_id,
                    "timestamp": preprocessed_metadata.timestamp,
                    "time_step": preprocessed_metadata.time_step,
                    "time_step_token": preprocessed_metadata.time_step_token,
                    "orderbook_path": None,
                    "simulation_artifacts": [],
                    "orderbook_views": (),
                },
            )
            entry["orderbook_path"] = path
            entry["time_step_token"] = preprocessed_metadata.time_step_token
            entry["orderbook_views"] = _union_available_views(
                detect_available_views(path, view_specs=view_specs),
                preferred_order=DEFAULT_VIEW_ORDER,
            )
            continue

        assert simulation_metadata is not None
        key = (
            simulation_metadata.product_id,
            simulation_metadata.timestamp,
            simulation_metadata.time_step,
        )
        entry = entries.setdefault(
            key,
            {
                "product_id": simulation_metadata.product_id,
                "timestamp": simulation_metadata.timestamp,
                "time_step": simulation_metadata.time_step,
                "time_step_token": simulation_metadata.time_step_token,
                "orderbook_path": None,
                "simulation_artifacts": [],
                "orderbook_views": (),
            },
        )
        simulation_artifacts = entry["simulation_artifacts"]
        if isinstance(simulation_artifacts, list):
            simulation_artifacts.append(
                SimulationArtifact(
                    product_id=simulation_metadata.product_id,
                    timestamp=simulation_metadata.timestamp,
                    time_step=simulation_metadata.time_step,
                    algorithm_name=simulation_metadata.algorithm_name,
                    path=path,
                    time_step_token=simulation_metadata.time_step_token,
                    resolved_time=simulation_metadata.resolved_time,
                    resolved_time_token=simulation_metadata.resolved_time_token,
                )
            )

    artifacts: list[PreprocessedArtifact] = []
    for entry in entries.values():
        orderbook_path = entry["orderbook_path"]
        time_step_token = str(entry["time_step_token"])
        orderbook_views = tuple(entry["orderbook_views"])
        simulation_artifacts = sorted(
            (
                artifact
                for artifact in entry["simulation_artifacts"]
                if isinstance(artifact, SimulationArtifact)
            ),
            key=lambda artifact: artifact.path.name,
        )

        if isinstance(orderbook_path, Path) and not simulation_artifacts:
            artifacts.append(
                PreprocessedArtifact(
                    product_id=str(entry["product_id"]),
                    timestamp=str(entry["timestamp"]),
                    time_step=float(entry["time_step"]),
                    path=orderbook_path,
                    available_views=orderbook_views,
                    time_step_token=time_step_token,
                )
            )
            continue

        for simulation_artifact in simulation_artifacts:
            artifacts.append(
                PreprocessedArtifact(
                    product_id=str(entry["product_id"]),
                    timestamp=str(entry["timestamp"]),
                    time_step=float(entry["time_step"]),
                    path=orderbook_path if isinstance(orderbook_path, Path) else simulation_artifact.path,
                    available_views=_union_available_views(
                        orderbook_views if isinstance(orderbook_path, Path) else (),
                        simulation_view_keys,
                        preferred_order=DEFAULT_VIEW_ORDER,
                    ),
                    time_step_token=time_step_token,
                    simulation_artifact=simulation_artifact,
                )
            )

    artifacts.sort(
        key=lambda artifact: (
            artifact.product_id,
            artifact.timestamp,
            artifact.time_step,
            artifact.simulation_path.name if artifact.simulation_path is not None else "",
        )
    )
    return artifacts
