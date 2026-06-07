from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from src.dataset_artifacts import build_analyze_output_path
from src.raw_batches import LoadedRawBatch, RawBatch, discover_raw_batches, load_raw_batch

from .core import analyze_loaded_data
from .models import (
    AnalyzeJobResult,
    AnalyzeRequest,
    AnalyzeResult,
    AnalyzeWorkerPayload,
    LoadedAnalyzeData,
)


DATA_V3_PATH = Path("data/v3")
OUTPUT_PATH = Path("data/preprocessed")
ANALYZE_RESULT_KEYS = (
    "price",
    "vol",
    "time",
    "side",
    "penetrated",
    "spread",
    "opp_vol",
    "fill_rate",
)
ANALYZE_TIMEZONE = ZoneInfo("Asia/Taipei")


def generate_analyze_timestamp() -> str:
    now = datetime.now(ANALYZE_TIMEZONE)
    return f"{now.strftime('%Y%m%d.%H%M%S')}.{now.microsecond // 1000:03d}"


def build_output_path(
    output_path: Path | str,
    analysis_name: str,
    analyze_timestamp: str,
    seq_num: int,
) -> Path:
    return build_analyze_output_path(
        output_path,
        analysis_name,
        analyze_timestamp,
        seq_num,
    )


def parse_dataset_groups(data_v3_path: Path | str) -> list[RawBatch]:
    return discover_raw_batches(data_v3_path)


def load_raw_dataset(dataset: RawBatch) -> LoadedAnalyzeData:
    loaded_batch: LoadedRawBatch = load_raw_batch(dataset)
    return LoadedAnalyzeData(
        init=loaded_batch.init,
        updates=loaded_batch.updates,
        trades=loaded_batch.trades,
        start_time=loaded_batch.start_time,
    )


def serialize_result_for_npz(result: AnalyzeResult) -> dict[str, Any]:
    return dict(zip(ANALYZE_RESULT_KEYS, result.as_tuple()))


def save_result_file(
    output_file: Path,
    *,
    request: AnalyzeRequest,
    analyze_timestamp: str,
    seq_num: int,
    dataset: RawBatch,
    result: AnalyzeResult,
) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {
        "analysis_name": request.analysis_name,
        "analyze_timestamp": analyze_timestamp,
        "seq_num": int(seq_num),
        "product_id": dataset.product_id,
        "timestamp": dataset.timestamp,
        "file_stem": dataset.file_stem,
    }
    save_kwargs.update(serialize_result_for_npz(result))
    np.savez_compressed(output_file, **save_kwargs)
    return output_file


def analyze_loaded_dataset(
    data: LoadedAnalyzeData,
    request: AnalyzeRequest,
) -> AnalyzeResult:
    del request
    return analyze_loaded_data(data)


def analyze_batch(
    dataset: RawBatch,
    request: AnalyzeRequest,
    output_dir: Path | str,
) -> AnalyzeJobResult:
    analyze_timestamp = generate_analyze_timestamp()
    seq_num = 0
    output_path = build_output_path(
        output_dir,
        request.analysis_name,
        analyze_timestamp,
        seq_num,
    )
    overwritten = output_path.exists()
    loaded_data = load_raw_dataset(dataset)
    result = analyze_loaded_dataset(loaded_data, request)
    saved_path = save_result_file(
        output_path,
        request=request,
        analyze_timestamp=analyze_timestamp,
        seq_num=seq_num,
        dataset=dataset,
        result=result,
    )
    return AnalyzeJobResult(
        dataset=dataset,
        output_path=saved_path,
        overwritten=overwritten,
        seq_num=seq_num,
    )


def get_default_worker_count(task_count: int) -> int:
    detected = os.cpu_count() or 1
    return max(1, min(task_count, detected))


def _process_dataset_job(
    dataset: RawBatch,
    output_path: Path | str,
    request: AnalyzeRequest,
    analyze_timestamp: str,
    seq_num: int,
) -> AnalyzeWorkerPayload:
    output_file = build_output_path(
        output_path,
        request.analysis_name,
        analyze_timestamp,
        seq_num,
    )
    overwritten = output_file.exists()
    loaded_data = load_raw_dataset(dataset)
    result = analyze_loaded_dataset(loaded_data, request)
    saved_path = save_result_file(
        output_file,
        request=request,
        analyze_timestamp=analyze_timestamp,
        seq_num=seq_num,
        dataset=dataset,
        result=result,
    )
    return AnalyzeWorkerPayload(
        file_stem=dataset.file_stem,
        output_file=str(saved_path),
        overwritten=overwritten,
        seq_num=seq_num,
    )


def _run_datasets_in_parallel(
    selected: list[RawBatch],
    output_path: Path | str,
    request: AnalyzeRequest,
) -> list[AnalyzeWorkerPayload]:
    worker_count = get_default_worker_count(len(selected))
    analyze_timestamp = generate_analyze_timestamp()
    results: list[AnalyzeWorkerPayload] = []
    failures: list[tuple[str, Exception]] = []
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        future_to_dataset = {
            executor.submit(
                _process_dataset_job,
                dataset,
                output_path,
                request,
                analyze_timestamp,
                seq_num,
            ): dataset
            for seq_num, dataset in enumerate(selected)
        }
        for future in as_completed(future_to_dataset):
            dataset = future_to_dataset[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append((dataset.file_stem, exc))

    if failures:
        failed_stems = ", ".join(file_stem for file_stem, _exc in failures)
        raise RuntimeError(f"Batch processing failed for: {failed_stems}")

    return results


def analyze_batches(
    datasets: list[RawBatch],
    request: AnalyzeRequest,
    output_dir: Path | str,
) -> list[AnalyzeJobResult]:
    if len(datasets) <= 1:
        return [analyze_batch(dataset, request, output_dir) for dataset in datasets]

    results = _run_datasets_in_parallel(datasets, output_dir, request)
    dataset_by_stem = {dataset.file_stem: dataset for dataset in datasets}
    job_results = [
        result.to_job_result(dataset_by_stem[result.file_stem])
        for result in results
    ]
    order_by_stem = {dataset.file_stem: index for index, dataset in enumerate(datasets)}
    job_results.sort(key=lambda result: order_by_stem[result.dataset.file_stem])
    return job_results
