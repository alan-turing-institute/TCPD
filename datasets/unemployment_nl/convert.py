#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

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
    with open(args.input_file, "r", newline="", encoding="UTF-8-SIG") as fp:
        reader = clevercsv.reader(
            fp, delimiter=";", quotechar='"', escapechar=""
        )
        rows = list(reader)

    # remove rows we don't need
    title = rows.pop(0)
    meta = rows.pop(0)
    meta = rows.pop(0)

    # filter out rows we want
    header = rows.pop(0)
    eligible_population = rows.pop(0)
    working_population = rows.pop(0)
    unemployed_population = rows.pop(0)

    years = header[3:]
    eligible = list(map(int, eligible_population[3:]))
    unemployed = list(map(int, unemployed_population[3:]))

    # compute the percentage unemployed
    by_year = {
        y: (u / e * 100) for y, e, u in zip(years, eligible, unemployed)
    }

    # remove value of 2001 before revision
    del by_year["2001 voor revisie"]
    # rename value of 2001 after revision as simply '2001'
    by_year["2001"] = by_year["2001 na revisie"]
    del by_year["2001 na revisie"]

    time = sorted(by_year.keys())
    values = [by_year[t] for t in time]
    series = [{"label": "V1", "type": "float", "raw": values}]

    data = {
        "name": "unemployment_nl",
        "longname": "Unemployment rate (NL)",
        "n_obs": len(time),
        "n_dim": len(series),
        "time": {
            "type": "string",
            "format": "%Y",
            "index": list(range(len(time))),
            "raw": time,
        },
        "series": series,
    }

    with open(args.output_file, "w") as fp:
        json.dump(data, fp, indent="\t")


if __name__ == "__main__":
    main()
