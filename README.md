# Quantitative Finance Project

Run `websocket.py` with `/server` being root to collect data. It works 24/7 (I wish.)

You can change websocket setting in `config.json`.

`plot.py` plots all data in `/data` and saves them into `/fig`.

The timestamps of the files in `/data` are in UTC, as well as those generated in `/server`.

## Data Structure

### v1

Store different product of same time period in a `.json` file.

```json
{
    "PRODUCT_ID": {
        "bid": {PRICE: AMOUNT, ...},
        "offer": {PRICE: AMOUNT, ...}
    }, ...
}
```
`v1` data is just snapshot every 10 second.


### v2

Store different product of same time period in a `.json` file.

#### Level 2

```json
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

`PRICE` and `AMOUNT` are *string*.

#### Market Trades

```json
{
    "PRODUCT_ID": {
        TIME: {
            "BUY": {PRICE: AMOUNT, ...},
            "SELL": {PRICE: AMOUNT, ...}
        }, ...
    }, ...
}
```
`PRICE` is *string* and `AMOUNT` is *float*.

### v3

Every `.csv` file contains data of single product.

#### Level 2

A complete level 2 data contains two files:

`level2-PRODUCT_ID-init-yyyymmdd.hhmmss.csv` and `level2-PRODUCT_ID-updates-yyyymmdd.hhmmss.csv`

The time should be identical and is the time of the initial order book.

`init`: The initial order book.

| Price | Volume | Side |
| - | - | - |
| PRICE 1 | VOLUME 1 | SIDE 1 |
| ... | ... | ... |

`update`: All updates during the period.

| Time | Price | Volume | Side |
| - | - | - | - |
| TIME 1 | PRICE 1 | VOLUME 1 | SIDE 1 |
| ... | ... | ... | ... |

- `SIDE`: -1 for sell order / +1 for buy order  
- `TIME`: Seconds from midnight of the filename date

#### Market Trades

File name:

`trade-PRODUCT_ID-yyyymmdd.hhmmss.csv`

The time refers to the very first data.

| Time | Price | Volume | Side |
| - | - | - | - |
| TIME 1 | PRICE 1 | VOLUME 1 | SIDE 1 |
| ... | ... | ... | ... |

- `SIDE`: -1 for buy taker / +1 for sell taker  
- `TIME`: Seconds from midnight of the filename date