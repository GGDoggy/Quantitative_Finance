from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocess import DEFAULT_DEPTH, preprocess_batch
from src.raw_batches import RawBatch, discover_raw_batches


RAW_DATA_DIR = PROJECT_ROOT / "data" / "temp"
OUTPUT_DIR = PROJECT_ROOT / "data" / "preprocessed"
PREPROCESS_DEPTH = DEFAULT_DEPTH
PREPROCESS_TRADE_WINDOWS = (1, 5, 10, 30)


@dataclass(frozen=True)
class PreprocessJobSummary:
    batch: RawBatch
    preprocess_count: int
    trade_windows: tuple[int, ...]


def _load_batches():
    return discover_raw_batches(RAW_DATA_DIR)


def _run_preprocess_windows(batch: RawBatch) -> list:
    preprocess_datasets = []
    for trade_window_seconds in PREPROCESS_TRADE_WINDOWS:
        preprocess_datasets.extend(
            preprocess_batch(
                batch=batch,
                output_dir=OUTPUT_DIR,
                depth=PREPROCESS_DEPTH,
                preprocess_timestamp=batch.timestamp,
                trade_window_seconds=trade_window_seconds,
            )
        )
    return preprocess_datasets


def _process_batch(batch_index: int) -> int:
    batches = _load_batches()
    if batch_index < 0 or batch_index >= len(batches):
        print(f"Invalid batch index {batch_index}. Expected 0..{len(batches) - 1}.")
        return 2

    batch = batches[batch_index]
    total = len(batches)
    print(f"[{batch_index + 1}/{total}] preprocessing {batch.display_name}")
    try:
        preprocess_datasets = _run_preprocess_windows(batch)
    except MemoryError as exc:
        detail = f" Details: {exc}" if str(exc) else ""
        print(
            "Preprocess failed with MemoryError while building a single dataset pair "
            f"for {batch.file_stem}.{detail}"
        )
        return 3

    print(
        "Wrote "
        f"{len(preprocess_datasets)} preprocess artifact write(s) for {batch.file_stem} "
        f"across windows {PREPROCESS_TRADE_WINDOWS}."
    )
    return 0


def _process_batches_in_parallel(batches: list[RawBatch]) -> int:
    total = len(batches)
    print(f"Preprocessing {total} batch(es) sequentially.")
    preprocess_summaries: list[PreprocessJobSummary] = []
    try:
        for index, batch in enumerate(batches, start=1):
            print(f"[{index}/{total}] preprocessing {batch.display_name}")
            preprocess_datasets = _run_preprocess_windows(batch)
            preprocess_summaries.append(
                PreprocessJobSummary(
                    batch=batch,
                    preprocess_count=len(preprocess_datasets),
                    trade_windows=PREPROCESS_TRADE_WINDOWS,
                )
            )
    except MemoryError as exc:
        detail = f" Details: {exc}" if str(exc) else ""
        print(f"Preprocess failed with MemoryError while building dataset pairs.{detail}")
        return 3

    for index, summary in enumerate(preprocess_summaries, start=1):
        print(
            "Wrote "
            f"{summary.preprocess_count} preprocess artifact write(s) for "
            f"{summary.batch.file_stem} [{index}/{total}] "
            f"across windows {summary.trade_windows}."
        )

    print(f"Finished preprocessing {total} batch(es).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-index", type=int)
    args = parser.parse_args(argv)

    if args.batch_index is not None:
        return _process_batch(args.batch_index)

    batches = _load_batches()
    if not batches:
        print(f"No complete raw batches found in {RAW_DATA_DIR}.")
        return 1

    print(f"Discovered {len(batches)} batch(es) in {RAW_DATA_DIR}.")
    print(f"Preprocess output dir: {OUTPUT_DIR}")

    total = len(batches)
    if total > 1:
        return _process_batches_in_parallel(batches)

    for batch_index in range(total):
        exit_code = _process_batch(batch_index)
        if exit_code != 0:
            print(f"Batch {batch_index + 1}/{total} failed with exit code {exit_code}.")
            return exit_code

    print(f"Finished preprocessing {total} batch(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
