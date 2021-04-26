#!/usr/bin/env python3
"""
smartDownloadModels.py downloads model data via curl.
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

from remote_dir_listing import RemoteDirListing

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


######################################################################################################
####    MODEL CONFIGURATION
######################################################################################################

# model_type is the model to download.  
#   valid: 'rffs_gsl_bgdawp_conus', 'rffs_gsl_bgrd3d_conus', 'rffs_gsl_bgsfc_conus', 
#          'rffs_gsl_bgdawp_ak', 'rffs_gsl_bgrd3d_ak', 'rffs_gsl_bgsfc_ak'

# If you set this via the cmd line, then other parameter values will be set based on model_type 
# (see _config_overide below), but parameters set on the command line take final precedence. 

# You do not need to use this configuration parameter at all.  It can be left an empty string and just set other values individually.
model_type = ""
# model_type.valid_values = ["rffs_gsl_bgdawp_conus", "rffs_gsl_bgrd3d_conus", "rffs_gsl_bgsfc_conus", 
#                             "rffs_gsl_bgdawp_ak", "rffs_gsl_bgrd3d_ak", "rffs_gsl_bgsfc_ak", "gfs0.5", "nam212"]

# look_back_hours is the maximum look back period. You can use this to determine how far back in time this script will look for data.
# i.e. if you set this to 12 it will start with the present time, and then look back an hour at a time
#      for a model run that you don't already have locally, and work it's way to the max look_back_hours.

look_back_max_hours = 24 

# for realtime model retrieval - set this to the lag between generation time & model availability 
look_back_start_hour = 1




# If force_cycle_hour >= 0, then the download script attempts to get data for that specific cycle hour
# this overrides look_back_hours
force_cycle_hour = -1


# the maximum forecast hour to download
max_forecast_hour = 36


# the step between forecast hours to be downloaded (only suppports integers)
#  If this is > 1, forecast hours will only be used if the modulus of the forecast hour and this value is zero.
forecast_step = 1


# the step between generation hours to be downloaded (only suppports integers)
#  If this is > 1, generations hours will only be used if the modulus of the generation hour and this value is zero.
gen_step = 6


################################################################################
####     CONNECTION CONFIGURATION
################################################################################
# location of the model data (url accessible via ftp or http)
base_url = 'ftp://gsdftp.fsl.noaa.gov'

# using curl for everything now.
# valid values: 'ftp' or 'http'
# retrieval_protocol = 'ftp' 


# username and password if authentication is required
# only used by ftp - not supported yet by http.
auth_user = 'ftp'
auth_pass = 'cowie@ucar.edu'

# When set to a positive number, the script will exit once this # of successful downloads have been achieved.
max_downloads = -1

# how long to sleep between url requests  (in seconds)
request_sleep = 1


# should we write an Ldata file?
write_ldata = True

ldata_dtype = "grib2"

# connection will retry until this number of errors reached.
max_errors = 6

########################################################################################################################
####    FILE AND DIRECTORY CONFIGURATION
########################################################################################################################


# You can use some various replacement field templates in these parameters
#   {cycle_year}         --- YYYY
#   {cycle_2year}        --- YY
#   {cycle_month}        --- MM
#   {cycle_day}          --- DD
#   {cycle_julian_day}   --- JJJ
#   {cycle_date}         --- YYYYMMDD
#   {cycle_time}         --- YYYYMMDDHH
#   {cycle_hour}         --- HH
#   {cycle_minute}       --- MM

#####  -- forecast fields are stored as integers, so you should specify a format specifier:
#   {forecast_hour}      --- h (lead) need to specify # of digits use e.g. {forecast_hour:03d} for 3 digit leading zeros
#   {forecast_minute}      --- m (lead) need to specify # of digits use e.g. {forecast_minute:02d} for 2 digit leading zeros

# NOTE: Currently cycle_minute and forecast_minute are forced to zero.  i.e. sub hourly times not currently supported.

# 2100412002300 
# YYJJJHHMMHHMM
# 2-digit year (21), julian day (004), gen hour/minutes (1200), forecast lead hour/minutes (2300)

# RFFS-CONUS-bgdawp/GSL/20210104/20210104_i12_f023_RFFS-CONUS-bgdawp_GSL.grib2

remote_filename = "{cycle_year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
local_filename = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_GSL_RFFS-CONUS-bgdwawp.grib2"        


# remote dir is *relative* and is appended to base_url 
remote_dir = "data/nccf/com/gfs/prod/gfs.{cycle_date}/{cycle_hour}"


#  local file = local_base_dir + local_dir + local_filename
# If write_ldata is true, ldata files are placed in local_base_dir, and -rpath is local_dir/local_filename
local_base_dir = "/rapdmg2/data/grib/"
local_dir = "{cycle_date}"


# if downloaded files are smaller than this, an error is assumed to have occurred.
# Set to a negative number to disable this check.
min_expected_filesize = 500e+6  # 500M



####################################################################################################################
####    COMMAND LINE OVERRIDES - These allow the user to set just one thing on the cmd line (i.e. model_type), and change several dependent values.
####################################################################################################################
# 
# If you set model_type to something on the command line then the _config_override values (below) 
# will override with values that make sense for other models.

########## RFFS #############

_config_override["model_type"]["rffs_gsl_bgdawp_conus"]["min_expected_filesize"] = 5e+6 # 5M
_config_override["model_type"]["rffs_gsl_bgdawp_conus"]["remote_dir"] = '/rrfs_dev1/conus/bgdawp'
_config_override["model_type"]["rffs_gsl_bgdawp_conus"]["remote_filename"] = "{cycle_2year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
_config_override["model_type"]["rffs_gsl_bgdawp_conus"]["local_base_dir"] = "/rapdmg2/data/grib/RRFS/GSL/CONUS/bgdawp"
_config_override["model_type"]["rffs_gsl_bgdawp_conus"]["local_filename"] = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_GSL_RFFS-CONUS-bgdwawp.grib2"        

_config_override["model_type"]["rffs_gsl_bgrd3d_conus"]["min_expected_filesize"] = 5e+6 # 5M
_config_override["model_type"]["rffs_gsl_bgrd3d_conus"]["remote_dir"] = '/rrfs_dev1/conus/bgrd3d'
_config_override["model_type"]["rffs_gsl_bgrd3d_conus"]["remote_filename"] = "{cycle_2year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
_config_override["model_type"]["rffs_gsl_bgrd3d_conus"]["local_base_dir"] = "/rapdmg2/data/grib/RRFS/GSL/CONUS/bgrd3d"
_config_override["model_type"]["rffs_gsl_bgrd3d_conus"]["local_filename"] = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_GSL_RFFS-CONUS-bgrd3d.grib2"        

_config_override["model_type"]["rffs_gsl_bgsfc_conus"]["min_expected_filesize"] = 3e+5 # 300k
_config_override["model_type"]["rffs_gsl_bgsfc_conus"]["remote_dir"] = '/rrfs_dev1/conus/bgsfc'
_config_override["model_type"]["rffs_gsl_bgsfc_conus"]["remote_filename"] = "{cycle_2year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
_config_override["model_type"]["rffs_gsl_bgsfc_conus"]["local_base_dir"] = "/rapdmg2/data/grib/RRFS/GSL/CONUS/bgsfc"
_config_override["model_type"]["rffs_gsl_bgsfc_conus"]["local_filename"] = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_GSL_RFFS-CONUS-bgsfc.grib2"        


_config_override["model_type"]["rffs_gsl_bgdawp_ak"]["min_expected_filesize"] = 2e+6 # 2M
_config_override["model_type"]["rffs_gsl_bgdawp_ak"]["remote_dir"] = '/rrfs_dev1/alaska/bgdawp'
_config_override["model_type"]["rffs_gsl_bgdawp_ak"]["remote_filename"] = "{cycle_2year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
_config_override["model_type"]["rffs_gsl_bgdawp_ak"]["local_base_dir"] = "/rapdmg2/data/grib/RRFS/GSL/AK/bgdawp"
_config_override["model_type"]["rffs_gsl_bgdawp_ak"]["local_filename"] = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_GSL_RFFS-AK-bgdwawp.grib2"        

_config_override["model_type"]["rffs_gsl_bgrd3d_ak"]["min_expected_filesize"] = 2e+6 # 2M
_config_override["model_type"]["rffs_gsl_bgrd3d_ak"]["remote_dir"] = '/rrfs_dev1/alaska/bgrd3d'
_config_override["model_type"]["rffs_gsl_bgrd3d_ak"]["remote_filename"] = "{cycle_2year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
_config_override["model_type"]["rffs_gsl_bgrd3d_ak"]["local_base_dir"] = "/rapdmg2/data/grib/RRFS/GSL/AK/bgrd3d"
_config_override["model_type"]["rffs_gsl_bgrd3d_ak"]["local_filename"] = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_GSL_RFFS-AK-bgrd3d.grib2"        

_config_override["model_type"]["rffs_gsl_bgsfc_ak"]["min_expected_filesize"] = 1e+5 # 100k
_config_override["model_type"]["rffs_gsl_bgsfc_ak"]["remote_dir"] = '/rrfs_dev1/alaska/bgsfc'
_config_override["model_type"]["rffs_gsl_bgsfc_ak"]["remote_filename"] = "{cycle_2year}{cycle_julian_day}{cycle_hour}00{forecast_hour:02d}00"
_config_override["model_type"]["rffs_gsl_bgsfc_ak"]["local_base_dir"] = "/rapdmg2/data/grib/RRFS/GSL/AK/bgsfc"
_config_override["model_type"]["rffs_gsl_bgsfc_ak"]["local_filename"] = "{cycle_date}_i{cycle_hour}_{cycle_minute}_f{forecast_hour:03d}_{forecast_minute:02d}_GSL_RFFS-AK-bgsfc.grib2"        


########## GFS  ################

_config_override["model_type"]["GFS0.5"]["local_filename"] = "{cycle_time}_fh.{forecast_hour:04d}_tl.press_gr.1p0deg.grib2"          
_config_override["model_type"]["GFS0.5"]["remote_filename"] = "gfs.t{cycle_hour}z.pgrb2.1p00.f{forecast_hour:03d}"
_config_override["model_type"]["GFS0.5"]["retrieval_protocal"] = "http"

######### NAM  ################
#           nam.t12z.awip3d36.tm00.grib2       
# 20210423_i06_f030_NAM212.grb2
_config_override["model_type"]["NAM212"]["base_url"] = "https://ftpprd.ncep.noaa.gov"
_config_override["model_type"]["NAM212"]["remote_filename"] = "nam.t{cycle_hour}z.awip3d{forecast_hour:02d}.tm00.grib2"
_config_override["model_type"]["NAM212"]["local_filename"] = "{cycle_date}_i{cycle_hour}_f{forecast_hour:03d}_NAM212.grb2"        

# remote dir is *relative* and is appended to base_url 
_config_override["model_type"]["NAM212"]["remote_dir"] = "/data/nccf/com/nam/prod/nam.{cycle_date}/"

_config_override["model_type"]["NAM212"]["local_base_dir"] = "/rapdmg1/data/grib/NAM212"





########################## testing validation stuff ###############
#_config_valid_values["model_type"] = ["rffs_gsl_bgdawp_conus", "rffs_gsl_bgrd3d_conus", "rffs_gsl_bgsfc_conus", "rffs_gsl_bgdawp_ak", "rffs_gsl_bgrd3d_ak", "rffs_gsl_bgsfc_ak", "GFS0.5"]

#def validate(key, value):
#  if key == "model_type":
#      return value in  ["rffs_gsl_bgdawp_conus", "rffs_gsl_bgrd3d_conus", "rffs_gsl_bgsfc_conus", "rffs_gsl_bgdawp_ak", "rffs_gsl_bgrd3d_ak", "rffs_gsl_bgsfc_ak", "GFS0.5"]


#test = {}
#test["this"] = "that"

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
    # p['retrieval_protocol'] = p['retrieval_protocol'].lower()

    if p['max_errors'] < 1:
        p['max_errors'] = 6
    p['_total_errors'] = 0


def check_params():
    valid_models = ["rffs_gsl_bgdawp_conus", "rffs_gsl_bgrd3d_conus", "rffs_gsl_bgsfc_conus", "rffs_gsl_bgdawp_ak",
                    "rffs_gsl_bgrd3d_ak", "rffs_gsl_bgsfc_ak", "gfs0.5", "nam212"]
    if p['model_type'] not in valid_models:
        logging.fatal(f"model_type ({p['model_type']} is not supported.  Must be one of {valid_models}")
        sys.exit(1)
    '''
    retrieval_values = ['ftp', 'http']
    if p['retrieval_protocol'] not in retrieval_values:
        logging.fatal(f"retrieval_protocol ({p['retrieval_protocol']} is not supported.  Must be one of {retrieval_values}")
        sys.exit(1)
    '''


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
    logging.info(f"sleeping: {p['request_sleep']} (before is_url_valid)")
    time.sleep(p['request_sleep'])

    if p['retrieval_protocol'] == 'http':
        try:
            url_dir = url_join(base_url, remote_dir)
            ret = urllib.request.urlopen(url_dir)
            ret.close()
        except urllib.error.URLError as e:
            return False
        return True

    if p['retrieval_protocol'] == 'ftp':
        try:
            p['_ftp'].cwd(remote_dir)  # change into "debian" directory
        except ftplib.error_perm as e:
            return False
        return True

    # This really only works if the data is organized into hourly directories...
    #   Maybe we should just skip this, and work backwards from present time if an hour is not
    #   explicitly given.

    # NOT BEING USED FOR ABOVE REASONS


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
    file_template_values["cycle_2year"] = dt.strftime('%y')
    file_template_values["cycle_month"] = dt.strftime('%m')
    file_template_values["cycle_hour"] = dt.strftime('%H')
    file_template_values["cycle_minute"] = dt.strftime('%M')
    file_template_values["cycle_time"] = file_template_values["cycle_date"] + file_template_values["cycle_hour"]
    file_template_values["cycle_day"] = dt.strftime('%d')
    file_template_values["cycle_julian_day"] = dt.strftime('%j')


def connection_error():
    p['_total_errors'] += 1
    p['request_sleep'] *= 1.5

    if p['_total_errors'] > p['max_errors']:
        logging.error(f"maximum errors reached: {p['max_errors']}")
        sys.exit(0)


def is_local_file_good(local_path, remote_file_size):
    """
    Check if the file is already available on the local disk and if the size is right
    :param local_path:
    :param remote_file_size:
        if less than zero, this check is skipped, but we still check against min expected file size
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

    if remote_file_size > 0:
        return local_file_size == remote_file_size
    else:
        return True

# return -1 on failure
def get_remote_file_size(remote_path):
    logging.info(f"sleeping: {p['request_sleep']} (before get_remote_file_size)")
    time.sleep(p['request_sleep'])

    try:
        if p["retrieval_protocol"] == 'http':
            # Get the remote size
            ret = urllib.request.urlopen(remote_path)
            file_size_at_server = int(ret.info().get('content-length', '0'))
            ret.close()
            return file_size_at_server

        if p["retrieval_protocol"] == 'ftp':
            return p["_ftp"].size(remote_path)
    except:
        logging.debug("file size retrieval failed.")
        return -1


def safe_mkdirs(d):
    if not os.path.exists(d):
        logging.info(f"making dir: {d}")
        os.makedirs(d, 0o777, exist_ok=True)


def print_params():
    logging.info(f"Using these parameters:")
    for line in p.getParamsString().splitlines():
        logging.info(f"\t{line}")


def get_remote_file(remote_dir, remote_file, local_dir, local_file):
    remote_path = os.path.join(remote_dir, remote_file)
    local_path = os.path.join(local_dir, local_file)

    cmd = f"rm -f {local_path}"
    run_cmd(cmd)

    logging.info(f"sleeping: {p['request_sleep']} (before get_remote_file)")
    time.sleep(p['request_sleep'])
    # File wasn't the right size or wasn't there. Either way
    # it isn't there now. Get the file.
    logging.info(f"downloading {remote_path} to {local_path}")

    curl_args = url_join(p['base_url'],remote_path)

    if p["auth_user"] or p["auth_pass"]:
        curl_args = f"-u \"{p['auth_user']}:{p['auth_pass']}\" {curl_args}"

    curl_args = f"{curl_args} -o {local_path}"
    cmd = f"curl {curl_args}"
    run_cmd(cmd)

def initiate_connection():
    if p['retrieval_protocol'] == 'ftp':
        logging.info(f"Connecting to {p['base_url']}")
        # logging.debug(f"Using <{p['auth_user']}>, <{p['auth_pass']}>")
        p['_ftp'] = ftplib.FTP(host=p['base_url'], user=p['auth_user'],
                               passwd=p['auth_pass'])  # connect to host, default port


def close_connection():
    if p['retrieval_protocol'] == 'ftp':
        p['_ftp'].quit()


def build_rdl_arguments(current_cycle):
    file_template_values = {}
    add_file_template_time_values(file_template_values, current_cycle)

    args = url_join(p['base_url'], p['remote_dir'].format(**file_template_values))

    if p["auth_user"] or p["auth_pass"]:
        args = f"-u \"{p['auth_user']}:{p['auth_pass']}\" {args}"

    return args


def get_remote_file_list(current_cycle):
    # get the remote directory listing for this cycle
    rdl = RemoteDirListing()
    curl_args = build_rdl_arguments(current_cycle=current_cycle)
    # rdl.store_dir_listing("-u \"ftp:cowie@ucar.edu\" ftp://gsdftp.fsl.noaa.gov/rrfs_dev1/conus/bgsfc/")

    rdl.store_dir_listing(curl_args)

    # TODO: we could be smarter about if we've already made a remote dir listing of the same dir.
    #       But I think we'd want to make a single rdl in main(), and pass it here?  Or convert entire thing to a class.
    return rdl.files


def main():
    condition_params()
    check_params()
    print_params()

    #initiate_connection()

    # determine earliest and latest cycles to get
    latest_cycle_to_get = datetime.utcnow()

    if p['force_cycle_hour'] >= 0:
        if latest_cycle_to_get.hour < p['force_cycle_hour']:
            latest_cycle_to_get -= timedelta(days=1)
        latest_cycle_to_get = latest_cycle_to_get.replace(hour=p['force_cycle_hour'])
        earliest_cycle_to_get = latest_cycle_to_get

    else:
        latest_cycle_to_get -= timedelta(hours=p["look_back_max_hours"])
        earliest_cycle_to_get = latest_cycle_to_get - timedelta(hours=p["look_back_max_hours"])

    downloaded_files = 0
    earliest_cycle_to_get = earliest_cycle_to_get.replace(minute=0, second=0, microsecond=0)
    latest_cycle_to_get = latest_cycle_to_get.replace(minute=0, second=0, microsecond=0)
    current_cycle = latest_cycle_to_get
    logging.debug(f"attempting retrieval from {latest_cycle_to_get} back to {earliest_cycle_to_get}")
    while current_cycle >= earliest_cycle_to_get:

        logging.debug(f"considering model cycle - {current_cycle}")
        gen_hour = current_cycle.hour
        if not gen_hour % p['gen_step'] == 0:
            current_cycle -= timedelta(hours=1)
            logging.debug(f"skipping cycle - {current_cycle}, hour {gen_hour} is not a modulus of gen_step ({p['gen_step']})")
            continue

        # Setup the file template dictionary now that we know what hour to get.
        file_template_values = {}
        add_file_template_time_values(file_template_values, current_cycle)

        # get the remote directory listing for this cycle
        remote_files = get_remote_file_list(current_cycle)

        # Check to see if the remote directory actually exists
        # TODO: if the directory doesn't have an hour in it, we should just do this once, not every loop
        # TODO: commented out for now, because without a check for dir, we are just pinging the server needlessly
        # if not is_url_valid(p['base_url'], p['remote_dir'].format(**file_template_values)):
        #    logging.warning(f"{p['remote_dir']} at {p['base_url']} is not available.")
        #    continue
        # else:
        #    logging.info(f"{p['remote_dir']} at {p['base_url']} is available.")

        # ------------------------------------------------------------------
        # Download the data
        # ------------------------------------------------------------------

        # loop over all forecast hours up to the maximum forecast hour.
        start_hour = 0
        end_hour = p['max_forecast_hour']
        hour_step = p['forecast_step']

        for fh in range(start_hour, end_hour + 1):

            if not fh % hour_step == 0:
                continue

            if p["max_downloads"] > 0 and downloaded_files >= p["max_downloads"]:
                continue

            file_template_values["forecast_hour"] = fh
            file_template_values["forecast_minute"] = 0

            # Remote file
            remote_dir = p['remote_dir'].format(**file_template_values)
            remote_file = p['remote_filename'].format(**file_template_values)
            remote_path = os.path.join(remote_dir, remote_file)

            if remote_file not in remote_files:
                logging.info(f"{remote_file} not yet available on the server")
                continue

            # Local file
            local_base_dir = p['local_base_dir'].format(**file_template_values)
            local_dir = p['local_dir'].format(**file_template_values)
            local_full_dir = os.path.join(local_base_dir, local_dir)
            local_file = p['local_filename'].format(**file_template_values)
            local_path = os.path.join(local_full_dir, local_file)

            logging.verbose(f"foreast hour: {fh}\tremote: {remote_path}\tlocal: {local_path}")

            safe_mkdirs(local_full_dir)

            # Check if the file is already available on the local disk

            # TODO - not doing remote file sizes -
            #      - could add it back, although http retrieval only has approximate size
            #remote_file_size = get_remote_file_size(remote_path)
            #logging.verbose(f"Remote File Size: {remote_file_size}")
            #if remote_file_size < 0:
            #    logging.debug(f"Couldn't get remote file size for {remote_path}, moving to next file.")
            #    continue

            remote_file_size = -1 # force skip this check

            if is_local_file_good(local_path, remote_file_size):
                logging.debug(f"Already have good local file - {local_path}")
            else:

                get_remote_file(remote_dir, remote_file, local_full_dir, local_file)

                # Check if we got a good file
                if is_local_file_good(local_path, remote_file_size):

                    # All is well. Tell the user
                    downloaded_files += 1
                    logging.info(f"{local_path} successfully retrieved.")

                    # Write latest_data_info if requested to do so
                    if p['write_ldata']:
                        cmd = (
                            f"LdataWriter -dir {local_base_dir} -rpath  {os.path.join(local_dir, local_file)}"
                             f" -dtype {p['ldata_dtype']} -lead {fh * 60 * 60}"
                            f" -ltime {current_cycle.strftime('%Y%m%d%H%M00')} -maxDataTime")
                        run_cmd(cmd)

                else:
                    logging.error(f"downloading {remote_path} failed !")
                    cmd = f'rm -f {local_path}'
                    run_cmd(cmd)
        current_cycle -= timedelta(hours=1)

    logging.info(f"{os.path.basename(__file__)} completed succesfully.  Retrieved {downloaded_files} files.")
    #close_connection()


if __name__ == '__main__':
    main()
