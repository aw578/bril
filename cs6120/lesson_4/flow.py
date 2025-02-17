"""
in[entry] = init
out[*] = init

worklist = all blocks
while worklist is not empty:
    b = pick any block from worklist
    in[b] = merge(out[p] for every predecessor p of b)
    out[b] = transfer(b, in[b])
    if out[b] changed:
        worklist += successors of b
"""
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lesson_2.blocks import function_blocks
from lesson_2.cfg import build_cfg, change_labels

def init_defines():
    return set()

def merge_defines(predecessors):
    final = set()
    for pred in predecessors:
        final = final.union(pred)
    return final

def transfer_defines(instrs, incoming):
    outgoing = incoming.copy()
    for instr in instrs:
        if("dest" in instr):
            outgoing.add(instr["dest"])
    return outgoing

def final_print_defines(blocks, incoming, outgoing):
    for block in blocks:
        print(f"{block[0]}:")
        if(incoming[block[0]] == set()):
            values = "∅"
        else:
            values = ", ".join(sorted(list(incoming[block[0]])))
        print(f"  in:  {values}")
        if(outgoing[block[0]] == set()):
            values = "∅"
        else:
            values = ", ".join(sorted(list(outgoing[block[0]])))
        print(f"  out: {values}")

def init_constants():
    return {}

def merge_constants(predecessors):
    final = {}
    for pred in predecessors:
        for var in pred:
            if(var not in final):
                final[var] = pred[var]
            else:
                # conflicting values -> ?
                if(pred[var] != final[var]): 
                    final[var] = "?"
    return final

def transfer_constants(instrs, incoming):
    outgoing = dict(incoming)
    for instr in instrs:
        if("dest" in instr):
            var = instr["dest"]
            # is it a valid const? 
            if("op" in instr and instr["op"] == "const"):
                outgoing[var] = instr["value"]
            else:
                outgoing[var] = "?"
    return outgoing

def final_print_constants(blocks, incoming, outgoing):
    for block in blocks:
        print(f"{block[0]}:")
        if(incoming[block[0]] == {}):
            values = "∅"
        else:
            values = ", ".join(sorted([f"{item}: {incoming[block[0]][item]}" for item in incoming[block[0]]]))
        print(f"  in:  {values}")
        if(outgoing[block[0]] == {}):
            values = "∅"
        else:
            values = ", ".join(sorted([f"{item}: {outgoing[block[0]][item]}" for item in outgoing[block[0]]]))
        print(f"  out: {values}")

def worklist(blocks, init, merge, transfer, final_print):
    # initialization
    incoming = {"entry": init()}
    outgoing = {"entry": init(), "exit": init()}
    for (label, block) in blocks:
        outgoing[label] = init()
    successors = build_cfg(blocks)
    predecessors = {"entry": []}
    for block, succs in successors.items():
        for succ in succs:
            if succ not in predecessors:
                predecessors[succ] = []
            predecessors[succ].append(block)

    label_blocks = {"entry": [], "exit": []}
    worklist = set(["entry", "exit"])
    for (label, instrs) in blocks:
        worklist.add((label))
        label_blocks[label] = instrs
    
    # work through worklist
    while(len(worklist) > 0):
        label = worklist.pop()
        incoming[label] = merge([outgoing[pred] for pred in predecessors[label]])
        old_outgoing = outgoing[label]
        outgoing[label] = transfer(label_blocks[label], incoming[label])
        if(old_outgoing != outgoing[label]):
            for successor in successors[label]:
                worklist.add(successor)
    
    final_print(blocks, incoming, outgoing)

if __name__ == "__main__":
    program_str = "".join(sys.stdin.readlines())
    program = json.loads(program_str)
    instrs = program["functions"][0]["instrs"]
    all_blocks = change_labels(function_blocks(instrs))
    # worklist(all_blocks, init_defines, merge_defines, transfer_defines, final_print_defines)
    worklist(all_blocks, init_constants, merge_constants, transfer_constants, final_print_constants)