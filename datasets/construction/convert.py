#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dataset conversion script

Author: G.J.J. van den Burg

"""

import argparse
import json
import xlrd

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


def format_date(datestr):
    """ expects: mmm-yyx with x an extraneous character or empty """
    mmm, yyx = datestr.split("-")
    midx = MONTHS[mmm]
    if len(yyx) == 3:
        yy = yyx[:2]
    elif len(yyx) == 2:
        yy = yyx
    else:
        raise ValueError

    # this will break in 71 years
    if yy.startswith("9"):
        yyyy = 1900 + int(yy)
    else:
        yyyy = 2000 + int(yy)
    return f"{yyyy}-{midx:02}"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="File to convert")
    parser.add_argument("output_file", help="File to write to")
    return parser.parse_args()


def main():
    args = parse_args()

    wb = xlrd.open_workbook(args.input_file)
    ws = wb.sheet_by_index(0)
    header = ws.row(3)
    assert header[0].value == "Date"

    by_month = {}
    ridx = 4
    while True:
        # stop if date cell is empty
        if ws.row(ridx)[0].ctype == xlrd.XL_CELL_EMPTY:
            break

        date_value = ws.row(ridx)[0].value
        construct_value = ws.row(ridx)[1].value

        date = format_date(date_value)
        construct = int(construct_value)

        by_month[date] = construct
        ridx += 1

    name = "construction"
    longname = "US Construction Spending"
    time = sorted(by_month.keys())
    time_fmt = "%Y-%m"
    values = [by_month[t] for t in time]

    series = [
        {
            "label": "Total Private Construction Spending",
            "type": "int",
            "raw": values,
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
