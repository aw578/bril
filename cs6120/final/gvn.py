import json
import sys
import os
sys.path.append(os.path.expanduser("~/bril/examples"))
from to_ssa import to_ssa
from collections import defaultdict

COMMUTATIVE_OPS = {'add', 'mul', 'eq', 'and', 'or'}

def find_congruence_classes(func):
  instrs = func.get('instrs', [])
  congruence_classes = defaultdict(set)
  var_op = {}

  # Get starting classes for normal ops
  for instr in instrs:
    if 'dest' in instr and 'op' in instr:
      dest = instr['dest']
      op = instr['op']
      if op == 'const':
        var_op[dest] = op + " " + str(instr["value"])
        congruence_classes[op + " " + str(instr["value"])].add(dest)
      else:
        var_op[dest] = op
        congruence_classes[op].add(dest)

  # Find max arg length
  max_arg_len = 0
  for instr in instrs:
    if 'args' in instr:
      max_arg_len = max(max_arg_len, len(instr['args']))
    if instr.get('op') in COMMUTATIVE_OPS and 'args' in instr:
      instr["args"] = sorted(instr['args'])

  # Build initial worklist (list of sets)
  worklist = [s for s in congruence_classes.values() if s]

  while worklist:
    c = worklist.pop()
    for p in range(max_arg_len):
      touched = set()
      for instr in instrs:
        if 'dest' in instr and 'args' in instr and len(instr['args']) > p:
          if instr['args'][p] in c:
            touched.add(instr['dest'])
      for o, s in list(congruence_classes.items()):
        n = s.intersection(touched)
        if 0 < len(n) < len(s):
          congruence_classes[o] = s.difference(n)
          new_class_id = f"{o}_new"
          congruence_classes[new_class_id] = n
          # Update worklist
          if s in worklist:
            worklist.remove(s)
            worklist.append(s.difference(n))
            worklist.append(n)
          else:
            # Add the smaller split to worklist
            worklist.append(min([n, s.difference(n)], key=len))

  # Convert defaultdict to normal dict for output
  return {k: list(v) for k, v in congruence_classes.items() if v}

def main():
    program_str = "".join(sys.stdin.readlines())
    bril_program = json.loads(program_str)

    # Convert the program to SSA form
    ssa_program = to_ssa(bril_program)
    # print(json.dumps(ssa_program, indent=2, sort_keys=True))
    # return

    # For each function in the program
    for func in ssa_program['functions']:
        # Find congruence classes
        congruence_classes = find_congruence_classes(func)
        
        # Print congruence classes
        print(f"Congruence classes for function {func['name']}:")
        for class_id, instrs in congruence_classes.items():
            print(f"Class {class_id}: {instrs}")

    # print(json.dumps(ssa_program, indent=2, sort_keys=True))

# TODO: not merging phis (need to restructure to_ssa)
# TODO: available expressions: set every congruence class to its first member -> available instructions for blocks
# -> instruction available? remove
if __name__ == "__main__":
    main()