from pathlib import Path

from src.raw_batches import discover_raw_batches, load_raw_batch, parse_raw_filename


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_parse_raw_filename_supports_hyphenated_product_ids() -> None:
    metadata = parse_raw_filename("level2-ETH-USD-updates-20260523.120000.csv")
    assert metadata is not None
    assert metadata.product_id == "ETH-USD"
    assert metadata.timestamp == "20260523.120000"
    assert metadata.kind == "updates"


def test_discover_raw_batches_requires_complete_triples(tmp_path: Path) -> None:
    _write(tmp_path / "level2-ETH-USD-init-20260523.120000.csv", "100,1,-1\n")
    _write(tmp_path / "level2-ETH-USD-updates-20260523.120000.csv", "43200,100,1,-1\n")
    _write(tmp_path / "trade-ETH-USD-20260523.120000.csv", "43200,100,1,1\n")
    _write(tmp_path / "level2-BTC-USD-init-20260523.120500.csv", "200,1,-1\n")

    batches = discover_raw_batches(tmp_path)

    assert len(batches) == 1
    batch = batches[0]
    assert batch.product_id == "ETH-USD"
    assert batch.timestamp == "20260523.120000"


def test_load_raw_batch_reads_all_three_csvs(tmp_path: Path) -> None:
    _write(tmp_path / "level2-ETH-USD-init-20260523.120000.csv", "100,1,-1\n")
    _write(tmp_path / "level2-ETH-USD-updates-20260523.120000.csv", "43200,100,1,-1\n")
    _write(tmp_path / "trade-ETH-USD-20260523.120000.csv", "43200,100,1,1\n")

    batch = discover_raw_batches(tmp_path)[0]
    loaded = load_raw_batch(batch)

    assert loaded.init == [[100.0, 1.0, -1.0]]
    assert loaded.updates == [[43200.0, 100.0, 1.0, -1.0]]
    assert loaded.trades == [[43200.0, 100.0, 1.0, 1.0]]
