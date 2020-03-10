#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset conversion script

Author: Gertjan van den Burg

"""

import json
import argparse
import clevercsv


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

    rows.pop(0)

    # the time format is monthly, so we convert that here
    time = [r[2][:-3] for r in rows]
    time_fmt = "%Y-%m"

    # source is in thousands, so we correct that here
    values = [float(r[3]) * 1000 for r in rows]

    name = "us_population"
    longname = "US Population"
    series = [{"label": "Population", "type": "int", "raw": values}]

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
