#!/usr/bin/env python3
import argparse
import os
import json
import re
import jinja2

default_lang_dict = {}
lang_dict = {}

lang_dir = ""
template_dir = ""


def load_lang(lang):
    with open(os.path.join(lang_dir, f"{lang}.json"), "r") as f:
        return json.load(f)


def tr(option):
    try:
        if option in lang_dict['web'] and lang_dict['web'][option]:
            string = lang_dict['web'][option]
        else:
            string = default_lang_dict['web'][option]
        return string
    except KeyError:
        raise KeyError("Missed strings in language file: '{string}'. "
                       .format(string=option))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Populate html templates with translation strings.")

    parser.add_argument("--lang-dir", dest="lang_dir",
                        type=str, help="Directory of the lang files.")
    parser.add_argument("--template-dir", dest="template_dir",
                        type=str, help="Directory of the template files.")

    args = parser.parse_args()
    lang_dir = args.lang_dir
    template_dir = args.template_dir

    html_files = os.listdir(template_dir)
    for html_file in html_files:
        match = re.search("(.+)\.template\.html", html_file)
        if match is None:
            continue

        print(f"Populating {html_file} with translations...")
        basename = match[1]
        with open(os.path.join(template_dir, f"{html_file}"), "r") as f:
            html = f.read()

        lang_files = os.listdir(lang_dir)
        lang_list = []

        default_lang_dict = load_lang("en_US")

        for lang_file in lang_files:
            match = re.search("([a-z]{2}_[A-Z]{2})\.json", lang_file)
            if match:
                lang_list.append(match[1])

        template = jinja2.Template(html)

        for lang in lang_list:
            print(f" - Populating {lang}...")
            lang_dict = load_lang(lang)

            with open(os.path.join(template_dir, f"{basename}.{lang}.html"),
                      "w") as f:
                f.write(template.render(tr=tr))
    print("Done.")
