#!/usr/bin/env python

import os
import requests

base_url = "https://translate.azlux.fr/api/v1"
project_id = "4aafb197-3282-47b3-a197-0ca870cf6ab2"
r_client = "be8215d4-2417-49db-9355-c418f26dc3f4"
r_secret = "MIMvdnECLkmTZyCQT4DekONN53EOSsj3"
w_client = os.environ.get("TRADUORA_W_CLIENT", default=None)
w_secret = os.environ.get("TRADUORA_W_SECRET", default=None)


def fetch_translation():
    print("Fetching translation from remote host...")
    data = {"grant_type": "client_credentials",
            "client_id": r_client,
            "client_secret": r_secret}

    r = requests.post(f"{base_url}/auth/token", json=data)
    token = r.json()["access_token"]

    headers = {"Authorization": "Bearer " + token,
               "Accept": "application/json, text/plain, */*"}

    r = requests.get(f"{base_url}/projects/{project_id}/translations", headers=headers)
    translations = r.json()['data']
    for translation in translations:
        lang_code = translation['locale']['code']
        print(f" - Fetching {lang_code}")
        params = {'locale': lang_code,
                  'format': 'jsonnested'}
        r = requests.get(f"{base_url}/projects/{project_id}/exports", params=params, headers=headers)
        with open(lang_code, "wb") as f:
            f.write(r.content)


def push_strings():
    print("Pushing local en_US file into the remote host...")
    data = {"grant_type": "client_credentials",
            "client_id": w_client,
            "client_secret": w_secret}

    r = requests.post(f"{base_url}/auth/token", json=data)
    token = r.json()["access_token"]

    headers = {"Authorization": "Bearer " + token,
               "Accept": "application/json, text/plain, */*"}

    params = {'locale': 'en_US',
              'format': 'jsonnested'}

    files = {'file': open('lang/en_US', 'r')}
    r = requests.post(f"{base_url}/projects/{project_id}/exports", data=params, headers=headers, files=files)
    assert r.status_code == 200, "Unable to push local en_US file into remote host."


if w_client and w_secret:
    print("Detected writable API keys from environ.")
    push_strings()

fetch_translation()

print("Done.")
