#!/bin/bash

if [ $# -lt 1 ]; then
  echo "Usage: $0 <bril_file> [args...]"
  exit 1
fi

bril_file="$1"
shift
args="$@"

bril2json < "$bril_file" | brili2 -p $args 2>/dev/null > trace
bril2json < "$bril_file" > prog
python cs6120/lesson_12/trace.py prog trace new_prog
cat prog | python cs6120/lesson_3/lvn.py | python cs6120/lesson_3/dce.py | brili -p $args
cat new_prog | python cs6120/lesson_3/lvn.py | python cs6120/lesson_3/dce.py | brili -p $args
# bril2txt < new_prog