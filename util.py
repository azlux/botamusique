#!/usr/bin/python3

import hashlib
import magic
import os
import variables as var
import zipfile
import urllib.request
import subprocess as sp
import logging
import youtube_dl
from importlib import reload

def get_recursive_filelist_sorted(path):
    filelist = []
    for root, dirs, files in os.walk(path):
        relroot = root.replace(path, '', 1)
        if relroot != '' and relroot in var.config.get('bot', 'ignored_folders'):
            continue
        if len(relroot):
            relroot += '/'
        for file in files:
            if file in var.config.get('bot', 'ignored_files'):
                continue

            fullpath = os.path.join(path, relroot, file)
            if not os.access(fullpath, os.R_OK):
                continue

            mime = magic.from_file(fullpath, mime=True)
            if 'audio' in mime or 'audio' in magic.from_file(fullpath).lower() or 'video' in mime:
                filelist.append(relroot + file)

    filelist.sort()
    return filelist


# - zips all files of the given zippath (must be a directory)
# - returns the absolute path of the created zip file
# - zip file will be in the applications tmp folder (according to configuration)
# - format of the filename itself = prefix_hash.zip
#       - prefix can be controlled by the caller
#       - hash is a sha1 of the string representation of the directories' contents (which are
#           zipped)
def zipdir(zippath, zipname_prefix=None):
    zipname = var.config.get('bot', 'tmp_folder')
    if zipname_prefix and '../' not in zipname_prefix:
        zipname += zipname_prefix.strip().replace('/', '_') + '_'

    files = get_recursive_filelist_sorted(zippath)
    hash = hashlib.sha1((str(files).encode())).hexdigest()
    zipname += hash + '.zip'

    if os.path.exists(zipname):
        return zipname

    zipf = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)

    for file in files:
        file_to_add = os.path.join(zippath, file)
        if not os.access(file_to_add, os.R_OK):
            continue
        if file in var.config.get('bot', 'ignored_files'):
            continue

        add_file_as = os.path.relpath(os.path.join(zippath, file), os.path.join(zippath, '..'))
        zipf.write(file_to_add, add_file_as)

    zipf.close()
    return zipname


def write_db():
    with open(var.dbfile, 'w') as f:
        var.db.write(f)


def get_user_ban():
    res = "List of ban hash"
    for i in var.db.items("user_ban"):
        res += "<br/>" + i[0]
    return res


def update(version):
    v = int(urllib.request.urlopen(urllib.request.Request("https://azlux.fr/botamusique/version")).read())
    if v > version:
        logging.info('New version, starting update')
        tp = sp.check_output(['/usr/bin/env', 'bash', 'update.sh']).decode()
        logging.debug(tp)
        logging.info('Update pip librairies dependancies')
        tp = sp.check_output([var.config.get('bot', 'pip3_path'), 'install', '--upgrade', '-r', 'requirements.txt']).decode()
        msg = "New version installed"
        
    else:
        logging.info('Starting update youtube-dl via pip3')
        tp = sp.check_output([var.config.get('bot', 'pip3_path'), 'install', '--upgrade', 'youtube-dl']).decode()
        msg = ""
        if "Requirement already up-to-date" in tp:
            msg += "Youtube-dl is up-to-date"
        else:
            msg += "Update done : " + tp.split('Successfully installed')[1]
    reload(youtube_dl)
    msg += "<br/> Youtube-dl reloaded"
    return msg


def user_ban(user):
    var.db.set("user_ban", user, None)
    res = "User " + user + " banned"
    write_db()
    return res


def user_unban(user):
    var.db.remove_option("user_ban", user)
    res = "Done"
    write_db()
    return res


def get_url_ban():
    res = "List of ban hash"
    for i in var.db.items("url_ban"):
        res += "<br/>" + i[0]
    return res


def url_ban(url):
    var.db.set("url_ban", url, None)
    res = "url " + url + " banned"
    write_db()
    return res


def url_unban(url):
    var.db.remove_option("url_ban", url)
    res = "Done"
    write_db()
    return res


class Dir(object):
    def __init__(self, path):
        self.name = os.path.basename(path.strip('/'))
        self.fullpath = path
        self.subdirs = {}
        self.files = []

    def add_file(self, file):
        if file.startswith(self.name + '/'):
            file = file.replace(self.name + '/', '', 1)

        if '/' in file:
            # This file is in a subdir
            subdir = file.split('/')[0]
            if subdir in self.subdirs:
                self.subdirs[subdir].add_file(file)
            else:
                self.subdirs[subdir] = Dir(os.path.join(self.fullpath, subdir))
                self.subdirs[subdir].add_file(file)
        else:
            self.files.append(file)
        return True

    def get_subdirs(self, path=None):
        subdirs = []
        if path and path != '' and path != './':
            subdir = path.split('/')[0]
            if subdir in self.subdirs:
                searchpath = '/'.join(path.split('/')[1::])
                subdirs = self.subdirs[subdir].get_subdirs(searchpath)
                subdirs = list(map(lambda subsubdir: os.path.join(subdir, subsubdir), subdirs))
        else:
            subdirs = self.subdirs

        return subdirs

    def get_subdirs_recursively(self, path=None):
        subdirs = []
        if path and path != '' and path != './':
            subdir = path.split('/')[0]
            if subdir in self.subdirs:
                searchpath = '/'.join(path.split('/')[1::])
                subdirs = self.subdirs[subdir].get_subdirs_recursively(searchpath)
        else:
            subdirs = list(self.subdirs.keys())

            for key, val in self.subdirs.items():
                subdirs.extend(map(lambda subdir: key + '/' + subdir, val.get_subdirs_recursively()))

        subdirs.sort()
        return subdirs

    def get_files(self, path=None):
        files = []
        if path and path != '' and path != './':
            subdir = path.split('/')[0]
            if subdir in self.subdirs:
                searchpath = '/'.join(path.split('/')[1::])
                files = self.subdirs[subdir].get_files(searchpath)
        else:
            files = self.files

        return files

    def get_files_recursively(self, path=None):
        files = []
        if path and path != '' and path != './':
            subdir = path.split('/')[0]
            if subdir in self.subdirs:
                searchpath = '/'.join(path.split('/')[1::])
                files = self.subdirs[subdir].get_files_recursively(searchpath)
        else:
            files = self.files

            for key, val in self.subdirs.items():
                files.extend(map(lambda file: key + '/' + file, val.get_files_recursively()))
        
        return files

    def render_text(self, ident=0):
        print('{}{}/'.format(' ' * (ident * 4), self.name))
        for key, val in self.subdirs.items():
            val.render_text(ident + 1)
        for file in self.files:
            print('{}{}'.format(' ' * (ident + 1) * 4, file))
