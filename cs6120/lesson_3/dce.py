import json
import sys
sys.path.append("/home/nya1025/bril/cs6120/lesson_2")
from blocks import function_blocks, merge_blocks

def dce_global(instrs):
  new_instrs = []
  used = set()
  changed = False
  # get all used variables
  for instr in instrs:
    if("args" in instr):
      for arg in instr["args"]:
        used.add(arg)
  
  # check if variables are used
  for instr in instrs:
    if "dest" in instr:
      if instr["dest"] in used:
        new_instrs.append(instr)
      else:
        changed = True
    else:
      new_instrs.append(instr)
  return changed, new_instrs

def dce_block(instrs):
  last_line_written = {}
  keep_instrs = [True for _ in instrs]
  changed = False
  for i in range(len(instrs)):
    instr = instrs[i]
    # remove used variables
    if("args" in instr):
      for arg in instr["args"]:
        last_line_written.pop(arg, None)
    # check for double writes
    if "dest" in instr:
      dest = instr["dest"]
      if dest in last_line_written:
        keep_instrs[last_line_written[dest]] = False
        changed = True
      last_line_written[dest] = i
  return changed, [instrs[i] for i in range(len(instrs)) if keep_instrs[i]]

def dce(instrs):
  changed = True
  while changed:
    changed, instrs = dce_global(instrs)
  blocks = function_blocks(instrs)
  new_blocks = []
  for block in blocks:
    instrs = block[1]
    changed = True
    while changed:
      changed, instrs = dce_block(instrs)
    new_blocks.append((block[0], instrs))
  return new_blocks

if __name__ == "__main__":
  program_str = "".join(sys.stdin.readlines())
  program = json.loads(program_str)
  program["functions"][0]["instrs"] = merge_blocks(dce(program["functions"][0]["instrs"]))
  print(json.dumps(program, indent=1))

# interpret: bril2json < examples/test/tdce/x.bril | brili
# optimize then interpret: bril2json < examples/test/tdce/x.bril | python cs6120/lesson_3/lvn.py | brili