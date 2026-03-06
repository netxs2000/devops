import requests
import urllib3


urllib3.disable_warnings()

URL_BASE = "https://rdm.tjhq.com"
ACCOUNT = "xushen"
PASSWORD = "DQPIxs@123"


def get_token():
    url = f"{URL_BASE}/api.php/v1/tokens"
    payload = {"account": ACCOUNT, "password": PASSWORD}
    headers = {"Content-Type": "application/json"}

    print(f"Attempting to get token from {url}...")
    try:
        r = requests.post(url, json=payload, headers=headers, verify=False, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")

        if r.status_code in {200, 201}:
            data = r.json()
            token = data.get("token")
            if token:
                print(f"\nSUCCESS! New Token: {token}")
                return token
            else:
                print("Token not found in response.")
        else:
            print(f"Failed to get token. Status: {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")

    # Try alternate endpoint if first one fails
    url_alt = f"{URL_BASE}/api.php?m=api&f=v1&path=/tokens"
    print(f"\nAttempting to get token from alternate URL: {url_alt}...")
    try:
        r = requests.post(url_alt, json=payload, headers=headers, verify=False, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
        if r.status_code in {200, 201}:
            data = r.json()
            token = data.get("token")
            if token:
                print(f"\nSUCCESS! New Token: {token}")
                return token
    except Exception as e:
        print(f"Error: {e}")

    return None


if __name__ == "__main__":
    token = get_token()
    if token:
        # Verify the token
        print("\nVerifying new token...")
        verify_url = f"{URL_BASE}/api.php/v1/products"
        r = requests.get(verify_url, headers={"Token": token}, verify=False)
        print(f"Verification Status: {r.status_code}")
        if r.status_code == 200:
            print("Token is valid!")
            print(f"Body snippet: {r.text[:200]}")
        else:
            print(f"Verification failed: {r.text}")
