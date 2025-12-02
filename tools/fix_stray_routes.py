"""
Fix stray @app.route decorators left from duplicate removal:
- For each function definition, collect its contiguous decorator block.
- Any @app.route lines elsewhere that reference the same route strings but are not
  part of that function's decorator block are removed (and an immediately following
  @login_required line, if present).
"""
from pathlib import Path
import re

p = Path(__file__).resolve().parent.parent / 'app.py'
lines = p.read_text(encoding='utf-8').splitlines(True)

route_re = re.compile(r"^\s*@app\.route\(([^)]*)\)")
def_re = re.compile(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\(")

# First pass: find decorator blocks for each function
func_blocks = {}  # func_name -> set of exact decorator lines
line_to_func = {}  # line index -> func_name when in that decorator block

i = 0
while i < len(lines):
    m = def_re.match(lines[i])
    if not m:
        i += 1
        continue
    func = m.group(1)
    # walk upward to collect contiguous decorators
    j = i - 1
    block = []
    while j >= 0:
        s = lines[j].strip()
        if not s:
            j -= 1
            continue
        if s.startswith('@'):
            block.append(lines[j])
            j -= 1
            continue
        break
    if block:
        block.reverse()
        func_blocks[func] = set(block)
        for k in range(j+1, i):
            line_to_func[k] = func
    i += 1

# Collect all canonical route lines from legitimate blocks
canonical_routes = set()
for block in func_blocks.values():
    for dec in block:
        if route_re.match(dec.strip()):
            canonical_routes.add(dec.strip())

out = []
pending_skip_login_req = False
for idx, line in enumerate(lines):
    s = line.strip()
    if pending_skip_login_req:
        if s.startswith('@login_required'):
            pending_skip_login_req = False
            continue
        else:
            pending_skip_login_req = False
    if s.startswith('@app.route('):
        # if this line is part of a canonical block (exact line match) keep it
        if idx in line_to_func:
            out.append(line)
            continue
        # if the exact decorator text is not in canonical set, it might be stray, remove
        if s in canonical_routes:
            pending_skip_login_req = True
            continue
    out.append(line)

p.write_text(''.join(out), encoding='utf-8')
print('✓ Fixed stray route decorators not attached to their function blocks')
