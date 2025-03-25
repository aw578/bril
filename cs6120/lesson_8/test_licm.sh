#!/bin/sh

total_dyn_inst1=0
total_dyn_inst2=0

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

  # Output comparison
  output1=$(bril2json < "$f" | brili -p $args 2>/dev/null)    
  output2=$(bril2json < "$f" | python cs6120/lesson_8/licm.py | brili -p $args 2>/dev/null)  
  if [ "$output1" != "$output2" ]; then
      echo "FAIL (out) $f $output1 $output2"
  fi

  
  total_inst1=$(bril2json < "$f" | brili -p $args 2>&1 > /dev/null | grep -oP '(?<=total_dyn_inst: )\d+')    
  total_inst2=$(bril2json < "$f" | python cs6120/lesson_8/licm.py | brili -p $args 2>&1 > /dev/null | grep -oP '(?<=total_dyn_inst: )\d+')     
  if [ "$total_inst1" -lt "$total_inst2" ]; then
      echo "FAIL (ins) $f $total_inst1 $total_inst2"
  fi
  total_dyn_inst1=$((total_dyn_inst1 + total_inst1))
  total_dyn_inst2=$((total_dyn_inst2 + total_inst2))
done

# Print the totals
echo "Total dynamic instructions for original: $total_dyn_inst1"
echo "Total dynamic instructions for reduced: $total_dyn_inst2"