#!/bin/bash
TIMELIMIT=$1
MEMORY=$2
FILE=$3
cd tmp/


ulimit -v $MEMORY
timeout $TIMELIMIT ./$FILE > /dev/null 
