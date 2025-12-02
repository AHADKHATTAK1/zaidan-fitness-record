"""
Remove duplicate function definitions from app.py
Keeps only the FIRST occurrence of each function
"""
import re
import sys

# Function to remove (pass as command line arg or default to get_upload)
func_name = sys.argv[1] if len(sys.argv) > 1 else 'get_upload'

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all lines with "def <func_name>("
def_lines = []
for i, line in enumerate(lines):
    if f'def {func_name}(' in line:
        def_lines.append(i + 1)  # 1-indexed

print(f"Found {len(def_lines)} definitions of {func_name} at lines: {def_lines}")

if len(def_lines) <= 1:
    print("No duplicates to remove!")
    exit(0)

# Keep the first one, mark others for deletion
keep_line = def_lines[0]
remove_lines = def_lines[1:]

print(f"Keeping definition at line {keep_line}")
print(f"Will remove definitions at lines: {remove_lines}")

if not remove_lines:
    print("No duplicates found!")
    exit(0)

# For each duplicate, find its block and replace with comment
output_lines = lines.copy()
removed_count = 0

for dup_line_num in remove_lines:
    idx = dup_line_num - 1  # 0-indexed
    
    # Find the end of this function (next def or @app.route at same/lower indentation)
    start_idx = idx
    end_idx = idx + 1
    
    # Get the indentation of the def line
    def_indent = len(lines[idx]) - len(lines[idx].lstrip())
    
    # Scan forward to find the end of the function
    while end_idx < len(output_lines):
        line = output_lines[end_idx]
        stripped = line.lstrip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            end_idx += 1
            continue
        
        # Check indentation
        current_indent = len(line) - len(stripped)
        
        # If we hit a line at same or lower indentation that's a def or decorator, we're done
        if current_indent <= def_indent:
            if stripped.startswith('@') or stripped.startswith('def '):
                break
        
        end_idx += 1
    
    print(f"\nRemoving duplicate {func_name} from lines {start_idx+1} to {end_idx}")
    
    # Replace the entire block with a single comment
    comment = f"# Duplicate removed: {func_name} (kept first definition at line {keep_line})\n"
    
    # Remove the block
    for i in range(start_idx, end_idx):
        output_lines[i] = ''
    
    # Add comment at the start
    output_lines[start_idx] = comment
    removed_count += 1

# Write the cleaned file
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print(f"\n✓ Removed {removed_count} duplicate {func_name} definitions")
print("File saved!")
