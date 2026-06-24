from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import zipfile

import numpy as np

from src.raw_batches import parse_timestamp


ARTIFACT_TIMESTAMP_RE = re.compile(r"^\d{8}\.\d{6}$")
_PREPROCESSED_RE = re.compile(
    r"^preprocess-(?P<preprocess_type>.+)-"
    r"(?P<preprocess_timestamp>\d{8}\.\d{6})\.npz$"
)
_ANALYZE_RE = re.compile(
    r"^analyze-(?P<analysis_name>.+)-(?P<analyze_timestamp>\d{8}\.\d{6})\.npz$"
)

PREPROCESS_METADATA_REQUIRED_KEYS = (
    "preprocess_type",
    "preprocess_timestamp",
    "product_id",
    "timestamp",
    "file_stem",
)
ANALYZE_METADATA_REQUIRED_KEYS = (
    "analysis_name",
    "analyze_timestamp",
    "product_id",
    "timestamp",
    "file_stem",
)
DEFAULT_VIEW_ORDER = (
    "orderbook",
    "trades_scatter",
    "trade_volume_timeline",
)
LEGACY_ORDERBOOK_VIEW_KEYS = frozenset(("price_axis", "time_axis", "data", "bid", "ask"))
SNAPSHOT_ORDERBOOK_VIEW_KEYS = frozenset(
    ("time_axis", "bid_price", "bid_size", "ask_price", "ask_size", "bid", "ask")
)
DEFAULT_VIEW_SPECS: tuple[tuple[str, frozenset[str]], ...] = (
    ("orderbook", SNAPSHOT_ORDERBOOK_VIEW_KEYS),
    (
        "trades_scatter",
        frozenset(("trade_time", "trade_price", "trade_volume", "trade_side")),
    ),
    (
        "trade_volume_timeline",
        frozenset(("trade_time", "trade_price", "trade_volume", "trade_side")),
    ),
)
ViewSpecs = Sequence[tuple[str, Iterable[str]]]


@dataclass(frozen=True)
class PreprocessedFilenameMetadata:
    preprocess_type: str
    preprocess_timestamp: str


@dataclass(frozen=True)
class AnalyzeFilenameMetadata:
    analysis_name: str
    analyze_timestamp: str


@dataclass(frozen=True)
class PreprocessedArtifact:
    product_id: str
    timestamp: str
    path: Path
    available_views: tuple[str, ...]
    preprocess_type: str = "orderbook"
    preprocess_timestamp: str | None = None
    depth: int | None = None

    @property
    def dataset_id(self) -> str:
        return str(self.path)

    @property
    def display_name(self) -> str:
        formatted = parse_timestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        details: list[str] = []
        if self.depth is not None:
            details.append(f"depth={self.depth}")
        views = ",".join(self.available_views)
        detail_suffix = f" | {' | '.join(details)}" if details else ""
        return f"{self.product_id} | {formatted}{detail_suffix} | {views}"

    def to_locator(
        self,
        preprocessed_dir: Path,
        payload_cache: MutableMapping[Path, dict[str, object]] | None = None,
    ) -> DatasetLocator:
        return DatasetLocator(
            product_id=self.product_id,
            timestamp=self.timestamp,
            preprocessed_dir=preprocessed_dir,
            preprocess_type=self.preprocess_type,
            preprocess_timestamp=self.preprocess_timestamp,
            depth=self.depth,
            original_path=self.path,
            payload_cache=payload_cache,
        )


@dataclass(frozen=True)
class DatasetLocator:
    product_id: str
    timestamp: str
    preprocessed_dir: Path
    preprocess_type: str = "orderbook"
    preprocess_timestamp: str | None = None
    depth: int | None = None
    original_path: Path | None = None
    payload_cache: MutableMapping[Path, dict[str, object]] | None = field(
        default=None,
        compare=False,
        hash=False,
        repr=False,
    )

    @property
    def path(self) -> Path:
        if self.original_path is not None:
            return self.original_path
        if self.preprocess_timestamp is None:
            raise ValueError("Cannot resolve dataset path without preprocess metadata.")
        return build_preprocessed_output_path(
            self.preprocessed_dir,
            self.preprocess_type,
            self.preprocess_timestamp,
        )


@dataclass(frozen=True)
class AnalyzeArtifact:
    product_id: str
    timestamp: str
    analysis_name: str
    path: Path
    analyze_timestamp: str


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


def parse_preprocessed_filename(filename: str) -> PreprocessedFilenameMetadata | None:
    match = _PREPROCESSED_RE.match(filename)
    if match is None:
        return None
    return PreprocessedFilenameMetadata(
        preprocess_type=match.group("preprocess_type"),
        preprocess_timestamp=match.group("preprocess_timestamp"),
    )


def parse_analyze_filename(filename: str) -> AnalyzeFilenameMetadata | None:
    match = _ANALYZE_RE.match(filename)
    if match is None:
        return None
    return AnalyzeFilenameMetadata(
        analysis_name=match.group("analysis_name"),
        analyze_timestamp=match.group("analyze_timestamp"),
    )


def build_preprocessed_output_path(
    output_dir: Path | str,
    preprocess_type: str,
    preprocess_timestamp: str,
) -> Path:
    if ARTIFACT_TIMESTAMP_RE.match(preprocess_timestamp) is None:
        raise ValueError(
            "preprocess_timestamp must match YYYYMMDD.HHMMSS: "
            f"{preprocess_timestamp!r}"
        )
    if not preprocess_type:
        raise ValueError("preprocess_type is required.")
    return Path(output_dir) / f"preprocess-{preprocess_type}-{preprocess_timestamp}.npz"


def build_analyze_output_path(
    output_dir: Path | str,
    analysis_name: str,
    analyze_timestamp: str,
) -> Path:
    if ARTIFACT_TIMESTAMP_RE.match(analyze_timestamp) is None:
        raise ValueError(
            "analyze_timestamp must match YYYYMMDD.HHMMSS: "
            f"{analyze_timestamp!r}"
        )
    if not analysis_name:
        raise ValueError("analysis_name is required.")
    return Path(output_dir) / f"analyze-{analysis_name}-{analyze_timestamp}.npz"


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


def _has_windowed_orderbook_keys(data_keys: set[str]) -> bool:
    prefixes = (
        "time_axis__w",
        "bid_price__w",
        "bid_size__w",
        "ask_price__w",
        "ask_size__w",
        "bid__w",
        "ask__w",
    )
    return any(
        all(f"{base}{suffix}" in data_keys for base in prefixes)
        for suffix in {
            key.removeprefix("time_axis")
            for key in data_keys
            if key.startswith("time_axis__w")
        }
    )


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
                available_views_list: list[str] = []
                if (
                    LEGACY_ORDERBOOK_VIEW_KEYS.issubset(data_keys)
                    or SNAPSHOT_ORDERBOOK_VIEW_KEYS.issubset(data_keys)
                    or _has_windowed_orderbook_keys(data_keys)
                ):
                    available_views_list.append("orderbook")
                available_views_list.extend(
                    view_key
                    for view_key, required_keys in _normalized_view_specs(view_specs)
                    if view_key != "orderbook" and required_keys.issubset(data_keys)
                )
                available_views = tuple(available_views_list)
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
        raise ValueError(f"Failed to load metadata from {path.name}: {error}") from error


def _read_required_str(metadata: Mapping[str, object], field_name: str) -> str:
    value = metadata.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Invalid metadata field {field_name!r}: {value!r}")
    return value


def _read_required_int(metadata: Mapping[str, object], field_name: str) -> int:
    value = metadata.get(field_name)
    try:
        numeric = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid metadata field {field_name!r}: {value!r}") from error
    return numeric


def _load_preprocessed_artifact(
    path: Path,
    view_specs: ViewSpecs | None = None,
) -> PreprocessedArtifact | None:
    filename_metadata = parse_preprocessed_filename(path.name)
    if filename_metadata is None:
        return None
    try:
        metadata = _load_npz_fields(path, (*PREPROCESS_METADATA_REQUIRED_KEYS, "depth"))
    except ValueError:
        metadata = _load_npz_fields(path, PREPROCESS_METADATA_REQUIRED_KEYS)
    preprocess_type = _read_required_str(metadata, "preprocess_type")
    preprocess_timestamp = _read_required_str(metadata, "preprocess_timestamp")
    if preprocess_type != filename_metadata.preprocess_type:
        raise ValueError(
            f"Preprocess metadata type does not match filename for {path.name}."
        )
    if preprocess_timestamp != filename_metadata.preprocess_timestamp:
        raise ValueError(
            f"Preprocess metadata timestamp does not match filename for {path.name}."
        )
    return PreprocessedArtifact(
        product_id=_read_required_str(metadata, "product_id"),
        timestamp=_read_required_str(metadata, "timestamp"),
        path=path,
        available_views=_union_available_views(
            detect_available_views(path, view_specs=view_specs),
            preferred_order=DEFAULT_VIEW_ORDER,
        ),
        preprocess_type=preprocess_type,
        preprocess_timestamp=preprocess_timestamp,
        depth=_read_required_int(metadata, "depth") if "depth" in metadata else None,
    )


def _load_analyze_artifact(path: Path) -> AnalyzeArtifact | None:
    filename_metadata = parse_analyze_filename(path.name)
    if filename_metadata is None:
        return None
    metadata = _load_npz_fields(path, ANALYZE_METADATA_REQUIRED_KEYS)
    analysis_name = _read_required_str(metadata, "analysis_name")
    analyze_timestamp = _read_required_str(metadata, "analyze_timestamp")
    if analysis_name != filename_metadata.analysis_name:
        raise ValueError(
            f"Analyze metadata analysis_name does not match filename for {path.name}."
        )
    if analyze_timestamp != filename_metadata.analyze_timestamp:
        raise ValueError(
            f"Analyze metadata timestamp does not match filename for {path.name}."
        )
    return AnalyzeArtifact(
        product_id=_read_required_str(metadata, "product_id"),
        timestamp=_read_required_str(metadata, "timestamp"),
        analysis_name=analysis_name,
        path=path,
        analyze_timestamp=analyze_timestamp,
    )


def discover_analyze_artifacts(
    preprocessed_dir: Path | str,
    *,
    product_id: str | None = None,
    timestamp: str | None = None,
    analysis_name: str | None = None,
) -> tuple[AnalyzeArtifact, ...]:
    artifacts: list[AnalyzeArtifact] = []
    for path in _iter_files(Path(preprocessed_dir), ".npz"):
        artifact = _load_analyze_artifact(path)
        if artifact is None:
            continue
        if product_id is not None and artifact.product_id != product_id:
            continue
        if timestamp is not None and artifact.timestamp != timestamp:
            continue
        if analysis_name is not None and artifact.analysis_name != analysis_name:
            continue
        artifacts.append(artifact)
    return tuple(sorted(artifacts, key=lambda artifact: artifact.path.name))


def discover_preprocessed_artifacts(
    preprocessed_dir: Path | str,
    view_specs: ViewSpecs | None = None,
) -> list[PreprocessedArtifact]:
    artifacts: list[PreprocessedArtifact] = []
    for path in _iter_files(Path(preprocessed_dir), ".npz"):
        artifact = _load_preprocessed_artifact(path, view_specs=view_specs)
        if artifact is None:
            continue
        artifacts.append(artifact)

    artifacts.sort(
        key=lambda artifact: (
            artifact.product_id,
            artifact.timestamp,
            artifact.preprocess_timestamp or "",
            artifact.path.name,
        )
    )
    return artifacts
