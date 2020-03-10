#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Author: Gertjan van den Burg

"""

import clevercsv
import json
import sys


def format_month(ymm):
    year, month = ymm.split("M")
    return f"{year}-{month}"


def main(input_filename, output_filename):
    with open(input_filename, "r", newline="", encoding="ascii") as fp:
        reader = clevercsv.DictReader(
            fp, delimiter=",", quotechar='"', escapechar=""
        )
        rows = list(reader)

    by_currency = {}
    for row in rows:
        cur = row["CURRENCY"]
        if not cur in by_currency:
            by_currency[cur] = []
        by_currency[cur].append(row)

    by_month = {}
    for cur in by_currency:
        for item in by_currency[cur]:
            if item["Value"] == ":":
                continue
            month = item["TIME"]
            if not month in by_month:
                by_month[month] = {}
            by_month[month][cur] = item

    to_delete = []
    for month in by_month:
        if not len(by_month[month]) == 2:
            to_delete.append(month)
    for month in to_delete:
        del by_month[month]

    ratio = {}
    for month in sorted(by_month.keys()):
        usd = by_month[month]["US dollar"]
        isk = by_month[month]["Icelandic krona"]
        ratio[format_month(month)] = float(usd["Value"]) / float(isk["Value"])

    tuples = [(m, ratio[m]) for m in ratio]

    name = "usd_isk"
    longname = "USD-ISK exhange rate"

    data = {
        "name": name,
        "longname": longname,
        "n_obs": len(tuples),
        "n_dim": 1,
        "time": {
            "format": "%Y-%m",
            "index": list(range(len(tuples))),
            "raw": [t[0] for t in tuples],
        },
        "series": [
            {
                "label": "Exchange rate",
                "type": "float",
                "raw": [t[1] for t in tuples],
            }
        ],
    }

    with open(output_filename, "w") as fp:
        json.dump(data, fp, indent="\t")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
