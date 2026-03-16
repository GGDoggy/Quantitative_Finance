from coinbase.websocket import WSClient
import json
import time
import calendar


def save_order_book(order_book, record_time):
    savetime = time.strftime("%Y%m%d-%H%M%S", time.gmtime(record_time))
    print(savetime)
    with open(f"orderbook-{savetime}.json", "w") as file:
        json.dump(order_book, file)

def on_message(msg):
    global order_book
    global record_interval
    global record_time
    msg = json.loads(msg)

    if msg["channel"] == "heartbeats":
        # print(msg)
        tstamp = msg["timestamp"][:-4]
        tstamp = time.strptime(tstamp, "%Y-%m-%dT%H:%M:%S.%f")
        tstamp = calendar.timegm(tstamp)
        # print(time.strftime("%Y-%m-%d-%H-%M-%S", tstamp))
        # print(tstamp, record_time)
        if tstamp >= record_time:
            save_order_book(order_book, tstamp)
            record_time = tstamp + record_interval
    
    if msg["channel"] == "l2_data":
        for event in msg["events"]:
            if event["type"] == "snapshot":

                # print(event["type"], event["product_id"])
                order_book[event["product_id"]] = {"bid": dict(), "offer": dict()}
                for update in event["updates"]:
                    order_book[event["product_id"]][update["side"]][update["price_level"]] = update["new_quantity"]

            elif event["type"] == "update":

                for update in event["updates"]:
                    if float(update["new_quantity"]) == 0:
                        # print(update)
                        try:
                            order_book[event["product_id"]][update["side"]].pop(update["price_level"])
                        except KeyError:
                            # print("Price " + update["price_level"] + " does not exist.")
                            pass
                        # print("pop success")
                    else:
                        order_book[event["product_id"]][update["side"]][update["price_level"]] = update["new_quantity"]


with open("config.json", "r") as file:
    config = json.load(file)

record_interval = config["record_interval"]
product_id = config["product_id"]

order_book = dict()
record_time = calendar.timegm(time.gmtime()) + record_interval
ws_client = WSClient(on_message=on_message, verbose=True)

ws_client.open()
ws_client.subscribe(product_id, ["heartbeats", "level2"])
ws_client.run_forever_with_exception_check()