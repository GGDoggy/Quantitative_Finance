import calendar
import os
import csv
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


DATA_V3_PATH = Path("data/v3")
OUTPUT_PATH = Path("data/preprocessed")
DEFAULT_TIME_STEP = 0.01
DEFAULT_BASE_TICK = 0.00000001
OUTPUT_SUFFIX = "simulation-time_averaged_random_cancelation"
DEBUG_BEST_STATE = os.environ.get("DEBUG_BEST_STATE", "").lower() in {"1", "true", "yes", "on"}


@dataclass
class VirtualOrder:
    submit_time: float
    price: float
    near_size: float
    opp_size: float
    ahead: float
    behind: float
    vorder_ratio: float
    remaining_size: float
    result: int = -1
    survival_time: float = -1.0


@dataclass
class TradeEvidence:
    price: float
    volume: float
    event_time: float


def read_csv(path):
    with open(path) as file:
        reader = csv.reader(file, quoting=csv.QUOTE_NONNUMERIC)
        data = list(reader)
    return data


def file_time_to_unix(file_time):
    sec = time.strptime(file_time, "%Y%m%d.%H%M%S")
    return calendar.timegm(sec)


def unix_to_daily_seconds(unix_time):
    dt = datetime.fromtimestamp(unix_time, tz=timezone.utc)
    return (
        dt.hour * 3600
        + dt.minute * 60
        + dt.second
        + dt.microsecond / 1_000_000
    )


def same_price(lhs, rhs):
    if np.isnan(lhs) or np.isnan(rhs):
        return False
    return np.isclose(lhs, rhs)


def get_price_index(price_levels, price):
    return int(np.searchsorted(price_levels, price))


def update_orderbook(orderbook, price_levels, price, volume, side):
    price_index = get_price_index(price_levels, price)
    orderbook[price_index] = volume * side * -1
    return price_index, orderbook[price_index]


def initialize_best_indices(orderbook):
    best_bid_index = None
    best_ask_index = None

    for index in range(len(orderbook) - 1, -1, -1):
        if orderbook[index] < 0:
            best_bid_index = index
            break

    for index in range(len(orderbook)):
        if orderbook[index] > 0:
            best_ask_index = index
            break

    return best_bid_index, best_ask_index


def has_valid_bid_at_index(orderbook, price_index):
    return price_index is not None and orderbook[price_index] < 0


def has_valid_ask_at_index(orderbook, price_index):
    return price_index is not None and orderbook[price_index] > 0


def refresh_best_indices(orderbook, best_bid_index, best_ask_index):
    if has_valid_bid_at_index(orderbook, best_bid_index) and has_valid_ask_at_index(orderbook, best_ask_index):
        return best_bid_index, best_ask_index
    return initialize_best_indices(orderbook)


def advance_best_bid_index(orderbook, updated_index, current_best_index):
    if current_best_index is None:
        if orderbook[updated_index] < 0:
            return updated_index
        return None

    if updated_index > current_best_index and orderbook[updated_index] < 0:
        return updated_index

    if updated_index != current_best_index:
        return current_best_index

    if orderbook[current_best_index] < 0:
        return current_best_index

    for index in range(current_best_index - 1, -1, -1):
        if orderbook[index] < 0:
            return index
    return None


def advance_best_ask_index(orderbook, updated_index, current_best_index):
    if current_best_index is None:
        if orderbook[updated_index] > 0:
            return updated_index
        return None

    if updated_index < current_best_index and orderbook[updated_index] > 0:
        return updated_index

    if updated_index != current_best_index:
        return current_best_index

    if orderbook[current_best_index] > 0:
        return current_best_index

    for index in range(current_best_index + 1, len(orderbook)):
        if orderbook[index] > 0:
            return index
    return None


def get_best_levels_from_indices(orderbook, price_levels, best_bid_index, best_ask_index):
    if best_bid_index is None:
        best_bid_price = np.nan
        best_bid_size = 0.0
    else:
        best_bid_price = price_levels[best_bid_index]
        best_bid_size = -orderbook[best_bid_index]

    if best_ask_index is None:
        best_ask_price = np.nan
        best_ask_size = 0.0
    else:
        best_ask_price = price_levels[best_ask_index]
        best_ask_size = orderbook[best_ask_index]

    return best_bid_price, best_bid_size, best_ask_price, best_ask_size


def debug_best_state(
    stage,
    orderbook,
    price_levels,
    best_bid_index,
    best_ask_index,
    best_bid_price,
    best_bid_size,
    best_ask_price,
    best_ask_size,
    event_time=None,
    event_type=None,
    event_price=None,
    event_volume=None,
    event_side=None,
    updated_index=None,
):
    if not DEBUG_BEST_STATE:
        return

    bid_raw = None if best_bid_index is None else float(orderbook[best_bid_index])
    ask_raw = None if best_ask_index is None else float(orderbook[best_ask_index])
    bid_invalid = best_bid_index is not None and bid_raw >= 0.0
    ask_invalid = best_ask_index is not None and ask_raw <= 0.0

    if not (bid_invalid or ask_invalid):
        return

    print(
        "[DEBUG_BEST_STATE]",
        f"stage={stage}",
        f"time={event_time}",
        f"event_type={event_type}",
        f"event_side={event_side}",
        f"event_price={event_price}",
        f"event_volume={event_volume}",
        f"updated_index={updated_index}",
        f"bid_index={best_bid_index}",
        f"bid_price={best_bid_price}",
        f"bid_size={best_bid_size}",
        f"bid_raw={bid_raw}",
        f"ask_index={best_ask_index}",
        f"ask_price={best_ask_price}",
        f"ask_size={best_ask_size}",
        f"ask_raw={ask_raw}",
    )


def build_event_stream(updates, trades):
    events = []
    for update in updates:
        events.append((update[0], 1, "update", update[1], update[2], int(update[3])))
    for trade in trades:
        events.append((trade[0], 0, "trade", trade[1], trade[2], int(trade[3])))
    events.sort(key=lambda item: (item[0], item[1]))
    return events


def side_to_trade_key(trade_side):
    return "bid" if trade_side == 1 else "ask"


def is_worse_best_price_change(book_side, previous_price, current_price):
    if np.isnan(previous_price) or np.isnan(current_price):
        return False
    if book_side == "bid":
        return current_price < previous_price and not same_price(current_price, previous_price)
    return current_price > previous_price and not same_price(current_price, previous_price)


def trade_reaches_price(book_side, trade_price, level_price):
    if np.isnan(level_price):
        return False
    if book_side == "bid":
        return trade_price <= level_price or same_price(trade_price, level_price)
    return trade_price >= level_price or same_price(trade_price, level_price)


def trade_hits_level(book_side, trade_price, level_price):
    return same_price(trade_price, level_price)


def create_virtual_order(best_size, opp_size, submit_time, submit_price, base_tick):
    if np.isnan(submit_price) or best_size <= 0:
        return None
    return VirtualOrder(
        submit_time=submit_time,
        price=float(submit_price),
        near_size=float(best_size),
        opp_size=float(opp_size),
        ahead=float(best_size),
        behind=0.0,
        vorder_ratio=float(base_tick / best_size),
        remaining_size=float(base_tick),
    )


def finalize_order(order, end_time, result):
    if order.result != -1:
        return
    order.result = result
    order.survival_time = float(end_time - order.submit_time)
    order.ahead = max(order.ahead, 0.0)
    order.behind = max(order.behind, 0.0)


def get_orders_bucket(orders_by_price, price_index):
    if price_index is None:
        return []
    return orders_by_price.setdefault(price_index, [])


def get_active_orders_at_index(orders_by_price, price_index):
    if price_index is None:
        return []
    return [order for order in orders_by_price.get(price_index, []) if order.result == -1]


def apply_size_delta(active_orders, delta):
    if not active_orders or delta == 0:
        return

    if delta > 0:
        for order in active_orders:
            if order.result == -1:
                order.behind += delta
        return

    reduction = -delta
    for order in active_orders:
        if order.result != -1:
            continue
        total_queue = order.ahead + order.behind
        if total_queue <= 0:
            continue
        ahead_reduction = reduction * order.ahead / total_queue
        behind_reduction = reduction * order.behind / total_queue
        order.ahead = max(order.ahead - ahead_reduction, 0.0)
        order.behind = max(order.behind - behind_reduction, 0.0)


def apply_trade_volume(active_orders, traded_size, event_time):
    if traded_size <= 0:
        return

    for order in active_orders:
        if order.result != -1:
            continue

        if order.ahead > 0:
            ahead_consumed = min(order.ahead, traded_size)
            order.ahead -= ahead_consumed
            traded_size -= ahead_consumed

        if traded_size <= 0:
            continue

        fill_size = min(order.remaining_size, traded_size)
        order.remaining_size -= fill_size
        traded_size -= fill_size

        if order.remaining_size <= 0:
            finalize_order(order, event_time, 1)


def append_trade_evidence(pending_trade_evidence, trade_side, price, volume, event_time):
    trade_key = side_to_trade_key(trade_side)
    pending_trade_evidence[trade_key].append(
        TradeEvidence(price=float(price), volume=float(volume), event_time=float(event_time))
    )


def split_trade_evidence(records, book_side, level_price):
    traded_at_level = 0.0
    traded_at_level_time = None
    traded_through_level = 0.0
    traded_through_level_time = None

    for record in records:
        if trade_hits_level(book_side, record.price, level_price):
            traded_at_level += record.volume
            traded_at_level_time = record.event_time
        if trade_reaches_price(book_side, record.price, level_price):
            traded_through_level += record.volume
            traded_through_level_time = record.event_time

    return (
        traded_at_level,
        traded_at_level_time,
        traded_through_level,
        traded_through_level_time,
    )


def reconcile_same_best_price(active_orders, size_delta, traded_at_level, event_time):
    if not active_orders:
        return

    if traded_at_level > 0:
        apply_trade_volume(active_orders, traded_at_level, event_time)

    residual = size_delta + traded_at_level
    if not np.isclose(residual, 0.0):
        apply_size_delta(active_orders, residual)


def reconcile_price_change(active_orders, has_sweep_evidence, event_time):
    for order in active_orders:
        if order.result != -1:
            continue
        finalize_order(order, event_time, 1 if has_sweep_evidence else 0)


def reconcile_one_side(
    book_side,
    orders_by_price,
    previous_best_index,
    previous_best_price,
    previous_best_size,
    current_best_price,
    current_best_size,
    pending_trade_records,
    update_event_time,
):
    if previous_best_index is None or np.isnan(previous_best_price):
        return False

    orders_at_previous_best = get_active_orders_at_index(orders_by_price, previous_best_index)
    best_price_unchanged = same_price(previous_best_price, current_best_price)
    best_size_unchanged = np.isclose(previous_best_size, current_best_size)
    if best_price_unchanged and best_size_unchanged:
        return False

    (
        traded_at_level,
        traded_at_level_time,
        traded_through_level,
        traded_through_level_time,
    ) = split_trade_evidence(pending_trade_records, book_side, previous_best_price)

    if best_price_unchanged:
        reconcile_same_best_price(
            orders_at_previous_best,
            current_best_size - previous_best_size,
            traded_at_level,
            traded_at_level_time if traded_at_level_time is not None else update_event_time,
        )
        return True

    if is_worse_best_price_change(book_side, previous_best_price, current_best_price):
        has_sweep_evidence = traded_through_level > 0
        reconcile_price_change(
            orders_at_previous_best,
            has_sweep_evidence,
            traded_through_level_time if traded_through_level_time is not None else update_event_time,
        )
        return True

    reconcile_price_change(orders_at_previous_best, False, update_event_time)
    return True


def finalize_unresolved(orders):
    price = np.array([order.price for order in orders], dtype=float)
    near_size = np.array([order.near_size for order in orders], dtype=float)
    opp_size = np.array([order.opp_size for order in orders], dtype=float)
    survival_time = np.array([order.survival_time for order in orders], dtype=float)
    ahead = np.array([max(order.ahead, 0.0) for order in orders], dtype=float)
    behind = np.array([max(order.behind, 0.0) for order in orders], dtype=float)
    vorder_ratio = np.array([order.vorder_ratio for order in orders], dtype=float)
    result = np.array([order.result for order in orders], dtype=int)
    return price, near_size, opp_size, survival_time, ahead, behind, vorder_ratio, result


def empty_outputs():
    empty_sim = np.array([], dtype=float)
    empty_result = np.array([], dtype=int)
    return (
        empty_sim,
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_result,
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_sim.copy(),
        empty_result.copy(),
    )


def parse_dataset_groups(data_v3_path):
    grouped = {}
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
        grouped.setdefault(
            key,
            {
                "product_id": product_id,
                "timestamp": timestamp,
                "file_stem": f"{product_id}-{timestamp}",
            },
        )[data_type] = path

    available = []
    for dataset in grouped.values():
        if {"init", "updates", "trade"} <= dataset.keys():
            available.append(dataset)
    return sorted(available, key=lambda item: (item["product_id"], item["timestamp"]))


def build_output_path(output_path, product_id, timestamp, time_step):
    filename = f"{product_id}-{timestamp}-{time_step}-{OUTPUT_SUFFIX}.npz"
    return Path(output_path) / filename


def is_processed(dataset, output_path, time_step):
    return build_output_path(output_path, dataset["product_id"], dataset["timestamp"], time_step).exists()


def load_dataset(dataset):
    init = read_csv(dataset["init"])
    updates = read_csv(dataset["updates"])
    trades = read_csv(dataset["trade"])
    start_time = file_time_to_unix(dataset["timestamp"])
    return init, updates, trades, start_time


def run_dataset_simulation(dataset, time_step, base_tick):
    init, updates, trades, start_time = load_dataset(dataset)
    return simulate_virtual_best_orders(
        init,
        updates,
        trades,
        start_time,
        time_step=time_step,
        base_tick=base_tick,
    )


def process_dataset_job(dataset, output_path, time_step, base_tick):
    result = run_dataset_simulation(dataset, time_step, base_tick)
    output_file = save_simulation_npz(dataset, output_path, time_step, base_tick, result)
    return {
        "file_stem": dataset["file_stem"],
        "output_file": str(output_file),
        "status": "saved",
    }


def save_simulation_npz(dataset, output_path, time_step, base_tick, result):
    output_file = build_output_path(output_path, dataset["product_id"], dataset["timestamp"], time_step)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    (
        bid_prices,
        bid_near_size,
        bid_opp_size,
        bid_survival_time,
        bid_ahead,
        bid_behind,
        bid_vorder_ratio,
        bid_result,
        ask_prices,
        ask_near_size,
        ask_opp_size,
        ask_survival_time,
        ask_ahead,
        ask_behind,
        ask_vorder_ratio,
        ask_result,
    ) = result

    np.savez_compressed(
        output_file,
        product_id=dataset["product_id"],
        file_stem=dataset["file_stem"],
        time_step=time_step,
        base_tick=base_tick,
        bid_prices=bid_prices,
        bid_near_size=bid_near_size,
        bid_opp_size=bid_opp_size,
        bid_survival_time=bid_survival_time,
        bid_ahead=bid_ahead,
        bid_behind=bid_behind,
        bid_vorder_ratio=bid_vorder_ratio,
        bid_result=bid_result,
        ask_prices=ask_prices,
        ask_near_size=ask_near_size,
        ask_opp_size=ask_opp_size,
        ask_survival_time=ask_survival_time,
        ask_ahead=ask_ahead,
        ask_behind=ask_behind,
        ask_vorder_ratio=ask_vorder_ratio,
        ask_result=ask_result,
    )
    return output_file


def format_dataset_line(index, dataset, output_path, time_step):
    output_file = build_output_path(output_path, dataset["product_id"], dataset["timestamp"], time_step)
    return f"[{index}] {dataset['file_stem']} -> {output_file.name}"


def parse_selection(selection, dataset_count):
    selection = selection.strip().lower()
    if selection == "all":
        return list(range(dataset_count))

    chosen = []
    for token in selection.split(","):
        token = token.strip()
        if not token:
            continue
        if not token.isdigit():
            raise ValueError(f"Invalid selection token: {token}")
        index = int(token) - 1
        if index < 0 or index >= dataset_count:
            raise ValueError(f"Selection out of range: {token}")
        chosen.append(index)

    if not chosen:
        raise ValueError("No dataset selected.")
    return sorted(set(chosen))


def prompt_dataset_selection(datasets, output_path, time_step):
    print("Available unprocessed datasets:")
    for index, dataset in enumerate(datasets, start=1):
        print(format_dataset_line(index, dataset, output_path, time_step))
    print("Enter a number, comma-separated numbers, or 'all'.")

    while True:
        raw = input("Selection: ")
        try:
            selected_indices = parse_selection(raw, len(datasets))
            return [datasets[index] for index in selected_indices]
        except ValueError as exc:
            print(exc)


def get_default_worker_count(task_count):
    cpu_count = os.cpu_count() or 1
    return max(1, min(task_count, cpu_count))


def run_datasets_in_parallel(selected, output_path, time_step, base_tick):
    worker_count = get_default_worker_count(len(selected))
    failures = []
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        future_to_dataset = {
            executor.submit(process_dataset_job, dataset, output_path, time_step, base_tick): dataset
            for dataset in selected
        }
        for future in as_completed(future_to_dataset):
            dataset = future_to_dataset[future]
            try:
                job_result = future.result()
                print(f"Saved {job_result['output_file']}")
            except Exception as exc:
                print(f"Failed {dataset['file_stem']}: {exc}")
                failures.append((dataset["file_stem"], exc))

    if failures:
        failed_stems = ", ".join(file_stem for file_stem, _exc in failures)
        raise RuntimeError(f"Batch processing failed for: {failed_stems}")


def run_cli(data_v3_path=DATA_V3_PATH, output_path=OUTPUT_PATH, time_step=DEFAULT_TIME_STEP, base_tick=DEFAULT_BASE_TICK):
    datasets = parse_dataset_groups(data_v3_path)
    pending = [dataset for dataset in datasets if not is_processed(dataset, output_path, time_step)]

    if not pending:
        print("No unprocessed datasets found.")
        return

    selected = prompt_dataset_selection(pending, output_path, time_step)
    if len(selected) == 1:
        dataset = selected[0]
        print(f"Processing {dataset['file_stem']}...")
        result = run_dataset_simulation(dataset, time_step, base_tick)
        output_file = save_simulation_npz(dataset, output_path, time_step, base_tick, result)
        print(f"Saved {output_file}")
        return

    print(f"Processing {len(selected)} datasets with {get_default_worker_count(len(selected))} workers...")
    run_datasets_in_parallel(selected, output_path, time_step, base_tick)


def simulate_virtual_best_orders(
    init,
    updates,
    trades,
    start_time,
    time_step,
    base_tick,
):
    price_levels = {level[0] for level in init}
    price_levels.update(update[1] for update in updates)
    price_levels = np.array(sorted(price_levels), dtype=float)

    orderbook = np.zeros(len(price_levels), dtype=float)
    for level in init:
        update_orderbook(orderbook, price_levels, level[0], level[1], level[2])

    best_bid_index, best_ask_index = initialize_best_indices(orderbook)

    orderbook_start_time = min(update[0] for update in updates) if updates else unix_to_daily_seconds(start_time)
    orderbook_end_time = max(update[0] for update in updates) if updates else orderbook_start_time

    if not trades:
        return empty_outputs()

    trade_start_time = min(trade[0] for trade in trades)
    trade_end_time = max(trade[0] for trade in trades)
    simulation_start = max(orderbook_start_time, trade_start_time) + 1.0
    simulation_end = min(orderbook_end_time, trade_end_time) - 1.0

    if simulation_end < simulation_start:
        return empty_outputs()

    events = build_event_stream(updates, trades)
    event_index = 0
    next_submit_time = simulation_start
    pending_trade_evidence = {"bid": [], "ask": []}

    bid_orders_by_price = {}
    ask_orders_by_price = {}

    while event_index < len(events) or next_submit_time <= simulation_end:
        next_event_time = events[event_index][0] if event_index < len(events) else float("inf")

        if next_event_time <= next_submit_time and event_index < len(events):
            (
                event_time,
                _priority,
                event_type,
                event_price,
                event_volume,
                event_side,
            ) = events[event_index]
            event_index += 1

            best_bid_price, best_bid_size, best_ask_price, best_ask_size = get_best_levels_from_indices(
                orderbook,
                price_levels,
                best_bid_index,
                best_ask_index,
            )
            debug_best_state(
                "before_event",
                orderbook,
                price_levels,
                best_bid_index,
                best_ask_index,
                best_bid_price,
                best_bid_size,
                best_ask_price,
                best_ask_size,
                event_time=event_time,
                event_type=event_type,
                event_price=event_price,
                event_volume=event_volume,
                event_side=event_side,
            )

            if event_type == "trade":
                append_trade_evidence(
                    pending_trade_evidence,
                    event_side,
                    event_price,
                    event_volume,
                    event_time,
                )
                continue

            previous_bid_price = best_bid_price
            previous_bid_size = best_bid_size
            previous_ask_price = best_ask_price
            previous_ask_size = best_ask_size
            previous_bid_index = best_bid_index
            previous_ask_index = best_ask_index

            updated_index, _updated_value = update_orderbook(orderbook, price_levels, event_price, event_volume, event_side)
            best_bid_index, best_ask_index = refresh_best_indices(
                orderbook,
                best_bid_index,
                best_ask_index,
            )

            current_bid_price, current_bid_size, current_ask_price, current_ask_size = get_best_levels_from_indices(
                orderbook,
                price_levels,
                best_bid_index,
                best_ask_index,
            )
            debug_best_state(
                "after_update",
                orderbook,
                price_levels,
                best_bid_index,
                best_ask_index,
                current_bid_price,
                current_bid_size,
                current_ask_price,
                current_ask_size,
                event_time=event_time,
                event_type=event_type,
                event_price=event_price,
                event_volume=event_volume,
                event_side=event_side,
                updated_index=updated_index,
            )

            bid_consumed = reconcile_one_side(
                "bid",
                bid_orders_by_price,
                previous_bid_index,
                previous_bid_price,
                previous_bid_size,
                current_bid_price,
                current_bid_size,
                pending_trade_evidence["bid"],
                event_time,
            )
            ask_consumed = reconcile_one_side(
                "ask",
                ask_orders_by_price,
                previous_ask_index,
                previous_ask_price,
                previous_ask_size,
                current_ask_price,
                current_ask_size,
                pending_trade_evidence["ask"],
                event_time,
            )

            if bid_consumed:
                pending_trade_evidence["bid"].clear()
            if ask_consumed:
                pending_trade_evidence["ask"].clear()
            continue

        if next_submit_time > simulation_end:
            break

        best_bid_price, best_bid_size, best_ask_price, best_ask_size = get_best_levels_from_indices(
            orderbook,
            price_levels,
            best_bid_index,
            best_ask_index,
        )
        debug_best_state(
            "before_submit",
            orderbook,
            price_levels,
            best_bid_index,
            best_ask_index,
            best_bid_price,
            best_bid_size,
            best_ask_price,
            best_ask_size,
            event_time=next_submit_time,
            event_type="submit",
        )

        bid_order = create_virtual_order(
            best_bid_size,
            best_ask_size,
            next_submit_time,
            best_bid_price,
            base_tick,
        )
        if bid_order is not None:
            get_orders_bucket(bid_orders_by_price, best_bid_index).append(bid_order)

        ask_order = create_virtual_order(
            best_ask_size,
            best_bid_size,
            next_submit_time,
            best_ask_price,
            base_tick,
        )
        if ask_order is not None:
            get_orders_bucket(ask_orders_by_price, best_ask_index).append(ask_order)

        next_submit_time += time_step

    bid_orders = [order for bucket in bid_orders_by_price.values() for order in bucket]
    ask_orders = [order for bucket in ask_orders_by_price.values() for order in bucket]

    for order in bid_orders:
        if order.result == -1:
            order.ahead = max(order.ahead, 0.0)
            order.behind = max(order.behind, 0.0)
    for order in ask_orders:
        if order.result == -1:
            order.ahead = max(order.ahead, 0.0)
            order.behind = max(order.behind, 0.0)

    return (
        *finalize_unresolved(bid_orders),
        *finalize_unresolved(ask_orders),
    )


if __name__ == "__main__":
    run_cli()
