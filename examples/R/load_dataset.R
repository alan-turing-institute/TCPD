#' ---
#' title: Example code to load a TCPD time series
#' author: G.J.J. van den Burg
#' date: 2020-01-06
#' license: See the LICENSE file.
#' copyright: 2019, The Alan Turing Institute
#' ---

library(RJSONIO)

load.dataset <- function(filename)
{
    data <- fromJSON(filename)

    # reformat the data into a data frame with a time index and the data values
    tidx <- data$time$index

    cols <- c()

    mat <- NULL
    for (j in 1:data$n_dim) {
        s <- data$series[[j]]
        v <- NULL
        for (i in 1:data$n_obs) {
            val <- s$raw[[i]]
            if (is.null(val)) {
                v <- c(v, NA)
            } else {
                v <- c(v, val)
            }
        }
        cols <- c(cols, s$label)
        mat <- cbind(mat, v)
    }

    mat <- cbind(tidx, mat)
    colnames(mat) <- c('t', cols)

    df <- as.data.frame(mat)
    return(df)
}
