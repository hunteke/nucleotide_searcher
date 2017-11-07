#!/usr/bin/env python3

import urllib.request

def read_url( url ):
	req = urllib.request.Request( url )
	res = urllib.request.urlopen( req )
	return res.read()

if '__main__' == __name__:
	url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nucleotide&id=30271926&rettype=fasta&retmode=xml'
	print( read_url( url ))
