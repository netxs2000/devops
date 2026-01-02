from pathlib import Path

def clean_file(path_str):
    path = Path(path_str)
    if not path.exists():
        print(f"File {path_str} not found.")
        return
    
    content = path.read_bytes()
    clean_content = content.replace(b'\x00', b'')
    
    if content != clean_content:
        path.write_bytes(clean_content)
        print(f"Cleaned null bytes from {path_str}")
    else:
        print(f"No null bytes found in {path_str}")

if __name__ == "__main__":
    clean_file("devops_collector/models/base_models.py")
