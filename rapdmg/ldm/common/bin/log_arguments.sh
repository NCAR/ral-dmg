#!/bin/bash

# usage:
#   ./log_arguments.sh LOG_DIR PROCESS [additional arguments]

echo "${@:3}" |& /rap/bin/LogFilter -d $1 -p $2  


