import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lesson_2.blocks import function_blocks, merge_blocks
from lesson_2.cfg import build_cfg, change_labels
from lesson_5.dominators import frontier, build_tree, fast_traverse

def naive_ssa(blocks, args):
  """
  Across basic blocks, here’s a really inefficient strategy that creates too many names and too many ϕ-nodes. 
  If your function uses n variables and has m blocks, create n × m new variable names so each block has its own, 
  private copy of the variable on entry. Then, at the top of every block, insert n ϕ-nodes to pick the right 
  incoming value among the predecessors’ names.
  Modifies blocks in place.
  """

  for (label, block) in blocks:
    # variable name: label.variable.iter
    var_counts = {}
    ghost_vars = set()
    for instr in block:
      # for each arg, get current value, default to 1 if not present
      if("args" in instr):
        for i in range(len(instr["args"])):
          arg = instr["args"][i]
          if(arg not in var_counts):
            var_counts[arg] = 1
            ghost_vars.add(arg)
          arg_val = var_counts[arg]
          instr["args"][i] = f"{label}.{arg}.{arg_val}"
      # for dest, increment + save
      if("dest" in instr):
        dest = instr["dest"]
        dest_val = 1
        if(dest in var_counts):
          dest_val = var_counts[dest]
        var_counts[dest] = dest_val + 1
        instr["dest"] = f"{label}.{dest}.{dest_val + 1}"
    
    # prepend:
    # if b.variable.1 was used, get it
    for var in ghost_vars:
      get = {
        "dest": f"{label}.{var}.1", 
        "op": "get"
      }
      block.insert(0, get)
    # edge case: empty blocks
    if(len(block) == 0):
      continue
    last_entry = len(block)
    if(block[last_entry - 1]["op"] in ["br", "jmp", "ret"]):
      last_entry -= 1
    #for each successor succ, variable read from / written to, set succ.variable.1 to b.variable.last
    for (succ, _) in blocks:
      for var in var_counts:
        set_instr = {
          "op": "set",
          "args": [f"{succ}.{var}.1", f"{label}.{var}.{var_counts[var]}"]
        }
        block.insert(last_entry, set_instr)
    
  # handle function args:
  for var in args:
    for (label, block) in blocks:
      set_instr = {
          "op": "set",
          "args": [f"{label}.{var}.1", var]
        }
      blocks[0][1].insert(0, set_instr)

def out_of_ssa(blocks):
  for (_, block) in blocks:
    # if instruction is a get: remove it!
    block[:] = [instr for instr in block if instr["op"] != "get"]
    # if instruction is a set: arg1 = id arg2
    for instr in block:
      if(instr["op"] == "set"):
        instr["op"] = "id"
        instr["dest"] = instr["args"][0]
        instr["args"] = [instr["args"][1]]

def fancy_ssa(blocks, args):
  # setup
  cfg = build_cfg(blocks)
  df = frontier(cfg)
  dom_tree = build_tree(cfg, fast_traverse(cfg))
  # throw out empty entry block
  dom_tree = dom_tree["children"][0]
  label_to_block = {label: block for (label, block) in blocks}

  # pass 0? insert dummy init functions for arguments (fix phi insertions in pass 1, then edit arg_inits back in pass 4)
  first_block = label_to_block[dom_tree["name"]]
  arg_inits = []
  for arg in args:
    arg_init = {"op": "id", "dest": arg, "args": [arg], "original_arg": [arg]}
    arg_inits.append(arg_init)
    first_block.insert(0, arg_init)

  # save all written vars, write locations
  all_vars = set()
  var_defs = {}
  for (label, block) in blocks:
    for instr in block:
      if("dest" in instr):
        dest = instr["dest"]
        if(dest not in var_defs):
          var_defs[dest] = []
        var_defs[dest].append(label)
        all_vars.add(dest)

  
  # pass 1: insert phi functions, save with original name for pass 2
  # (block, var) -> set of (block, varname) pairs
  pending_phis = {}
  for v in all_vars:
    defs = var_defs[v]
    i = 0
    while(i < len(defs)):
      d = defs[i]
      for label in df[d]:
        if(label == "entry" or label == "exit"):
          continue
        if(label not in defs):
          defs.append(label)
        if((label, v) not in pending_phis):
          phi_instr = {"op": "phi", "dest": v, "args": []}
          pending_phis[(label, v)] = phi_instr
          label_to_block[label].insert(0, phi_instr)
      i += 1
  # pass 2: rename functions
  stack = {v: [v] for v in all_vars}
  stack_num = {v: 0 for v in all_vars}
  def rename(tree_node):
    label = tree_node["name"]
    if(label == "entry" or label == "exit"):
      return
    block = label_to_block[label]
    names_added = {v: 0 for v in all_vars}
    for instr in block:
      # replace each argument to instr with stack[old name]
      if("args" in instr):
        # don't replace args for phi functions
        if(isinstance(instr["args"], set)):
          break
        for i in range(len(instr["args"])):
          arg = instr["args"][i]
          if(arg in stack):
            instr["args"][i] = stack[arg][-1]
          else:
            # not written to yet, og name is fine
            pass
      if("dest" in instr):
        dest = instr["dest"]
        new_dest = f"{dest}.{stack_num[dest]}"
        stack[dest].append(new_dest)
        stack_num[dest] += 1
        names_added[dest] += 1
        instr["dest"] = new_dest
    for succ in cfg[label]:
      for var in all_vars:
        if((succ, var) in pending_phis):
          if((label, stack[var][-1]) not in pending_phis[(succ, var)]["args"]) and len(stack[var]) > 1:
            pending_phis[(succ, var)]["args"].append((label, stack[var][-1]))
    for succ in tree_node["children"]:
      rename(succ)
    for name in names_added:
      for _ in range(names_added[name]):
        stack[name].pop()
    return
  rename(dom_tree)

  # pass 3: add set and get nodes 
  # turn phi nodes to sets
  block_sets = {}
  for (block_label, block) in blocks:
    for instr in block:
      if(instr["op"] == "phi"):
        instr["op"] = "get"
        for (label, var) in instr["args"]:
          if(label not in block_sets):
            block_sets[label] = []
          block_sets[label].append({"op": "set", "args": [instr["dest"], var]})
        del instr["args"]

  # add queued set nodes
  for (label, block) in blocks:
    # edge case: empty blocks
    last_entry = len(block)
    if(last_entry > 0 and block[last_entry - 1]["op"] in ["br", "jmp", "ret"]):
      last_entry -= 1
    if(label in block_sets):
      for instr in block_sets[label]:
        block.insert(last_entry, instr)
  
  # pass 4: add dummy set undef nodes to beginning, fix arg inits
  for instr in arg_inits:
    instr["args"] = instr["original_arg"]
    del instr["original_arg"]
  for v in all_vars:
    if(v in args): 
      pass
    else:
      for i in range(stack_num[v]):
        first_block.insert(0, {"op": "set", "args": [f"{v}.{i}", "dummy_undef"]})
  first_block.insert(0, {"op": "undef", "dest": "dummy_undef", "args": []})
    
if __name__ == "__main__":
  program_str = "".join(sys.stdin.readlines())
  program = json.loads(program_str)
  for i in range(len(program["functions"])):
    instrs = program["functions"][i]["instrs"]
    blocks = change_labels(function_blocks(instrs))
    if("args" in program["functions"][i]):
      args = [arg["name"] for arg in program["functions"][i]["args"]]
    else:
      args = []
    # naive_ssa(blocks, args)
    fancy_ssa(blocks, args)
    program["functions"][i]["instrs"] = merge_blocks(blocks)
  print(json.dumps(program))