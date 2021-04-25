
import re

import os
import sys
import subprocess
import urllib.error
import urllib.request
import shlex
import time
import ftplib

from functools import reduce
from datetime import datetime, timedelta

# Let's make sure we have at least 3.6 so we can use f-strings
if sys.version_info[0] < 3:
    raise Exception(f"Must be using Python 3.6 or later")
if sys.version_info[0] == 3 and sys.version_info[1] < 6:
    raise Exception(f"Must be using Python 3.6 or later")

import logging

'''
prestop@asimov:~/git/ral-dmg/tmp$ curl -u "ftp:passwd"  ftp://gsdftp.fsl.noaa.gov/rr/
drwxr-xr-x    6 3399     3000         2048 Jun 26  2019 130_conus
drwxr-xr-x    5 3399     3000         1536 Jun 26  2019 200_puertorico
drwxr-xr-x    5 3399     3000         1536 Jun 26  2019 221_full
drwxr-xr-x    5 3399     3000         1536 Jun 26  2019 236_conus
drwxr-xr-x    5 3399     3000         1536 Jun 26  2019 242_alaska
drwxr-xr-x    5 3399     3000         1536 Jun 26  2019 243_hawaii
drwxr-xr-x    5 3399     3000         1536 Jun 26  2019 252_conus
drwxr-xr-x    2 3399     3000            0 Mar 13 14:40 for_ncep
drwxr-xr-x    5 3399     3000         1536 Jun 26  2019 full
'''

'''
prestop@asimov:~/git/ral-dmg/tmp$ curl https://ftpprd.ncep.noaa.gov/data/nccf/com/
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /data/nccf/com</title>
 </head>
 <body>
<h1>Index of /data/nccf/com</h1>
<pre>Name                    Last modified      Size  <hr><a href="/data/nccf/">Parent Directory</a>                             -   
<a href="557ww/">557ww/</a>                  12-Apr-2016 12:15    -   
<a href="aqm/">aqm/</a>                    20-Mar-2021 02:51    -   
<a href="arch/">arch/</a>                   20-Mar-2021 00:58    -   
<a href="blend/">blend/</a>                  12-Aug-2020 14:37    -   
<a href="ccpa/">ccpa/</a>                   29-Mar-2016 16:12    -   
<a href="cdas/">cdas/</a>                   20-Mar-2021 02:52    -   
<a href="cdas2/">cdas2/</a>                  20-Mar-2021 04:16    -   
<a href="cfs/">cfs/</a>                    30-Aug-2018 18:26    -   
<a href="ens_tracker/">ens_tracker/</a>            18-Jul-2018 16:19    -   
<a href="estofs/">estofs/</a>                 03-Feb-2015 15:45    -   
<a href="etss/">etss/</a>                   14-Sep-2017 17:28    -   
<a href="fnmoc/">fnmoc/</a>                  19-Mar-2021 13:39    -   
<a href="gefs_legacy/">gefs_legacy/</a>            30-Sep-2015 12:09    -   
<a href="gens/">gens/</a>                   31-Aug-2018 15:03    -   
<a href="gfs/">gfs/</a>                    15-Dec-2016 22:47    -   
<a href="glmp/">glmp/</a>                   22-Oct-2019 13:57    -   
<a href="hiresw/">hiresw/</a>                 03-Feb-2015 16:01    -   
<a href="hourly/">hourly/</a>                 18-Feb-2015 18:33    -   
<a href="hrrr/">hrrr/</a>                   16-Apr-2020 16:52    -   
<a href="hur/">hur/</a>                    06-May-2015 09:27    -   
<a href="hysplit/">hysplit/</a>                13-Feb-2019 17:02    -   
<a href="ingest/">ingest/</a>                 25-Aug-2017 00:15    -   
<a href="lmp/">lmp/</a>                    22-Oct-2019 13:55    -   
<a href="naefs/">naefs/</a>                  16-Dec-2019 18:48    -   
<a href="nam/">nam/</a>                    27-Mar-2017 18:42    -   
<a href="narre/">narre/</a>                  02-Dec-2020 13:45    -   
<a href="navo/">navo/</a>                   02-Feb-2021 20:18    -   
<a href="ncom/">ncom/</a>                   04-Feb-2015 12:53    -   
<a href="ngac/">ngac/</a>                   05-Feb-2015 07:33    -   
<a href="nhc/">nhc/</a>                    03-Feb-2015 16:06    -   
<a href="nldas/">nldas/</a>                  17-Nov-2015 18:05    -   
<a href="nos/">nos/</a>                    11-Jun-2019 13:06    -   
<a href="nwm/">nwm/</a>                    04-Jun-2018 16:37    -   
<a href="nwps/">nwps/</a>                   11-Apr-2016 12:17    -   
<a href="omb/">omb/</a>                    03-Feb-2015 16:26    -   
<a href="pcpanl/">pcpanl/</a>                 02-May-2017 15:33    -   
<a href="petss/">petss/</a>                  06-Dec-2017 17:45    -   
<a href="psurge/">psurge/</a>                 23-May-2017 17:14    -   
<a href="rap/">rap/</a>                    14-May-2018 14:29    -   
<a href="rtma/">rtma/</a>                   28-Jul-2020 13:27    -   
<a href="rtofs/">rtofs/</a>                  16-Oct-2017 18:28    -   
<a href="spcpost/">spcpost/</a>                05-Apr-2021 16:19    -   
<a href="sref/">sref/</a>                   03-Feb-2015 18:42    -   
<a href="swmf/">swmf/</a>                   03-Feb-2021 17:25    -   
<a href="ukmet/">ukmet/</a>                  04-Feb-2015 18:27    -   
<a href="urma/">urma/</a>                   03-Feb-2015 15:52    -   
<a href="wave/">wave/</a>                   25-Jul-2017 12:16    -   
<a href="wsa_enlil/">wsa_enlil/</a>              11-Sep-2015 17:43    -   
<hr></pre>
</body></html>'''

class RemoteDirListing:


    def  __init__(self):
        # instance class vars
        self.files = set()

    def store_dir_listing(self, curl_args):
        cmd = f"curl {curl_args}"
        completed_process = run_cmd(cmd, log_func_on_failure=logging.info)
        if completed_process.returncode != 0:
            return

        if "http" in cmd:
            self.store_http_out(completed_process.stdout)
        elif "ftp" in cmd:
            self.store_ftp_out(completed_process.stdout)

    def store_http_out(self, http_dir):

        files = re.findall(r'(?<=<a href=")[^"]*', http_dir)

        # remove directories (i.e. end with '/'
        files  = [f for f in files if not f.endswith('/')]
        #logging.debug(f"found files: {files}")
        self.files.update(files)

    def store_ftp_out(self, ftp_dir):
        for line in ftp_dir.splitlines():
            #print (f"line: {line}")
            # skip directories
            if line.startswith("d"):
                continue

            # NOTE: I gave up on perfectly supporting spaces in file names in ftp... I don't need it right now.
            # I think this works if there is just one space at a time.  If you put a double space or other white space
            # in your filename then this is not going to work.
            file = ' '.join(line.split()[8:])
            self.files.add(file)
            #logging.debug(file)

    def file_exists(self, file):
        return file in self.files

    def print_files(self):
        print(self.files)

    def clear_files(self):
        self.files.clear()


def main():

    rdl = RemoteDirListing()
    #rdl.store_dir_listing("https://ftpprd.ncep.noaa.gov/data/nccf/com/nam/prod/nam.20210423/")
    #rdl.print_files()
    #rdl.clear()
    rdl.store_dir_listing("-u \"ftp:cowie@ucar.edu\" ftp://gsdftp.fsl.noaa.gov/rrfs_dev1/conus/bgsfc/")
    rdl.print_files()


def run_cmd(cmd, exception_on_error=False, log_func_on_failure=logging.warning):
    """
    runs a command with blocking
    returns a CompletedProcess instance
        - you can get stdout with .stdout.decode('UTF-8').strip('\n')
    """
    logging.debug(f"running command: {cmd}")

    # I know you shouldn't use shell=True, but splitting up a piped cmd into
    # multiple separate commands is too much work right now.
    # shell=True is also required if using wildcards
    # TODO: https://stackoverflow.com/questions/13332268/how-to-use-subprocess-command-with-pipes
    # https://stackoverflow.com/questions/295459/how-do-i-use-subprocess-popen-to-connect-multiple-processes-by-pipes
    if '|' in cmd or ';' in cmd or '*' in cmd or '?' in cmd:
        completed_process = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 encoding='utf-8')
    else:
        splitcmd = shlex.split(cmd)
        completed_process = subprocess.run(splitcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 encoding='utf-8')

    if completed_process.returncode != 0:
        log_func_on_failure(f'Command returned non-zero exit status: {cmd_out.returncode}\n\tcmd: {cmd}.')
        log_func_on_failure(f'\tstderr: {cmd_out.stderr}')
        if exception_on_error:
            raise subprocess.CalledProcessError(cmd_out.returncode, cmd)

    return completed_process




if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.debug("in main")
    main()
