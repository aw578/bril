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
  # Convert to SSA form
  ssa_output=$(bril2json < "$f" | python cs6120/lesson_6/ssa.py 2>/dev/null)
  
  # Check if the SSA form is valid
  is_ssa=$(echo "$ssa_output" | python examples/is_ssa.py 2>/dev/null)
  
  if [ "$is_ssa" != "yes" ]; then
    echo "FAIL (SSA) $is_ssa"
  fi
  
  # Run the SSA form and save the output
  ssa_run_output=$(echo "$ssa_output" | brili -p $args 2>/dev/null)
  
  # output comparison
  output1=$(bril2json < "$f" | brili -p $args 2>/dev/null)    
  output2=$(bril2json < "$f" | python cs6120/lesson_6/ssa.py | brili -p $args 2>/dev/null)  
  if [ "$output1" != "$output2" ]; then
      echo "FAIL (out) $f $output1 $output2"
  fi
done