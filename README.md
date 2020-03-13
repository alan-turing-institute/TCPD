# Turing Change Point Dataset

Welcome to the host repository of the Turing Change Point Dataset, a set of 
time series specifically collected for the evaluation of change point 
detection algorithms on real-world data. For the repository containing the 
code and annotations, see 
[TCPDBench](https://github.com/alan-turing-institute/TCPDBench).

**Useful links:**
- [Turing Change Point Dataset](https://github.com/alan-turing-institute/TCPD) 
  on GitHub.
- [Turing Change Point Benchmark](https://github.com/alan-turing-institute/TCPDBench)
- [An Evaluation of Change Point Detection Algorithms](URL_TO_PAPER), a paper 
  by [Gertjan van den Burg](https://gertjan.dev) and [Chris 
  Williams](https://homepages.inf.ed.ac.uk/ckiw/).

## Getting Started

Many of the time series in the dataset are included in this repository. 
However, due to licensing restrictions, some series can not be redistributed 
and need to be downloaded locally. We've added a Python script and a Makefile 
to make this process as easy as possible.

Note that work based on the dataset should cite [our paper](URL_TO_PAPER):

```bib
@article{vandenburg2020evaluation,
        title={An Evaluation of Change Point Detection Algorithms},
        author={{Van den Burg}, G. J. J. and Williams, C. K. I.},
        journal={arXiv preprint},
        year={2020}
}
```

To obtain the dataset, please run the following steps:

1. Clone the GitHub repository and change to the new directory:

   ```
   $ git clone https://github.com/alan-turing-institute/TCPD
   $ cd TCPD
   ```

2. Make sure you have Python (v3.2 or newer) installed, as well as 
   [virtualenv](https://virtualenv.pypa.io/en/latest/):
   ```
   $ pip install virtualenv
   ```

3. Next, use either of these steps:
   - To obtain the dataset using Make, simply run:

     ```
     $ make
     ```

     This command will download all remaining datasets and verify that they 
     match the expected checksums.

   - If you don't have Make, you can obtain the dataset by manually executing 
     the following commands:

     ```
     $ virtualenv ./venv
     $ source ./venv/bin/activate
     $ pip install -r requirements.txt
     $ python build_tcpd.py -v collect
     ```

     If you wish to verify the downloaded datasets you can run:

     ```
     $ python ./utils/check_checksums.py -v -c ./checksums.json -d ./datasets
     ```

4. It may be convenient to export all dataset files to a single directory. 
   This can be done using Make as follows:

   ```
   $ make export
   ```

All datasets are stored in individual directories inside the ``datasets`` 
directory and each has its own README file with additional metadata and 
sources. The data format used is [JSON](https://json.org/) and each file 
follows the [JSON Schema](https://json-schema.org/) provided in 
``schema.json``.

## Using the data

For your convenience, example code to load a dataset from the JSON format to a 
data frame is provided in the ``examples`` directory in the following 
languages:

- [Python](examples/python/)
- [R](examples/R/)

Implementations of various change point detection algorithms that use these 
datasets are available in 
[TCPDBench](https://github.com/alan-turing-institute/TCPDBench).

## License

The code in this repository is licensed under the MIT license. See the 
[LICENSE file](LICENSE) for more details. Individual data files are often 
distributed under different terms, see the relevant README files for more 
details. Work that uses this dataset should cite [our paper](URL_TO_PAPER).

## Notes

If you find any problems or have a suggestion for improvement of this 
repository, please let us know as it will help us make this resource better 
for everyone. You can open an issue on 
[GitHub](https://github.com/alan-turing-institute/TCPD) or send an email to 
``gvandenburg at turing dot ac dot uk``.
