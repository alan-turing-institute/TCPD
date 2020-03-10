#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset conversion script

Author: G.J.J. van den Burg

"""

import json
import argparse

SAMPLE = 6


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="File to convert")
    parser.add_argument("output_file", help="File to write to")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.input_file, "r") as fp:
        rows = [l.strip() for l in fp]

    rows = [r for i, r in enumerate(rows) if i % SAMPLE == 0]

    values = list(map(float, rows))
    name = "well_log"
    longname = "Well Log"

    series = [{"label": "V1", "type": "float", "raw": values}]

    data = {
        "name": name,
        "longname": longname,
        "n_obs": len(values),
        "n_dim": len(series),
        "time": {"index": list(range(len(values)))},
        "series": series,
    }

    with open(args.output_file, "w") as fp:
        json.dump(data, fp, indent="\t")


if __name__ == "__main__":
    main()
