import json
import os

import variables as var

default_lang_dict = {}
lang_dict = {}
default_lib_lang_dicts = {}
lib_lang_dicts = {}

def load_lang(lang):
    global lang_dict, default_lang_dict, lib_lang_dicts, default_lib_lang_dicts
    with open("lang/en_US.json", "r") as f:
        default_lang_dict = json.load(f)
    with open(f"lang/{lang}.json", "r") as f:
        lang_dict = json.load(f)

    # Extend with the help strings from the libs.
    folder_path = var.config.get('commands', 'lib-path')
    flibs_enabled = json.loads(var.config.get('commands', 'enabled_modules'))

    for flib in os.listdir(folder_path):
        if flib in flibs_enabled:
            try:
                with open("lang/en_US.json", "r") as f:
                    default_lib_lang_dicts[flib] = json.load(f)
                with open(f"local-lib/{flib}/lang/{lang}.json", "r") as f:
                    lib_lang_dicts[flib] = json.load(f)
                    # Extend lang_dict help line
                    helpstring_extend = lib_lang_dicts[flib]['cli'][flib]['help']
                    lang_dict['cli']['help'] = lang_dict['cli']['help'] + helpstring_extend
            except FileNotFoundError:
                raise FileNotFoundError(f'Local lang error importing language file: local-lib/{flib}/lang/{lang}.json.')


def tr_lib(option, libname, *argv, **kwargs):
    try:
        if option in lib_lang_dicts[libname]['lib'] and lib_lang_dicts[libname]['lib'][option]:
            string = lib_lang_dicts[libname]['lib'][option]
        else:
            string = default_lib_lang_dicts[libname]['lib'][option]
    except KeyError:
        raise KeyError(f"Missed strings in {libname} language file: '{option}'.")
    return _tr(string, *argv, **kwargs)


def tr_cli(option, *argv, **kwargs):
    try:
        if option in lang_dict['cli'] and lang_dict['cli'][option]:
            string = lang_dict['cli'][option]
        else:
            string = default_lang_dict['cli'][option]
    except KeyError:
        raise KeyError(f"Missed strings in language file: '{option}'.")
    return _tr(string, *argv, **kwargs)


def tr_web(option, *argv, **kwargs):
    try:
        if option in lang_dict['web'] and lang_dict['web'][option]:
            string = lang_dict['web'][option]
        else:
            string = default_lang_dict['web'][option]
    except KeyError:
        raise KeyError(f"Missed strings in language file: '{option}'.")
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
