import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lesson_2.blocks import function_blocks, merge_blocks
from lesson_2.cfg import build_cfg, change_labels
from lesson_5.dominators import fast_traverse, invert  
from lesson_4.flow import reaching_defs

has_side_effects = ["div", "jmp", "br", "call", "ret", "print"]

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

def find_backedges(cfg):
  """find all backedges in a cfg"""
  backedges = {}
  dominates = fast_traverse(cfg)
  for n in cfg:
    for h in cfg[n]:
      if(h in dominates[n]):
        if(h not in backedges):
          backedges[h] = []
        backedges[h].append(n)
  return backedges

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
  # rebuild blocks
  blocks = new_blocks
  cfg = build_cfg(blocks)
  inv_cfg = invert(cfg)

  dominates = fast_traverse(cfg)
  var_defs = reaching_defs(args, blocks)
  backedges = find_backedges(cfg)
  for header in loops:
    # mark all invariant instrs
    changed = True
    while changed:
      changed = False
      for block in loops[header]:
        for instr in block_map[block]:
          invariant = True
          if("args" in instr):
            for arg in instr["args"]:
              # var_defs[arg] = [("entry", {})]
              arg_defs = var_defs[block].get(arg, [])
              has_li_def = False
              if(len(arg_defs) == 1 and "invariant" in instr):
                has_li_def = True
              has_inside_def = False
              for (label, _) in arg_defs:
                if(label in loops[header]):
                  has_inside_def = True
                  break
              # all reaching defs of x are not in loops or 1 LI definition = invar
              if(not has_li_def and has_inside_def):
                invariant = False
                break
          else:
            # no arguments: const, jmp, call, ret
            pass
          if(invariant and "invariant" not in instr):
            changed = True
            instr["invariant"] = True

    # move all invariant instrs
    for block in loops[header]:
      instrs = block_map[block]
      for instr in instrs[:]:
        if("invariant" in instr):
          conditions_met = True
          # instr has a def
          if("dest" not in instr):
            conditions_met = False
          if(not conditions_met):
            continue

          # def dominates uses
          for use_lbl in loops[header]:
            use_block = block_map[use_lbl]
            for use_instr in use_block:
              if "args" in use_instr and instr["dest"] in use_instr["args"]:
                if(block not in dominates[use_lbl]):
                  conditions_met = False
                  break
          if(not conditions_met):
            continue

          # no other defs in loop
          for def_lbl in loops[header]:
            def_block = block_map[def_lbl]
            for def_instr in def_block:
              if "dest" in def_instr and def_instr["dest"] == instr["dest"] and def_instr != instr:
                conditions_met = False
                break
          if(not conditions_met):
            continue

          # instr dominates exits (backedges ...)
          dominates_exits = True
          for backedge in backedges:
            if(block not in dominates[backedge]):
              dominates_exits = False
              break
          # no uses after loop
          used = False
          # for every block not in the loop, if block has instr["dest"], if instr actually reaches block, check that nothing reads from dest?
          # Thoughts: definition reaches + not in loop means it's after the loop, we don't care if it's in the loop because the loop doesn't run!
          for (label, outside_block) in blocks:
            if(label not in loops[header] and instr["dest"] in var_defs[label]):
              if((label, instr) in var_defs[label][instr["dest"]]):
                for outside_instr in outside_block:
                  if("args" in outside_instr and instr["dest"] in outside_instr["args"]):
                    used = True
                    break
          conditions_met = dominates_exits or (not used and instr["op"] not in has_side_effects)
          if(not conditions_met):
            continue
          instrs.remove(instr)
          block_map[f"fake.{header}"].append(instr)
  return blocks

def reachable_blocks(blocks):
  cfg = build_cfg(blocks)
  reachable = set(["entry"])
  stack = ["entry"]
  while stack:
    node = stack.pop()
    for succ in cfg.get(node, []):
      if succ not in reachable:
        reachable.add(succ)
        stack.append(succ)
  return [(label, block) for (label, block) in blocks if label in reachable]

if __name__ == "__main__":
  program_str = "".join(sys.stdin.readlines())
  program = json.loads(program_str)
  for i in range(len(program["functions"])):
    instrs = program["functions"][i]["instrs"]
    args = []
    if("args" in program["functions"][i]):
      args = program["functions"][i]["args"]    
    blocks = change_labels(function_blocks(instrs))
    blocks = reachable_blocks(blocks)
    new_blocks = licm(args, blocks)
    program["functions"][i]["instrs"] = merge_blocks(new_blocks)
  print(json.dumps(program))
