import sys

def sanitize(path):
    with open(path, 'rb') as f:
        data = f.read()
    
    # Remove BOM
    if data.startswith(b'\xef\xbb\xbf'):
        data = data[3:]
    
    # Remove null bytes
    data = data.replace(b'\x00', b'')
    
    # Try to decode as utf-8, replace errors
    text = data.decode('utf-8', errors='replace')
    
    # Write back as clean utf-8
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"Sanitized {path}")

if __name__ == "__main__":
    sanitize("devops_collector/models/base_models.py")
