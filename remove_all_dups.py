"""
Remove ALL duplicate function definitions from app.py automatically
Keeps only the FIRST occurrence of each function
"""
from collections import defaultdict

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all function definitions
func_defs = defaultdict(list)
for i, line in enumerate(lines):
    if line.strip().startswith('def ') and '(' in line:
        func_name = line.strip().split('(')[0].replace('def ', '')
        func_defs[func_name].append(i)

# Identify duplicates (keep first, mark rest for removal)
to_remove = []
for name, indices in func_defs.items():
    if len(indices) > 1:
        # Keep first, remove rest
        for idx in indices[1:]:
            to_remove.append((idx, name))

print(f"Found {len(to_remove)} duplicate functions to remove")

# Sort by line number descending (remove from bottom up to preserve indices)
to_remove.sort(reverse=True)

output_lines = lines.copy()
removed_count = 0

for start_idx, func_name in to_remove:
    # Find the end of this function
    end_idx = start_idx + 1
    def_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    
    while end_idx < len(output_lines):
        line = output_lines[end_idx]
        stripped = line.lstrip()
        
        if not stripped or stripped.startswith('#'):
            end_idx += 1
            continue
        
        current_indent = len(line) - len(stripped)
        
        if current_indent <= def_indent:
            if stripped.startswith('@') or stripped.startswith('def ') or stripped.startswith('class '):
                break
        
        end_idx += 1
    
    print(f"Removing {func_name} at lines {start_idx+1}-{end_idx}")
    
    # Replace with comment
    comment = f"# Duplicate removed: {func_name}\n"
    for i in range(start_idx, end_idx):
        output_lines[i] = ''
    output_lines[start_idx] = comment
    removed_count += 1

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print(f"\n✓ Removed {removed_count} duplicate functions")
print("File saved!")
