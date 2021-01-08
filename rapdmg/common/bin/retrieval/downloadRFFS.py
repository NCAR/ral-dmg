#!/usr/bin/env python3
"""
downloadRFFS.py downloads RFFS data using wget.
"""


######################
# PYTHON LIB IMPORTS
#####################
import os
import sys
import subprocess
from datetime import datetime, timedelta
import urllib.error
import urllib.request
import shlex
import time

from functools import reduce

# Let's make sure we have at least 3.6 so we can use f-strings
if sys.version_info[0] < 3:
    raise Exception(f"Must be using Python 3.6 or later")
if sys.version_info[0] == 3 and sys.version_info[1] < 6:
    raise Exception(f"Must be using Python 3.6 or later")

#####################
# CONFIG MASTER STUFF
#####################
import logging

try:
    from ConfigMaster import ConfigMaster
except ImportError:
    print(f"{os.path.basename(__file__)} needs ConfigMaster to run.")
    print(f"https://github.com/NCAR/ConfigMaster")
    exit(1)

defaultParams = """

# model_type is the model to download
#   valid: bgdawp, bgrd3d, bgsfc
# if you set this via the cmd line, then other parameter values will be set based on model_type 
# (see _config_overide below), but parameters set on the command line take final precedence. 
model_type = "bgdawp"

# look_back_hours is the look back period. You can use this to get older model data.
# i.e. if you set this to 12 it will first look for a model run from 12 hours ago that you don't already have locally, and then work it's way to the present time.
look_back_hours = 24  

# If force_cycle_hour >= 0, then the download script attempts to get data for that specific cycle hour
# this overrides look_back_hours
force_cycle_hour = -1

# the maximum forecast hour to download
max_forecast_hour = 36

# the step between forecast hours to be downloaded (only suppports integers)
forecast_step    = 1

# location of the gfs data (passed to ncftpget)
gfs_base_url = 'gsdftp.fsl.noaa.gov'

# set this if ncftpget is not in your path
ncftpget_location = ''

# credential file for ncftpget
ncftpget_config = '/home/rapdmg/ftp/nomads_nco_noaa_gov.cfg'

# should we write an Ldata file?
write_ldata = False

# how long to sleep between url requests  (in seconds)
url_sleep = .25

# if downloaded files are smaller than this, an error is assumed to have occurred.
min_expected_filesize = 500e+6  # 500M

# You can use some various replacement field templates in these parameters
#   {cycle_year}         --- YYYY
#   {cycle_month}        --- MM
#   {cycle_day}          --- DD
#   {cycle_julian_day}   --- JJJ
#   {cycle_date}         --- YYYYMMDD
#   {cycle_time}         --- YYYYMMDDHH
#   {cycle_hour}         --- HH
#   {forecast_hour}      --- FF (lead) use e.g. {forecast_hour:04d} for 4 digit leading zeros


# 2100412002300 
# YYJJJHHMMHHMM
# 2-digit year (21), julian day (004), gen hour/minutes (1200), forecast lead hour/minutes (2300)

# RFFS-CONUS-bgdawp/GSL/20210104/20210104_i12_f023_RFFS-CONUS-bgdawp_GSL.grib2

remote_filename = "{cycle_year}{cycle_julian_day}{cycle_hour}00{forecast_hour}00"
local_filename = "{cycle_date}_i{cycle_hour}_f{forecast_hour:03d}_RFFS-CONUS-bgdwawp.grib2"        

# remote dir is *relative* and is appended to gfs_base_url 
remote_dir =  "data/nccf/com/gfs/prod/gfs.{cycle_date}/{cycle_hour}"
local_dir = "/rapdmg2/data/grib/RRFS/GSL/CONUS/bgdawp/{cycle_year}/{cycle_month}{cycle_day}"

##################################  CMD-LINE OVERRIDES  ########################

# DEFAULTS in this file are for bgdawp, if you set model_type to something else on the command line, 
# then the _config_override values (below) will override with values that make sense for other models.

# This allows you to set just one thing on the cmd line (i.e. model_type), and change several dependent values.

_config_override["model_type"]["bgdawp"]["min_expected_filesize"] = 500e+6 # 500M
_config_override["model_type"]["GFS3"]["local_filename"] = "{cycle_time}_fh.{forecast_hour:04d}_tl.press_gr.1p0deg.grib2"          
_config_override["model_type"]["GFS3"]["remote_filename"] = "gfs.t{cycle_hour}z.pgrb2.1p00.f{forecast_hour:03d}"

"""

p = ConfigMaster(defaultParams, __doc__, add_default_logging=True, allow_extra_parameters=True)


# --------------------------
#  HELPER FUNCTIONS
# --------------------------

def run_cmd(cmd, exception_on_error=False):
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
        cmd_out = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 encoding='utf-8')
    else:
        splitcmd = shlex.split(cmd)
        cmd_out = subprocess.run(splitcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 encoding='utf-8')

    if cmd_out.returncode != 0:
        logging.warning(f'Command returned non-zero exit status: {cmd_out.returncode}\n\tcmd: {cmd}.')
        logging.warning(f'\tstderr: {cmd_out.stderr}')
        if exception_on_error:
            raise subprocess.CalledProcessError(cmd_out.returncode, cmd)

    return cmd_out


def condition_params():
    p['model_type'] = p['model_type'].lower()


def check_params():
    model_type_values = ['bgdawp', 'bgrd3d', 'bgsfc']
    if p['model_type'] not in model_type_values:
        logging.fatal(f"model_type ({p['model_type']} is not supported.  Must be one of {model_type_values}")
        sys.exit(1)

    #if not os.path.exists(p['local_dir']):
    #    logging.fatal(f"{p['local_dir']} does not exist")
    #    sys.exit(1)


def join_slash(a, b):
    return a.rstrip('/') + '/' + b.lstrip('/')


# official urljoin doesn't do what I want.
# https://stackoverflow.com/questions/1793261/how-to-join-components-of-a-path-when-you-are-constructing-a-url-in-python
# In [4]: parts = ['https://foo-bar.quux.net', '/foo', 'bar', '/bat/', '/quux/']
# In [5]: urljoin(*parts)
# Out[5]: 'https://foo-bar.quux.net/foo/bar/bat/quux/'
#
# In [6]: urljoin('https://quux.com/', '/path', 'to/file///', '//here/')
# Out[6]: 'https://quux.com/path/to/file/here/'
#
# In [7]: urljoin()
# Out[7]: ''
#
# In [8]: urljoin('//','beware', 'of/this///')
# Out[8]: '/beware/of/this///'
#
# In [9]: urljoin('/leading', 'and/', '/trailing
# Out[9]: '/leading/and/trailing/slash/'
def url_join(*args):
    return reduce(join_slash, args) if args else ''


def find_latest_hour():
    # Get current time
    ctimeutc = datetime.utcnow()

    p['off_hours'] = None

    for hour_offset in range(0, p['look_back_hours']):
        ptimeutc = ctimeutc - timedelta(hours=hour_offset)
        file_template_values = {}
        add_file_template_time_values(file_template_values, ptimeutc)
        url_dir = url_join(p['gfs_base_url'], p['remote_dir'].format(**file_template_values))
        # urlsite = f"{p['gfs_base_url']}gfs.{ptimeutc.strftime('%Y%m%d')}/{ptimeutc.strftime('%H')}"
        try:
            time.sleep(p['url_sleep'])
            ret = urllib.request.urlopen(url_dir)
            ret.close()
            p['off_hours'] = hour_offset
            break
        except urllib.error.HTTPError as e:
            logging.debug(f"{url_dir} is not available.")

    if not p['off_hours']:
        logging.warning(f'No data in last {p["look_back_hours"]} hours found -- Exiting.')
        sys.exit(0)


# file_template_values is a dictionary, and dt is the datetime used.
# TODO: use typehints here?
def add_file_template_time_values(file_template_values, dt):
    file_template_values["cycle_date"] = dt.strftime('%Y%m%d')
    file_template_values["cycle_year"] = dt.strftime('%Y')
    file_template_values["cycle_month"] = dt.strftime('%m')
    file_template_values["cycle_hour"] = dt.strftime('%H')
    file_template_values["cycle_time"] = file_template_values["cycle_date"] + file_template_values["cycle_hour"]


def check_required_url(url_dir):
    try:
        time.sleep(p['url_sleep'])
        ret = urllib.request.urlopen(url_dir)
        ret.close()
    except urllib.error.URLError as e:
        logging.warning(f'Failure when looking at required url: {url_dir} - Raised exception {e}.  Giving up.')
        sys.exit(1)


def check_local_file(remote_path, local_path):
    """
    Check if the file is already available on the local disk and if the size is right
    :param remote_path: 
    :param local_path: 
    :return: True if file is ok, False if not ok.
    """
    # Get the remote size
    full_url = url_join(p['gfs_base_url'], remote_path)
    try:
        time.sleep(p['url_sleep'])
        ret = urllib.request.urlopen(full_url)
        file_size_at_server = int(ret.info().get('content-length', '0'))
        ret.close()

        # See if the corresponding local file exists...
        if os.path.isfile(local_path):

            local_file_size = os.path.getsize(local_path)

            # See if the size is the same as that on the remote
            # server. If so, the local file is okay and we don't
            # need to do anything. If not, remove the local file
            # and move on as thought we didn't have the file.
            # Note though that we are lumping the two cases where
            # the local file size is not the same as the remote
            # file size into one catagory (i.e. local < remote
            # AND remote < local). The case where remote < local
            # would be extremely odd, but maybe removing the local
            # and keeping the remote is not the way to go in that
            # case.
            if local_file_size == file_size_at_server:
                logging.debug(f"already have good local file - {local_path}")
                return True

    except urllib.error.URLError as e:
        logging.warning(f"Exception ({e}) when attempting to find size of {full_url}")

    logging.debug(f"TODO")
    cmd = f"rm -f {local_path}"
    run_cmd(cmd)


def get_remote_file_size(remote_path):
    # Get the remote size
    time.sleep(p['url_sleep'])
    ret = urllib.request.urlopen(remote_path)
    file_size_at_server = int(ret.info().get('content-length', '0'))
    ret.close()
    return file_size_at_server

def safe_mkdirs(d):
    logging.info(f"making dir: {d}")
    if not os.path.exists(d):
        os.makedirs(d, 0o777, exist_ok=True)

def print_params():
    logging.info(f"Using these parameters:")
    for line in p.getParamsString().splitlines():
        logging.info(f"\t{line}")

def main():
    condition_params()
    check_params()
    print_params()

    #logging.info(f"Downloading {p['model_type']} to {p['local_dir']}")

    if 0 <= p['force_cycle_hour']:
        ptimeutc = datetime.utcnow()
        ptimeutc = ptimeutc.replace(hour=p['force_cycle_hour'])
    else:
        # If the offset in hours is set to -1, look through the previous
        # 24 hours to see what is available right now and reset off_hours to the most recent available data
        if 0 > p['off_hours']:
            find_latest_hour()

        ptimeutc = datetime.utcnow() - timedelta(hours=p['off_hours'])

    # Setup the file template dictionary now that we know what hour to get.
    file_template_values = {}
    add_file_template_time_values(file_template_values, ptimeutc)

    # Check to see if the remote directory actually exists
    url_dir = url_join(p['gfs_base_url'], p['remote_dir'].format(**file_template_values))
    logging.info(f"url_dir is {url_dir}")
    check_required_url(url_dir)

    # ------------------------------------------------------------------
    # Download the data
    # ------------------------------------------------------------------
    downloaded_files = 0
    for member in p['ensemble_members']:

        file_template_values['member'] = member
        # loop over all forecast hours up to the maximum forecast hour.
        start_hour = 0
        end_hour = p['max_forecast_hour']
        hour_step = p['forecast_step']

        for h in range(start_hour, end_hour + 1, hour_step):

            file_template_values["forecast_hour"] = h

            # Remote file name
            remote_dir = p['remote_dir'].format(**file_template_values)
            remote_file = p['remote_filename'].format(**file_template_values)
            remote_path = os.path.join(remote_dir, remote_file)

            # Local file name
            local_dir = p['local_dir'].format(**file_template_values)
            local_file = p['local_filename'].format(**file_template_values)
            local_path = os.path.join(local_dir, local_file)
            logging.debug(f"hour: {h}\tremote: {remote_path}\tlocal: {local_path}")

            safe_mkdirs(local_dir)

            # Check if the file is already available on the local disk
            # and if the size is right
            fok = 0

            url_path = url_join(p['gfs_base_url'], remote_path)
            logging.info(f"url_path is {url_path}")

            try:

                # Get the remote size
                remote_file_size = get_remote_file_size(url_path)

                # See if the corresponding local file exists...
                if os.path.isfile(local_path):

                    # Get the file size
                    local_file_size = os.path.getsize(local_path)

                    # See if the size is the same as that on the remote
                    # server. If so, the local file is okay and we don't
                    # need to do anything. If not, remove the local file
                    # and move on as thought we didn't have the file.
                    # Note though that we are lumping the two cases where
                    # the local file size is not the same as the remote
                    # file size into one catagory (i.e. local < remote
                    # AND remote < local). The case where remote < local
                    # would be extremely odd, but maybe removing the local
                    # and keeping the remote is not the way to go in that
                    # case.
                    if local_file_size == remote_file_size:
                        fok = 1
                        logging.debug(f"already have good local file - {local_path}")
                    else:
                        cmd = f"rm -f {local_path}"
                        run_cmd(cmd)

                # File wasn't the right size or wasn't there. Either way
                # it isn't there now. Get the file.
                if fok == 0:

                    logging.info(f"downloading {url_path}")

                    # Get the file using wget
                    cmd = f'wget {url_path} -O {local_path}'
                    time.sleep(p['url_sleep'])
                    run_cmd(cmd)

                    # Check if we even got a file
                    if os.path.isfile(local_path):

                        # Check file size against a minimum size
                        local_file_size = os.path.getsize(local_path)
                        if local_file_size > p['min_expected_filesize']:

                            # All is well. Tell the user
                            downloaded_files += 1
                            logging.debug(f"{local_path} is OK-ed !")

                            # Write latest_data_info and register
                            # with data mapper if requested to do so
                            if p['write_ldata']:
                                cmd = (f"LdataWriter -dir {local_dir} -rpath  {local_file} -dtype grib2 -lead {h*60*60} "
                                       f"-ltime {file_template_values['cycle_time']}0000 -maxDataTime")
                                run_cmd(cmd)

                        # Didn't meet the minimum file size requirement.
                        # Tell the user what happened and remove file we assume is incomplete
                        else:
                            logging.warning(
                                f"{url_path} did not meet the minimum size: {p['min_expected_filesize']}, and will be deleted.")
                            cmd = f'rm -f {local_path}'
                            run_cmd(cmd)

                    # We didn't get a file. The downloading failed.
                    else:
                        logging.error(f"downloading {url_path} failed !")

            #
            # Exception: Couldn't connect or couldn't file the file we
            # are looking for. Tell the user.
            #
            except urllib.error.HTTPError as e:
                logging.error(f"Download of {url_path} failed!")
                logging.error(f"{e}")

    logging.info(f"downloadGFS.py completed succesfully.  Retrieved {downloaded_files} files.")


if __name__ == '__main__':
    main()
