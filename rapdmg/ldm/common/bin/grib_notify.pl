#!/usr/bin/perl
#
# Simple script to run pqinsert to notify ADDS that model GRIB data
# has been received at RAP by LDM-CONDUIT feed and ADDS may now retrieve
# the files for their use.
# Author: Greg Thompson, 22 Mar 2005, updated 05 Oct 2007.
# Modified by Gary Cunning & Paul Prestopnik - added destination_dir argument 5-25-2006
#                                            - added -n option
use Getopt::Std;
use Time::Local;


($prog = $0) =~ s%.*/%%;                 # Determine program basename.
$| = 1;                                  # Unbuffer standard output.
umask 002;                               # Set file permissions.

# For debugging purposes, open a log file to send output from this script because
# LDM throws it into /dev/null
$todayDate = `date +%Y%m%d`;
$logDir = "/home/ldm/logs/" . $todayDate;
chomp($logDir);
if (!-d $logDir) {
    system("mkdir ".$logDir);
}


#initial pq_insert flag to default (true)
$pq_insert = 1;
$grib_ext = ".grb";
$writeLdata = 0;
$sleep_interval = 5;

#...------------...Usage Info...-----------------------

$usage = <<EOF;
Usage: $prog [-dhnL] [-p productId] status_file destination_dir
  -d  Print out debug information
  -h  Print out this usage information
  -L  Write an LdataInfo file  
  -2  Run on grib2 files (expects .grb2 for their extension)
  -n  Do not insert the status notification into product queue
  -p  set productId; otherwise, retrieved from status_file naming convention
      Status and GRIB filenames take form of:  20041104_i19_f001_RUC252p.status|grb
EOF
&getopts('dhnL2p:') || die $usage;
$debug = 1 if $opt_d;
$pq_insert = 0  if $opt_n;
$writeLdata = 1 if $opt_L;
$grib_ext = ".grb2" if $opt_2;
die $usage if $opt_h;
die $usage if $#ARGV < 0;

#...Get destination directory from arguments
$destination_dir = $ARGV[1];

#...From status filename, create GRIB filename.
$status_file = $ARGV[0];

($grib_file = $status_file) =~ s/\.status/$grib_ext/;
($gfile = $grib_file) =~ s%.*/%%;


#...From status filename, get date and model info.
($yyyy, $mm, $dd, $hh, $fff, $model) = $status_file =~ /(2[0-9]{3})([0-1][0-9])([0-3][0-9])_i([0-2][0-9])_f([0-9]{3}|xxxx)_(.*)\.status$/;


$logFile = $logDir."/grib_notify." . $model . "." . $hh . ".f" . $fff . "." . $$ . ".log";
open (LOGFILE, ">>",$logFile);

print LOGFILE "grib_file: $grib_file\n" if $debug;


#...Make certain status and GRIB files and destination dir exist.
if (!-e "$status_file"){
    print LOGFILE "Status file, $status_file, does not exist\n\n";
    die ("Status file, $status_file, does not exist\n\n");
}

if (!-e "$grib_file"){
    print LOGFILE "GRIB file, $grib_file, does not exist\n\n";
    die ("GRIB file, $grib_file, does not exist\n\n");
}
if (!-d "$destination_dir"){
    print LOGFILE "Destination dir, $destination_dir, does not exist\n\n";
    die ("Destination dir, $destination_dir, does not exist\n\n");
}

# massage date/time strings
$yyyymmdd = $yyyy . $mm . $dd;
$ddhh = $dd . $hh;
if ($fff eq 'xxxx') {
    $fhr = sprintf("%03d", 0);
} elsif ( ($fff*1) >= 100 ) {
    $fhr = sprintf("%03d", $fff*1);
} else {
    $fhr = sprintf("%02d", $fff*1);
}
$fsecs = $fff * 3600;

#...Command-line option may override productId from model name.


if ($opt_p) {
    $productId = $opt_p;
} else {
    $productId = $model;
}

$productDir = "$destination_dir/$productId";
mkdir ("$productDir") unless (-d "$productDir");

$final_dir = "$productDir/$yyyymmdd";
print LOGFILE "final_dir: $final_dir\n" if $debug;

mkdir ("$final_dir") unless (-d "$final_dir");

#...Open status file and retrieve supposed size (bytes) of GRIB file.

$numExpect = 0;
if (! open (SFILE, "$status_file")){
    print LOGFILE "Could not open $status_file\n$!\n\n";
    die ("Could not open $status_file\n$!\n\n");
    }
while (<SFILE>) {
    chop;
    if (/^Inserted\s+([0-9]+)\s+of\s+([0-9]+)/) {
        $numSoFar = $1;
        $numExpect = $2;
    }
}
close (SFILE);

if (! $numExpect)
{
    print LOGFILE "Status file, $status_file, does not contain the needed byte info.\n\n";
    die ("Status file, $status_file, does not contain the needed byte info.\n\n");
}

if ($numSoFar == $numExpect) {

    # Just because status file says all bytes shipped, does not mean we got them all yet so test file size
    # and only reach success when file size accumulates to advertised size, but quit after 15 min waiting.
    $grib_file_size = -s $grib_file;
    print LOGFILE "Comparing:  grib file size: $grib_file_size expected size: $numExpect\n";
    $file_done = ($grib_file_size >= $numExpect)? 1: 0;
    $sleep_total = 0;
    until ($file_done) {
        print LOGFILE "File $grib_file still being filled with data\n" if $debug;
        sleep $sleep_interval;
        $sleep_total = $sleep_total + $sleep_interval;
        $file_done = 1 if (-s "$grib_file" >= $numExpect);
	print LOGFILE "Current Size - " . -s "$grib_file\n" if $debug;
	if ($sleep_total > 900){
	    print LOGFILE "FAIL: never received advertised size of file, gave up waiting.\n";
	    die "FAIL: never received advertised size of file, gave up waiting.\n";
	}
    }
    #print LOGFILE "sleeping for 5 minutes\n" if $debug;
    #sleep(300);
    $productId = "\U$productId" unless ($opt_p);
    print LOGFILE "GRIB file, $grib_file, fully received.\n" if $debug;
    print LOGFILE "    moving to $final_dir/$gfile.\n" if $debug;
    ((system ("/bin/mv -f $grib_file $final_dir/$gfile") >> 8) == 0) || print LOGFILE "SYSTEM: mv failed.\n$!\n\n";

    # what is this doing?  These temp files never get cleaned up and now there a million of them hanging around...
    # why not just put this info right into the log?
    $now = time();
    $temp_file = "/tmp/grib_notify_$productId.$$.tmp";
    unlink ("$temp_file") if (-e "$temp_file");
    if (! open (TMP, ">$temp_file")){
	print LOGFILE "Cannot open $temp_file\n$!\n\n";
	die ("Cannot open $temp_file\n$!\n\n");
    }
    print TMP "$status_file $now\n";
    close (TMP);

    
    my ($S,$M,$H,$d,$m,$Y) = localtime($now);
    $m += 1;
    $y += 1900;
    my $dt = sprintf("%04d-%02d-%02d %02d:%02d:%02d", $Y,$m,$d, $H,$M,$S);
    print LOGFILE "statusfile,now: $status_file $dt\n";

    # log destination directory listing to verify file got there
    my $cmd = "ls -l $final_dir";
    my $dirls = `$cmd`;
    print LOGFILE "running cmd: $cmd";
    print LOGFILE $dirls;

    if ($writeLdata == 1) {
	$ext = substr($grib_file, rindex($grib_file, ".")+1);
	$cmd = "LdataWriter -dir $productDir -rpath ${yyyymmdd}/${gfile} -ltime ${yyyymmdd}${hh}0000 -lead $fsecs -ext $ext -writer ldm";
	((system("$cmd") >> 8) == 0) || print LOGFILE "SYSTEM: $cmd failed.\n$!\n\n";
    }

    if ($pq_insert == 1) {
        $cmd = "pqinsert -l /home/ldm/logs/grib_notify.log -p \"GRIB AVAL ${ddhh}00 GRIB $productId $fhr\" -f OTHER $temp_file";
        print LOGFILE "Will run pqinsert to notify downstream users.\n  ($cmd) ... \n" if $debug;
        ((system("$cmd") >> 8) == 0) || print LOGFILE "SYSTEM: $cmd failed.\n$!\n\n";
    }

} else {

    print LOGFILE "Warning: NCEP status file indicates INCOMPLETE shipment of $numSoFar out of $numExpect bytes over LDM-CONDUIT.\n" if $debug;

}

print LOGFILE "done, exiting $prog\n" if $debug;
close (LOGFILE);

exit 0;
