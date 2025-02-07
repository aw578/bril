"""
table = mapping from value tuples to canonical variables,
  with each row numbered
var2num = mapping from variable names to their current
  value numbers (i.e., rows in table)

for instr in block:
    value = (instr.op, var2num[instr.args[0]], ...)

    if value in table:
        # The value has been computed before; reuse it.
        num, var = table[value]
        replace instr with copy of var

    else:
        # A newly computed value.
        num = fresh value number

        dest = instr.dest
        if dest will be overwritten later:
             dest = fresh variable name
             instr.dest = dest
        else:
             dest = instr.dest

        table[value] = num, dest

        for a in instr.args:
            replace a with table[var2num[a]].var

    var2num[instr.dest] = num

live-ins? (called before defined)
just add to table if you see an arg that's not in var2num?
"""
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lesson_2.blocks import function_blocks, merge_blocks

class Table():
  def __init__(self):
    self.row = 0
    self.value_var = {}
    self.row_var = {}
    self.val_row = {}
  def add(self, value, var_name):
    """Add a row (value, var_name, row #) to the table. Return the row number."""
    assert self.row not in self.row_var and not self.contains_val(value)
    self.value_var[value] = var_name
    self.row_var[self.row] = var_name
    self.val_row[value] = self.row
    self.row += 1
    return self.row - 1
  def add_livein(self, var_name):
    """
    Add a row (var_name, row #) to the table to represent a livein without a value. Return the row number.
    
    This shouldn't be a problem, because while it's a livein it only exists as an argument (accessed by row number)?
    """
    assert(self.row not in self.row_var)
    self.row_var[self.row] = var_name
    self.row += 1
    return self.row - 1
  def contains_val(self, value):
    # jank for booleans thank u guido!
    return any(k is value and type(k) == type(value) for k in self.value_var)
  def name_from_val(self, value):
    """Get a var name using its value."""
    return self.value_var[value]
  def name_from_row(self, row):
    """Get a var name using its row."""
    return self.row_var[row]
  def row_from_val(self, value):
    """Get a row number using its value."""
    return self.val_row[value]

def find_overwrites(instrs):
  overwritten = [False for _ in instrs]
  used = set()
  for i in range(len(instrs) - 1, -1, -1):
    instr = instrs[i]
    if "dest" in instr:
      if instr["dest"] in used:
        overwritten[i] = True
      else:
        used.add(instr["dest"])
  return overwritten

def lvn(instrs):
  table = Table()
  # var name -> row
  var2num = {}
  
  fresh_name = "lvn."
  fresh_num = 0
  overwritten = find_overwrites(instrs)
  for (instr, overwrite) in zip(instrs, overwritten):
    if not instr["op"] or instr["op"] == "jmp" or instr["op"] == "br":
      # label
      continue

    # get value
    if "args" in instr:
      argset = []
      for arg in instr["args"]:
        # livein, need to add to table and var2num
        if arg not in var2num:
          row = table.add_livein(arg)
          var2num[arg] = row
        argset.append(var2num[arg])
      value = (instr["op"], tuple(argset))
    elif "value" in instr:
      value = (instr["op"], instr["value"])
    elif instr["op"] == "ret":
      # empty ret
      continue
    else:
      raise Exception(instr)

    if table.contains_val(value):
      # The value has been computed before; reuse it.
      var = table.name_from_val(value)
      num = table.row_from_val(value)
      dest = instr["dest"]
      old_dest = instr["dest"]
      # rename instruction
      instr.clear()
      instr["dest"] = dest
      instr["op"] = "id"
      instr["args"] = [var]
    else:
      # A newly computed value.

      if "dest" in instr:
        dest = instr["dest"]
        old_dest = instr["dest"]
        if overwrite:
          # rename to prevent clobbering 
          dest = fresh_name + str(fresh_num)
          instr["dest"] = dest

        num = table.add(value, dest)
      if "args" in instr:
        for i in range(len(instr["args"])):
          arg = instr["args"][i]
          new_arg = table.name_from_row(var2num[arg])
          instr["args"][i] = new_arg
    
    # guaranteed to exist in if / else
    if "dest" in instr:
      # i think you need to save the old variable too?
      var2num[old_dest] = num
      var2num[instr["dest"]] = num
def lvn_func(instrs):
  """Perform LVN on a list of instructions and return the updated list."""
  blocks = function_blocks(instrs)
  for block in blocks:
    lvn(block[1])
  return merge_blocks(blocks)

if __name__ == "__main__":
  program_str = "".join(sys.stdin.readlines())
  program = json.loads(program_str)
  program["functions"][0]["instrs"] = lvn_func(program["functions"][0]["instrs"])
  print(json.dumps(program, indent=1))