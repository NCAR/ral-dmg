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
#   valid: rffs_bgdawp, rffs_bgrd3d, rffs_bgsfc
# if you set this via the cmd line, then other parameter values will be set based on model_type 
# (see _config_overide below), but parameters set on the command line take final precedence. 
model_type = "rffs_bgdawp"

# look_back_hours is the look back period. You can use this to get older model data.
# i.e. if you set this to 12 it will start with the present time, and then look back an hour at a time
#      for a model run that you don't already have locally, and work it's way to the max look_back_hours.
look_back_hours = 24  

# If force_cycle_hour >= 0, then the download script attempts to get data for that specific cycle hour
# this overrides look_back_hours
force_cycle_hour = -1

# the maximum forecast hour to download
max_forecast_hour = 36

# the step between forecast hours to be downloaded (only suppports integers)
forecast_step    = 1

# location of the gfs data (passed to ncftpget)
base_url = 'gsdftp.fsl.noaa.gov'

# valid values: 'ftp' or 'http'
retrieval_protocol = 'ftp' 

# username and password if authentication is required
# only used by ftp - not supported yet by http.
auth_user = 'ftp'
auth_pass = ''

# should we write an Ldata file?
write_ldata = False

# how long to sleep between url requests  (in seconds)
request_sleep = .25

# if downloaded files are smaller than this, an error is assumed to have occurred.
# Set to a negative number to disable this check.
min_expected_filesize = 500e+6  # 500M

# You can use some various replacement field templates in these parameters
#   {cycle_year}         --- YYYY
#   {cycle_month}        --- MM
#   {cycle_day}          --- DD
#   {cycle_julian_day}   --- JJJ
#   {cycle_date}         --- YYYYMMDD
#   {cycle_time}         --- YYYYMMDDHH
#   {cycle_hour}         --- HH
#   {cycle_minute}       --- MM
#   {forecast_hour}      --- h (lead) need to specify # of digits use e.g. {forecast_hour:03d} for 3 digit leading zeros
#   {forecast_minute}      --- m (lead) need to specify # of digits use e.g. {forecast_minute:02d} for 2 digit leading zeros


# 2100412002300 
# YYJJJHHMMHHMM
# 2-digit year (21), julian day (004), gen hour/minutes (1200), forecast lead hour/minutes (2300)

# RFFS-CONUS-bgdawp/GSL/20210104/20210104_i12_f023_RFFS-CONUS-bgdawp_GSL.grib2

remote_filename = "{cycle_year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
local_filename = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_RFFS-CONUS-bgdwawp.grib2"        

# remote dir is *relative* and is appended to base_url 
remote_dir = "data/nccf/com/gfs/prod/gfs.{cycle_date}/{cycle_hour}"
local_dir = "/rapdmg2/data/grib/RRFS/GSL/CONUS/bgdawp/{cycle_year}/{cycle_month}{cycle_day}"

##################################  CMD-LINE OVERRIDES  ########################

# DEFAULTS in this file are for bgdawp, if you set model_type to something else on the command line, 
# then the _config_override values (below) will override with values that make sense for other models.

# This allows you to set just one thing on the cmd line (i.e. model_type), and change several dependent values.

########## RFFS #############
 
_config_override["model_type"]["rffs_bgdawp"]["min_expected_filesize"] = 500e+6 # 500M
_config_override["model_type"]["rffs_bgdawp"]["remote_dir"] = '/rrfs_dev1/conus/bgdawp'
_config_override["model_type"]["rffs_bgdawp"]["remote_filename"] = "{cycle_year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
_config_override["model_type"]["rffs_bgdawp"]["local_dir"] = "/rapdmg2/data/grib/RRFS/GSL/CONUS/bgdawp/{cycle_year}/{cycle_month}{cycle_day}"
_config_override["model_type"]["rffs_bgdawp"]["local_filename"] = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_RFFS-CONUS-bgdwawp.grib2"        

_config_override["model_type"]["rffs_bgrd3d"]["min_expected_filesize"] = 500e+6 # 500M
_config_override["model_type"]["rffs_bgrd3d"]["remote_dir"] = '/rrfs_dev1/conus/bgrd3d'
_config_override["model_type"]["rffs_bgrd3d"]["remote_filename"] = "{cycle_year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
_config_override["model_type"]["rffs_bgrd3d"]["local_dir"] = "/rapdmg2/data/grib/RRFS/GSL/CONUS/bgrd3d/{cycle_year}/{cycle_month}{cycle_day}"
_config_override["model_type"]["rffs_bgrd3d"]["local_filename"] = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_RFFS-CONUS-bgrd3d.grib2"        

_config_override["model_type"]["rffs_bgsfc"]["min_expected_filesize"] = -1 # 500e+6 # 500M
_config_override["model_type"]["rffs_bgsfc"]["remote_dir"] = '/rrfs_dev1/conus/bgsfc'
_config_override["model_type"]["rffs_bgsfc"]["remote_filename"] = "{cycle_year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
_config_override["model_type"]["rffs_bgsfc"]["local_dir"] = "/rapdmg2/data/grib/RRFS/GSL/CONUS/bgsfc/{cycle_year}/{cycle_month}{cycle_day}"
_config_override["model_type"]["rffs_bgsfc"]["local_filename"] = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_RFFS-CONUS-bgsfc.grib2"        


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
    p['retrieval_protocol'] = p['retrieval_protocol'].lower()

def check_params():
    model_type_values = ['rffs_bgdawp', 'rffs_bgrd3d', 'rffs_bgsfc']
    if p['model_type'] not in model_type_values:
        logging.fatal(f"model_type ({p['model_type']} is not supported.  Must be one of {model_type_values}")
        sys.exit(1)

    retrieval_values = ['ftp', 'http']
    if p['retrieval_protocol'] not in retrieval_values:
        logging.fatal(f"retrieval_protocol ({p['retrieval_protocol']} is not supported.  Must be one of {retrieval_values}")
        sys.exit(1)

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
# In [9]: urljoin('/leading', 'and/', '/trailingf
# Out[9]: '/leading/and/trailing/slash/'
def url_join(*args):
    return reduce(join_slash, args) if args else ''


def is_url_valid(base_url, remote_dir):

    if p['retrieval_protocol'] == 'http':
        try:
            url_dir = url_join(base_url, remote_dir)
            time.sleep(p['request_sleep'])
            ret = urllib.request.urlopen(url_dir)
            ret.close()
        except urllib.error.URLError as e:
            return False
        return True

    if p['retrieval_protocol'] == 'ftp':
        try:
            time.sleep(p['request_sleep'])
            p['_ftp'].cwd(remote_dir)  # change into "debian" directory
        except ftplib.error_perm as e:
            return False
        return True


    # This really only works if the data is organized into hourly directories...
    #   Maybe we should just skip this, and work backwards from present time if an hour is not
    #   explicitly given.
def find_latest_hour_offset():
    # Get current time
    ctimeutc = datetime.utcnow()

    for hour_offset in range(0, p['look_back_hours']):
        ptimeutc = ctimeutc - timedelta(hours=hour_offset)
        file_template_values = {}
        add_file_template_time_values(file_template_values, ptimeutc)
        remote_dir = p['remote_dir'].format(**file_template_values)
        if is_url_valid(p['base_url'], remote_dir):
            return hour_offset
        else:
            logging.debug(f"{remote_dir} at {p['base_url']} is not available.")

    logging.warning(f'No data in last {p["look_back_hours"]} hours found -- Exiting.')
    sys.exit(0)


# file_template_values is a dictionary, and dt is the datetime used.
# TODO: use typehints here?
def add_file_template_time_values(file_template_values, dt):
    file_template_values["cycle_date"] = dt.strftime('%Y%m%d')
    file_template_values["cycle_year"] = dt.strftime('%Y')
    file_template_values["cycle_month"] = dt.strftime('%m')
    file_template_values["cycle_hour"] = dt.strftime('%H')
    file_template_values["cycle_minute"] = dt.strftime('%m')
    file_template_values["cycle_time"] = file_template_values["cycle_date"] + file_template_values["cycle_hour"]
    file_template_values["cycle_day"] = dt.strftime('%d')
    file_template_values["cycle_julian_day"] = dt.strftime('%j')




def is_local_file_good(local_path, remote_file_size):
    """
    Check if the file is already available on the local disk and if the size is right
    :param local_path:
    :param remote_file_size:
    :return: True if file is ok, False if not ok.
    """

    # See if the corresponding local file exists...
    if not os.path.isfile(local_path):
        return False

    local_file_size = os.path.getsize(local_path)

    if p["min_expected_filesize"] > 0 and local_file_size < p["min_expected_filesize"]:
        logging.warning(
            f"{local_path} did not meet the minimum size: {p['min_expected_filesize']}, and will be deleted.")
        return False

    return local_file_size == remote_file_size


# TODO: what if this fails?
def get_remote_file_size(remote_path):

    time.sleep(p['request_sleep'])

    if p["retrieval_protocol"] == 'http':
        # Get the remote size
        ret = urllib.request.urlopen(remote_path)
        file_size_at_server = int(ret.info().get('content-length', '0'))
        ret.close()
        return file_size_at_server

    if p["retrieval_protocol"] == 'ftp':
        return p["_ftp"].size(remote_path)

def safe_mkdirs(d):
    logging.info(f"making dir: {d}")
    if not os.path.exists(d):
        os.makedirs(d, 0o777, exist_ok=True)


def print_params():
    logging.info(f"Using these parameters:")
    for line in p.getParamsString().splitlines():
        logging.info(f"\t{line}")

def get_remote_file(local_dir, local_file, remote_dir, remote_file):

    remote_path = os.path.join(remote_dir, remote_file)
    local_path = os.path.join(local_dir, local_file)

    cmd = f"rm -f {local_path}"
    run_cmd(cmd)

    # File wasn't the right size or wasn't there. Either way
    # it isn't there now. Get the file.
    logging.info(f"downloading {remote_path}")

    # TODO: would be better to use a python module (urllib?)
    if p['retrieval_protocol'] == 'http':
        # Get the file using wget
        cmd = f'wget {remote_path} -O {local_path}'
        time.sleep(p['request_sleep'])
        run_cmd(cmd)

    if p['retrieval_protocol'] == 'ftp':
        with open(local_path, 'wb') as fp:
            ftp.retrbinary('RETR ' + remote_file, fp.write)


def initiate_connection():

    if p['retrieval_protocol'] == 'ftp':
        logging.debug(f"Connecting to {p['base_url']}")
        logging.debug(f"Using <{p['auth_user']}>, <{p['auth_pass']}>")
        p['_ftp'] = ftplib.FTP(host=p['base_url'], user=p['auth_user'], passwd=p['auth_pass'])  # connect to host, default port

def close_connection():
    if p['retrieval_protocol'] == 'ftp':
        p['_ftp'].quit()

def

def main():
    condition_params()
    check_params()
    print_params()

    initiate_connection()

    if p['force_cycle_hour'] >= 0:
        ptimeutc = datetime.utcnow()
        ptimeutc = ptimeutc.replace(hour=p['force_cycle_hour'])
    else:
        # If the offset in hours is set to -1, look through the previous
        # hours to see what is available right now and reset force_cycle_hour to the most recent available data
        p['force_cycle_hour'] = find_latest_hour_offset()
        ptimeutc = datetime.utcnow() - timedelta(hours=p['force_cycle_hour'])

    # Setup the file template dictionary now that we know what hour to get.
    file_template_values = {}
    add_file_template_time_values(file_template_values, ptimeutc)

    # Check to see if the remote directory actually exists

    if not is_url_valid(p['base_url'], p['remote_dir'].format(**file_template_values)):
        logging.warning(f"{p['remote_dir']} at {p['base_url']} is not available.")
    else:
        logging.info(f"{p['remote_dir']} at {p['base_url']} is available.")

    # ------------------------------------------------------------------
    # Download the data
    # ------------------------------------------------------------------
    downloaded_files = 0

    # loop over all forecast hours up to the maximum forecast hour.
    start_hour = 0
    end_hour = p['max_forecast_hour']
    hour_step = p['forecast_step']

    for fh in range(start_hour, end_hour + 1, hour_step):

        file_template_values["forecast_hour"] = fh
        file_template_values["forecast_minute"] = "00"

        # Remote file name
        remote_dir = p['remote_dir'].format(**file_template_values)
        remote_file = p['remote_filename'].format(**file_template_values)
        remote_path = os.path.join(remote_dir, remote_file)

        # Local file name
        local_dir = p['local_dir'].format(**file_template_values)
        local_file = p['local_filename'].format(**file_template_values)
        local_path = os.path.join(local_dir, local_file)

        logging.debug(f"foreast hour: {h}\tremote: {remote_path}\tlocal: {local_path}")

        safe_mkdirs(local_dir)

        # Check if the file is already available on the local disk
        remote_file_size = get_remote_file_size(remote_path)

        if is_local_file_good(local_path, remote_file_size):
            logging.debug(f"Already have good local file - {local_path}")
        else:

            get_remote_file(remote_dir, remote_file, local_dir, local_file)


            # Check if we got a good file
            if is_local_file_good(local_path, remote_file_size):

                # All is well. Tell the user
                downloaded_files += 1
                logging.debug(f"{local_path} successfully retrieved.")

                # Write latest_data_info and register
                # with data mapper if requested to do so
                if p['write_ldata']:
                    cmd = (f"LdataWriter -dir {local_dir} -rpath  {local_file} -dtype grib2 -lead {h * 60 * 60} "
                           f"-ltime {file_template_values['cycle_time']}0000 -maxDataTime")
                    run_cmd(cmd)

            else:
                logging.error(f"downloading {remote_path} failed !")
                cmd = f'rm -f {local_path}'
                run_cmd(cmd)

    logging.info(f"{os.path.basename(__file__)} completed succesfully.  Retrieved {downloaded_files} files.")
    close_connection()

if __name__ == '__main__':
    main()
