from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui.data_catalog import discover_raw_batches
from gui.preprocess_service import DEFAULT_TIME_STEP, preprocess_batches


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "v3"
PREPROCESSED_DIR = PROJECT_ROOT / "data" / "preprocessed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess Coinbase v3 CSV files into compressed plotting datasets.")
    parser.add_argument(
        "--batch",
        action="append",
        default=[],
        help="Batch id in the form PRODUCT_ID|yyyymmdd.HHMMSS. Repeat to preprocess multiple batches.",
    )
    parser.add_argument("--all", action="store_true", help="Preprocess all discovered batches, including existing outputs.")
    parser.add_argument("--time-step", type=float, default=DEFAULT_TIME_STEP, help="Sampling time step in seconds.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw v3 CSV files.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PREPROCESSED_DIR,
        help="Directory where compressed .npz files will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    batches = discover_raw_batches(args.raw_dir, args.output_dir)

    if args.batch:
        selected_ids = set(args.batch)
        selected = [batch for batch in batches if batch.batch_id in selected_ids]
    elif args.all:
        selected = batches
    else:
        selected = [batch for batch in batches if not batch.is_preprocessed]

    if not selected:
        print("No batches selected for preprocessing.")
        return

    preprocess_batches(
        selected,
        output_dir=args.output_dir,
        time_step=args.time_step,
        progress_callback=print,
    )


if __name__ == "__main__":
    main()
