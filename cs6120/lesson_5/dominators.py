import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lesson_2.blocks import function_blocks
from lesson_2.cfg import build_cfg, change_labels

def slow_traverse(cfg):
  """build a dominance tree naively by checking all paths"""
  dominates = {}
  start_set = set(cfg.keys())
  for node in cfg:
    dominates[node] = start_set
  dominates["entry"] = set(["entry"])
  path = []
  # record current path, for each node 
  def traverse(node):
    path.append(node)
    new_dominates = set(path)
    dominates[node] = new_dominates.intersection(dominates[node])
    for succ in cfg[node]:
      if(succ not in path):
        # if you loop to previous node in path, it was already visited so its dominators will always be a subset of current pah
        traverse(succ)
    path.pop()
  traverse("entry")
  return dominates

def invert(cfg):
  preds = {}
  for node in cfg:
    preds[node] = []
  for node in cfg:
    for succ in cfg[node]:
      preds[succ].append(node)
  return preds

def postorder(cfg):
  order = []
  path = []
  def po(node):
    path.append(node)
    for succ in cfg[node]:
      if succ not in path:
        po(succ)
    order.append(node)
    path.pop()
  po("entry")
  return order

def fast_traverse(cfg):
  """build a dominance tree using reverse postorder? for each node, nodes that dominate it"""
  preds = invert(cfg)
  dominates = {}
  start_set = set(cfg.keys())
  for node in cfg:
    dominates[node] = start_set
  order = postorder(cfg)[::-1]

  # iterate
  changed = True
  while changed:
    changed = False
    for node in order:
      new_dominates = set()
      for pred in preds[node]:
        if(new_dominates == set()):
          new_dominates = set(dominates[pred])
        else:
          new_dominates = new_dominates.intersection(dominates[pred])
      new_dominates.add(node)
      if(dominates[node] != new_dominates):
        assert(len(dominates[node]) > len(new_dominates))
        changed = True
        dominates[node] = new_dominates
  return dominates

def frontier(cfg):
  dominates = fast_traverse(cfg)
  preds = invert(cfg)
  dom_frontier = {}
  for b in cfg:
    dom_frontier[b] = []
  # a doesn't SD b, but a dominates a pred of b
  for b in cfg:
    # dominates of preds of b
    pred_doms = set()
    for pred in preds[b]:
      pred_doms = dominates[pred].union(pred_doms)
    
    # check they don't SD b
    for a in pred_doms:
      if not (a in dominates[b] or a == b):
        dom_frontier[b].append(a)
  return dom_frontier

def compare(dom1, dom2):
  assert(len(dom1) == len(dom2) and key in dom2 for key in dom1)
  for key in dom1:
    assert(dom1[key] == dom2[key])

if __name__ == "__main__":
  program_str = "".join(sys.stdin.readlines())
  program = json.loads(program_str)
  instrs = program["functions"][-1]["instrs"]
  cfg = build_cfg(change_labels(function_blocks(instrs)))
  fast = fast_traverse(cfg)
  slow = slow_traverse(cfg)
  compare(fast, slow)
  print(fast)
  print(frontier(cfg))