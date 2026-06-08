from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analyze import AnalyzeRequest, analyze_batch
from src.preprocess import DEFAULT_DEPTH, PLOT_REGISTRY
from src.preprocess.pipeline import (
    _save_preprocess_payload,
    build_preprocess_context,
    generate_preprocess_timestamp,
)
from src.raw_batches import LoadedRawBatch, discover_raw_batches, load_raw_batch


RAW_DATA_DIR = PROJECT_ROOT / "data" / "temp"
OUTPUT_DIR = PROJECT_ROOT / "data" / "preprocessed"
ANALYZE_REQUEST = AnalyzeRequest(analysis_name="fill_rate")
PREPROCESS_DEPTH = DEFAULT_DEPTH
ORDERBOOK_CHUNK_SIZE = 10_000


def _apply_book_update(levels: dict[float, float], price: float, volume: float) -> None:
    if volume <= 0:
        levels.pop(price, None)
        return
    levels[price] = volume


def _initialize_book_state(
    init_rows: list[list[float]],
) -> tuple[dict[float, float], dict[float, float]]:
    bid_levels: dict[float, float] = {}
    ask_levels: dict[float, float] = {}
    for price_raw, volume_raw, side_raw in init_rows:
        price = float(price_raw)
        volume = float(volume_raw)
        if int(side_raw) == -1:
            _apply_book_update(bid_levels, price, volume)
        else:
            _apply_book_update(ask_levels, price, volume)
    return bid_levels, ask_levels


def _book_state_to_init_rows(
    bid_levels: dict[float, float],
    ask_levels: dict[float, float],
) -> list[list[float]]:
    init_rows: list[list[float]] = []
    for price, volume in bid_levels.items():
        init_rows.append([price, volume, -1.0])
    for price, volume in ask_levels.items():
        init_rows.append([price, volume, 1.0])
    return init_rows


def _save_preprocess_spec(
    *,
    batch,
    loaded_batch: LoadedRawBatch,
    preprocess_type: str,
    preprocess_timestamp: str,
    seq_num: int,
):
    spec = PLOT_REGISTRY[preprocess_type]
    context = build_preprocess_context(
        batch,
        PREPROCESS_DEPTH,
        loaded_batch=loaded_batch,
    )
    payload = spec.preprocess_builder(context)
    return _save_preprocess_payload(
        context=context,
        output_dir=OUTPUT_DIR,
        preprocess_type=spec.preprocess_type,
        payload=payload,
        available_views=spec.available_views,
        preprocess_timestamp=preprocess_timestamp,
        seq_num=seq_num,
    )


def _save_chunked_orderbook_preprocess(
    *,
    batch,
    loaded_batch: LoadedRawBatch,
    preprocess_timestamp: str,
    seq_num_start: int,
) -> int:
    updates = sorted(loaded_batch.updates, key=lambda row: float(row[0]))
    bid_levels, ask_levels = _initialize_book_state(loaded_batch.init)
    seq_num = seq_num_start

    for chunk_start in range(0, len(updates), ORDERBOOK_CHUNK_SIZE):
        chunk_updates = updates[chunk_start : chunk_start + ORDERBOOK_CHUNK_SIZE]
        chunk_loaded_batch = LoadedRawBatch(
            init=_book_state_to_init_rows(bid_levels, ask_levels),
            updates=chunk_updates,
            trades=[],
            start_time=loaded_batch.start_time,
        )
        _save_preprocess_spec(
            batch=batch,
            loaded_batch=chunk_loaded_batch,
            preprocess_type="orderbook",
            preprocess_timestamp=preprocess_timestamp,
            seq_num=seq_num,
        )
        seq_num += 1

        for update_time, price_raw, volume_raw, side_raw in chunk_updates:
            del update_time
            price = float(price_raw)
            volume = float(volume_raw)
            if int(side_raw) == -1:
                _apply_book_update(bid_levels, price, volume)
            else:
                _apply_book_update(ask_levels, price, volume)

    return seq_num - seq_num_start


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
    loaded_batch = load_raw_batch(batch)
    preprocess_timestamp = generate_preprocess_timestamp()
    preprocess_count = 0

    try:
        _save_preprocess_spec(
            batch=batch,
            loaded_batch=loaded_batch,
            preprocess_type="orderbook",
            preprocess_timestamp=preprocess_timestamp,
            seq_num=preprocess_count,
        )
        preprocess_count += 1
    except MemoryError:
        chunk_count = _save_chunked_orderbook_preprocess(
            batch=batch,
            loaded_batch=loaded_batch,
            preprocess_timestamp=preprocess_timestamp,
            seq_num_start=preprocess_count,
        )
        preprocess_count += chunk_count

    _save_preprocess_spec(
        batch=batch,
        loaded_batch=loaded_batch,
        preprocess_type="trade",
        preprocess_timestamp=preprocess_timestamp,
        seq_num=preprocess_count,
    )
    preprocess_count += 1

    print(f"[{batch_index + 1}/{total}] analyzing {batch.display_name}")
    analyzed = analyze_batch(
        batch,
        request=ANALYZE_REQUEST,
        output_dir=OUTPUT_DIR,
    )

    print(f"Wrote {preprocess_count} preprocess artifact(s) for {batch.file_stem}.")
    print(f"Wrote 1 analyze artifact for {batch.file_stem}: {analyzed.output_path.name}")
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
    for batch_index in range(total):
        exit_code = _process_batch(batch_index)
        if exit_code != 0:
            print(f"Batch {batch_index + 1}/{total} failed with exit code {exit_code}.")
            return exit_code

    print(f"Finished converting {total} batch(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
