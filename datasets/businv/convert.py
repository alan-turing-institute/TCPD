#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset conversion script

Author: G.J.J. van den Burg

"""

import argparse
import json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="File to convert")
    parser.add_argument("output_file", help="File to write to")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.input_file, "r") as fp:
        lines = [l.strip() for l in fp]

    # header data should be first three lines
    # we use some asserts to ensure things are what we expect them to be
    header = lines[:3]
    assert header[-1] == "Total Business"

    lines = lines[4:]
    assert lines[0].startswith("1992")

    by_month = {}
    for line in lines:
        # stop on first empty line
        if not line.strip():
            break
        parts = [x for x in line.split(" ") if x.strip()]
        assert len(parts) == 13  # year + 12 months
        year = parts.pop(0)
        for midx, v in enumerate(parts, start=1):
            if v == ".":
                break
            by_month[f"{year}-{midx:02}"] = int(v)

    name = "businv"
    longname = "Business Inventory"
    time = sorted(by_month.keys())
    time_fmt = "%Y-%m"
    values = [by_month[t] for t in time]

    series = [{"label": "Business Inventory", "type": "int", "raw": values}]

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
