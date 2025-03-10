import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lesson_2.blocks import function_blocks
from lesson_2.cfg import build_cfg, change_labels

def slow_traverse(cfg):
  """build dominators naively by checking all paths"""
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
  """build dominators using reverse postorder? for each node, nodes that dominate it"""
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

def build_tree(cfg, dominates):
  """Returns the root of a dominance tree {name, children}"""
  nodes = {}
  for node in cfg:
    nodes[node] = {"name": node, "children": []}
  
  # Find the immediate dominator for each node
  idom = {}
  for node in dominates:
    idom[node] = None
    for dom in dominates[node]:
      # idom[node] in dominates[dom] means dom below idom?
      if dom != node and (idom[node] is None or idom[node] in dominates[dom]):
        idom[node] = dom

  # Build the tree using the immediate dominators
  for node in idom:
    parent = idom[node]
    if parent:
      nodes[parent]["children"].append(nodes[node])
  
  return nodes["entry"]

def frontier(cfg):
  """Return a dict containing the dominance frontier of every node."""
  dominates = fast_traverse(cfg)
  dominated_by = invert(dominates)
  frontiers = {}
  # A doesn't strictly dominate B, but A dominates a predecessor of B
  # steps: x = everything A dominates, y = every child of a node in x
  # remove A from x (x is now everything A strictly dominates), return y - x 
  for node in cfg:
    x = set()
    visited = set()
    def downstream(nd):
      visited.add(nd)
      x.add(nd)
      for child in dominated_by[nd]:
        if(child not in visited):
          downstream(child)
    # downstream of node, not root
    downstream(node)
    y = set()
    for nd in x:
      for child in cfg[nd]:
        y.add(child)

    x.remove(node)  
    frontiers[node] = y.difference(x)
  return frontiers

def compare(dom1, dom2):
  assert(len(dom1) == len(dom2) and key in dom2 for key in dom1)
  for key in dom1:
    assert(dom1[key] == dom2[key])

if __name__ == "__main__":
  program_str = "".join(sys.stdin.readlines())
  program = json.loads(program_str)
  instrs = program["functions"][-1]["instrs"]
  print([program["functions"][x]["name"] for x in range(len(program["functions"]))])
  cfg = build_cfg(change_labels(function_blocks(instrs)))
  fast = fast_traverse(cfg)
  slow = slow_traverse(cfg)
  compare(fast, slow)
  print(frontier(cfg))