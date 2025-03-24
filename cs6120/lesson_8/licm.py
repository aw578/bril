import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lesson_2.blocks import function_blocks, merge_blocks
from lesson_2.cfg import build_cfg, change_labels
from lesson_5.dominators import fast_traverse, invert  
from lesson_4.flow import reaching_defs

side_effects = ["div", "jmp", "br", "call", "ret", "print"]

def find_loops(cfg):
  """find all natural loops in a cfg, head block -> blocks in body"""
  backedges = []
  loops = {}
  dominates = fast_traverse(cfg)
  inv_cfg = invert(cfg)
  for n in cfg:
    for h in cfg[n]:
      if(h in dominates[n]):
        backedges.append((n, h))
        loops[h] = set()
  
  for (n, h) in backedges:
    body = set([h])
    stack = [n]
    while(len(stack) > 0):
      d = stack.pop()
      if(d not in body):
        body.add(d)
        for pred in inv_cfg[d]:
          stack.append(pred)
    loops[h] = loops[h].union(body)
  return loops

def licm(args, blocks):
  # label -> instr map
  block_map = {"entry": []}
  for (label, block) in blocks:
    block_map[label] = block
  # find all loops
  cfg = build_cfg(blocks)
  inv_cfg = invert(cfg)
  loops = find_loops(cfg)

  # prepend fake preheader for loop headers, redirect outside edges to them
  new_blocks = []
  for (label, block) in blocks:
    if(label in loops):
      new_label = f"fake.{label}"
      new_block = []
      new_blocks.append((new_label, new_block))
      block_map[new_label] = new_block
      for pred in inv_cfg[label]:
        if(pred not in loops[label] and len(block_map[pred]) > 0):
          final_instr = block_map[pred][-1]
          if(final_instr["op"] in ["br", "jmp"]):
            label_idx = final_instr["labels"].index(label)
            final_instr["labels"][label_idx] = new_label
        pass
    new_blocks.append((label, block))

  var_defs = reaching_defs(args, new_blocks)
  for header in loops:
    # mark all invariant instrs
    changed = True
    while changed:
      changed = False
      for block in loops[header]:
        for instr in block_map[block]:
          if("args" in instr):
            for arg in instr["args"]:
              # var_defs[arg] = [("entry", {})]
              arg_defs = var_defs[block].get(arg, [])
              has_li_def = False
              if(len(arg_defs) == 1 and "invariant" in instr):
                has_li_def = True
              has_inside_def = False
              for (label, _) in arg_defs:
                if(label in loops):
                  has_inside_def = True
                  break
              # all reaching defs of x are not in loops or 1 LI definition = invar
              if(not has_li_def and has_inside_def):
                continue
          else:
            pass
          if("invariant" not in instr):
            changed = True
            instr["invariant"] = True
    # move all invariant instrs
    for block in loops[header]:
      instrs = block_map[block]
      for instr in instrs[:]:
        if("invariant" in instr): # if it has a def, def dominates uses, no other defs in loop, instr dominates all exits OR var is unused after loop, no side effects
          # if("def" in instr and "def domiantes uses" and "no oher defs in loop" and ("instr dominates exits" or ("var unused after loop, no side effects"))):
            instrs.remove(instr)
            block_map[f"fake.{header}"].append(instr)
  return new_blocks

if __name__ == "__main__":
  program_str = "".join(sys.stdin.readlines())
  program = json.loads(program_str)
  for i in range(len(program["functions"])):
    instrs = program["functions"][i]["instrs"]
    args = []
    if("args" in program["functions"][i]):
      args = program["functions"][i]["args"]
    blocks = change_labels(function_blocks(instrs))
    new_blocks = licm(args, blocks)
    program["functions"][i]["instrs"] = merge_blocks(new_blocks)
  print(json.dumps(program))
