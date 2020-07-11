import json

import variables as var

lang_dict = {}


def load_lang(lang):
    global lang_dict
    with open(f"lang/{lang}", "r") as f:
        lang_dict = json.load(f)


def tr_cli(option, *argv, **kwargs):
    try:
        string = lang_dict['cli'][option]
    except KeyError:
        raise KeyError("Missed strings in language file: '{string}'. ".format(string=option))
    return _tr(string, *argv, **kwargs)


def tr_web(option, *argv, **kwargs):
    try:
        string = lang_dict['web'][option]
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
