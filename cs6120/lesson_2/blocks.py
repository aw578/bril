import json
import sys

terminators = ('br', 'jmp', 'ret')

def function_blocks(function_instrs):
  """
  Get a list of (label, block) tuples from a list of instructions in a function.
  """
  cur_block = (None, [])
  all_blocks = [cur_block]
  for instr in function_instrs:
    if "op" in instr:
      cur_block[1].append(instr)
      if(instr["op"] in terminators):
        cur_block = (None, [])
        all_blocks.append(cur_block)
    else:
      # blocks that are empty and have no labels can safely be removed 
      if(len(cur_block[1]) == 0 and cur_block[0] == None):
        all_blocks = all_blocks[:-1]
      cur_block = (instr["label"], [])
      all_blocks.append(cur_block)
  # remove empty last block  
  if(len(cur_block[1]) == 0 and cur_block[0] == None):
        all_blocks = all_blocks[:-1]
  return all_blocks

def blocks(filename):
  with open(filename) as file:
    program = json.load(file)
    function_instrs = program["functions"][0]["instrs"]
    return function_blocks(function_instrs)
  
def merge_blocks(blocks):
  instrs = []
  for (label, block_instrs) in blocks:
    if label is not None:
      instrs.append({"label": label})
    instrs += block_instrs
  return instrs

if __name__ == "__main__":
  filename = sys.argv[1]
  all_blocks = blocks(filename)
  for (label, contents) in all_blocks:
    print(label)
    print(contents)