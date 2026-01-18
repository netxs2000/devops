import os

file_path = r"c:\Users\netxs\devops\devops\docs\zentao-user.csv"

with open(file_path, "r", encoding="utf-8-sig") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # 修正左真玉工号
    if "3975,左真玉," in line:
        line = line.replace("3975,左真玉,", "3974,左真玉,")
    
    # 修正张鑫名字
    if "2568,张鑫2568," in line:
        line = line.replace("2568,张鑫2568,", "2568,张鑫,")
    
    # 修正张磊名字
    if "LT-0311,张磊311," in line:
        line = line.replace("LT-0311,张磊311,", "LT-0311,张磊,")
        
    new_lines.append(line)

with open(file_path, "w", encoding="utf-8-sig") as f:
    f.writelines(new_lines)

print("CSV correction completed.")
