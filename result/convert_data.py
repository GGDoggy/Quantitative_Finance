from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analyze import AnalyzeRequest, analyze_batch, analyze_batches
from src.preprocess import DEFAULT_DEPTH, preprocess_batch
from src.raw_batches import RawBatch, discover_raw_batches


RAW_DATA_DIR = PROJECT_ROOT / "data" / "temp"
OUTPUT_DIR = PROJECT_ROOT / "data" / "preprocessed"
ANALYZE_REQUEST = AnalyzeRequest(analysis_name="fill_rate")
PREPROCESS_DEPTH = DEFAULT_DEPTH


@dataclass(frozen=True)
class PreprocessJobSummary:
    batch: RawBatch
    preprocess_count: int


def _load_batches():
    return discover_raw_batches(RAW_DATA_DIR)


def _process_batch(batch_index: int) -> int:
    batches = _load_batches()
    if batch_index < 0 or batch_index >= len(batches):
        print(f"Invalid batch index {batch_index}. Expected 0..{len(batches) - 1}.")
        return 2

    batch = batches[batch_index]
    total = len(batches)
    print(f"[{batch_index + 1}/{total}] preprocessing {batch.display_name}")
    try:
        preprocess_datasets = preprocess_batch(
            batch=batch,
            output_dir=OUTPUT_DIR,
            depth=PREPROCESS_DEPTH,
            preprocess_timestamp=batch.timestamp,
        )
    except MemoryError as exc:
        detail = f" Details: {exc}" if str(exc) else ""
        print(
            "Preprocess failed with MemoryError while building a single dataset pair "
            f"for {batch.file_stem}.{detail}"
        )
        return 3

    print(f"[{batch_index + 1}/{total}] analyzing {batch.display_name}")
    analyzed = analyze_batch(
        batch,
        request=ANALYZE_REQUEST,
        output_dir=OUTPUT_DIR,
        analyze_timestamp=batch.timestamp,
    )

    print(
        "Wrote "
        f"{len(preprocess_datasets)} preprocess artifact(s) for {batch.file_stem}."
    )
    print(f"Wrote 1 analyze artifact for {batch.file_stem}: {analyzed.output_path.name}")
    return 0


def _process_batches_in_parallel(batches: list[RawBatch]) -> int:
    total = len(batches)
    print(f"Preprocessing {total} batch(es) sequentially.")
    preprocess_summaries: list[PreprocessJobSummary] = []
    try:
        for index, batch in enumerate(batches, start=1):
            print(f"[{index}/{total}] preprocessing {batch.display_name}")
            preprocess_datasets = preprocess_batch(
                batch=batch,
                output_dir=OUTPUT_DIR,
                depth=PREPROCESS_DEPTH,
                preprocess_timestamp=batch.timestamp,
            )
            preprocess_summaries.append(
                PreprocessJobSummary(
                    batch=batch,
                    preprocess_count=len(preprocess_datasets),
                )
            )
    except MemoryError as exc:
        detail = f" Details: {exc}" if str(exc) else ""
        print(f"Preprocess failed with MemoryError while building dataset pairs.{detail}")
        return 3

    for index, summary in enumerate(preprocess_summaries, start=1):
        print(
            "Wrote "
            f"{summary.preprocess_count} preprocess artifact(s) for "
            f"{summary.batch.file_stem} [{index}/{total}]."
        )

    print(f"Analyzing {total} batch(es) in parallel.")
    analyze_results = analyze_batches(
        batches,
        request=ANALYZE_REQUEST,
        output_dir=OUTPUT_DIR,
    )
    for index, analyzed in enumerate(analyze_results, start=1):
        print(
            f"Wrote 1 analyze artifact for {analyzed.dataset.file_stem} "
            f"[{index}/{total}]: {analyzed.output_path.name}"
        )

    print(f"Finished converting {total} batch(es).")
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
    print(f"Analyze output dir: {OUTPUT_DIR}")

    total = len(batches)
    if total > 1:
        return _process_batches_in_parallel(batches)

    for batch_index in range(total):
        exit_code = _process_batch(batch_index)
        if exit_code != 0:
            print(f"Batch {batch_index + 1}/{total} failed with exit code {exit_code}.")
            return exit_code

    print(f"Finished converting {total} batch(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
