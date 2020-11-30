# -*- coding: utf-8 -*-

import logging
import os
import sys
import importlib
import json

#import interface
#import util
import variables as var


log = logging.getLogger("bot")

class ExtensionFailed(LookupError):
    pass

class NoEntryPointError(LookupError):
    pass

class ExtensionNotFound(LookupError):
    pass


def load_lib(bot, libname):
    # The extension name to load. It must be dot separated like
    # regular Python imports if accessing a sub-module. e.g.
    # foo.typical if you want to import ``foo/typical.py``.
    # https://docs.python.org/3.8/library/importlib.html

    log.info(f'lib import: setting up local lib: {libname}')
    try:
        # Find the spec for a module, optionally relative to the specified package name
        spec = importlib.util.find_spec(f'{libname}.typ_{libname}')
        log.debug(f'load_lib: activate: {libname}, spec : {spec}')

        if spec is None:
            raise ExtensionNotFound()
        lm = 'loadmod'
        # Create a new module based on spec.
        lib = importlib.util.module_from_spec(spec)
        sys.modules[lm] = lib
    except Exception as e:
        log.debug(f'load_lib: failed to import lib file{spec}\n{e}')

    # load file
    try:
        # Execute the module in its own namespace when a module is imported or reloaded.
        log.debug(f'load_lib: try loading {lib}')
        spec.loader.exec_module(lib)
    except Exception as e:
        del sys.modules[lm]
        log.debug(f'{e}')
        raise ExtensionFailed()

    # load plugin
    try:
        load_plugin = getattr(lib, 'load_plugin')
        load_plugin(bot)
    except AttributeError:
        del sys.modules[lm]
        raise NoEntryPointError()
    else:
        log.debug(f'load_lib: self.__extensions[{load_plugin}]')


def import_all_local_libs(bot):
    # Gather libs from lib-path folder
    folder_path = var.config.get('commands', 'lib-path')
    flibs_enabled = json.loads(var.config.get('commands', 'enabled_modules'))
    log.info(f'lib import: enabled local-libs: {flibs_enabled}')
    for flib in flibs_enabled:
        if not flib in os.listdir(folder_path):
            log.info(f'lib import: "{flib}" is enabled in config, but does not exist in local-lib directory')

    for flib in os.listdir(folder_path):
        if flib in flibs_enabled:
            log.debug(f'import_all_local_libs: found source: {flib}')
            try:
                load_lib(bot, libname=flib)
            except Exception as e:
                log.info(f'lib import: error importing {flib}')
                log.debug(f'{e}')
        else:
            log.info(f'lib import: skipping source: {flib} (disabled or not installed)')
            log.info(f'lib import: to Install local lib use pip:\tvenv/bin/python -m pip install -e local-lib/mylib')

