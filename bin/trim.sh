#!/bin/bash
F1=$1
F2=$2
cd tmp
perl -pi -e 's/^[\ \t]+|[\ \t]+$//g' $F1
perl -pi -e 's/^[\ \t]+|[\ \t]+$//g' $F2

perl -p -i -e 's/[\n\r\R\Zl]//g;' $F1
perl -p -i -e 's/[\n\r\R\Zl]//g;' $F2
