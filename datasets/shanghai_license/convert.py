#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset conversion script

Author: Gertjan van den Burg

"""

import json
import argparse
import clevercsv


def reformat_time(mmmyy):
    """ From MMM-YY to %Y-%m """
    MONTHS = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }
    mmm, yy = mmmyy.split("-")
    Y = int(yy) + 2000
    m = MONTHS.get(mmm)
    return "%i-%02i" % (Y, m)


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

    time = [reformat_time(r[0]) for r in rows]
    values = [int(r[-1]) for r in rows]

    # Manually split Jan-08 into two, see readme for details.
    jan08idx = time.index("2008-01")
    values[jan08idx] /= 2
    time.insert(jan08idx + 1, "2008-02")
    values.insert(jan08idx + 1, values[jan08idx])

    name = "shanghai_license"
    longname = "Shanghai License"
    time_fmt = "%Y-%m"
    series = [{"label": "No. of Applicants", "type": "int", "raw": values}]

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
