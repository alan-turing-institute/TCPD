#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Retrieve the bitcoin dataset.

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

CSV_URL = "https://web.archive.org/web/20191114131838if_/https://api.blockchain.info/charts/market-price?timespan=all&format=csv"

MD5_CSV = "9bd4f7b06d78347415f6aafe1d9eb680"
MD5_JSON = "f90ff14ed1fc0c3d47d4394d25cbce93"

NAME_CSV = "market-price.csv"
NAME_JSON = "bitcoin.json"


class ValidationError(Exception):
    def __init__(self, filename):
        message = (
            "Validating the file '%s' failed. \n"
            "Please raise an issue on the GitHub page for this project "
            "if the error persists." % filename
        )
        super().__init__(message)


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
def get_market_price(target_path=None):
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


@validate(MD5_JSON)
def write_json(csv_path, target_path=None):
    rows = clevercsv.read_table(csv_path)

    rows = rows[500:]
    last_idx = next(
        (i for i, r in enumerate(rows) if r[0] == "2019-06-19 00:00:00"), None
    )
    rows = rows[: (last_idx + 1)]

    name = "bitcoin"
    longname = "Bitcoin Price"
    values = [float(r[1]) for r in rows]
    time = [r[0].split(" ")[0] for r in rows]
    time_fmt = "%Y-%m-%d"
    series = [{"label": "USD/Bitcoin", "type": "float", "raw": values}]

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

    get_market_price(target_path=csv_path)
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
