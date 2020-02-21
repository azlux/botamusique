#!/usr/bin/python3
# coding=utf-8

import hashlib
import magic
import os
import variables as var
import zipfile
import urllib.request
import mutagen
import re
import subprocess as sp
import logging
import youtube_dl
from importlib import reload
from PIL import Image
from io import BytesIO
import base64
import media

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


def get_music_tag_info(music, uri = ""):

    if "path" in music:
        if not uri:
            uri = var.config.get('bot', 'music_folder') + music["path"]

        if os.path.isfile(uri):
            match = re.search("(.+)\.(.+)", uri)
            if match is None:
                return music

            file_no_ext = match[1]
            ext = match[2]

            try:
                im = None
                path_thumbnail = file_no_ext + ".jpg"
                if os.path.isfile(path_thumbnail):
                    im = Image.open(path_thumbnail)

                if ext == "mp3":
                    # title: TIT2
                    # artist: TPE1, TPE2
                    # album: TALB
                    # cover artwork: APIC:
                    tags = mutagen.File(uri)
                    if 'TIT2' in tags:
                        music['title'] = tags['TIT2'].text[0]
                    if 'TPE1' in tags: # artist
                        music['artist'] = tags['TPE1'].text[0]

                    if im is None:
                        if "APIC:" in tags:
                            im = Image.open(BytesIO(tags["APIC:"].data))

                elif ext == "m4a" or ext == "m4b" or ext == "mp4" or ext == "m4p":
                    # title: ©nam (\xa9nam)
                    # artist: ©ART
                    # album: ©alb
                    # cover artwork: covr
                    tags = mutagen.File(uri)
                    if '©nam' in tags:
                        music['title'] = tags['©nam'][0]
                    if '©ART' in tags: # artist
                        music['artist'] = tags['©ART'][0]

                        if im is None:
                            if "covr" in tags:
                                im = Image.open(BytesIO(tags["covr"][0]))

                if im:
                    im.thumbnail((100, 100), Image.ANTIALIAS)
                    buffer = BytesIO()
                    im = im.convert('RGB')
                    im.save(buffer, format="JPEG")
                    music['thumbnail'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
            except:
                pass
    else:
        uri = music['url']

    # if nothing found
    if 'title' not in music:
        match = re.search("([^\.]+)\.?.*", os.path.basename(uri))
        music['title'] = match[1]

    return music


def format_current_playing():
    if var.playlist.length() > 0:
        reply = ""
        current_music = var.playlist.current_item()
        source = current_music["type"]
        if source == "radio":
            reply = "[radio] {title} on {url} by {user}".format(
                title=media.radio.get_radio_title(
                    current_music["url"]),
                url=current_music["title"],
                user=current_music["user"]
            )
        elif source == "url" and 'from_playlist' in current_music:
            thumbnail_html = ''
            if 'thumbnail' in current_music:
                thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                                 current_music['thumbnail'] + '"/>'
            reply = "[url] {title} (from playlist <a href=\"{url}\">{playlist}</a> by {user} <br> {thumb}".format(
                title=current_music["title"],
                url=current_music["playlist_url"],
                playlist=current_music["playlist_title"],
                user=current_music["user"],
                thumb=thumbnail_html
            )
        elif source == "url":
            thumbnail_html = ''
            if 'thumbnail' in current_music:
                thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                                 current_music['thumbnail'] + '"/>'
            reply = "[url] <a href=\"{url}\">{title}</a> by {user} <br> {thumb}".format(
                title=current_music["title"],
                url=current_music["url"],
                user=current_music["user"],
                thumb=thumbnail_html
            )
        elif source == "file":
            thumbnail_html = ''
            if 'thumbnail' in current_music:
                thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                                 current_music['thumbnail'] + '"/>'
            reply = "[file] {title} by {user} <br> {thumb}".format(
                title=(current_music['artist'] + ' - ' + current_music['title']) if 'artist' in current_music \
                    else current_music['title'],
                user=current_music["user"],
                thumb=thumbnail_html
            )
        else:
            logging.error(current_music)
        return reply
    else:
        return None



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
    return res


def user_unban(user):
    var.db.remove_option("user_ban", user)
    res = "Done"
    return res


def get_url_ban():
    res = "List of ban hash"
    for i in var.db.items("url_ban"):
        res += "<br/>" + i[0]
    return res


def url_ban(url):
    var.db.set("url_ban", url, None)
    res = "url " + url + " banned"
    return res


def url_unban(url):
    var.db.remove_option("url_ban", url)
    res = "Done"
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
