#!/usr/bin/perl
#
# Simple script to run pqinsert to notify ADDS or Greg T. that model GRIB data
# has been received at RAP and may now be retrieved for their use.

# This script fakes the process that happened for model data retrieved via LDM.

# Author: Paul Prestopnik, May 24, 2012

use Getopt::Std;
use Time::Local;
use File::Spec;

($prog = $0) =~ s%.*/%%;                 # Determine program basename.
$| = 1;                                  # Unbuffer standard output.
umask 002;                               # Set file permissions.



#...------------...Usage Info...-----------------------

$usage = <<EOF;
Usage: $prog [-dh] model_file
  -d  Print out debug information
  -h  Print out this usage information
EOF

# product ID is  retrieved from status_file naming convention
#      Status and GRIB filenames take form of:  20041104_i19_f001_RUC252p.status|grb

&getopts('dh') || die $usage;
$debug = 1 if $opt_d;
die $usage if $opt_h;
die $usage if $#ARGV < 0;

$debug = 1;

# For debugging purposes, open a log file to send output from this script
$todayDate = `date +%Y%m%d`;
$logDir = "/home/ldm/logs/" . $todayDate;
chomp($logDir);
if (!-d $logDir) {
    system("mkdir ".$logDir);
}

$logFile = $logDir."/" . $prog . ".log";
open (LOGFILE, ">>",$logFile);
print LOGFILE "$prog called with @ARGV \n";


#...split input arg, to get GRIB file & path 
$model_filepath = $ARGV[0];
print LOGFILE "model_filepath: $model_filepath\n" if $debug;
($volume,$model_dir,$model_file) = File::Spec->splitpath($model_filepath);
print LOGFILE "model_dir: $model_dir\n" if $debug;
print LOGFILE "model_file: $model_file\n" if $debug;


# WRF-RR-NCO-130-bgrb/
# WRF-RR-NCO-130-pgrb/
if ($model_dir =~ m/WRF-RR-NCO-130-pgrb/){
    $productId = "RAP130P"
}
if ($model_dir =~ m/WRF-RR-NCO-130-bgrb/){
    $productId = "RAP130N"
}
if ($model_dir =~ m/HRRR-wrfprs/){
    $productId = "HRRR-wrfprs"
}
if ($model_dir =~ m/HRRR-wrfnat/){
    $productId = "HRRR-wrfnat"	
}
if ($model_dir =~ m/HRRR-NCEP-wrfprs/){
    $productId = "HRRR-NCEP-wrfprs"
}
if ($model_dir =~ m/HRRR-NCEP-wrfnat/){
    $productId = "HRRR-NCEP-wrfnat"
}



print LOGFILE "prouctID: $productId\n" if $debug;



#...Make certain  GRIB file exists.

if (!-e "$model_filepath"){
    print LOGFILE "GRIB file, $model_filepath, does not exist\n\n";
    close (LOGFILE);
    die ("GRIB file, $model_filepath, does not exist\n\n");
}

#...From  filename, get date and model info.
# 20160318_i20_f002_HRRR.grb2
# 20120524_i21_f017_WRF-RR-NCO.grb2
($yyyy, $mm, $dd, $hh, $fff, $model) = $model_file =~ /(2[0-9]{3})([0-1][0-9])([0-3][0-9])_i([0-2][0-9])_f([0-9]{3})_(.*)\.grb2/;
$yyyymmdd = $yyyy . $mm . $dd;
$ddhh = $dd . $hh;

if ( ($fff*1) >= 100 ) {
    $fhr = sprintf("%03d", $fff*1);
} else {
    $fhr = sprintf("%02d", $fff*1);
}
$fsecs = $fff * 3600;


#create fake status file:
# 20120524_i12_f003_NAM218.status 
# data/nccf/com/nam/prod/nam.20120524/nam.t12z.awip1203.tm00.grib2 complete (16788348 bytes) at Thu May 24 13:43:45 2012
# Inserted 16788348 of 16788348
 
$tmpDir = "/home/ldm/tmp";
chomp($tmpDir);
if (!-d $tmpDir) {
    system("mkdir ".$tmpDir);
}

$temp_filepath = $tmpDir . "/" . $productId . ".tmp";

$now = time();
unlink ("$temp_filepath") if (-e "$temp_filepath");

if (! open (TMPFILE, ">$temp_filepath")){
    print LOGFILE "Cannot open $temp_filepath\n$!\n\n";
    die ("Cannot open $temp_filepath\n$!\n\n");
}

# Change from this:
# /rapdmg1/data/grib/WRF-RR-NCO-130-pgrb/20120525/20120525_i16_f018_WRF-RR-NCO.grb2
# to this:
# /rapdmg1/data/grib/tmp/WRF-RR-NCO-130-pgrb/20120525/20120525_i16_f018_WRF-RR-NCO.status

$model_filepath =~ m/(.*)grib(.*)grb2/;
$fakePath = $1 . "grib/tmp" . $2 . "status";

print LOGFILE "fakePath: $fakePath\n" if $debug;

print TMPFILE "$fakePath $now\n";
close (TMPFILE);


# do pqinsert
$cmd = "pqinsert -l /home/ldm/logs/pqinsertNotify.log -p \"GRIB AVAL ${ddhh}00 GRIB $productId $fhr\" -f OTHER $temp_filepath";
print LOGFILE "Will run pqinsert to notify downstream users.\n  ($cmd) ... " if $debug;
((system("$cmd") >> 8) == 0) || warn "SYSTEM: $cmd failed.\n$!\n\n";


print LOGFILE "done, exiting $prog\n" if $debug;
close (LOGFILE);

exit 0;
