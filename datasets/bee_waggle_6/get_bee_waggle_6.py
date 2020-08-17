#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the bee_waggle_6 dataset.

See the README file for more information.

Author: G.J.J. van den Burg
License: This file is part of TCPD, see the top-level LICENSE file.
Copyright: 2019, The Alan Turing Institute

"""

import argparse
import hashlib
import json
import math
import os
import zipfile
import sys
import time

from functools import wraps
from urllib.request import urlretrieve
from urllib.error import URLError

ZIP_URL = "https://web.archive.org/web/20191114130815if_/https://www.cc.gatech.edu/%7Eborg/ijcv_psslds/psslds.zip"

MD5_ZIP = "039843dc15c72fd5450eeb11c6e5599c"
MD5_JSON = "4f03feafecb3be0b069b3cb0d6b17d4f"
# known alternative checksums for small rounding errors
MD5_JSON_X = [
    "71311783488ee5f1122545d24c15429b",
    "3632e004b540de5c3eb049fb5591d044",
]

NAME_ZIP = "psslds.zip"
NAME_JSON = "bee_waggle_6.json"


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


def validate(checksum, alt_checksums=None):
    """Decorator that validates the target file."""

    def validate_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            target = kwargs.get("target_path", None)
            if os.path.exists(target) and check_md5sum(target, checksum):
                return
            if (
                os.path.exists(target)
                and alt_checksums
                and any(check_md5sum(target, c) for c in alt_checksums)
            ):
                print(
                    "Note: Matched alternative checksum for %s. "
                    "This indicates that small differences exist compared to "
                    "the original version of this time series, likely due to "
                    "rounding differences. Usually this is nothing to "
                    "worry about." % target,
                    file=sys.stderr,
                )
                return
            out = func(*args, **kwargs)
            if not os.path.exists(target):
                raise FileNotFoundError("Target file expected at: %s" % target)
            if not (
                check_md5sum(target, checksum)
                or (
                    alt_checksums
                    and any(check_md5sum(target, c) for c in alt_checksums)
                )
            ):
                print(
                    "Warning: Generated dataset %s didn't match a "
                    "known checksum. This is likely due to "
                    "rounding differences caused by "
                    "different system architectures. Minor differences in "
                    "algorithm performance can occur for this dataset. "
                    % target,
                    file=sys.stderr,
                )
            return out

        return wrapper

    return validate_decorator


@validate(MD5_ZIP)
def download_zip(target_path=None):
    count = 0
    while count < 5:
        count += 1
        try:
            urlretrieve(ZIP_URL, target_path)
            return
        except URLError as err:
            print(
                "Error occurred (%r) when trying to download zip. Retrying in 5 seconds"
                % err,
                sys.stderr,
            )
            time.sleep(5)


@validate(MD5_JSON, MD5_JSON_X)
def write_json(zip_path, target_path=None):
    with zipfile.ZipFile(zip_path) as thezip:
        with thezip.open("psslds/zips/data/sequence6/btf/ximage.btf") as fp:
            ximage = [float(l.strip()) for l in fp]
        with thezip.open("psslds/zips/data/sequence6/btf/yimage.btf") as fp:
            yimage = [float(l.strip()) for l in fp]
        with thezip.open("psslds/zips/data/sequence6/btf/timage.btf") as fp:
            timage = [float(l.strip()) for l in fp]

    sintimage = [math.sin(t) for t in timage]
    costimage = [math.cos(t) for t in timage]

    name = "bee_waggle_6"
    longname = "Bee Waggle no. 6"

    series = [
        {"label": "x", "type": "float", "raw": ximage},
        {"label": "y", "type": "float", "raw": yimage},
        {"label": "sin(theta)", "type": "float", "raw": sintimage},
        {"label": "cos(theta)", "type": "float", "raw": costimage},
    ]

    data = {
        "name": name,
        "longname": longname,
        "n_obs": len(ximage),
        "n_dim": len(series),
        "time": {"index": list(range(len(ximage)))},
        "series": series,
    }

    with open(target_path, "w") as fp:
        json.dump(data, fp, indent="\t")


def collect(output_dir="."):
    zip_path = os.path.join(output_dir, NAME_ZIP)
    json_path = os.path.join(output_dir, NAME_JSON)

    download_zip(target_path=zip_path)
    write_json(zip_path, target_path=json_path)


def clean(output_dir="."):
    zip_path = os.path.join(output_dir, NAME_ZIP)
    json_path = os.path.join(output_dir, NAME_JSON)

    if os.path.exists(zip_path):
        os.unlink(zip_path)
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


def main():
    args = parse_args()
    if args.action == "collect":
        collect(output_dir=args.output_dir)
    elif args.action == "clean":
        clean(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
