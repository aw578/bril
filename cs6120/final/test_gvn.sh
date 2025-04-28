#!/bin/sh

for f in benchmarks/core/*.bril; do
    echo "$f"
    args=""

    # jank
    while IFS= read -r line; do
        if echo "$line" | grep -q "^# ARGS:"; then
            args=$(echo "$line" | sed 's/^# ARGS: //')
            break
        elif echo "$line" | grep -q "^#ARGS:"; then
            args=$(echo "$line" | sed 's/^#ARGS: //')
            break
        fi
    done < "$f"
    
    # instruction reduction
    # total_inst1=$(bril2json < "$f" | python cs6120/lesson_3/dce.py | brili -p $args 2>&1 > /dev/null | grep -oP '(?<=total_dyn_inst: )\d+')    
    # total_inst2=$(bril2json < "$f" | python cs6120/lesson_3/lvn.py | python cs6120/lesson_3/dce.py | brili -p $args 2>&1 > /dev/null | grep -oP '(?<=total_dyn_inst: )\d+')    
    # if [ "$total_inst1" -lt "$total_inst2" ]; then
    #     echo "FAIL (ins) $f $total_inst1 $total_inst2"
    # fi

    # output comparison
    output1=$(bril2json < "$f" | brili -p $args 2>/dev/null)    
    output2=$(bril2json < "$f" | python cs6120/final/gvn.py | brili -p $args 2>/dev/null)  
    if [ "$output1" != "$output2" ]; then
        echo "FAIL (out) $f $output1 $output2"
    fi  
done