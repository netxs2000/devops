
# -*- coding: utf-8 -*-
import os

path = 'scripts/init_zentao_links.py'
with open(path, 'rb') as f:
    content = f.read().decode('utf-8', errors='replace')

# Fix the broken triple quotes
content = content.replace('"""同步产品关联，支持多种匹配策略\ufffd""', '"""同步产品关联，支持多种匹配策略"""')
content = content.replace('"""同步项目关联，支持多种匹配策略\ufffd""', '"""同步项目关联，支持多种匹配策略"""')
# Also fix other potential ones
content = content.replace('策略 B: 如果 Ref 匹配\ufffdProduct', '策略 B: 如果 Ref 匹配 Product')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed!")
