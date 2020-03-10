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

    with open(args.input_file, "r", newline="", encoding="UTF-8-SIG") as fp:
        reader = clevercsv.reader(
            fp, delimiter=",", quotechar='"', escapechar=""
        )
        rows = list(reader)
    rows = rows[4:]
    header = rows.pop(0)

    as_dicts = []
    for row in rows:
        as_dicts.append({h: v for h, v in zip(header, row)})

    croatia = next(
        (d for d in as_dicts if d["Country Name"] == "Croatia"), None
    )

    tuples = []
    for key in croatia:
        try:
            ikey = int(key)
        except ValueError:
            continue
        if not croatia[key]:
            continue
        tuples.append((ikey, int(croatia[key])))

    name = "gdp_croatia"
    longname = "GDP Croatia"
    time = [str(t[0]) for t in tuples]
    time_fmt = "%Y"
    series = [
        {
            "label": "GDP (constant LCU)",
            "type": "int",
            "raw": [t[1] for t in tuples],
        }
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
