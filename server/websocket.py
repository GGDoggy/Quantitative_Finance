from coinbase.websocket import WSClient
import json
import time
import calendar


def received_time_to_float(str):
    sec = str[:19]
    sec = time.strptime(sec, "%Y-%m-%dT%H:%M:%S")
    sec = calendar.timegm(sec)
    return sec, float("0" + str[19:-1])

def save_update(update_hist, start_time, end_time):
    if update_hist == dict():
        return
    start_time = time.strftime("%Y%m%d.%H%M%S", time.gmtime(start_time))
    end_time = time.strftime("%Y%m%d.%H%M%S", time.gmtime(end_time))
    print("Saved update at ", end_time)
    with open(f"update-{start_time}-{end_time}.json", "w") as file:
        json.dump(update_hist, file)

def on_message(msg):
    global update_hist
    global saving_interval
    global saving_time
    global last_saving_time
    msg = json.loads(msg)

    if msg["channel"] == "heartbeats":
        tstamp = received_time_to_float(msg["timestamp"])[0]

        # Save data at saving_time or later
        if tstamp >= saving_time:
            save_update(update_hist, last_saving_time, tstamp)
            update_hist = dict()
            saving_time = tstamp + saving_interval
            last_saving_time = tstamp
    
    if msg["channel"] == "l2_data":
        for event in msg["events"]:
            # for new update_hist, add product_id
            if not event["product_id"] in update_hist:
                update_hist[event["product_id"]] = dict()

            for update in event["updates"]:
                # Unix time
                t = received_time_to_float(update["event_time"])
                t = str(t[0]) + str(t[1])[1:]
                # If it is a new time stamp
                if not t in update_hist[event["product_id"]]:
                    update_hist[event["product_id"]][t] = {"type": event["type"], "data": {"bid": dict(), "offer": dict()}}

                if event["type"] != update_hist[event["product_id"]][t]["type"]:
                    print("Cannot update data: Two types appear in a same time.")
                else:
                    update_hist[event["product_id"]][t]["data"][update["side"]][update["price_level"]] = update["new_quantity"]



with open("config.json", "r") as file:
    config = json.load(file)

saving_interval = config["saving_interval"]
product_id = config["product_id"]

update_hist = dict()
current_time = calendar.timegm(time.gmtime())
saving_time = current_time + saving_interval
last_saving_time = current_time
ws_client = WSClient(on_message=on_message, verbose=True)

ws_client.open()
ws_client.subscribe(product_id, ["heartbeats", "level2"])
ws_client.run_forever_with_exception_check()