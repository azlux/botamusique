#!/usr/bin/env python3

import os
import re
import argparse
import requests

base_url = "https://translate.azlux.fr/api/v1"
project_id = "4aafb197-3282-47b3-a197-0ca870cf6ab2"

lang_dir = ""


def get_access_header(client, secret):
    data = {"grant_type": "client_credentials",
            "client_id": client,
            "client_secret": secret}

    r = requests.post(f"{base_url}/auth/token", json=data)

    if r.status_code != 200:
        print("Access denied! Please check your client ID or secret.")
        exit(1)

    token = r.json()["access_token"]

    headers = {"Authorization": "Bearer " + token,
               "Accept": "application/json, text/plain, */*"}

    return headers


def fetch_translation(r_client, r_secret):
    headers = get_access_header(r_client, r_secret)

    r = requests.get(f"{base_url}/projects/{project_id}/translations", headers=headers)
    translations = r.json()['data']
    for translation in translations:
        lang_code = translation['locale']['code']
        print(f" - Fetching {lang_code}")
        params = {'locale': lang_code,
                  'format': 'jsonnested'}
        r = requests.get(f"{base_url}/projects/{project_id}/exports", params=params, headers=headers)
        with open(os.path.join(lang_dir, f"{lang_code}.json"), "wb") as f:
            f.write(r.content)


def push_strings(w_client, w_secret):
    print("Pushing local translation files into the remote host...")
    headers = get_access_header(w_client, w_secret)

    lang_files = os.listdir(lang_dir)
    lang_list = []
    for lang_file in lang_files:
        match = re.search("([a-z]{2}_[A-Z]{2})\.json", lang_file)
        if match:
            lang_list.append(match[1])

    for lang in lang_list:
        print(f" - Pushing {lang}")

        params = {'locale': lang,
                  'format': 'jsonnested'}
        files = {'file': open(os.path.join(lang_dir, f"{lang}.json"), 'r')}

        r = requests.post(f"{base_url}/projects/{project_id}/imports", params=params, headers=headers, files=files)
        assert r.status_code == 200, f"Unable to push {lang} into remote host. {r.status_code}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync translation files with azlux's traduora server.")

    parser.add_argument("--lang-dir", dest="lang_dir",
                        type=str, help="Directory of the lang files.")
    parser.add_argument("--client", dest="client",
                        type=str, help="Client ID used to access the server.")
    parser.add_argument("--secret", dest="secret",
                        type=str, help="Secret used to access the server.")

    parser.add_argument("--fetch", dest='fetch', action="store_true",
                        help='Fetch translation files from the server.')
    parser.add_argument("--push", dest='push', action="store_true",
                        help='Push local translation files into the server.')

    args = parser.parse_args()

    lang_dir = args.lang_dir

    if not args.client or not args.secret:
        print("Client ID and secret need to be provided!")
        exit(1)

    if args.push:
        push_strings(args.client, args.secret)

    if args.fetch:
        fetch_translation(args.client, args.secret)

    print("Done.")

