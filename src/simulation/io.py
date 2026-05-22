from __future__ import annotations

from pathlib import Path

from ._simulation_core import file_time_to_unix, read_csv
from .models import LoadedMarketData, RawSimulationDataset


def parse_dataset_groups(data_v3_path: Path | str) -> list[RawSimulationDataset]:
    grouped: dict[tuple[str, str], RawSimulationDataset] = {}
    for path in sorted(Path(data_v3_path).glob("*.csv")):
        stem_parts = path.stem.split("-")
        if len(stem_parts) < 4:
            continue

        if stem_parts[0] == "level2" and stem_parts[-2] in {"init", "updates"}:
            data_type = stem_parts[-2]
            timestamp = stem_parts[-1]
            product_id = "-".join(stem_parts[1:-2])
        elif stem_parts[0] == "trade":
            data_type = "trade"
            timestamp = stem_parts[-1]
            product_id = "-".join(stem_parts[1:-1])
        else:
            continue

        key = (product_id, timestamp)
        dataset = grouped.get(key)
        if dataset is None:
            dataset = RawSimulationDataset(
                product_id=product_id,
                timestamp=timestamp,
                file_stem=f"{product_id}-{timestamp}",
                init=Path(),
                updates=Path(),
                trade=Path(),
            )

        grouped[key] = RawSimulationDataset(
            product_id=dataset.product_id,
            timestamp=dataset.timestamp,
            file_stem=dataset.file_stem,
            init=path if data_type == "init" else dataset.init,
            updates=path if data_type == "updates" else dataset.updates,
            trade=path if data_type == "trade" else dataset.trade,
        )

    available = [
        dataset
        for dataset in grouped.values()
        if dataset.init and dataset.updates and dataset.trade
    ]
    return sorted(available, key=lambda item: (item.product_id, item.timestamp))


def load_raw_dataset(dataset: RawSimulationDataset) -> LoadedMarketData:
    init = read_csv(dataset.init)
    updates = read_csv(dataset.updates)
    trades = read_csv(dataset.trade)
    start_time = file_time_to_unix(dataset.timestamp)
    return init, updates, trades, start_time
