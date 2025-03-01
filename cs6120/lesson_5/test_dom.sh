#!/bin/sh

for f in benchmarks/core/*.bril; do
    echo "$f"
    output2=$(bril2json < "$f" | python cs6120/lesson_5/dominators.py) 
    echo "$output2" 
done