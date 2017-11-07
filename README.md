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

## Command Line synopsis:

There are four required parameters, the database name, a database
identifier, a regular expression search pattern, and an output filename

```
$ ./nucleotide_search.py --dbname <DBNAME> --dbid <DBID> --regex <REGEX_PATTERN> --ofname <OUTPUT_FILENAME>

