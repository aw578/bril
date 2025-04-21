import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lesson_2.blocks import function_blocks, merge_blocks
import copy

def merge_trace(blocks, trace):
  # Build a mapping from label to block index and instructions
  label_to_block = {}
  for idx, (label, instrs) in enumerate(blocks):
    label_to_block[label] = (idx, instrs)

  # Helper to deep copy instructions
  def deepcopy_instr(instr):
    return copy.deepcopy(instr)

  # For generating new variable names for not cond
  not_cond_counter = 0

  # Record of (instr_or_label, len(trace_block_instrs)) in order
  record = []
  trace_block_instrs = []
  i = 0
  instr_count = 0
  max_instrs = 100

  while i < len(trace):
    instr = deepcopy_instr(trace[i])
    instr_count += 1

    # If it's a label
    if "label" in instr:
      record.append((instr, len(trace_block_instrs)))
      i += 1
      continue

    # If over 100 instructions and you reach a br or jmp, stop
    if instr_count > max_instrs and instr.get("op") in ("br", "jmp"):
      break

    # If it's a branch
    if instr.get("op") == "br":
      record.append((instr, len(trace_block_instrs)))
      branch_val = instr.get("branch")
      labels = instr.get("labels")
      if not labels or len(labels) != 2:
        raise Exception("Malformed branch in trace")
      cond_var = instr["args"][0]
      if branch_val == 0:
        guard_instr = {
          "op": "guard",
          "args": [cond_var],
          "labels": ["trace.failed"]
        }
        trace_block_instrs.append(guard_instr)
      elif branch_val == 1:
        not_var = f"trace_not_{not_cond_counter}"
        not_cond_counter += 1
        not_instr = {
          "op": "not",
          "args": [cond_var],
          "dest": not_var,
          "type": "bool"
        }
        guard_instr = {
          "op": "guard",
          "args": [not_var],
          "labels": ["trace.failed"]
        }
        trace_block_instrs.append(not_instr)
        trace_block_instrs.append(guard_instr)
      else:
        raise Exception("Unknown branch value in trace")
      del instr["branch"]
      i += 1
      continue

    # If it's a print or call, stop
    if instr.get("op") in ("print", "call", "ret"):
      break

    # ignore jumps
    if instr.get("op") == "jmp":
      continue

    # Otherwise, just add the instruction
    record.append((instr, len(trace_block_instrs)))
    trace_block_instrs.append(instr)
    i += 1

  # Remove trailing branches and labels from record and trace_block_instrs
  while record:
    last_entry, instrs_len = record[-1]
    if ("op" in last_entry and last_entry["op"] == "br"):
      # Remove the branch and any instructions added after its recorded length
      record.pop()
      trace_block_instrs = trace_block_instrs[:instrs_len]
    elif "label" in last_entry:
      record.pop()
    else:
      break
  # Find last label in record for last_nonlabel_block
  last_nonlabel_block = None
  for entry, _ in reversed(record):
    if "label" in entry:
      last_nonlabel_block = entry["label"]
      break

  # Last instruction in trace_block_instrs is last_trace_instr
  last_trace_instr = trace_block_instrs[-1] if trace_block_instrs else None

  # Prepend speculate, append commit, append jmp trace.1
  speculate_instr = {"op": "speculate"}
  commit_instr = {"op": "commit"}
  jmp_instr = {"op": "jmp", "labels": ["trace.1"]}
  failed_label = {"label": "trace.failed"}

  if len(trace_block_instrs) == 0:
    return blocks

  trace_block_instrs = [speculate_instr] + trace_block_instrs + [commit_instr, jmp_instr, failed_label]

  # Find the original location of the last trace instruction
  found_instr_idx = None

  _, block_instrs = label_to_block[last_nonlabel_block]
  for idx, orig_instr in enumerate(block_instrs):
    if orig_instr == last_trace_instr:
      found_instr_idx = idx
      break
  if found_instr_idx is None:
    print(last_trace_instr)
    print(last_nonlabel_block)
    print(trace_block_instrs)
    raise Exception("Could not find last trace instruction in any block (UNSURE)")

  # Insert fake label trace.1 after the location of the last instruction in the list in the original code
  new_blocks = []
  for idx, (label, instrs) in enumerate(blocks):
    if label == last_nonlabel_block:
      new_instrs = instrs[:found_instr_idx+1] + [{"label": "trace.1"}] + instrs[found_instr_idx+1:]
      new_blocks.append((label, new_instrs))
    else:
      new_blocks.append((label, copy.deepcopy(instrs)))

  # Add the trace block as the first block, label "traceblock"
  trace_block = ("traceblock", trace_block_instrs)
  return [trace_block] + new_blocks

if __name__ == "__main__":
  if len(sys.argv) != 4:
    print("Usage: python trace.py <program_file> <trace_file> <output_file>")
    sys.exit(1)

  program_file = sys.argv[1]
  trace_file = sys.argv[2]
  output_file = sys.argv[3]

  with open(program_file, "r") as pf:
    program_str = pf.read()
  program = json.loads(program_str)

  with open(trace_file, "r") as tf:
    trace = tf.readlines()
    trace = [tr for tr in trace if tr[0] == "{"]
    trace = [json.loads(tr) for tr in trace]

  for i in range(len(program["functions"])):
    if program["functions"][i]["name"] == "main":
      instrs = program["functions"][i]["instrs"]
      args = []
      if "args" in program["functions"][i]:
        args = program["functions"][i]["args"]
      blocks = function_blocks(instrs)
      new_blocks = merge_trace(blocks, trace)
      program["functions"][i]["instrs"] = merge_blocks(new_blocks)

  with open(output_file, "w") as of:
    json.dump(program, of, indent=2)