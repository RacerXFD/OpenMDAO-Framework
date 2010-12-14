"""
A script to add a group of required packages to the current python
environment.
"""

import sys
import os
import urllib2
from optparse import OptionParser
import subprocess


# requirements files have the following format:
#
# - python style comments are allowed  '#'
# - blank lines are allowed
# - each non-comment, non-blank line begins with a requirement string
#    followed by an optional url of a 'find-links' server where
#    the required package can be found.  Whitespace is NOT allowed
#    within a requirement string.

def _get_reqs_from_filelike(f):
    reqs = []
    for line in f:
        line = line.split('#')[0]
        line = line.strip()
        if not line:  # skip blank lines
            continue
        parts = line.split()
        if len(parts) == 1:
            parts.append(None)
        elif len(parts) > 2:
            raise RuntimeError("invalid format for line '%s'" % line)
        reqs.append((parts[0], parts[1]))
    return reqs

def _get_reqs_from_file(name):
    with open(name, 'r') as f:
        print "Reading requirements from file: %s" % name
        return _get_reqs_from_filelike(f)

def _get_reqs_from_url(url):
    try:
        f = urllib2.urlopen(url)
        print "Reading requirements from URL: %s" % f.geturl()
        return _get_reqs_from_filelike(f)
    finally:
        f.close()
    
def add_reqs(argv=None, default_flink=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = OptionParser()
    parser.usage = "add_reqs.py [options] <req_file1> <req_file2> ... <req_file_n>"
    parser.add_option("-f", action="store", type="string", dest='flink', 
                      help="find-links server url")
    
    (options, args) = parser.parse_args(argv)

    reqs = []
    for entry in args:
        try:
            if os.path.exists(entry):  # a local file
                reqs.extend(_get_reqs_from_file(entry))
            else:  # assume it's a url
                reqs.extend(_get_reqs_from_url(entry))
        except Exception as err:
            print "'%s' does not specify a valid requirements file or url: %s" % (entry, str(err))
            sys.exit(-1)

    for req, flink in reqs:
        if flink is None:
            if options.flink is None:
                cmd = []
            else:
                cmd = ['-f', options.flink]
        else:
            cmd = ['-f', flink]
        subprocess.check_call([os.path.join(os.path.dirname(sys.executable),'easy_install'),'-NZ'] + cmd + [req])

   
if __name__ == "__main__": # pragma no cover
    sys.exit(add_reqs())
   
