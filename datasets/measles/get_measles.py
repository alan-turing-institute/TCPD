#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the measles dataset

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

DAT_URL = "https://web.archive.org/web/20191128124615if_/https://ms.mcmaster.ca/~bolker/measdata/ewmeas.dat"

MD5_DAT = "143d1dacd791df963674468c8b005bf9"
MD5_JSON = "e42afd03be893fc7deb98514c94fa4c7"

NAME_DAT = "ewmeas.dat"
NAME_JSON = "measles.json"


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


@validate(MD5_DAT)
def download_zip(target_path=None):
    count = 0
    while count < 5:
        count += 1
        try:
            urlretrieve(DAT_URL, target_path)
            return
        except URLError as err:
            print(
                "Error occurred (%r) when trying to download zip. Retrying in 5 seconds"
                % err,
                sys.stderr,
            )
            time.sleep(5)



@validate(MD5_JSON)
def write_json(dat_path, target_path=None):
    with open(dat_path, "r", newline="", encoding="ascii") as fp:
        reader = clevercsv.reader(
            fp, delimiter=" ", quotechar="", escapechar=""
        )
        rows = list(reader)

    as_dicts = {t: int(x) for t, x in rows}

    time = sorted(as_dicts.keys())
    values = [as_dicts[t] for t in time]
    series = [{"label": "V1", "type": "int", "raw": values}]

    data = {
        "name": "measles",
        "longname": "Measles cases (England & Wales)",
        "n_obs": len(time),
        "n_dim": len(series),
        "time": {
            "type": "string",
            "format": "%Y-%F",
            "index": list(range(len(time))),
            "raw": time,
        },
        "series": series,
    }

    with open(target_path, "w") as fp:
        json.dump(data, fp, indent="\t")


def collect(output_dir="."):
    dat_path = os.path.join(output_dir, NAME_DAT)
    json_path = os.path.join(output_dir, NAME_JSON)

    download_zip(target_path=dat_path)
    write_json(dat_path, target_path=json_path)


def clean(output_dir="."):
    dat_path = os.path.join(output_dir, NAME_DAT)
    json_path = os.path.join(output_dir, NAME_JSON)

    if os.path.exists(dat_path):
        os.unlink(dat_path)
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
