#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the ratner_stock dataset.

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
import yfinance
import sys
import time

from functools import wraps
from urllib.error import URLError

MD5_CSV = "db7406dc7d4eb480d73b4fe6c4bb00be"
MD5_JSON = "f7086ff916f35b88463bf8fd1857815e"

SAMPLE = 3

NAME_CSV = "SIG.csv"
NAME_JSON = "ratner_stock.json"


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
            sig = yfinance.download(
                "SIG",
                start="1988-07-14",
                end="1995-08-23",
                progress=False,
                rounding=False,
            )
            sig.round(6).to_csv(target_path, float_format="%.6f")
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
        reader = clevercsv.reader(
            fp, delimiter=",", quotechar="", escapechar=""
        )
        rows = list(reader)

    header = rows.pop(0)

    rows = [r for i, r in enumerate(rows) if i % SAMPLE == 0]

    # take the first 600 rows
    rows = rows[:600]

    name = "ratner_stock"
    longname = "Ratner Group Stock Price"
    time = [r[0] for r in rows]
    time_fmt = "%Y-%m-%d"

    values = [float(r[4]) for r in rows]

    series = [{"label": "Close Price", "type": "float", "raw": values}]

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
