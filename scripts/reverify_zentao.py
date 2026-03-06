import requests
import urllib3


urllib3.disable_warnings()


def check():
    # Use current settings or provided values
    url = "https://rdm.tjhq.com/api.php/v1/products"
    token = "14677062f0da822642a26b0cd3db0ed9"

    print(f"Checking {url} with current token...")
    try:
        r = requests.get(url, headers={"Token": token}, verify=False, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("✓ URL and Token are working!")
            print(f"Response: {r.text[:200]}...")
            return True
        else:
            print(f"✗ Failed: {r.text}")
    except Exception as e:
        print(f"Error connecting: {e}")

    return False


if __name__ == "__main__":
    check()
