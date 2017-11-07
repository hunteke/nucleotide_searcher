#!/usr/bin/env python3

import argparse
import gzip
import urllib.request

def msg_and_die( msg ):
	if args.debug:
		raise

	raise SystemExit( "{}\n\nUse --debug for developer friendly information\n".format(msg) )


def read_url( url ):
	req = urllib.request.Request( url )
	req.add_header('Accept-Encoding', 'gzip')  # Let server send compressed data
	req.add_header('Cache-Control', 'max-age=0')   # Attempt to ensure a 'fresh' copy

	try:
		res = urllib.request.urlopen( req )
	except urllib.request.HTTPError as e:
		msg_and_die( 'Attempted url: {}\nHTTP error reading data from server.\nLibrary error message: {}'.format(url, e) )
	except urllib.error.URLError as e:
		msg_and_die( 'Attempted url: {}\nUnable to make connection; check your internet connection?\nLibrary error message: {}'.format(url, e) )

	data = res.read()
	encoding = res.info().get('Content-Encoding') or ''
	if 'gzip' in encoding.lower():
		data = gzip.decompress( data )

	return data


parser = argparse.ArgumentParser(
	description='Search for nucleotide sequences.'
)
parser.add_argument('--debug', action='store_true', help="Rather than the simplistic error messages, show developer-useful information (i.e., tracebacks).")

if '__main__' == __name__:
	args = parser.parse_args()

	url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nucleotide&id=30271926&rettype=fasta&retmode=xml'
	print( read_url( url ))
