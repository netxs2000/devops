#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清理base_models.py中的null bytes"""

with open('devops_collector/models/base_models.py', 'rb') as f:
    data = f.read()

null_count = data.count(b'\x00')
print(f'Found {null_count} null bytes in base_models.py')

if null_count > 0:
    clean_data = data.replace(b'\x00', b'')
    with open('devops_collector/models/base_models.py', 'wb') as f:
        f.write(clean_data)
    print(f'Removed {null_count} null bytes')
else:
    print('No null bytes found')
