#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Validate the datasets by checksum

Author: G.J.J. van den Burg
License: This file is part of TCPD, see the top-level LICENSE file.
Copyright: 2019, The Alan Turing Institute

"""

import argparse
import hashlib
import os
import json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--checksum-file", help="Checksum file (json)", required=True
    )
    parser.add_argument(
        "-d", "--dataset-dir", help="Dataset directory", required=True
    )
    parser.add_argument(
        "-v", "--verbose", help="Enable verbose mode", action="store_true"
    )
    return parser.parse_args()


def md5sum(filename):
    with open(filename, "rb") as fp:
        data = fp.read()
    return hashlib.md5(data).hexdigest()


def load_checksums(checksum_file):
    with open(checksum_file, "r") as fp:
        checksums = json.load(fp)
    assert checksums["kind"] == "md5"
    return checksums["checksums"]


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


def main():
    args = parse_args()

    log = lambda *a, **kw: print(*a, **kw) if args.verbose else None

    checksums = load_checksums(args.checksum_file)
    data_files = find_datafiles(args.dataset_dir)

    for fname in checksums:
        log("Checking %s" % fname)
        if not fname in data_files:
            raise FileNotFoundError("Missing data file: %s" % fname)
        md5 = md5sum(data_files[fname])
        if isinstance(checksums[fname], list):
            if not md5 in checksums[fname]:
                raise ValueError(
                    "Checksums don't match for file: %s" % (data_files[fname])
                    )
        else:
            if not md5 == checksums[fname]:
                raise ValueError(
                "Checksums don't match for file: %s" % (data_files[fname])
            )

    log("All ok.")


if __name__ == "__main__":
    main()
