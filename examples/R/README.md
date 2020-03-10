# Loading a TCPD dataset into R

The file ``load_dataset.R`` contains the function ``load.dataset`` that reads 
the JSON file into an R dataframe. The 
[RJSONIO](https://cran.r-project.org/web/packages/RJSONIO/index.html) package 
is required:

```R
> install.packages('RJSONIO')
```

Simply run:

```R
> source('./load_dataset.R')
> df <- load.dataset('../../datasets/ozone/ozone.json')
> df
    t Total Emissions
1   0          380000
2   1          400000
3   2          440000
4   3          480000
5   4          510000
6   5          540000
7   6          580000
8   7          630000
```

Notice that the time axis in TCPD is always 0-based. This needs to be taken 
into account when comparing detection results to the human annotations. (This 
is an unfortunate consequence of the differences between indexing in R and 
Python.)

Missing observations in time series are represented with a ``NA`` value.
