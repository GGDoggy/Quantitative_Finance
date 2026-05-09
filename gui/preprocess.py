from os import walk
import csv
import time
import calendar
import numpy as np
from datetime import datetime, timezone, timedelta

def search_data(path: str):
    for a, b, c in walk(path):
        filelist = c
        break
    
    data_name_list = []
    for file in filelist:
        split = file.split("-")
        if split[-2] == "init":
            id = file[7:-25]
            data_name_list.append((id, split[-1][:-4]))
    
    available = []
    ids = set()
    for data_name in data_name_list:
        l2_updates = f"level2-{data_name[0]}-updates-{data_name[1]}.csv"
        trade = f"trade-{data_name[0]}-{data_name[1]}.csv"
        if l2_updates in filelist and trade in filelist:
            available.append(data_name)
            ids.add(data_name[0])
    
    return available, list(ids)

def read_csv(path):
    with open(path) as file:
        reader = csv.reader(file, quoting=csv.QUOTE_NONNUMERIC)
        data = list(reader)
    return data

def file_time_to_unix(file_time: str):
    sec = time.strptime(file_time, "%Y%m%d.%H%M%S")
    sec = calendar.timegm(sec)
    return sec

def update_orderbook(orderbook, price_levels, price, volume, side):
    ind = np.searchsorted(price_levels, price)
    orderbook[ind] = volume * side * -1

def orderbook_to_volatility(orderbooks):
    for i, vol in enumerate(orderbooks):
        if vol > 0:
            mid = i
            break
    for i in range(mid+1, len(orderbooks)):
        orderbooks[i] += orderbooks[i-1]
    i = mid - 2
    while i >= 0:
        orderbooks[i] += orderbooks[i+1]
        i -= 1
    return orderbooks

def get_bid_ask(orderbook, price_levels):
    for i, v in enumerate(orderbook):
        if v > 0:
            break
        if v != 0:
            bid = price_levels[i]
    n = len(orderbook) - 1
    for i in range(n):
        v = orderbook[n - i]
        if v < 0:
            break
        if v != 0:
            ask = price_levels[n - i]
    return bid, ask

def to_plotable(init, updates, start_time: int, time_step):
    # Generate price axis
    price_levels = set()
    for level in init:
        price_levels.add(level[0])
    for update in updates:
        price_levels.add(update[1])
    price_levels = np.array(list(price_levels))
    price_levels.sort()
    price_num = len(price_levels)
    
    orderbook = np.zeros(price_num)
    for level in init:
        update_orderbook(orderbook, price_levels, level[0], level[1], level[2])
    # Generate order book history
    orderbook_list = []
    bid = []
    ask = []
    start_time = datetime.fromtimestamp(start_time, tz=timezone(timedelta()))
    time_origin = start_time - timedelta(hours=start_time.hour, minutes=start_time.minute, seconds=start_time.second)
    time_step = timedelta(seconds=time_step)
    index = 0
    time_num = 0
    updates.sort()
    current_time = time_origin
    start_update = False
    while index < len(updates):
        next_update_time = time_origin + timedelta(seconds=updates[index][0])
        if current_time < next_update_time:
            if start_update:
                orderbook_list.append(orderbook.copy())
                b, a = get_bid_ask(orderbook, price_levels)
                bid.append(b)
                ask.append(a)
                end_time = current_time
                time_num += 1
            current_time += time_step
            continue
        else:
            update_orderbook(orderbook, price_levels, updates[index][1], updates[index][2], updates[index][3])
            start_update = True
            index += 1
            continue
    else:
        orderbook_list.append(orderbook.copy())
        b, a = get_bid_ask(orderbook, price_levels)
        bid.append(b)
        ask.append(a)
        end_time = current_time
        time_num += 1
    start_time = end_time - time_step * (time_num - 1)
    # Generage time axis
    time_axis = start_time + np.arange(time_num) * time_step

    return price_levels, np.array(time_axis, dtype='datetime64[ns]'), np.array(orderbook_list), np.array(bid), np.array(ask)



time_step = 0.01
path = "data/v3/"
save_path = "data/preprocessed/"

file_list, products = search_data(path)

for file in file_list:
    l2_init = read_csv(path + f"level2-{file[0]}-init-{file[1]}.csv")
    l2_updates = read_csv(path + f"level2-{file[0]}-updates-{file[1]}.csv")
    trade = read_csv(path + f"trade-{file[0]}-{file[1]}.csv")

    price_axis, time_axis, data, bid, ask = to_plotable(l2_init, l2_updates, file_time_to_unix(file[1]), time_step)

    np.savez_compressed(save_path + f"{file[0]}-{file[1]}-{time_step}-orderbook_for_plot", price_axis=price_axis, time_axis=time_axis, data=data, bid=bid, ask=ask)