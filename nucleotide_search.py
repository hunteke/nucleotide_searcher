#!/usr/bin/env python3

import collections
import csv
import operator
import os
import queue
import re
import sys
import tempfile
import threading
import time
import urllib.request
import xml.etree.ElementTree
import zlib

from functools import reduce

def msg_and_die( msg ):
	if args.debug:
		raise

	raise SystemExit( "{}\n\nUse --debug for developer friendly information\n".format(msg) )


def sort_by_value( d, reverse=False ):
	return sorted(d.items(), key=operator.itemgetter(1), reverse=reverse)


def read_url_stream( url ):
	"""Retrieve data from `url`, in a streaming fashion

	Will read HTTP data, placing each consecutive chunk into a queue
	(queue.Queue).  When read operaion is complete, the queue will contain a
	final None sentinel value.

	Args:
		url (str): A valid URL from which to read data.

	Returns:
		A queue (queue.Queue) that will contain consecutive pieces as the read
		task progresses.  When the read operation is complete, a sentinel None
		will be placed in the queue.
	"""
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

	filter_funcs = []
	encoding = res.info().get('Content-Encoding') or ''
	if 'gzip' in encoding.lower():
		filter_funcs.append( zlib.decompressobj(16+zlib.MAX_WBITS).decompress )

	return stream_read(res, filter_funcs=filter_funcs)


def stream_read( fileObj, chunksize=64*1024, filter_funcs=[] ):
	"""Read a file-like object in parts.

	Reads consecutive chunksize chunks of data from fileObj, placing each
	chunk/part into a queue (queue.Queue).  When all data has been read, will
	place a sentinel None into the queue.

	Args:
		fileObj (file-like object): must implement the .read() method of the
		  Python file-API
		chunksize (non-negative integer): size of chunks to read from fileObj.
		  Default: 64KiB
		filter_funcs (list of functions): a list of filtering functions to be
		  applied to each chunk before it reaches the queue.  For example, to
		  uncompress each chunk, [zlib.dcompressobj().decompress]

	Returns:
		A queue (queue.Queue) that will contain consecutive pieces as the read
		task progresses.  When the read operation is complete, a sentinel None
		will be placed in the queue.
	"""
	def _reader(q, chunksize, filter_funcs):
		# The kernel for a n-ary set of operations ( fn(...f3(f2(f1(data)))...) ).
		# Necessary in this small project to enable handling of GZIP data, above
		reduce_func = lambda res, fn: fn( res )

		chunk = fileObj.read( chunksize )
		while chunk:
			chunk = reduce(reduce_func, filter_funcs, chunk)
			q.put( chunk )
			chunk = fileObj.read( chunksize )
		q.put( None )
		q.join()

	if not isinstance(chunksize, int) or chunksize < 1:
		raise ValueError('chunksize: must be a positive integer; suggest a power of 2.  Invalid value: {}'.format(chunksize))

	# we'll die harder if filter_funcs is not iterable, but that's okay.  We're
	# just helping this coder out for now.
	for i, f in enumerate(filter_funcs):
		if not callable( f ):
			raise ValueError('filter_funcs: must only contain callable items.  Invalid item (index: {}): {}'.format(i, f))

	chunks_q = queue.Queue( maxsize=16 )
	threading.Thread(target=_reader, args=(chunks_q, chunksize, filter_funcs)).start()

	return chunks_q


def write_file_stream( q, fileObj ):
	"""Write a file-like object in parts.

	Iterate q (queue.Queue), writing each received item to fileObj.  When
	there are no more items in the queue, flush the file and attempt to shut
	the queue down.

	Args:
		q (queue.Queue): a queue from which to receive consecutive pieces of a
		  file
		fileObj (file-like object): must implement the .read() method of the
		  Python file-API
	"""
	chunk = q.get()
	while chunk:
		fileObj.write( chunk )
		q.task_done()
		chunk = q.get()
	fileObj.flush()
	q.task_done()
	q.join()


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


def find_user_regex( source_f, pattern_re, csvwriter ):
	"""Search XML source for pattern, writing found items to CSV

	Each line of the output CSV will contain a found pattern, and how many
	characters into the nucleotide it was found.  Of note: the first character
	in the sequence is considered to be at index 1.

	Args:
		source_f (fileObj): an XML source, containing a TSeq_sequence tag
		pattern_re (regex): a compiled regular expression, for searching source_f
		csvwriter: a csvwriter object where results will be written
	"""
	stats = collections.defaultdict(int)

	for event, el in xml.etree.ElementTree.iterparse( source_f ):
		if el.tag == 'TSeq_sequence':
			for m in pattern_re.finditer( el.text ):
				# +1 = non-CS folks think 1-based.  Who knew?!?! ;-)
				start, end = m.start() + 1, m.end()
				stats[ m.group() ] += 1
				csvwriter.writerow((m.group(), start, end))
		el.clear()

	sorted_by_occurrence = sort_by_value(stats, reverse=True)
	if sorted_by_occurrence:
		for k, v in sorted_by_occurrence:
			print("{}\t{}".format(k, v))
	else:
		print("No matching sequences found.")


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
	parser.add_argument('--baseurl', default='http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi', help='The base URL from which to fetch data. [http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi]')
	parser.add_argument('--dbname', default="nucleotide", type=dbname_format, help="NCBI database name. [nucleotide]")
	parser.add_argument('--dbid',   default="30271926", type=dbid_format, help="NCBI database identifier. [30271926]")
	parser.add_argument('--regex',  default="AAAATAGCCCC", help="Regular expression search pattern. [AAAATAGCCCC]")
	parser.add_argument('--ofname', required=True, help="Output file name to write results (CSV format). Ex: 'results.csv'")
	parser.add_argument('--save-nucleotide', action='store_true', help="Save network result to a local file for later use with --localsource; useful for iteration as large file does not have to be re-downloaded")
	parser.add_argument('--localsource', help="Use a local file instead of making a (slow) network request")
	parser.add_argument('--debug', action='store_true', help="Rather than the simplistic error messages, show developer-useful information (i.e., tracebacks).")
	args = parser.parse_args()

	# prepare user's regex
	pattern_re = re.compile( args.regex )

	if args.localsource:
		with open(args.localsource, 'rb') as srcf, open(csv_fname, 'w', newline='') as csvf:
			csvwriter = csv.writer(csvf, quoting=csv.QUOTE_MINIMAL)
			find_user_regex(srcf, pattern_re, csvwriter)

	else:
		url = create_efetch_url( args )
		with tempfile.NamedTemporaryFile(mode='r+b') as tmpf:
			write_file_stream(read_url_stream(url), tmpf)

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
						write_file_stream(stream_read(tmpf), savef)
					sys.stderr.write('File saved locally to: {}\n'.format( save_name ))

			tmpf.seek(0)
			with open(csv_fname, 'w', newline='') as csvf:
				csvwriter = csv.writer(csvf, quoting=csv.QUOTE_MINIMAL)
				find_user_regex(tmpf, pattern_re, csvwriter)
