#!/bin/bash
EXT=$1
cd tmp/
if [ "$EXT" == "pas" ]; then
	fpc -Xs file.pas 2>&1 >/dev/null
fi
if [ "$EXT" == "c" ]; then
	g++ -Wall -O2 -static -o file file.c 2>&1 >/dev/null
fi
if [ "$EXT" == "cpp" ]; then
	g++ -Wall -O2 -static -o file file.cpp 2>&1 >/dev/null
fi

if [ -f file ]; then
	REZ="0"
else
	REZ="1"
fi;
echo $REZ