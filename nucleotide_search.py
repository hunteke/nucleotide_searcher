#!/usr/bin/env python3

import gzip
import os
import re
import sys
import tempfile
import time
import urllib.request

def msg_and_die( msg ):
	if args.debug:
		raise

	raise SystemExit( "{}\n\nUse --debug for developer friendly information\n".format(msg) )


def read_url( url ):
	req = urllib.request.Request( url )
	req.add_header('Accept-Encoding', 'gzip')  # Let server send compressed data
	req.add_header('Cache-Control', 'max-age=0')   # Attempt to ensure a 'fresh' copy
	req.add_header('User-Agent', 'Python3-based research script, urllib')

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


def create_efetch_url( args ):
	# Ostensibly performed more simply and quickly with a couple of regexes:
	# not knowing what the hiring committee wants to see, nor the scope of what
	# this "project" might entail beyond the "What can this candidate do?"
	# question, I've opted for the more robust library approach.
	url_parts = list( urllib.parse.urlparse( args.baseurl ))
	query = urllib.parse.parse_qs( url_parts[ 4 ])
	query.update({
		'db': args.dbname,
		'id': args.dbid,
		'rettype': 'fasta',
		'retmode': 'xml'
	})
	url_parts[4] = urllib.parse.urlencode( query )
	return urllib.parse.urlunparse( url_parts )


if '__main__' == __name__:
	import argparse

	def dbname_format( s, pat=re.compile(r'^[A-z]{1,16}$') ):
		"""
		From eyeballing all of the database names, a valid name must be an ASCII
		alpha letter (A through Z), capitalized or not, and be no more than 16
		characters lone.
		"""
		if not pat.match( s ):
			raise argparse.ArgumentTypeError('Invalid database name.  (Single word, all letters, no more than 16 characters.)')
		return s


	def dbid_format( s, pat=re.compile(r'^\d+(?:,\d+)*') ):
		"""
		From the documentation, the strong inference is that database IDs are
		numerical; more than one may be specified with a comma.
		"""
		if not pat.match( s ):
			raise argparse.ArgumentTypeError('Invalid database ID(s).  (Database IDs are numerical; multiple IDs may be separated by a comma.)')
		return s


	parser = argparse.ArgumentParser(
		description='Search for nucleotide sequences.'
	)
	parser.add_argument('--baseurl', default='http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi', help='The base URL from which to fetch data.')
	parser.add_argument('--dbname', default="nucleotide", type=dbname_format, help="NCBI database name. [nucleotide]")
	parser.add_argument('--dbid',   default="30271926", type=dbid_format, help="NCBI database identifier. [30271926]")
	parser.add_argument('--save-nucleotide', action='store_true', help="Save network result to a local file for later use with --localsource; useful for iteration as large file does not have to be re-downloaded")
	parser.add_argument('--localsource', help="Use a local file instead of making a (slow) network request")
	parser.add_argument('--debug', action='store_true', help="Rather than the simplistic error messages, show developer-useful information (i.e., tracebacks).")
	args = parser.parse_args()

	if args.localsource:
		with open(args.localsource, 'rb') as srcf:
			print(srcf.read())    # TODO: not memory smart.

	else:
		url = create_efetch_url( args )
		with tempfile.NamedTemporaryFile(mode='r+b') as tmpf:
			tmpf.write( read_url( url ))    # TODO: not memory smart

			if args.save_nucleotide:
				# ex: "nucleotide-30271926-20171105.xml"
				save_name = "{}-{}-{}.xml".format(args.dbname, args.dbid, time.strftime('%Y%m%d'))
				try:
					os.link(tmpf.name, save_name)
				except OSError as e:
					# failed once; perhaps a cross-device or other issue; let's try a
					# second write operation (rather than a shutil.copy so script
					# will still succeed inside of Window's weird access rules.)
					tmpf.seek(0)
					with open(save_name, 'wb') as savef:
						savef.write( tmpf.read() )    # TODO: not memory smart
					sys.stderr.write('File saved locally to: {}\n'.format( save_name ))

			tmpf.seek(0)
			print( tmpf.read() )    # TODO: not memory smart