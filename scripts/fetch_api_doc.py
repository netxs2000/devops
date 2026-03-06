import requests
import urllib3


urllib3.disable_warnings()


def fetch_doc():
    url = "https://rdm.tjhq.com"
    session = requests.Session()
    session.verify = False

    # Optional GET token/zentaosid first to grab correct cookies if needed
    session.get(f"{url}/user-login.html")

    login_url = f"{url}/user-login.html"
    session.post(login_url, data={"account": "xushen", "password": "DQPIxs@123"}, headers={"Referer": login_url})

    api_url = f"{url}/dev-api-restapi.html"
    res2 = session.get(api_url)

    with open("api_doc.html", "w", encoding="utf-8") as f:
        f.write(res2.text)

    print("Done. Saved to api_doc.html. Length: ", len(res2.text))
    if "忘记密码" in res2.text:
        print("Seems login failed.")


if __name__ == "__main__":
    fetch_doc()
