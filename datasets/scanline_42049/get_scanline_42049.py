#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the scanline_42049 dataset.

See the README file for more information.

Author: Gertjan van den Burg
License: This file is part of TCPD, see the top-level LICENSE file.
Copyright: 2019, The Alan Turing Institute

"""

import argparse
import hashlib
import os
import numpy as np
import json
import sys
import time

from PIL import Image
from functools import wraps
from urllib.request import urlretrieve
from urllib.error import URLError

IMG_URL = "https://web.archive.org/web/20070611230044im_/http://www.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/segbench/BSDS300/html/images/plain/normal/gray/42049.jpg"

MD5_IMG = "75a3d395b4f3f506abb9edadacaa4d55"
MD5_JSON = "39921dfa959576bd0b3d6c95558f17f4"

NAME_IMG = "42049.jpg"
NAME_JSON = "scanline_42049.json"


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


@validate(MD5_IMG)
def download_img(target_path=None):
    count = 0
    while count < 5:
        count += 1
        try:
            urlretrieve(IMG_URL, target_path)
            return
        except URLError as err:
            print(
                "Error occurred (%r) when trying to download img. Retrying in 5 seconds"
                % err,
                sys.stderr,
            )
            time.sleep(5)


@validate(MD5_JSON)
def write_json(img_path, target_path=None):
    name = "scanline_42049"
    longname = "Scanline 42049"
    index = 170

    im = Image.open(img_path)
    arr = np.array(im)
    line = list(map(int, list(arr[index, :])))

    series = [{"label": "Line %s" % index, "type": "int", "raw": line}]

    data = {
        "name": name,
        "longname": longname,
        "n_obs": len(line),
        "n_dim": len(series),
        "time": {"index": list(range(len(line)))},
        "series": series,
    }

    with open(target_path, "w") as fp:
        json.dump(data, fp, indent="\t")


def collect(output_dir="."):
    img_path = os.path.join(output_dir, NAME_IMG)
    json_path = os.path.join(output_dir, NAME_JSON)

    download_img(target_path=img_path)
    write_json(img_path, target_path=json_path)


def clean(output_dir="."):
    img_path = os.path.join(output_dir, NAME_IMG)
    json_path = os.path.join(output_dir, NAME_JSON)

    if os.path.exists(img_path):
        os.unlink(img_path)
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
