#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset conversion script

Author: Gertjan van den Burg

"""

import argparse
import clevercsv
import json


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

    header = rows.pop(0)

    name = "run_log"
    longname = "Run Log"

    time = [r[0].rstrip("Z").replace("T", " ") for r in rows]
    time_fmt = "%Y-%m-%d %H:%M:%S"
    pace = [float(r[3]) for r in rows]
    distance = [float(r[4]) for r in rows]

    series = [
        {"label": "Pace", "type": "float", "raw": pace},
        {"label": "Distance", "type": "float", "raw": distance},
    ]

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
