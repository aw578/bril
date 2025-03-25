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

  # licm_output=$(bril2json < "$f" | python cs6120/lesson_8/licm.py | bril2txt)
  # echo "$licm_output"
   # output comparison
  output1=$(bril2json < "$f" | brili -p $args 2>/dev/null)    
  output2=$(bril2json < "$f" | python cs6120/lesson_8/licm.py | brili -p $args 2>/dev/null)  
  if [ "$output1" != "$output2" ]; then
      echo "FAIL (out) $f $output1 $output2"
  fi
done