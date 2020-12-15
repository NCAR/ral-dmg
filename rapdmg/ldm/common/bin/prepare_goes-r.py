#!/usr/bin/env python

import sys
import os
import datetime

fn = sys.argv[1]

if len(sys.argv) > 2:
    log_dir = sys.argv[2]
    debug = 1
else:
    debug = 0

if not os.path.exists(os.path.dirname(fn)):
    try:
        os.makedirs(os.path.dirname(fn))
    except OSError as exc: # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise

data = sys.stdin.read()

if debug:
    log_date_dir = os.path.join(log_dir,datetime.datetime.now().strftime("%Y%m%d"))
    if not os.path.exists(log_date_dir):
        os.mkdir(log_date_dir)
    log_file = os.path.join(log_date_dir,"prepare_goes-r.log")
    o = open(log_file, "a+")
    o.write("Removing WMO header from file: {:s}\nHeader:{:s}\n\n".format(fn,data[0:36]))
    o.close()

o = open(fn, 'wb')
o.write(data[36:])
o.close()
