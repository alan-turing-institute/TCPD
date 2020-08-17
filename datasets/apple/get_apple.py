#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the apple dataset.

This script uses the yfinance package to download the data from Yahoo Finance 
and subsequently reformats it to a JSON file that adheres to our dataset 
schema. See the README file for more information on the dataset.

Author: G.J.J. van den Burg
License: This file is part of TCPD, see the top-level LICENSE file.
Copyright: 2019, The Alan Turing Institute

"""


import argparse
import clevercsv
import hashlib
import json
import os
import yfinance
import sys
import time

from functools import wraps
from urllib.error import URLError

MD5_CSV = "9021c03bb9fea3f16ecc812d77926168"
MD5_JSON = "22edb48471bd3711f7a6e15de6413643"

SAMPLE = 3

NAME_CSV = "AAPL.csv"
NAME_JSON = "apple.json"


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


def write_csv(target_path=None):
    count = 0
    while count < 5:
        count += 1
        try:
            aapl = yfinance.download(
                "AAPL",
                start="1996-12-12",
                end="2004-05-15",
                progress=False,
                rounding=False,
                threads=False,
            )
            aapl.round(6).to_csv(target_path, float_format="%.6f")
            return
        except URLError as err:
            print(
                "Error occurred (%r) when trying to download csv. Retrying in 5 seconds"
                % err,
                sys.stderr,
            )
            time.sleep(5)


@validate(MD5_JSON)
def write_json(csv_path, target_path=None):
    with open(csv_path, "r", newline="", encoding="ascii") as fp:
        reader = clevercsv.DictReader(
            fp, delimiter=",", quotechar="", escapechar=""
        )
        rows = list(reader)

    # offset to ensure drop is visible in sampled series
    rows = rows[1:]

    if SAMPLE:
        rows = [r for i, r in enumerate(rows) if i % SAMPLE == 0]

    time = [r["Date"] for r in rows]
    close = [float(r["Close"]) for r in rows]
    volume = [int(r["Volume"]) for r in rows]

    name = "apple"
    longname = "Apple Stock"
    time_fmt = "%Y-%m-%d"

    series = [
        {"label": "Close", "type": "float", "raw": close},
        {"label": "Volume", "type": "int", "raw": volume},
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
            "raw": time,
        },
        "series": series,
    }

    with open(target_path, "w") as fp:
        json.dump(data, fp, indent="\t")


def collect(output_dir="."):
    csv_path = os.path.join(output_dir, NAME_CSV)
    json_path = os.path.join(output_dir, NAME_JSON)

    write_csv(target_path=csv_path)
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
