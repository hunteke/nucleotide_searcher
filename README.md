# Nucleotide Search

A project submitted as a proof-of-capability for employment at the
Simons Foundation.

Nucleotide Search (NS) is a command line Python3 script that:

 * fetches biological sequence data from the National Center for
    Biotechnology Institute (NCBI),
 * scans for a user-supplied regular expression (regex -- in human
   terms, a "pattern"),
 * returns the location of all patterns found in CSV format,
 * and display rudimentary statistics about the results.

## Command Line Interface:

```
$ ./nucleotide_search.py -h
usage: nucleotide_search.py [-h] [--baseurl BASEURL] [--dbname DBNAME]
                            [--dbid DBID] [--regex REGEX] --ofname OFNAME
                            [--save-nucleotide] [--localsource LOCALSOURCE]
                            [--debug]

Search for nucleotide sequences.

optional arguments:
  -h, --help            show this help message and exit
  --baseurl BASEURL     The base URL from which to fetch data. [http://eutils.
                        ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi]
  --dbname DBNAME       NCBI database name. [nucleotide]
  --dbid DBID           NCBI database identifier. [30271926]
  --regex REGEX         Regular expression search pattern. [AAAATAGCCCC]
  --ofname OFNAME       Output file name to write results (CSV format). Ex:
                        'results.csv'
  --save-nucleotide     Save network result to a local file for later use with
                        --localsource; useful for iteration as large file does
                        not have to be re-downloaded
  --localsource LOCALSOURCE
                        Use a local file instead of making a (slow) network
                        request
  --debug               Rather than the simplistic error messages, show
                        developer-useful information (i.e., tracebacks)
```

In short, the default values are chosen to be fast (against the small
SARS Corono virus nucleotide sequence, a search pattern that does not
exist), and the only required argument is `--ofname` to specify the
filename of where to place the CSV results.

An invocation that uses all of the problem flags might be:

`$ ./nucleotide_search.py --dbname nucleotide --dbid 224589800 --regex '(A|C|G|T)' --ofname out.csv`

For iteration, it will likely be considerably faster to cache the
downloaded nucleotide XML data.  First:

```
$ ./nucleotide_search.py --dbid 224589800 --ofname out.csv --regex '(A|C|G|T)' --save-nucleotide
File saved locally to: nucleotide-224589800-20171107.xml
T       65668756
A       65570891
C       47024412
G       47016562
```

Now, using `--localsource`, the refined search can immediately process
rather than waiting for a quarter of a gigabyte to redownload:

```
$ ./nucleotide_search.py --localsource ./nucleotide-224589800-20171107.xml --ofname out2.csv --regex '(AAAAA|CCCCC|GGGGG|TACGGCAT)'
AAAAA   786514
CCCCC   133642
GGGGG   133126
TACGGCAT        349

```

## Design choices

 * Given the choice of making this Python 2 and 3 compatible, I opted to
   create this strictly in Python 3.   The biggest reason is that Python
   2 is inside of 3 years until end-of-life (2020).  That said, if
   Python 2 compatability is required, there are only a couple of pain
   points to work through (mainly in the URL parsing)

 * Given how large genomic research data can get, I opted for a
   streaming approach.  Wherever possible, the script streams data and
   frees what is no longer needed.  For example, the

   * downloader works in a separate thread retrieving small chunks of
     the URL file, putting each consecutive piece into a queue.   At the
     same time, another thread writes those pieces to a temporary file.
     For at least the file download portion of the script, the whole
     file will never be in memory at the same time.

   * xml parsing stage clears each element from memory once processing
     is complete

 * I chose ElementTree over the more traditional expat library for
   parsing the XML.  My main reasoning is it is a much simpler API and
   had all the required functionality for this project

