#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the homeruns dataset

See the README file for more information.

Author: G.J.J. van den Burg
License: This file is part of TCPD, see the top-level LICENSE file.
Copyright: 2019, The Alan Turing Institute

"""

import argparse
import clevercsv
import hashlib
import json
import os
import sys
import time

from functools import wraps
from urllib.request import urlretrieve
from urllib.error import URLError

# Original source of the batting csv file
CSV_URL = "https://web.archive.org/web/20191128150525if_/https://raw.githubusercontent.com/chadwickbureau/baseballdatabank/242285f8f5e8981327cf50c07355fb034833ce4a/core/Batting.csv"

MD5_CSV = "43d8f8135e76dcd8b77d0709e33d2221"
MD5_JSON = "987bbab63e2c72acba1c07325303720c"

NAME_CSV = "Batting.csv"
NAME_JSON = "homeruns.json"


class ValidationError(Exception):
    def __init__(self, filename):
        self.message = (
            "Validating the file '%s' failed. \n"
            "Please raise an issue on the GitHub page for this project \n"
            "if the error persists." % filename
        )


def check_md5sum(filename, checksum):
    with open(filename, "rb") as fp:
        data = fp.read()
    h = hashlib.md5(data).hexdigest()
    return h == checksum


def validate(checksum):
    """Decorator that validates the target file."""

    def validate_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            target = kwargs.get("target_path", None)
            if os.path.exists(target) and check_md5sum(target, checksum):
                return
            out = func(*args, **kwargs)
            if not os.path.exists(target):
                raise FileNotFoundError("Target file expected at: %s" % target)
            if not check_md5sum(target, checksum):
                raise ValidationError(target)
            return out

        return wrapper

    return validate_decorator


@validate(MD5_CSV)
def download_csv(target_path=None):
    count = 0
    while count < 5:
        count += 1
        try:
            urlretrieve(CSV_URL, target_path)
            return
        except URLError as err:
            print(
                "Error occurred (%r) when trying to download csv. Retrying in 5 seconds"
                % err,
                sys.stderr,
            )
            time.sleep(5)


def read_csv(csv_file):
    with open(csv_file, "r", newline="", encoding="ascii") as fp:
        reader = clevercsv.reader(
            fp, delimiter=",", quotechar="", escapechar=""
        )
        rows = list(reader)

    header = rows.pop(0)
    dicts = [dict(zip(header, row)) for row in rows]

    AL = [d for d in dicts if d["lgID"] == "AL"]
    years = sorted(set((d["yearID"] for d in AL)))
    by_year = {
        int(y): sum(int(d["HR"]) for d in [x for x in AL if x["yearID"] == y])
        for y in years
    }
    return by_year


@validate(MD5_JSON)
def write_json(csv_path, target_path=None):
    by_year = read_csv(csv_path)

    name = "homeruns"
    longname = "Homeruns"
    time_fmt = "%Y"

    time = sorted(by_year.keys())
    values = [by_year[t] for t in time]

    series = [
        {"label": "American League Home Runs", "type": "int", "raw": values},
    ]

    data = {
        "name": name,
        "longname": longname,
        "n_obs": len(time),
        "n_dim": len(series),
        "time": {
            "type": "string",
            "format": time_fmt,
            "index": list(range(0, len(time))),
            "raw": list(map(str, time)),
        },
        "series": series,
    }

    with open(target_path, "w") as fp:
        json.dump(data, fp, indent="\t")


def collect(output_dir="."):
    csv_path = os.path.join(output_dir, NAME_CSV)
    json_path = os.path.join(output_dir, NAME_JSON)

    download_csv(target_path=csv_path)
    write_json(csv_path, target_path=json_path)


def clean(output_dir="."):
    csv_path = os.path.join(output_dir, NAME_CSV)
    json_path = os.path.join(output_dir, NAME_JSON)

    if os.path.exists(csv_path):
        os.unlink(csv_path)
    if os.path.exists(json_path):
        os.unlink(json_path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output-dir", help="output directory to use", default="."
    )
    parser.add_argument(
        "action",
        choices=["collect", "clean"],
        help="Action to perform",
        default="collect",
        nargs="?",
    )
    return parser.parse_args()


def main(output_dir="."):
    args = parse_args()
    if args.action == "collect":
        collect(output_dir=args.output_dir)
    elif args.action == "clean":
        clean(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
