"""Download bar data from Yahoo Finance's public chart API into data/*.csv.

Usage: python3 fetch.py

Each file holds one series: time (UTC, ISO 8601), open, high, low, close, volume.
Yahoo limits intraday history: 30-minute bars reach back about 60 days and
1-hour bars about 730 days. Daily bars go back to each symbol's start.
The last bar of every download is dropped because it may still be forming.
"""

import csv
import datetime as dt
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

SYMBOLS = ["ES=F", "SPY"]
INTERVALS = {
    "30m": "interval=30m&range=60d",
    "1h": "interval=60m&range=730d",
    "1d": "interval=1d&period1=0&period2={now}",
}


def fetch(symbol, query):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/{}?{}".format(
        urllib.request.quote(symbol), query.format(now=int(time.time()))
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
    result = body["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    rows = []
    for i, ts in enumerate(result["timestamp"]):
        bar = [quote[f][i] for f in ("open", "high", "low", "close", "volume")]
        if bar[3] is None:
            continue
        stamp = dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()
        rows.append([stamp] + bar)
    return rows[:-1]


def main():
    os.makedirs(DATA, exist_ok=True)
    for symbol in SYMBOLS:
        for name, query in INTERVALS.items():
            rows = fetch(symbol, query)
            path = os.path.join(DATA, "{}_{}.csv".format(symbol.replace("=", ""), name))
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["time", "open", "high", "low", "close", "volume"])
                w.writerows(rows)
            print("{}: {} bars, {} to {}".format(path, len(rows), rows[0][0], rows[-1][0]))


if __name__ == "__main__":
    main()
