"""
Clean up stray duplicate route decorators for /members, /index, /home.
Keeps only the first occurrence of each and removes an immediately following
@login_required if it directly follows a removed decorator.
"""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / 'app.py'
text = p.read_text(encoding='utf-8').splitlines(True)

targets = {"/members": False, "/index": False, "/home": False}

def is_target_route(line: str) -> bool:
    s = line.strip()
    if not s.startswith("@app.route("):
        return False
    return any(f"'{k}'" in s or f'"{k}"' in s for k in targets)

def which_target(line: str):
    s = line.strip()
    for k in targets:
        if f"'{k}'" in s or f'"{k}"' in s:
            return k
    return None

out = []
pending_remove_login_required = False
for line in text:
    if pending_remove_login_required:
        if line.strip().startswith('@login_required'):
            pending_remove_login_required = False
            continue
        else:
            pending_remove_login_required = False
    if is_target_route(line):
        key = which_target(line)
        if key is None:
            out.append(line)
            continue
        if not targets[key]:
            targets[key] = True
            out.append(line)
        else:
            # Remove this duplicate and the immediately following @login_required if present
            pending_remove_login_required = True
            continue
    else:
        out.append(line)

p.write_text(''.join(out), encoding='utf-8')
print('✓ Cleaned duplicate decorators for /members, /index, /home')
