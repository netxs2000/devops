import os
import re

# Logic to rename files 0..17 -> 1..18, leaving 19 alone.
pages_dir = r"c:\Users\netxs\devops\devops\dashboard\pages"

files_to_rename = []
file_19_exists = False

# 1. Scan directory
for f in os.listdir(pages_dir):
    match = re.match(r"^(\d+)_(.*\.py)$", f)
    if match:
        num = int(match.group(1))
        name_part = match.group(2)
        
        if 0 <= num <= 17:
            files_to_rename.append((num, name_part, f))
        elif num == 19:
            file_19_exists = True
            print(f"File {f} is already 19, leaving it as is.")
        else:
            print(f"Skipping unexpected file number: {f}")

# 2. Sort descending (17 -> 18, 16 -> 17 ... 0 -> 1) to avoid overwriting
files_to_rename.sort(key=lambda x: x[0], reverse=True)

# 3. Rename
print("Starting rename process...")
for num, name_part, old_filename in files_to_rename:
    new_num = num + 1
    new_filename = f"{new_num}_{name_part}"
    
    old_path = os.path.join(pages_dir, old_filename)
    new_path = os.path.join(pages_dir, new_filename)
    
    print(f"Renaming {old_filename} -> {new_filename}")
    os.rename(old_path, new_path)

print("Rename complete.")
