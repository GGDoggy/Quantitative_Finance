# Quantitative Finance Project

Run `websocket.py` with `/server` being root to collect data. It works 24/7 (I wish.)

You can change websocket setting in `config.json`.

`plot.py` plots all data in `/data` and saves them into `/fig`.

The timestamps of the files in `/data` are in UTC, as well as those generated in `/server`.

## Data structure

### v1
```
{
    "PRODUCT_ID": {
        "bid": {PRICE: AMOUNT, ...},
        "offer": {PRICE: AMOUNT, ...}
    }, ...
}
```
`v1` data is just snapshot every 10 second.


### v2
```
{
    "PRODUCT_ID": {
        TIME: {
            "type": TYPE,
            "data": {
                "bid": {PRICE: AMOUNT, ...},
                "offer": {PRICE: AMOUNT, ...}
            }
        }, ...
    }, ...
}
```
`TYPE` can be either `"snapshot"` or `"update"`.