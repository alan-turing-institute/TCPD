#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example code for loading a dataset to a TimeSeries object.

Note that this code requires Pandas to be available.

Author: Gertjan van den Burg
Copyright: The Alan Turing Institute, 2019
License: See LICENSE file.

"""

import json
import numpy as np
import pandas as pd


class TimeSeries:
    def __init__(
        self,
        t,
        y,
        name=None,
        longname=None,
        datestr=None,
        datefmt=None,
        columns=None,
    ):
        self.t = t
        self.y = y

        self.name = name
        self.longname = longname
        self.datestr = datestr
        self.datefmt = datefmt
        self.columns = columns

        # whether the series is stored as zero-based or one-based
        self.zero_based = True

    @property
    def n_obs(self):
        return len(self.t)

    @property
    def n_dim(self):
        return self.y.shape[1]

    @property
    def shape(self):
        return (self.n_obs, self.n_dim)

    @classmethod
    def from_json(cls, filename):
        with open(filename, "rb") as fp:
            data = json.load(fp)

        tidx = np.array(data["time"]["index"])
        tidx = np.squeeze(tidx)

        if "format" in data["time"]:
            datefmt = data["time"]["format"]
            datestr = np.array(data["time"]["raw"])
        else:
            datefmt = None
            datestr = None

        y = np.zeros((data["n_obs"], data["n_dim"]))
        columns = []

        for idx, series in enumerate(data["series"]):
            columns.append(series.get("label", "V%i" % (idx + 1)))
            thetype = np.int if series["type"] == "integer" else np.float64
            vec = np.array(series["raw"], dtype=thetype)
            y[:, idx] = vec

        ts = cls(
            tidx,
            y,
            name=data["name"],
            longname=data["longname"],
            datefmt=datefmt,
            datestr=datestr,
            columns=columns,
        )
        return ts

    @property
    def df(self):
        d = {"t": self.t}
        for i in range(len(self.columns)):
            col = self.columns[i]
            val = self.y[:, i]
            d[col] = val
        return pd.DataFrame(d)

    def make_one_based(self):
        """ Convert the time index to a one-based time index. """
        if self.zero_based:
            self.t = [t + 1 for t in self.t]
            self.zero_based = False

    def __repr__(self):
        return "TimeSeries(name=%s, n_obs=%s, n_dim=%s)" % (
            self.name,
            self.n_obs,
            self.n_dim,
        )

    def __str__(self):
        return repr(self)
