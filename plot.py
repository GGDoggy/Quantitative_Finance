import matplotlib.pyplot as plt
import json
from os import walk, makedirs

def one_plot(path, id, param):
    with open(path + ".json", "r") as file:
        data = json.load(file)
        try:
            data = data[id]
        except KeyError:
            print(f"There's no {id} in {path}.")
            return

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

    bid_color = "g"
    offer_color = "r"
    wid = param["width"]

    plt.cla()
    plt.bar(bid_price, bid_volume, wid, color=bid_color)
    plt.bar(offer_price, offer_volume, wid, color=offer_color)
    plt.ylim(param["ylim"])
    plt.xlim(param["xlim"])
    plt.title(path[5:] + f" ({id})")
    plt.xlabel(f"Price ({(param["xunit"])})")
    plt.ylabel(f"Depth ({param["yunit"]})")

    makedirs("fig/" + id, exist_ok=True)
    plt.savefig("fig/" + id + "/" + path[5:] + ".png")


with open("fig/plot_param.json", "r") as file:
    plot_param = json.load(file)

for a, b, c in walk("data"):
    for cs in c:
        if cs[-5:] == ".json":
            path = a + "/" + cs
            path = path[:-5]
            for id in list(plot_param):
                one_plot(path, id, plot_param[id])

# path = "orderbook-20260316-115946"
# id = "ETP-20DEC30-CDE"

# one_plot(path, id, plot_param[id])