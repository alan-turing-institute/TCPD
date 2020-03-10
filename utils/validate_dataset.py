#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Validate the dataset schema of a given file.

Note that this script requires the ``jsonschema`` package.

Author: G.J.J. van den Burg
License: This file is part of TCPD. See the LICENSE file.
Copyright: 2019, The Alan Turing Institute

"""

import argparse
import json
import jsonschema
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--schema-file",
        help="Schema file to use",
        default="./schema.json",
    )
    parser.add_argument("-d", "--dataset-dir", help="Dataset directory")
    parser.add_argument(
        "datafile", help="JSON file with a TCPD time series", nargs="?"
    )
    parser.add_argument(
        "-v", "--verbose", help="Enable verbose mode", action="store_true"
    )
    return parser.parse_args()


def load_schema(schema_file):
    if not os.path.exists(schema_file):
        raise FileNotFoundError(schema_file)
    with open(schema_file, "rb") as fp:
        schema = json.load(fp)
    return schema


def find_datafiles(dataset_dir):
    data_files = {}

    datadirs = os.listdir(dataset_dir)
    for ddir in datadirs:
        pth = os.path.join(dataset_dir, ddir)
        files = os.listdir(pth)
        json_files = [f for f in files if f.endswith(".json")]
        for jf in json_files:
            jfpath = os.path.join(pth, jf)
            if jf in data_files:
                raise KeyError("Duplicate data file '%s'?" % jfpath)
            data_files[jf] = jfpath

    return data_files


def validate_dataset(filename, schema_file=None):
    """Validate a dataset file against the schema and other requirements
    """
    if not os.path.exists(filename):
        return "File not found."

    with open(filename, "rb") as fp:
        try:
            data = json.load(fp)
        except json.JSONDecodeError as err:
            return "JSON decoding error: %s" % err.msg

    try:
        schema = load_schema(schema_file)
    except FileNotFoundError:
        return "Schema file not found."

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as err:
        return "JSONSchema validation error: %s" % err.message

    if len(data["series"]) != data["n_dim"]:
        return "Number of dimensions and number of series don't match"

    if "time" in data.keys():
        if not "format" in data["time"] and "raw" in data["time"]:
            return "'raw' must be accompanied by format"
        if "format" in data["time"] and not "raw" in data["time"]:
            return "Format must be accompanied by 'raw'"
        if "index" in data["time"]:
            if not data["time"]["index"][0] == 0:
                return "Index should start at zero."
            if not len(data["time"]["index"]) == data["n_obs"]:
                return "Number of indices must match number of observations"
        if "raw" in data["time"]:
            if len(data["time"]["raw"]) != data["n_obs"]:
                return "Number of time points doesn't match number of observations"
            if None in data["time"]["raw"]:
                return "Null is not supported in time axis. Use 'NaN' instead."

    has_missing = False
    for var in data["series"]:
        if len(var["raw"]) != data["n_obs"]:
            return "Number of observations doesn't match for %s" % var["label"]
        if float("nan") in var["raw"]:
            return "NaN is not supported in series. Use null instead."
        has_missing = has_missing or any(map(lambda x: x is None, var["raw"]))

    # this doesn't exist yet, so let's not implement it until we need it.
    if data["n_dim"] > 1 and has_missing:
        return "Missing values are not yet supported for multidimensional data"

    return None


def main():
    args = parse_args()

    log = lambda *a, **kw: print(*a, **kw) if args.verbose else None

    if args.dataset_dir:
        datafiles = find_datafiles(args.dataset_dir)
        for dset in datafiles:
            log("Validating %s" % dset)
            result = validate_dataset(
                datafiles[dset], schema_file=args.schema_file
            )
            if not result is None:
                print(
                    "Dataset: %s. Error: %s" % (dset, result), file=sys.stderr
                )
                raise SystemExit(1)
    else:
        result = validate_dataset(args.datafile, schema_file=args.schema_file)
        if not result is None:
            print("Error: %s" % result, file=sys.stderr)
            raise SystemExit(1)
    log("Validation passed.")


if __name__ == "__main__":
    main()
