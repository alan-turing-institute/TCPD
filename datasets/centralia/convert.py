#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset conversion script

Author: Gertjan van den Burg

"""

import json
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--subsample",
        help="Number of observations to skip during subsampling",
        type=int,
    )
    parser.add_argument("input_file", help="File to convert")
    parser.add_argument("output_file", help="File to write to")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.input_file, "r") as fp:
        rows = [l.strip().split("\t") for l in fp]

    time = []
    values = []
    for year, pop in rows:
        time.append(year)
        values.append(int(pop))

    name = "centralia"
    longname = "Centralia Pennsylvania Population"
    time_fmt = "%Y"
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
