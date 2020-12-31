import os
import json

import variables as var

default_lang_dict = {}
lang_dict = {}


def load_lang(lang):
    global lang_dict, default_lang_dict
    root_dir = os.path.dirname(__file__)
    with open(os.path.join(root_dir, "lang/en_US.json"), "r") as f:
        default_lang_dict = json.load(f)
    with open(os.path.join(root_dir, f"lang/{lang}.json"), "r") as f:
        lang_dict = json.load(f)


def tr_cli(option, *argv, **kwargs):
    try:
        if option in lang_dict['cli'] and lang_dict['cli'][option]:
            string = lang_dict['cli'][option]
        else:
            string = default_lang_dict['cli'][option]
    except KeyError:
        raise KeyError("Missed strings in language file: '{string}'. ".format(string=option))
    return _tr(string, *argv, **kwargs)


def tr_web(option, *argv, **kwargs):
    try:
        if option in lang_dict['web'] and lang_dict['web'][option]:
            string = lang_dict['web'][option]
        else:
            string = default_lang_dict['web'][option]
    except KeyError:
        raise KeyError("Missed strings in language file: '{string}'. ".format(string=option))
    return _tr(string, *argv, **kwargs)


def _tr(string, *argv, **kwargs):
    if argv or kwargs:
        try:
            formatted = string.format(*argv, **kwargs)
            return formatted
        except KeyError as e:
            raise KeyError(
                "Missed/Unexpected placeholder {{{placeholder}}} in string "
                "'{string}'. ".format(placeholder=str(e).strip("'"),
                                      string=string))
        except TypeError:
            raise KeyError(
                "Missed placeholder in string '{string}'. ".format(string=string))
    else:
        return string


def commands(command):
    try:
        string = var.config.get("commands", command)
        return string
    except KeyError:
        raise KeyError("Missed command in configuration file: '{string}'. ".format(string=command))
