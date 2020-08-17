#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the occupancy dataset.

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

SAMPLE = 16

TXT_URL = "https://web.archive.org/web/20191128145102if_/https://raw.githubusercontent.com/LuisM78/Occupancy-detection-data/master/datatraining.txt"

MD5_TXT = "e656cd731300cb444bd10fcd28071e37"
MD5_JSON = "bc6cd9adaf496fe30bf0e417d2c3b0c6"

NAME_TXT = "datatraining.txt"
NAME_JSON = "occupancy.json"


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


@validate(MD5_TXT)
def download_txt(target_path=None):
    count = 0
    while count < 5:
        count += 1
        try:
            urlretrieve(TXT_URL, target_path)
            return
        except URLError as err:
            print(
                "Error occurred (%r) when trying to download txt. Retrying in 5 seconds"
                % err,
                sys.stderr,
            )
            time.sleep(5)


@validate(MD5_JSON)
def write_json(txt_path, target_path=None):
    with open(txt_path, "r", newline="", encoding="ascii") as fp:
        reader = clevercsv.reader(
            fp, delimiter=",", quotechar='"', escapechar=""
        )
        rows = list(reader)

    header = rows.pop(0)
    header.insert(0, "id")
    as_dicts = [dict(zip(header, r)) for r in rows]

    var_include = ["Temperature", "Humidity", "Light", "CO2"]

    time = [x["date"] for x in as_dicts]
    time = [time[i] for i in range(0, len(time), SAMPLE)]

    data = {
        "name": "occupancy",
        "longname": "Occupancy",
        "n_obs": len(time),
        "n_dim": len(var_include),
        "time": {
            "type": "string",
            "format": "%Y-%m-%d %H:%M:%S",
            "index": list(range(len(time))),
            "raw": time,
        },
        "series": [],
    }
    for idx, var in enumerate(var_include, start=1):
        lbl = "V%i" % idx
        obs = [float(x[var]) for x in as_dicts]
        obs = [obs[i] for i in range(0, len(obs), SAMPLE)]
        data["series"].append({"label": lbl, "type": "float", "raw": obs})

    with open(target_path, "w") as fp:
        json.dump(data, fp, indent="\t")


def collect(output_dir="."):
    txt_path = os.path.join(output_dir, NAME_TXT)
    json_path = os.path.join(output_dir, NAME_JSON)

    download_txt(target_path=txt_path)
    write_json(txt_path, target_path=json_path)


def clean(output_dir="."):
    txt_path = os.path.join(output_dir, NAME_TXT)
    json_path = os.path.join(output_dir, NAME_JSON)

    if os.path.exists(txt_path):
        os.unlink(txt_path)
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
