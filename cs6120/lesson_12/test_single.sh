#!/bin/bash

if [ $# -lt 1 ]; then
  echo "Usage: $0 <bril_file> [args...]"
  exit 1
fi

bril_file="$1"
shift
args="$@"

bril2json < "$bril_file" | brili2 -p $args > trace
bril2json < "$bril_file" > prog
python cs6120/lesson_12/trace.py prog trace new_prog
brili -p $args < prog
brili -p $args < new_prog
bril2txt < new_prog