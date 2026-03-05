import requests
import json
import urllib3

urllib3.disable_warnings()

def check_structure():
    token = "e745103d5c00e1b8182f7af931ec83ad"
    urls = [
        "https://rdm.tjhq.com/api.php/v1/departments",
        "https://rdm.tjhq.com/api.php/v1/users",
        "https://rdm.tjhq.com/api.php/v1/products/1/plans",
        "https://rdm.tjhq.com/api.php/v1/executions"
    ]
    
    for u in urls:
        print(f"\n--- Checking {u} ---")
        try:
            r = requests.get(u, headers={"Token": token}, verify=False, timeout=10)
            data = r.json()
            print(f"Status: {r.status_code}")
            print(f"Type of data: {type(data)}")
            if isinstance(data, list):
                print(f"Length: {len(data)}")
                print(f"First item keys: {data[0].keys() if data else 'N/A'}")
            elif isinstance(data, dict):
                print(f"Keys: {data.keys()}")
            else:
                print(f"Data: {str(data)[:500]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_structure()
