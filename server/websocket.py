from coinbase.websocket import WSClient
import json
import time
import calendar
import bisect
import copy
import asyncio
import aiofiles
from aiocsv import AsyncWriter
import threading


save_queue = None
async_loop = None

def start_async_thread():
    global async_loop, save_queue
    async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(async_loop)
    save_queue = asyncio.Queue()
    async_loop.create_task(save_csv())
    async_loop.run_forever()

async def save_csv():
    while True:
        data, filename = await save_queue.get()
        try:
            if data:
                async with aiofiles.open(filename, "w", newline="") as file:
                    writer = AsyncWriter(file)
                    await writer.writerows(data)
        finally:
            save_queue.task_done()

threading.Thread(target=start_async_thread, daemon=True).start()

def trigger_save_l2(data, id, data_type, start_time: int):
    start_time = time.strftime("%Y%m%d.%H%M%S", time.gmtime(start_time))
    filename = f"level2-{id}-{data_type}-{start_time}.csv"
    if async_loop and async_loop.is_running():
        async_loop.call_soon_threadsafe(save_queue.put_nowait, (data, filename))

def trigger_save_trade(data, id, start_time: int):
    start_time = time.strftime("%Y%m%d.%H%M%S", time.gmtime(start_time))
    filename = f"trade-{id}-{start_time}.csv"
    if async_loop and async_loop.is_running():
        async_loop.call_soon_threadsafe(save_queue.put_nowait, (data, filename))

def received_time_to_float(time_from_websocket: str):
    sec = time_from_websocket[:19]
    sec = time.strptime(sec, "%Y-%m-%dT%H:%M:%S")
    sec = calendar.timegm(sec)
    return sec, float("0" + time_from_websocket[19:-1])

def unix_to_daily_sec(unix_time: str):
    t = received_time_to_float(unix_time)
    sec = int(time.strftime("%S", time.gmtime(t[0])))
    min = int(time.strftime("%M", time.gmtime(t[0])))
    hr = int(time.strftime("%H", time.gmtime(t[0])))
    return hr*1440 + min*60 + sec + t[1]

def update_to_order(update):
    side = {"bid":1, "offer":-1}[update["side"]]
    price = float(update["price_level"])
    return [(-side, price), unix_to_daily_sec(update["event_time"]), update["price_level"], update["new_quantity"], side]

def one_trade_to_csvarr(trade):
    t = str(unix_to_daily_sec(trade["time"])) + str(received_time_to_float(trade["time"])[1])[1:]
    return [unix_to_daily_sec(trade["time"]), trade["price"], trade["size"], {"BUY":1, "SELL":-1}[trade["side"]]]

def orderbook_to_csvarr(snapshot):
    csvarr = []
    orderbook = []
    for s in snapshot:
        csvarr.append([s["price_level"], s["new_quantity"], {"bid":1, "offer":-1}[s["side"]]])
        orderbook.append(update_to_order(s))
    return csvarr, orderbook

def save_all_data(l2_updates, trade, id, start_time):
    trigger_save_l2(copy.deepcopy(l2_updates), id, "updates", start_time)
    print("Level2 updates saved.")
    trigger_save_trade(copy.deepcopy(trade), id, start_time)
    print("Trade saved.")

def on_message(msg):
    global l2_hist
    global trade_hist
    global orderbook
    global start_time
    global restart
    global id
    global heartbeat_counter
    global seq_num
    msg = json.loads(msg)

    # Skip everything and wait for restart
    if restart:
        return

    # Check sequence_num continuity
    if msg["sequence_num"] != seq_num:
        print("sequence_num error.")
        restart = True
        return
    else:
        seq_num += 1

    if msg["channel"] == "heartbeats":
        # Check heartbeat continuity
        if len(msg["events"]) > 1:
            print("Received more than 1 heartbeat.")
            restart = True
            return
        if heartbeat_counter == 0:
            heartbeat_counter = int(msg["events"][0]["heartbeat_counter"])
        else:
            if int(msg["events"][0]["heartbeat_counter"]) != heartbeat_counter + 1:
                print("Heartbeat counter error.")
                restart = True
                return
            heartbeat_counter += 1
    
    if msg["channel"] == "l2_data":
        for event in msg["events"]:
            if event["type"] == "snapshot":
                if orderbook:
                    # Get second snapshot -> something went wrong
                    print("Received second snapshot.")
                    restart = True
                    break
                start_time = received_time_to_float(msg["timestamp"])[0]
                csvarr, orderbook = orderbook_to_csvarr(event["updates"])
                orderbook.sort()
                # Save init orderbook
                trigger_save_l2(copy.deepcopy(csvarr), id, "init", start_time)
                print("Level2 init saved.")
            else:  # Receive update
                for update in event["updates"]:
                    if orderbook == []:
                        continue
                    u = update_to_order(update)
                    ind = bisect.bisect_left(orderbook, u)
                    # Only keep new information
                    if ind >= len(orderbook):
                        l2_hist.append(u[1:])
                        orderbook.append(u)
                    elif orderbook[ind][1] < u[1]:
                        l2_hist.append(u[1:])
                        if orderbook[ind][2] == u[2] and orderbook[ind][4] == u[4]:
                            if u[2] == "0":
                                del orderbook[ind]
                            else:
                                orderbook[ind] = u
                        else:
                            bisect.insort(orderbook, u)
    
    if msg["channel"] == "market_trades":
        for event in msg["events"]:            
            for trade in event["trades"]:
                # Unix time
                tr = one_trade_to_csvarr(trade)
                trade_hist.append(tr)


with open("config.json", "r") as file:
    config = json.load(file)

saving_interval = config["saving_interval"]
# Only one id for now
if len(config["product_id"]) > 1:
    print("Can only work on 1 product.")
    run = False
else:
    run = True
product_id = [config["product_id"][0]]
id = product_id[0]

ws_client = WSClient(on_message=on_message, verbose=True)

while run:
    l2_hist = []
    trade_hist = []
    orderbook = []
    start_time = None
    restart = False
    heartbeat_counter = 0
    seq_num = 0
    current_time = calendar.timegm(time.gmtime())
    save_time = current_time + saving_interval
    ws_client.open()
    ws_client.subscribe(product_id, ["heartbeats", "level2", "market_trades"])

    while calendar.timegm(time.gmtime()) < save_time:
        ws_client.sleep_with_exception_check(sleep=1)
        if restart:
            print("Client is forced to stop. Saving data...")
            break
    else:
        print("Reach saving_interval. Saving data...")

    save_all_data(l2_hist, trade_hist, id, start_time)
    print("Closing client...")
    ws_client.unsubscribe(product_id, ["heartbeats", "level2", "market_trades"])
    ws_client.close()
    # save recorded
    print("Restarting client...")
    time.sleep(3)