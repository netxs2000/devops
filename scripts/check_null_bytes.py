import os
from pathlib import Path

def check_null_bytes(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = Path(root) / file
                try:
                    content = path.read_bytes()
                    if b'\x00' in content:
                        print(f"NULL BYTES FOUND IN: {path}")
                    else:
                        pass
                except Exception as e:
                    print(f"Error reading {path}: {e}")

if __name__ == "__main__":
    check_null_bytes("devops_collector/models")
    check_null_bytes("dagster_repo")
