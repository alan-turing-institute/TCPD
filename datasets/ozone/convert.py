#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset conversion script

Author: G.J.J. van den Burg

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

    total = [r for r in rows if r[0] == "Total emissions"]
    time = [r[2] for r in total]
    values = [int(r[-1]) for r in total]

    name = "ozone"
    longname = "Ozone-Depleting Emissions"
    time_fmt = "%Y"

    series = [{"label": "Total Emissions", "type": "int", "raw": values}]

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
