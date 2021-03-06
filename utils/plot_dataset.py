#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility script to plot datasets and annotations.

Author: G.J.J. van den Burg
Copyright (c) 2020 - The Alan Turing Institute
License: See the LICENSE file.

"""

import argparse
import datetime
import json
import matplotlib.pyplot as plt
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r",
        "--result-file",
        help="JSON file with results from a change point detection method",
    )
    parser.add_argument(
        "-o", "--output-file", help="Output file to save the figure to"
    )
    parser.add_argument("input", help="Input dataset file (in JSON format)")
    return parser.parse_args()


def frac_to_dt(number):
    number = float(number)
    year = int(float(number))
    remainder = number - year
    begin = datetime.datetime(year, 1, 1)
    end = datetime.datetime(year + 1, 1, 1)
    seconds = remainder * (end - begin).total_seconds()
    return begin + datetime.timedelta(seconds=seconds)


def load_data(filename):
    with open(filename, "rb") as fid:
        data = json.load(fid)
    title = data["name"]
    y = data["series"][0]["raw"]
    if "time" in data and "format" in data["time"]:
        fmt = data["time"]["format"]
        if fmt == "%Y.%F":
            x = list(map(frac_to_dt, data["time"]["raw"]))
        else:
            try:
                x = pd.to_datetime(
                    data["time"]["raw"], format=data["time"]["format"]
                )
            except ValueError:
                x = list(range(1, len(y) + 1))
    else:
        x = list(range(1, len(y) + 1))
    as_dict = {"x": x}
    for idx, series in enumerate(data["series"]):
        as_dict["y" + str(idx)] = series["raw"]

    df = pd.DataFrame(as_dict)
    return df, title


def load_result(filename):
    with open(filename, "r") as fp:
        data = json.load(fp)
    if not data["status"] == "SUCCESS":
        print("Detection wasn't successful.")
        return None
    return data["result"]["cplocations"]


def main():
    args = parse_args()
    df, title = load_data(args.input)

    results = None
    if args.result_file:
        results = load_result(args.result_file)

    has_date = False
    try:
        _ = df["x"].dt
        has_date = True
    except AttributeError:
        pass

    fig, axes = plt.subplots(df.shape[1] - 1, 1, squeeze=False)
    for idx, col in enumerate(df.columns[1:]):
        if has_date:
            axes[idx, 0].plot_date(df["x"], df[col], ".", color="tab:blue")
            axes[idx, 0].plot_date(df["x"], df[col], "-", color="tab:blue")
            if results:
                for loc in results:
                    if loc == 0:
                        continue
                    if loc == df.shape[0]:
                        continue
                    pos = df["x"].values[loc]
                    axes[idx, 0].axvline(x=pos, linestyle="--", color="red")
        else:
            axes[idx, 0].scatter(df["x"], df[col], color="tab:blue")
            axes[idx, 0].plot(df["x"], df[col], color="tab:blue")
            if results:
                for loc in results:
                    if loc == 0:
                        continue
                    if loc == df.shape[0]:
                        continue
                    pos = df["x"].values[loc]
                    axes[idx, 0].axvline(x=pos, linestyle="--", color="red")
    fig.suptitle(title)
    if args.output_file:
        plt.savefig(args.output_file, transparent=True)
    else:
        plt.show()


if __name__ == "__main__":
    main()
