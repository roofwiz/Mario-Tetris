lines = []
with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix indentation for lines 4568-4570 (0-based 4567-4569) to 35 spaces
idx_start = 4567 # 4568 1-based
idx_end = 4570   # 4571 1-based (exclusive)

for i in range(idx_start, idx_end):
    content = lines[i].strip()
    lines[i] = " " * 35 + content + "\n"

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Indentation fixed to 35.")
