import requests
import urllib3


urllib3.disable_warnings()

paths = [
    "/api.php/v1/products",
    "/zentao/api.php/v1/products",
    "/z/api.php/v1/products",
    "/index.php?m=api&f=getsession",
    "/api.php?m=api&f=getsession",
    "/zentao/api.php?m=api&f=getsession",
]

ip = "198.18.0.47"


def probe():
    for p in paths:
        url = f"http://{ip}{p}"
        print(f"Probing {url}...")
        try:
            r = requests.get(url, timeout=3)
            print(f"Status: {r.status_code}, Length: {len(r.text)}")
            if r.status_code == 200:
                print(f"Body snippet: {r.text[:100]}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    probe()
