import matplotlib.pyplot as plt
import matplotlib.animation as ani
from os import walk, makedirs
import json
import copy

def animation_local(data, sorted_list, start_time, end_time, time_step, min_price, max_price, max_depth, id, bar_width, xunit, yunit):
    current_time = start_time
    if end_time < start_time:
        print("WDYM end_time < start_time???")

    frame_data = [{"bid": dict(), "offer": dict()}]
    index = 0
    while current_time < end_time:
        while index < len(sorted_list) and float(sorted_list[index][4:]) < current_time:
            # clear history if snapshot comming
            if data[sorted_list[index]]["type"] == "snapshot":
                frame_data[-1] = {"bid": dict(), "offer": dict()}
            # bid
            for price in data[sorted_list[index]]["data"]["bid"]:
                if data[sorted_list[index]]["data"]["bid"][price] == "0" and float(price) in frame_data[-1]["bid"]:
                    frame_data[-1]["bid"].pop(float(price))
                else:
                    frame_data[-1]["bid"][float(price)] = float(data[sorted_list[index]]["data"]["bid"][price])
            # offer
            for price in data[sorted_list[index]]["data"]["offer"]:
                if data[sorted_list[index]]["data"]["offer"][price] == "0" and float(price) in frame_data[-1]["offer"]:
                    frame_data[-1]["offer"].pop(float(price))
                else:
                    frame_data[-1]["offer"][float(price)] = float(data[sorted_list[index]]["data"]["offer"][price])
            # next index
            index += 1
        frame_data.append(copy.deepcopy(frame_data[-1]))
        current_time += time_step
    frame_data = frame_data[:-1]

    # print(frame_data[0])
    # print(frame_data[-1])

    # defind frame update function
    def draw(data):
        ax.clear()

        ax.set_xlim((min_price, max_price))
        ax.set_ylim((0, max_depth))
        ax.set_title(id)
        ax.set_xlabel(f"Price ({xunit})")
        ax.set_ylabel(f"Depth ({yunit})")

        bid = data["bid"]
        offer = data["offer"]

        bid_price = []
        bid_volume = []
        offer_price = []
        offer_volume = []

        for b in bid:
            bid_price.append(float(b))
            bid_volume.append(float(bid[b]))
        for o in offer:
            offer_price.append(float(o))
            offer_volume.append(float(offer[o]))

        ax.bar(bid_price, bid_volume, bar_width, color="g")
        ax.bar(offer_price, offer_volume, bar_width, color="r")

    # generate animation
    fig, ax = plt.subplots()
    animate = ani.FuncAnimation(fig, draw, frame_data, interval=time_step*1000)
    animate.save(f"fig/{id}.mp4")

def sort_data(raw):
    listdata = list(raw)
    listdata.sort(key=strUnix_to_float)
    return listdata

def trim_data(data, sorted_list):
    # Start from the first snapshot
    for i, t in enumerate(sorted_list):
        if data[t]["type"] == "snapshot":
            sorted_list = sorted_list[i:]
            break

    init_snap = copy.deepcopy(data[sorted_list[0]]["data"])
    list_bid = list(init_snap["bid"])
    list_offer = list(init_snap["offer"])
    list_bid.sort(key=to_float)
    list_offer.sort(key=to_float)
    max_bid = list_bid[-1]
    min_offer = list_offer[0]
    init_mid = (float(max_bid) + float(min_offer)) * 0.5

    # Set some lower bound and upper bound
    lower_lim_ratio = 0.3
    upper_lim_ratio = 0.3

    min_price = init_mid * (1 - lower_lim_ratio)
    max_price = init_mid * (1 + upper_lim_ratio)
    
    max_depth = 0
    ret = copy.deepcopy(data)
    for t in sorted_list:
        for price in data[t]["data"]["bid"]:
            fprice = float(price)
            if fprice < min_price:
                ret[t]["data"]["bid"].pop(price)
            else:
                max_depth = max(max_depth, float(data[t]["data"]["bid"][price]))
        for price in data[t]["data"]["offer"]:
            fprice = float(price)
            if max_price < fprice:
                ret[t]["data"]["offer"].pop(price)
            else:
                max_depth = max(max_depth, float(data[t]["data"]["offer"][price]))

    return min_price, max_price, max_depth, ret

def strUnix_to_float(strUnix):
    return float(strUnix[4:])

def to_float(str):
    return float(str)


with open("fig/plot_param.json", "r") as file:
    plot_param = json.load(file)

id = "ETP-20DEC30-CDE"
path = "update-20260318.075722-20260318.075822.json"

with open("data/v2/" + path, "r") as file:
    data = json.load(file)

data = data[id]
sorted = sort_data(data)
min_price, max_price, max_depth, trimed = trim_data(data, sorted)

animation_local(trimed, sorted, 820641.913696, 820702.630042, 0.01, min_price, max_price, max_depth, id, plot_param[id]["width"], plot_param[id]["xunit"], plot_param[id]["yunit"])