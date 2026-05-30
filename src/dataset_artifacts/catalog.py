from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import zipfile

import numpy as np

from src.raw_batches import parse_timestamp


TIME_STEP_RE_FRAGMENT = r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
_PREPROCESSED_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    rf"(?P<time_step>{TIME_STEP_RE_FRAGMENT})-orderbook_for_plot\.npz$"
)
_SIMULATION_RE = re.compile(
    r"^simulation-(?P<algorithm>.+)-(?P<simulation_timestamp>\d{8}\.\d{6}\.\d{3})-(?P<seq_num>\d+)\.npz$"
)

DEFAULT_RESOLVED_TIME_FALLBACK = 1.0
SIMULATION_TIMESTAMP_RE = re.compile(r"^\d{8}\.\d{6}\.\d{3}$")
SIMULATION_METADATA_REQUIRED_KEYS = (
    "algorithm",
    "simulation_timestamp",
    "seq_num",
    "product_id",
    "timestamp",
    "file_stem",
    "time_step",
    "base_tick",
    "resolved_time",
)
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


@dataclass(frozen=True)
class PreprocessedFilenameMetadata:
    product_id: str
    timestamp: str
    time_step: float
    time_step_token: str


@dataclass(frozen=True)
class SimulationFilenameMetadata:
    algorithm_name: str
    simulation_timestamp: str
    seq_num: int


@dataclass(frozen=True)
class SimulationArtifact:
    product_id: str
    timestamp: str
    time_step: float
    algorithm_name: str
    path: Path
    simulation_timestamp: str
    seq_num: int
    time_step_token: str | None = None
    resolved_time: float | None = None
    depths: tuple[int, ...] | None = None


@dataclass(frozen=True)
class PreprocessedArtifact:
    product_id: str
    timestamp: str
    time_step: float
    path: Path
    available_views: tuple[str, ...]
    time_step_token: str | None = None
    simulation_artifact: SimulationArtifact | None = None

    @property
    def resolved_time(self) -> float | None:
        return None if self.simulation_artifact is None else self.simulation_artifact.resolved_time

    @property
    def resolved_time_token(self) -> str | None:
        if self.simulation_artifact is None or self.simulation_artifact.resolved_time is None:
            return None
        return format_resolved_time(self.simulation_artifact.resolved_time)

    @property
    def algorithm_name(self) -> str | None:
        return None if self.simulation_artifact is None else self.simulation_artifact.algorithm_name

    @property
    def simulation_path(self) -> Path | None:
        return None if self.simulation_artifact is None else self.simulation_artifact.path

    @property
    def dataset_id(self) -> str:
        if self.simulation_artifact is not None:
            return f"{self.path}#{self.simulation_artifact.path.name}"
        return str(self.path)

    @property
    def display_name(self) -> str:
        formatted = parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        views = ",".join(self.available_views)
        simulation_suffix = (
            f" | {self.simulation_artifact.path.stem}"
            if self.simulation_artifact is not None
            else ""
        )
        return (
            f"{self.product_id} | {formatted} | {format_time_step(self.time_step)}s"
            f"{simulation_suffix} | {views}"
        )

    def to_locator(
        self,
        preprocessed_dir: Path,
        payload_cache: MutableMapping[Path, dict[str, object]] | None = None,
    ) -> DatasetLocator:
        return DatasetLocator(
            product_id=self.product_id,
            timestamp=self.timestamp,
            time_step=self.time_step,
            preprocessed_dir=preprocessed_dir,
            time_step_token=self.time_step_token,
            original_path=self.path,
            simulation_artifact=self.simulation_artifact,
            payload_cache=payload_cache,
        )


@dataclass(frozen=True)
class DatasetLocator:
    product_id: str
    timestamp: str
    time_step: float
    preprocessed_dir: Path
    time_step_token: str | None = None
    original_path: Path | None = None
    simulation_artifact: SimulationArtifact | None = None
    payload_cache: MutableMapping[Path, dict[str, object]] | None = field(
        default=None,
        compare=False,
        hash=False,
        repr=False,
    )

    @property
    def base_id(self) -> str:
        token = self.time_step_token or format_time_step(self.time_step)
        return f"{self.product_id}-{self.timestamp}-{token}"

    @property
    def path(self) -> Path:
        if self.original_path is not None:
            return self.original_path
        return self.preprocessed_dir / f"{self.base_id}-orderbook_for_plot.npz"


def _format_positive_decimal(value: float | str | Decimal, *, field_name: str) -> str:
    try:
        decimal_value = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"Invalid {field_name}: {value!r}") from error

    if not decimal_value.is_finite() or decimal_value <= 0:
        raise ValueError(f"{field_name} must be a positive finite value: {value!r}")

    normalized = decimal_value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f").rstrip("0").rstrip(".")


def format_time_step(time_step: float | str | Decimal) -> str:
    return _format_positive_decimal(time_step, field_name="time step")


def format_resolved_time(resolved_time: float | str | Decimal) -> str:
    try:
        decimal_value = Decimal(str(resolved_time))
    except InvalidOperation as error:
        raise ValueError(f"Invalid resolved time: {resolved_time!r}") from error

    if not decimal_value.is_finite() or decimal_value < 0:
        raise ValueError(
            f"resolved time must be a non-negative finite value: {resolved_time!r}"
        )

    normalized = decimal_value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f").rstrip("0").rstrip(".")


def parse_preprocessed_filename(filename: str) -> PreprocessedFilenameMetadata | None:
    match = _PREPROCESSED_RE.match(filename)
    if match is None:
        return None
    return PreprocessedFilenameMetadata(
        product_id=match.group("product_id"),
        timestamp=match.group("timestamp"),
        time_step=float(match.group("time_step")),
        time_step_token=match.group("time_step"),
    )


def parse_simulation_filename(filename: str) -> SimulationFilenameMetadata | None:
    match = _SIMULATION_RE.match(filename)
    if match is None:
        return None
    return SimulationFilenameMetadata(
        algorithm_name=match.group("algorithm"),
        simulation_timestamp=match.group("simulation_timestamp"),
        seq_num=int(match.group("seq_num")),
    )


def build_preprocessed_output_path(
    output_dir: Path | str,
    product_id: str,
    timestamp: str,
    time_step: float,
) -> Path:
    token = format_time_step(time_step)
    return Path(output_dir) / f"{product_id}-{timestamp}-{token}-orderbook_for_plot.npz"


def build_simulation_output_path(
    output_dir: Path | str,
    algorithm_name: str,
    simulation_timestamp: str,
    seq_num: int,
) -> Path:
    if SIMULATION_TIMESTAMP_RE.match(simulation_timestamp) is None:
        raise ValueError(
            "simulation_timestamp must match YYYYMMDD.HHMMSS.mmm: "
            f"{simulation_timestamp!r}"
        )
    if seq_num < 0:
        raise ValueError(f"seq_num must be a non-negative integer: {seq_num!r}")
    return Path(output_dir) / f"simulation-{algorithm_name}-{simulation_timestamp}-{seq_num}.npz"


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
    metadata: SimulationArtifact,
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
        format_resolved_time(metadata.resolved_time) in expected_tokens
        or metadata.resolved_time == resolved_time
    )


def _load_npz_fields(path: Path, required_keys: Iterable[str]) -> dict[str, object]:
    try:
        with np.load(path, allow_pickle=False) as data:
            missing_keys = [key for key in required_keys if key not in data.files]
            if missing_keys:
                raise ValueError(
                    f"missing required key(s): {', '.join(sorted(missing_keys))}"
                )
            return {key: data[key].tolist() for key in required_keys}
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise ValueError(f"Failed to load simulation metadata from {path.name}: {error}") from error


def _read_required_str(metadata: Mapping[str, object], field_name: str) -> str:
    value = metadata.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Invalid simulation metadata field {field_name!r}: {value!r}")
    return value


def _read_required_float(metadata: Mapping[str, object], field_name: str) -> float:
    value = metadata.get(field_name)
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid simulation metadata field {field_name!r}: {value!r}"
        ) from error
    if not np.isfinite(numeric):
        raise ValueError(f"Simulation metadata field {field_name!r} must be finite.")
    return numeric


def _read_required_int(metadata: Mapping[str, object], field_name: str) -> int:
    value = metadata.get(field_name)
    try:
        numeric = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid simulation metadata field {field_name!r}: {value!r}"
        ) from error
    return numeric


def _read_depths(metadata: Mapping[str, object]) -> tuple[int, ...] | None:
    if "depths" in metadata:
        value = metadata.get("depths")
        try:
            array = np.asarray(value, dtype=int).reshape(-1)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid simulation metadata field 'depths': {value!r}") from error
        return tuple(int(item) for item in array.tolist())
    if "depth" in metadata:
        return (_read_required_int(metadata, "depth"),)
    return None


def _load_simulation_artifact(path: Path) -> SimulationArtifact | None:
    filename_metadata = parse_simulation_filename(path.name)
    if filename_metadata is None:
        return None
    required_keys = SIMULATION_METADATA_REQUIRED_KEYS
    try:
        metadata = _load_npz_fields(path, (*required_keys, "depths"))
    except ValueError:
        metadata = _load_npz_fields(path, (*required_keys, "depth"))
    algorithm_name = _read_required_str(metadata, "algorithm")
    simulation_timestamp = _read_required_str(metadata, "simulation_timestamp")
    seq_num = _read_required_int(metadata, "seq_num")
    if algorithm_name != filename_metadata.algorithm_name:
        raise ValueError(
            f"Simulation metadata algorithm does not match filename for {path.name}."
        )
    if simulation_timestamp != filename_metadata.simulation_timestamp:
        raise ValueError(
            f"Simulation metadata timestamp does not match filename for {path.name}."
        )
    if seq_num != filename_metadata.seq_num:
        raise ValueError(
            f"Simulation metadata seq_num does not match filename for {path.name}."
        )
    return SimulationArtifact(
        product_id=_read_required_str(metadata, "product_id"),
        timestamp=_read_required_str(metadata, "timestamp"),
        time_step=_read_required_float(metadata, "time_step"),
        algorithm_name=algorithm_name,
        path=path,
        simulation_timestamp=simulation_timestamp,
        seq_num=seq_num,
        time_step_token=format_time_step(_read_required_float(metadata, "time_step")),
        resolved_time=_read_required_float(metadata, "resolved_time"),
        depths=_read_depths(metadata),
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
        artifact = _load_simulation_artifact(path)
        if artifact is None:
            continue
        if product_id is not None and artifact.product_id != product_id:
            continue
        if timestamp is not None and artifact.timestamp != timestamp:
            continue
        if time_step is not None and not _matches_numeric_token(
            artifact.time_step,
            artifact.time_step_token or format_time_step(artifact.time_step),
            time_step,
            explicit_token=time_step_token,
        ):
            continue
        if algorithm_name is not None and artifact.algorithm_name != algorithm_name:
            continue
        if not _matches_resolved_time(artifact, resolved_time, resolved_time_token):
            continue
        artifacts.append(artifact)
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
        simulation_artifact = _load_simulation_artifact(path)
        if preprocessed_metadata is None and simulation_artifact is None:
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

        key = (
            simulation_artifact.product_id,
            simulation_artifact.timestamp,
            simulation_artifact.time_step,
        )
        entry = entries.setdefault(
            key,
            {
                "product_id": simulation_artifact.product_id,
                "timestamp": simulation_artifact.timestamp,
                "time_step": simulation_artifact.time_step,
                "time_step_token": simulation_artifact.time_step_token,
                "orderbook_path": None,
                "simulation_artifacts": [],
                "orderbook_views": (),
            },
        )
        simulation_artifacts = entry["simulation_artifacts"]
        if isinstance(simulation_artifacts, list):
            simulation_artifacts.append(simulation_artifact)

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
