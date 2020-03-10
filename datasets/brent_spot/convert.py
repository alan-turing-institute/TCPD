#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset conversion script

Author: G.J.J. van den Burg

"""

import argparse
import clevercsv
import json

SAMPLE = 10

def date_to_iso(datestr):
    mm, dd, yyyy = list(map(int, datestr.split("/")))
    return f"{yyyy}-{mm:02d}-{dd:02d}"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="File to convert")
    parser.add_argument("output_file", help="File to write to")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.input_file, "r", newline="", encoding="ascii") as fp:
        reader = clevercsv.reader(
            fp, delimiter=",", quotechar="", escapechar=""
        )
        rows = list(reader)

    rows = rows[5:]
    rows = list(reversed(rows))

    rows = [r for i, r in enumerate(rows) if i % SAMPLE == 0]

    idx2000 = next((i for i, x in enumerate(rows) if x[0].endswith("2000")))
    rows = rows[idx2000:]

    name = "brent_spot"
    longname = "Brent Spot Price"
    time = [date_to_iso(r[0]) for r in rows]
    time_fmt = "%Y-%m-%d"
    values = [float(r[1]) for r in rows]

    series = [{"label": "Dollars/Barrel", "type": "float", "raw": values}]

    data = {
        "name": name,
        "longname": longname,
        "n_obs": len(time),
        "n_dim": len(series),
        "time": {
            "type": "string",
            "format": time_fmt,
            "index": list(range(len(time))),
            "raw": time,
        },
        "series": series,
    }

    with open(args.output_file, "w") as fp:
        json.dump(data, fp, indent="\t")


if __name__ == "__main__":
    main()
