#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset conversion script

Author: G.J.J. van den Burg

"""

import json
import argparse
import clevercsv


def month2index(month):
    return {
        "Jan": "01",
        "Feb": "02",
        "Mar": "03",
        "Apr": "04",
        "May": "05",
        "Jun": "06",
        "Jul": "07",
        "Aug": "08",
        "Sep": "09",
        "Oct": "10",
        "Nov": "11",
        "Dec": "12",
    }[month]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="File to convert")
    parser.add_argument("output_file", help="File to write to")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.input_file, "r", newline="", encoding="ascii") as fp:
        reader = clevercsv.DictReader(
            fp, delimiter=",", quotechar="", escapechar=""
        )
        items = list(reader)

    for it in items:
        it["time"] = f"{it['Year']}-{month2index(it['Month'])}"
        it["value"] = int(it["Total Passengers"])

    lgas = [it for it in items if it["Airport Code"] == "LGA"]
    pairs = [(it["time"], it["value"]) for it in lgas]
    # with this date format string sort is date sort
    pairs.sort()

    name = "lga_passengers"
    longname = "LaGuardia Passengers"
    time_fmt = "%Y-%m"
    time = [p[0] for p in pairs]
    values = [p[1] for p in pairs]

    series = [{"label": "Number of Passengers", "type": "int", "raw": values}]

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
