"""TODO: Add module description."""
import sys
import os
sys.path.append(os.getcwd())
from devops_collector.models.base_models import Organization, User
from sqlalchemy import inspect
print('Inspecting Organization mapper:')
try:
    insp = inspect(Organization)
    for prop in insp.attrs:
        print(f'Prop: {prop.key} -> {prop}')
except Exception as e:
    print(f'Error inspecting Organization: {e}')
print('\nInspecting User mapper:')
try:
    insp = inspect(User)
    for prop in insp.attrs:
        print(f'Prop: {prop.key} -> {prop}')
except Exception as e:
    print(f'Error inspecting User: {e}')