import json
import sys
from ssa import to_ssa, from_ssa
from temp_ssa import fake_to_ssa
from collections import defaultdict
import os
sys.path.append(os.path.expanduser("~/bril/examples"))

from cfg import block_map, reassemble
from df import Analysis, df_worklist
from form_blocks import form_blocks

COMMUTATIVE_OPS = {'add', 'mul', 'eq', 'and', 'or'}

###############################################################################
# Helpers
###############################################################################


def _is_real_expr(instr: dict) -> bool:
  """Return True if `instr` is a genuine computation that defines a new value
  and should participate in value-numbering / availability analysis."""
  return instr["op"] not in {
    "phi",
    "jmp",
    "br",
    "ret",
    "store",
    "print",
    "nop",
  }

def _expr_key(instr: dict):
  """Canonical, hashable key for an instruction's expression.

  We use a JSON dump with sorted keys so that instructions that are *structurally*
  identical map to the same key.  For commutative ops we sort the operands to
  canonicalise `a + b` vs `b + a`.
  """
  if not _is_real_expr(instr):
      return None

  op = instr["op"]
  key_instr = dict(instr)  # shallow copy

  if op in COMMUTATIVE_OPS:
    # For commutative binary ops, sort the operands canonically
    key_instr["args"] = sorted(key_instr.get("args", []))

  # Stable, hashable representation
  return json.dumps(key_instr, sort_keys=True)


###############################################################################
# Pass 1 – duplicate-expression removal within each basic block
###############################################################################


def _dedup_block_instrs(instrs):
  """Remove duplicate *identical* expressions that occur later in the same
  basic block."""
  seen = set()
  new_instrs = []
  for ins in instrs:
    key = _expr_key(ins)
    if key is not None and key in seen:
      continue
    if key is not None:
      seen.add(key)
    new_instrs.append(ins)
  return new_instrs


###############################################################################
# Pass 2 – AVAIL-based global redundant-expression elimination
###############################################################################


def _compute_avail(func_blocks):
  """Run forward data-flow to compute AVIN / AVOUT sets per block.

  AVIN(b)  =  intersection of AVOUT(preds)     (empty set for entry block)
  AVOUT(b) =  AVIN(b) + GEN(b),  where GEN(b) are expressions computed in b.
  """

  def merge(pred_out_sets):
    """Intersection over predecessors (TOP = all_expr; BOTTOM = ∅)."""
    out = None
    for s in pred_out_sets:
      if(out == None):
        out = s
      else:
        out = out.intersection(s)
    # unreachable or entry
    if(out == None):
      return set()
    return out

  def transfer(instrs, in_set):
    gen_set = set()
    for ins in instrs:
      k = _expr_key(ins)
      if k is not None:
        gen_set.add(k)
    return in_set.union(gen_set)

  # Build analysis object
  av_analysis = Analysis(
    True,
    init=set(),
    merge=merge,
    transfer=transfer,
  )

  # Provide CFG edges: predecessors & successors are implicit in blocks’ terminators
  av_in, av_out = df_worklist(func_blocks, av_analysis)
  return av_in, av_out


def _avail_eliminate(func_blocks, av_in):
  """Remove instructions whose expression is already available along *all*
  paths to that point."""
  for bname, binstrs in func_blocks.items():
    avail_here = set(av_in[bname])  # start with AVIN for the block
    new_instrs = []
    for ins in binstrs:
      key = _expr_key(ins)
      if key is not None and key in avail_here:
        # Already available, redundant
        continue
      if key is not None:
        avail_here.add(key)
      new_instrs.append(ins)
    func_blocks[bname] = new_instrs

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
  # First, build a mapping from variable name to its block label
  block_labels = {}
  if 'name' in func:
    blocks = block_map(form_blocks(instrs))
    for block in blocks:
      for instr in blocks[block]:
        if 'dest' in instr:
          block_labels[instr['dest']] = block
  for instr in instrs:
    if 'dest' in instr and 'op' in instr:
      dest = instr['dest']
      op = instr['op']
      class_id = None
      if op == 'const': # only group consts w/ same value
        class_id = op + " " + str(instr["value"])
      elif op == 'call': # only group calls w/ same func
        class_id = op + " " + str(" ".join(instr["funcs"]))
      elif op == 'phi': # can't compare across blocks
        # Use the block label where this phi instruction appears
        # Find the block containing this instruction
        if dest in block_labels:
          block_label = block_labels[dest]
        else:
          block_label = "None"
        class_id = f"{op}_{block_label}"
      elif op != "undef": # ignore 
        class_id = op
      if(class_id):
        var_op[dest] = class_id
        congruence_classes[class_id].add(dest)

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
  values = ["original", "classes", "final", "none"]
  value = values[2]

  # Convert the program to SSA form
  if(value == values[0]):
    print(json.dumps(fake_to_ssa(bril_program), indent=2, sort_keys=True))

  ssa_program = to_ssa(bril_program)
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

    blocks = block_map(form_blocks(func["instrs"]))
    # --- Pass 1: same-block duplicate removal ----------------------------------
    for bname, binstrs in blocks.items():
        blocks[bname] = _dedup_block_instrs(binstrs)

    # --- Pass 2: AVAIL-based global removal ------------------------------------
    av_in, _ = _compute_avail(blocks)
    _avail_eliminate(blocks, av_in)

    # --- reassemble back into flat instruction list ----------------------------
    func["instrs"] = reassemble(blocks)


  if(value == values[2]):
    from_ssa(ssa_program)
    print(json.dumps(ssa_program, indent=2, sort_keys=True))

# TODO: available expressions: set every congruence class to its first member -> available instructions for blocks
# -> instruction available? remove
if __name__ == "__main__":
    main()