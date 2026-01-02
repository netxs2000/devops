"""TODO: Add module description."""
import sys
import os
import importlib
sys.path.append(os.getcwd())
modules_to_check = ['devops_collector.core.base_worker', 'devops_collector.models.base_models', 'devops_collector.plugins.gitlab.worker', 'devops_collector.plugins.sonarqube.worker', 'devops_collector.plugins.sonarqube.transformer', 'devops_collector.core.utils']
print('Starting import verification...')
failed = False
for module_name in modules_to_check:
    try:
        importlib.import_module(module_name)
        print(f'[OK] {module_name}')
    except Exception as e:
        print(f'[FAIL] {module_name}: {e}')
        failed = True
if failed:
    print('\nVerification FAILED.')
    sys.exit(1)
else:
    print('\nAll modules imported successfully.')
    sys.exit(0)