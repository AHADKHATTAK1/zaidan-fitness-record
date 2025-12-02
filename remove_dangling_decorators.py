"""
Remove dangling Flask decorators (e.g., @app.route, @login_required) that are not
followed by a function definition due to duplicate-cleanup.
Keeps valid decorator stacks that are immediately followed by a 'def ...'.
"""
from typing import List

DECORATOR_PREFIXES = (
    "@app.route(",
    "@login_required",
    "@admin_required",
    "@scheduler.task",
)

def is_decorator(line: str) -> bool:
    s = line.lstrip()
    return any(s.startswith(p) for p in DECORATOR_PREFIXES)

with open('app.py', 'r', encoding='utf-8') as f:
    lines: List[str] = f.readlines()

out: List[str] = []
N = len(lines)

i = 0
removed_blocks = 0
while i < N:
    line = lines[i]
    if is_decorator(line):
        # Collect a contiguous block of decorators/comments/blank lines
        start = i
        j = i
        saw_decorator = False
        while j < N:
            s = lines[j].lstrip()
            if not s or s.startswith('#') or is_decorator(lines[j]):
                if is_decorator(lines[j]):
                    saw_decorator = True
                j += 1
                continue
            # Found first non-empty, non-comment, non-decorator line
            break
        # Now s at j is meaningful content or j == N
        if j < N and lines[j].lstrip().startswith('def '):
            # Valid stack; emit original lines unchanged
            out.extend(lines[start:j])
            # Continue normally from j (the def and beyond)
            i = j
            continue
        else:
            # Dangling decorators without a following def; remove them all
            out.append(f"# Removed dangling decorators block from lines {start+1}-{j}\n")
            removed_blocks += 1
            i = j
            continue
    else:
        out.append(line)
        i += 1

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(out)

print(f"Removed {removed_blocks} dangling decorator blocks")
