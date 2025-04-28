#!/bin/bash

if [ $# -lt 1 ]; then
  echo "Usage: $0 <bril_file> [args...]"
  exit 1
fi

bril_file="$1"
shift
while IFS= read -r line; do
    if echo "$line" | grep -q "^# ARGS:"; then
        args=$(echo "$line" | sed 's/^# ARGS: //')
        break
    elif echo "$line" | grep -q "^#ARGS:"; then
        args=$(echo "$line" | sed 's/^#ARGS: //')
        break
    fi
done < "$bril_file"

bril2json < "$bril_file" | brili -p $args 2>/dev/null 
bril2json < "$bril_file" | python cs6120/final/gvn.py | brili -p $args 2>/dev/null