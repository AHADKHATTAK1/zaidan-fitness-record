"""
Find all duplicate function definitions in app.py
"""
from collections import defaultdict

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all function definitions
func_defs = defaultdict(list)
for i, line in enumerate(lines):
    if line.strip().startswith('def ') and '(' in line:
        func_name = line.strip().split('(')[0].replace('def ', '')
        func_defs[func_name].append(i + 1)

# Show duplicates
duplicates = {name: lines for name, lines in func_defs.items() if len(lines) > 1}

if duplicates:
    print(f"Found {len(duplicates)} functions with duplicates:\n")
    for name, line_nums in sorted(duplicates.items()):
        print(f"  {name}: {len(line_nums)} copies at lines {line_nums}")
else:
    print("No duplicate functions found!")
