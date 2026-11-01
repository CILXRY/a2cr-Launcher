import time

import requests

CLIENT_ID = ""


def start_device_flow():
    res = requests.post(url='https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode',
                        data={"client_id": CLIENT_ID,
                              "scope": "XboxLive.signin offline_access"},
                        headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()

    return {"user_code": res.get("user_code", ""),
            "device_code": res.get("device_code", ""),
            "verification_uri": res.get("verification_uri", ""),
            "expires_in": res.get("expires_in", 900),
            "interval": res.get("interval", 5)}


def poll_for_token() -> dict:
    front = start_device_flow()
    print(f"To sign in, open ", front["verification_uri"], " and input", front["user_code"], "in the input-box.")

    for _ in range(front["expires_in"] // front["interval"]):
        res = requests.post(url='https://login.microsoftonline.com/consumers/oauth2/v2.0/token',
                            data={"client_id": CLIENT_ID, "device_code": front["device_code"],
                                  "grant_type": "urn:ietf:params:oauth:grant-type:device_code"},
                            headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
        if res.get("access_token"):
            return {"access_token": res["access_token"], "refresh_token": res.get("refresh_token", "")}
        else:
            if res.get("error") == "authorization_pending":
                time.sleep(front["interval"])
                print("Authorization pending..")
            elif res.get("error") == "slow_down":
                time.sleep(front["interval"] + 5)
            else:
                print("Authorization failed..")
                break

    raise RuntimeError("获取 Token 过程中出现错误")


if __name__ == '__main__':
    print(poll_for_token())
