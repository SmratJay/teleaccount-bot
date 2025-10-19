"""Remove leader panel button section from real_handlers.py"""

# Read the file
with open('handlers/real_handlers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and remove lines 173-188 (leader panel section)
# Line numbers are 0-indexed in Python
start_line = 172  # Line 173 in editor
end_line = 188  # Line 188 in editor

# Remove those lines
new_lines = lines[:start_line] + lines[end_line:]

# Write back
with open('handlers/real_handlers.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Removed leader panel button section")
print(f"   Deleted lines {start_line+1} to {end_line}")
print(f"   Total lines removed: {end_line - start_line}")
