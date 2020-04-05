#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect the robocalls dataset

See the README file for more information.

Author: G.J.J. van den Burg
License: This file is part of TCPD, see the top-level LICENSE file.
Copyright: 2019, The Alan Turing Institute

"""


import argparse
import bs4
import hashlib
import json
import os
import requests
import sys
import time

from functools import wraps

URL = "https://web.archive.org/web/20191027130452/https://robocallindex.com/history/time"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 "
    "Safari/537.36"
}

MD5_JSON = "f67ec0ccb50f2a835912e5c51932c083"

MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


NAME_HTML = "robocalls.html"
NAME_JSON = "robocalls.json"


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


# We can't validate the HTML as the wayback machine inserts the retrieval time
# in the HTML, so the checksum is not constant.
def write_html(target_path=None):
    count = 0
    jar = {}
    tries = 10
    while count < tries:
        count += 1
        error = False
        try:
            res = requests.get(URL, headers=HEADERS, cookies=jar)
        except requests.exceptions.ConnectionError:
            error = True
        if error or not res.ok:
            print(
                "(%i/%i) Error getting URL %s. Retrying in 5 seconds."
                % (count, tries, URL),
                file=sys.stderr,
            )
            time.sleep(5)
            continue
    if error:
        raise ValueError("Couldn't retrieve URL %s" % URL)
    with open(target_path, "wb") as fp:
        fp.write(res.content)


@validate(MD5_JSON)
def write_json(html_path, target_path=None):
    with open(html_path, "rb") as fp:
        soup = bs4.BeautifulSoup(fp, "html.parser")

    items = []

    table = soup.find(id="robocallers-detail-table-1")
    for row in table.find_all(attrs={"class": "month-row"}):
        tds = row.find_all("td")
        month_year = tds[0].a.text
        amount = tds[1].text

        month, year = month_year.split(" ")
        value = int(amount.replace(",", ""))

        month_idx = MONTHS[month]

        items.append({"time": "%s-%02d" % (year, month_idx), "value": value})

    # During initial (manual) data collection it wasn't noticed that the first
    # observation is at April 2015, not May 2015. Technically, this means that
    # this series has a missing value at May 2015. However, because the
    # annotators have considered the series as a consecutive series without the
    # missing value, we do not add it in here. This way, the file that this
    # script creates corresponds to what the annotators and algorithms have
    # seen during the study.

    apr2015 = next((it for it in items if it["time"] == "2015-04"), None)
    apr2015["time"] = "2015-05"

    by_date = {it["time"]: it["value"] for it in items}

    # remove the observations that were not part of the original dataset
    del by_date["2019-09"]

    time = sorted(by_date.keys())
    values = [by_date[t] for t in time]

    series = [{"label": "V1", "type": "int", "raw": values}]

    data = {
        "name": "robocalls",
        "longname": "Robocalls",
        "n_obs": len(time),
        "n_dim": len(series),
        "time": {
            "type": "string",
            "format": "%Y-%m",
            "index": list(range(0, len(time))),
            "raw": time,
        },
        "series": series,
    }

    with open(target_path, "w") as fp:
        json.dump(data, fp, indent="\t")


def collect(output_dir="."):
    html_path = os.path.join(output_dir, NAME_HTML)
    json_path = os.path.join(output_dir, NAME_JSON)

    write_html(target_path=html_path)
    write_json(html_path, target_path=json_path)


def clean(output_dir="."):
    html_path = os.path.join(output_dir, NAME_HTML)
    json_path = os.path.join(output_dir, NAME_JSON)

    if os.path.exists(html_path):
        os.unlink(html_path)

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
