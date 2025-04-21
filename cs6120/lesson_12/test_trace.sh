#!/bin/sh

for f in benchmarks/core/*.bril; do
  echo "$f"
  args=""

  # Extract arguments from the file
  while IFS= read -r line; do
    if echo "$line" | grep -q "^# ARGS:"; then
      args=$(echo "$line" | sed 's/^# ARGS: //')
      break
    elif echo "$line" | grep -q "^#ARGS:"; then
      args=$(echo "$line" | sed 's/^#ARGS: //')
      break
    fi
  done < "$f"

  # Prepare files
  bril2json < "$f" 2>/dev/null | brili2 -p $args 2>/dev/null > trace
  bril2json < "$f" 2>/dev/null > prog
  python cs6120/lesson_12/trace.py prog trace new_prog 2>/dev/null

  # Run with original args
  output_new_prog=$(brili -p $args < new_prog 2>/dev/null)
  output_prog=$(brili -p $args < prog 2>/dev/null)
  if [ "$output_new_prog" != "$output_prog" ]; then
    echo "FAIL (orig args) $f"
    echo "new_prog: $output_new_prog"
    echo "prog: $output_prog"
  fi

  # Decrement each arg by 1 if it's a number
  new_args=""
  for arg in $args; do
    if echo "$arg" | grep -Eq '^-?[0-9]+$'; then
      new_args="$new_args $((arg - 1))"
    else
      new_args="$new_args $arg"
    fi
  done
  new_args=$(echo $new_args)

  output_new_prog_dec=$(cat new_prog | python cs6120/lesson_3/lvn.py | python cs6120/lesson_3/dce.py | brili -p $new_args)
  output_prog_dec=$(cat prog | python cs6120/lesson_3/lvn.py | python cs6120/lesson_3/dce.py | brili -p $new_args)
  if [ "$output_new_prog_dec" != "$output_prog_dec" ]; then
    echo "FAIL (decremented args) $f"
    echo "new_prog: $output_new_prog_dec"
    echo "prog: $output_prog_dec"
  fi
done