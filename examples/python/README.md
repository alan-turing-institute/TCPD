# Loading a TCPD time series in Python

The ``load_dataset.py`` file contains example code to load a time series as a 
``TimeSeries`` object.

```python
>>> from load_dataset import TimeSeries
>>> ts = TimeSeries.from_json('../../datasets/ozone/ozone.json')
```

To export the time series as a [pandas 
DataFrame](https://pandas.pydata.org/pandas-docs/stable/getting_started/dsintro.html#dataframe), 
simply use:

```python
>>> ts.df
     t  Total Emissions
0    0         380000.0
1    1         400000.0
2    2         440000.0
3    3         480000.0
4    4         510000.0
5    5         540000.0
...
```

The ``TimeSeries`` instance ``ts`` has an integer time axis at ``ts.t`` and 
the observations at ``ts.y``. The time axis is zero-based by default. If you 
prefer to use a one-based indexing, simply run:

```python
>>> ts.make_one_based()
>>> ts.df
     t  Total Emissions
0    1         380000.0
1    2         400000.0
2    3         440000.0
3    4         480000.0
4    5         510000.0
5    6         540000.0
...
```

Many of the time series in TCPD have date or datetime labels for the time 
axis. This axis can be retrieved using:

```python
>>> ts.datestr
array(['1961', '1962', '1963', '1964', '1965', '1966', '1967', '1968',
        ...
       '2009', '2010', '2011', '2012', '2013', '2014'], dtype='<U4')
```

which uses the date format stored in ``ts.datefmt``.

```python
>>> ts.datefmt
'%Y'
```
