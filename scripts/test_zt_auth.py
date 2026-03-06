import requests
import urllib3


urllib3.disable_warnings()

url = "https://rdm.tjhq.com/api.php/v1/products"
token = "a7794c49367d7b089be2e170354584d7"


def test_headers():
    variants = [
        {"Token": token},
        {"x-zentao-token": token},
        {"Authorization": f"Bearer {token}"},
        {"Cookie": f"zentaosid={token}"},
    ]

    for headers in variants:
        print(f"\nTesting headers: {headers}")
        try:
            r = requests.get(url, headers=headers, verify=False, timeout=5)
            print(f"Status: {r.status_code}")
            print(f"Response: {r.text[:200]}")
            if r.status_code == 200:
                print("✓ SUCCESS with these headers!")
                return
        except Exception as e:
            print(f"Error: {e}")

    print("\nTesting query param ?token=...")
    r = requests.get(f"{url}?token={token}", verify=False, timeout=5)
    print(f"Status: {r.status_code}, Response: {r.text[:200]}")

    print("\nTesting query param ?zentaosid=...")
    r = requests.get(f"{url}?zentaosid={token}", verify=False, timeout=5)
    print(f"Status: {r.status_code}, Response: {r.text[:200]}")


if __name__ == "__main__":
    test_headers()
