#!/usr/bin/python3

import configparser
import os
import variables as var

__CONFIG = configparser.ConfigParser(interpolation=None)
__CONFIG.read("configuration.ini", encoding='latin-1')

def get_recursive_filelist_sorted(path):
    filelist = []
    for root, dirs, files in os.walk(path):
        relroot = root.replace(path, '')
        if relroot != '' and relroot in __CONFIG.get('bot', 'ignored_folders'):
            continue
        if len(relroot):
            relroot += '/'
        for file in files:
            if file in __CONFIG.get('bot', 'ignored_files'):
                continue
            filelist.append(relroot + file)

    filelist.sort()
    return filelist

class Dir(object):
    def __init__(self, name):
        self.name = name
        self.subdirs = {}
        self.files = []

    def add_file(self, file):
        if file.startswith(self.name + '/'):
            file = file.replace(self.name + '/', '')

        if '/' in file:
            # This file is in a subdir
            subdir = file.split('/')[0]
            if subdir in self.subdirs:
                self.subdirs[subdir].add_file(file)
            else:
                self.subdirs[subdir] = Dir(subdir)
                self.subdirs[subdir].add_file(file)
        else:
            self.files.append(file)
        return True

    def get_subdirs(self, path=None):
        if path and path != '':
            subdir = path.split('/')[0]
            if subdir in self.subdirs:
                searchpath = '/'.join(path.split('/')[1::])
                return self.subdirs[subdir].get_subdirs(searchpath)
        else:
            return self.subdirs


    def get_files(self, path=None):
        if path and path != '':
            subdir = path.split('/')[0]
            if subdir in self.subdirs:
                searchpath = '/'.join(path.split('/')[1::])
                return self.subdirs[subdir].get_files(searchpath)
        else:
            return self.files

    def get_files_recursively(self, path=None):
        print('in get_files_recursively', path)
        if path and path != '':
            subdir = path.split('/')[0]
            if subdir in self.subdirs:
                searchpath = '/'.join(path.split('/')[1::])
                return self.subdirs[subdir].get_files_recursively(searchpath)
        else:
            files = self.files

            for key, val in self.subdirs.items():
                files.extend(map(lambda file: key + '/' + file,val.get_files_recursively()))

        return files

    def render_text(self, ident=0):
        print('{}{}/'.format(' ' * (ident * 4), self.name))
        for key, val in self.subdirs.items():
            val.render_text(ident+1)
        for file in self.files:
            print('{}{}'.format(' ' * ((ident + 1)) * 4, file))
