import json
import sys
from ssa import to_ssa, from_ssa
from temp_ssa import fake_to_ssa
from collections import defaultdict

COMMUTATIVE_OPS = {'add', 'mul', 'eq', 'and', 'or'}

def find_congruence_classes(func):
  instrs = func.get('instrs', [])
  congruence_classes = defaultdict(set)
  var_op = {}

  # Add function arguments as their own congruence classes of 1
  for arg in func.get('args', []):
    if isinstance(arg, dict) and 'name' in arg:
      arg_name = arg['name']
    else:
      arg_name = arg
    congruence_classes[f"arg_{arg_name}"].add(arg_name)

  # Get starting classes for normal ops
  for instr in instrs:
    if 'dest' in instr and 'op' in instr:
      dest = instr['dest']
      op = instr['op']
      class_id = None
      if op == 'const':
        class_id = op + " " + str(instr["value"])
      elif op == 'call':
        class_id = op + " " + str(" ".join(instr["funcs"]))
      elif op == 'phi':
        block_label = instr.get('labels', [None])[0] if 'labels' in instr and instr['labels'] else func.get('name', '')
        class_id = f"{op}_{block_label}"
      elif op != "undef": # ignore 
        class_id = op
      if(class_id):
        var_op[dest] = class_id
        congruence_classes[op].add(class_id)

  # Find max arg length
  max_arg_len = 0
  for instr in instrs:
    if 'args' in instr:
      max_arg_len = max(max_arg_len, len(instr['args']))
    if instr.get('op') in COMMUTATIVE_OPS and 'args' in instr:
      instr["args"] = sorted(instr['args'])

  # Build initial worklist (list of sets)
  worklist = [s for s in congruence_classes.values() if s]
  id_counter = defaultdict(int)
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
          new_class_id = f"{o}_{id_counter[o]}"
          id_counter[o] += 1
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
  values = ["original", "classes", "final"]
  value = values[2]

  # Convert the program to SSA form
  if(value == values[0]):
    print(json.dumps(fake_to_ssa(bril_program), indent=2, sort_keys=True))

  ssa_program = to_ssa(bril_program)
  # TODO: find probleem in gebmm main
  for func in ssa_program['functions']:
    congruence_classes = find_congruence_classes(func)

    # Build a mapping from variable to its class representative (first member)
    var_to_rep = {}
    for class_vars in congruence_classes.values():
      rep = sorted(class_vars)[0]
      for v in class_vars:
        var_to_rep[v] = rep

    # Replace dest and args with class representative if exists
    for instr in func.get('instrs', []):
      if 'dest' in instr and instr['dest'] in var_to_rep:
        instr['dest'] = var_to_rep[instr['dest']]
      if 'args' in instr:
        instr['args'] = [var_to_rep.get(arg, arg) for arg in instr['args']]

    if(value == values[1]):
      print(f"Congruence classes for function {func['name']}:")
      for class_id, instrs in congruence_classes.items():
        print(f"Class {class_id}: {sorted(instrs)}")

  if(value == values[2]):
    from_ssa(ssa_program)
    print(json.dumps(ssa_program, indent=2, sort_keys=True))

# TODO: available expressions: set every congruence class to its first member -> available instructions for blocks
# -> instruction available? remove
if __name__ == "__main__":
    main()