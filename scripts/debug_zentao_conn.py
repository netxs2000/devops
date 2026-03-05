import requests
import urllib3
import json

urllib3.disable_warnings()

# Configuration from .env context
URL_BASE = "https://rdm.tjhq.com"
TOKEN = "a7794c49367d7b089be2e170354584d7"

def probe_api():
    print(f"Propbing ZenTao at {URL_BASE}...")
    
    # List of possible API endpoints and their auth style
    probes = [
        # REST API v1 (Default PathInfo)
        {"url": f"{URL_BASE}/api.php/v1/products", "headers": {"Token": TOKEN}},
        # REST API v1 (Common PathInfo)
        {"url": f"{URL_BASE}/zentao/api.php/v1/products", "headers": {"Token": TOKEN}},
        # REST API v1 (GET mode)
        {"url": f"{URL_BASE}/api.php?m=api&f=v1&path=/products", "headers": {"Token": TOKEN}},
        
        # Old API (Session based)
        {"url": f"{URL_BASE}/api.php?m=api&f=getsession&t=json", "headers": {}},
        
        # Try Token as cookie
        {"url": f"{URL_BASE}/api.php/v1/products", "headers": {"Cookie": f"zentaosid={TOKEN}"}},
        {"url": f"{URL_BASE}/api.php/v1/products", "headers": {"Cookie": f"za={TOKEN}"}},
    ]

    for p in probes:
        print(f"\n--- Testing: {p['url']} ---")
        try:
            r = requests.get(p['url'], headers=p['headers'], verify=False, timeout=5)
            print(f"Status: {r.status_code}")
            print(f"Headers: {dict(r.headers)}")
            print(f"Response Body: {r.text[:300]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    probe_api()
