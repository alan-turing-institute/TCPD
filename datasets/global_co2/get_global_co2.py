#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the global_co2 dataset

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

from functools import wraps
from urllib.request import urlretrieve


CSV_URL = "ftp://data.iac.ethz.ch/CMIP6/input4MIPs/UoM/GHGConc/CMIP/mon/atmos/UoM-CMIP-1-1-0/GHGConc/gr3-GMNHSH/v20160701/mole_fraction_of_carbon_dioxide_in_air_input4MIPs_GHGConcentrations_CMIP_UoM-CMIP-1-1-0_gr3-GMNHSH_000001-201412.csv"

MD5_CSV = "a3d42f5e339f4c652b8ae80e830b6941"
MD5_JSON = "7c8edd8887f51a6f841cc9d806ab4e56"

NAME_CSV = "mole_fraction_of_carbon_dioxide_in_air_input4MIPs_GHGConcentrations_CMIP_UoM-CMIP-1-1-0_gr3-GMNHSH_000001-201412.csv"
NAME_JSON = "global_co2.json"

SAMPLE = 48


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
def get_csv(target_path=None):
    urlretrieve(CSV_URL, target_path)


def reformat_time(datestr):
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
    dd, mmm, rest = datestr.split("-")
    yyyy = rest.split(" ")[0]
    m = MONTHS.get(mmm)
    return "%s-%02d-%s" % (yyyy, m, dd)


@validate(MD5_JSON)
def write_json(csv_path, target_path=None):
    with open(csv_path, "r", newline="", encoding="ascii") as fp:
        reader = clevercsv.reader(
            fp, delimiter=",", quotechar="", escapechar=""
        )
        rows = list(reader)

    header = rows.pop(0)
    rows = [r for i, r in enumerate(rows) if i % SAMPLE == 0]

    as_dicts = [{h: v for h, v in zip(header, row)} for row in rows]
    by_date = {
        reformat_time(d["datetime"]): float(d["data_mean_global"])
        for d in as_dicts
    }

    # trim off anything before 1600
    by_date = {k: v for k, v in by_date.items() if k.split("-")[0] >= "1600"}

    time = sorted(by_date.keys())
    values = [by_date[t] for t in time]

    name = "global_co2"
    longname = "Global CO2"
    time_fmt = "%Y-%m-%d"
    series = [{"label": "Mean", "type": "float", "raw": values}]

    data = {
        "name": name,
        "longname": longname,
        "n_obs": len(values),
        "n_dim": len(series),
        "time": {
            "type": "string",
            "format": time_fmt,
            "index": list(range(len(time))),
            "raw": time,
        },
        "series": series,
    }
    if time is None:
        del data["time"]

    with open(target_path, "w") as fp:
        json.dump(data, fp, indent="\t")


def collect(output_dir="."):
    csv_path = os.path.join(output_dir, NAME_CSV,)
    json_path = os.path.join(output_dir, NAME_JSON)

    get_csv(target_path=csv_path)
    write_json(csv_path, target_path=json_path)


def clean(output_dir="."):
    csv_path = os.path.join(output_dir, NAME_CSV,)
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
