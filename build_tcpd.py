#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Collect and verify all time series that are not packaged in the repository.

Author: Gertjan van den Burg
License: See LICENSE file.
Copyright: 2019, The Alan Turing Institute

"""

import argparse
import platform
import os

DATASET_DIR = "./datasets"

TARGETS = [
    ("apple", "get_apple.py"),
    ("bee_waggle_6", "get_bee_waggle_6.py"),
    ("bitcoin", "get_bitcoin.py"),
    ("iceland_tourism", "get_iceland_tourism.py"),
    ("measles", "get_measles.py"),
    ("occupancy", "get_occupancy.py"),
    ("ratner_stock", "get_ratner_stock.py"),
    ("robocalls", "get_robocalls.py"),
    ("scanline_126007", "get_scanline_126007.py"),
    ("scanline_42049", "get_scanline_42049.py"),
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", help="Enable logging", action="store_true"
    )
    parser.add_argument(
        "-o", "--output-dir", help="Output directory to store all time series"
    )
    parser.add_argument(
        "action",
        help="Action to perform",
        choices=["collect", "clean"],
        default="collect",
        nargs="?",
    )
    return parser.parse_args()


def load_dataset_script(module_name, path):
    """Load the dataset collection script as a module

    This is not a *super* clean way to do this, but it maintains the modularity 
    of the dataset, where each dataset can be downloaded individually as well 
    as through this script.
    """
    version = platform.python_version_tuple()
    if version[0] == "2":
        import imp

        module = imp.load_source(module_name, path)
    elif version[0] == "3" and version[1] in ["3", "4"]:
        from importlib.machinery import SourceFileLoader

        module = SourceFileLoader(module_name, path).load_module()
    else:
        import importlib.util

        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def run_dataset_func(name, script, funcname):
    dir_path = os.path.join(DATASET_DIR, name)
    get_path = os.path.join(dir_path, script)
    module = load_dataset_script("tcpd.%s" % name, get_path)
    func = getattr(module, funcname)
    func(output_dir=dir_path)


def collect_dataset(name, script):
    return run_dataset_func(name, script, "collect")


def clean_dataset(name, script):
    return run_dataset_func(name, script, "clean")


def main():
    args = parse_args()

    log = lambda *a, **kw: print(*a, **kw) if args.verbose else None

    if args.action == "collect":
        func = collect_dataset
    elif args.action == "clean":
        func = clean_dataset
    else:
        raise ValueError("Unknown action: %s" % args.action)

    for name, script in TARGETS:
        log(
            "Running %s action for dataset: %s ... " % (args.action, name),
            end="",
            flush=True,
        )
        func(name, script)
        log("ok", flush=True)


if __name__ == "__main__":
    main()
