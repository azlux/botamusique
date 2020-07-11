#!/usr/bin/env python3

import requests

base_url = "https://translate.azlux.fr/api/v1"
client = "be8215d4-2417-49db-9355-c418f26dc3f4"
secret = "MIMvdnECLkmTZyCQT4DekONN53EOSsj3"
project_id = "4aafb197-3282-47b3-a197-0ca870cf6ab2"

data = {"grant_type": "client_credentials",
        "client_id": client,
        "client_secret": secret}

r = requests.post(f"{base_url}/auth/token", json=data)
token = r.json()["access_token"]

headers = {"Authorization": "Bearer " + token,
           "Accept": "application/json, text/plain, */*"}

r = requests.get(f"{base_url}/projects/{project_id}/translations", headers=headers)
translations = r.json()['data']
for translation in translations:
    lang_code = translation['locale']['code']
    params = {'locale': lang_code,
              'format': 'jsonnested'}
    r = requests.get(f"{base_url}/projects/{project_id}/exports", params=params, headers=headers)
    with open(lang_code, "wb")as f:
        f.write(r.content)
