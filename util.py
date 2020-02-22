#!/usr/bin/python3
# coding=utf-8

import hashlib
import magic
import os
import sys
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
from sys import platform
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

def format_song_string(music):
    display = ''
    source = music["type"]
    title = music["title"] if "title" in music else "Unknown title"
    artist = music["artist"] if "artist" in music else "Unknown artist"

    if source == "radio":
        display = "[radio] {title} from {url} by {user}".format(
            title=media.radio.get_radio_title(music["url"]),
            url=music["url"],
            user=music["user"]
        )
    elif source == "url" and 'from_playlist' in music:
        display = "[url] {title} (from playlist <a href=\"{url}\">{playlist}</a>) by {user}".format(
            title=title,
            url=music["playlist_url"],
            playlist=music["playlist_title"],
            user=music["user"]
        )
    elif source == "url":
        display = "[url] <a href=\"{url}\">{title}</a> by {user}".format(
            title=title,
            url=music["url"],
            user=music["user"]
        )
    elif source == "file":
        display = "[file] {artist} - {title} by {user}".format(
            title=title,
            artist=artist,
            user=music["user"]
        )

    return display

def format_debug_song_string(music):
    display = ''
    source = music["type"]
    title = music["title"] if "title" in music else "??"
    artist = music["artist"] if "artist" in music else "??"

    if source == "radio":
        display = "[radio] {url} by {user}".format(
            url=music["url"],
            user=music["user"]
        )
    elif source == "url" and 'from_playlist' in music:
        display = "[url] {title} ({url}) from playlist {playlist} by {user}".format(
            title=title,
            url=music["url"],
            playlist=music["playlist_title"],
            user=music["user"]
        )
    elif source == "url":
        display = "[url] {title} ({url}) by {user}".format(
            title=title,
            url=music["url"],
            user=music["user"]
        )
    elif source == "file":
        display = "[file] {artist} - {title} ({path}) by {user}".format(
            title=title,
            artist=artist,
            path=music["path"],
            user=music["user"]
        )

    return display

def format_current_playing():
    music = var.playlist.current_item()
    display = format_song_string(music)

    thumbnail_html = ''
    if 'thumbnail' in music:
        thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                         music['thumbnail'] + '"/>'

    display = (var.config.get(
        'strings', 'now_playing') % (display, thumbnail_html))

    return display


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

def new_release_version():
    v = int(urllib.request.urlopen(urllib.request.Request("https://azlux.fr/botamusique/version")).read())
    return v

def update(version):
    v = new_release_version()
    if v > version:
        logging.info('update: new version, start updating...')
        tp = sp.check_output(['/usr/bin/env', 'bash', 'update.sh']).decode()
        logging.debug(tp)
        logging.info('update: update pip librairies dependancies')
        tp = sp.check_output([var.config.get('bot', 'pip3_path'), 'install', '--upgrade', '-r', 'requirements.txt']).decode()
        msg = "New version installed, please restart the bot."
        
    else:
        logging.info('update: starting update youtube-dl via pip3')
        tp = sp.check_output([var.config.get('bot', 'pip3_path'), 'install', '--upgrade', 'youtube-dl']).decode()
        msg = ""
        if "Requirement already up-to-date" in tp:
            msg += "Youtube-dl is up-to-date"
        else:
            msg += "Update done: " + tp.split('Successfully installed')[1]
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

def pipe_no_wait(pipefd):
    ''' Used to fetch the STDERR of ffmpeg. pipefd is the file descriptor returned from os.pipe()'''
    if platform == "linux" or platform == "linux2" or platform == "darwin":
        import fcntl
        import os
        try:
            fl = fcntl.fcntl(pipefd, fcntl.F_GETFL)
            fcntl.fcntl(pipefd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        except:
            print(sys.exc_info()[1])
            return False
        else:
            return True

    elif platform == "win32":
        # https://stackoverflow.com/questions/34504970/non-blocking-read-on-os-pipe-on-windows
        import msvcrt
        import os

        from ctypes import windll, byref, wintypes, GetLastError, WinError
        from ctypes.wintypes import HANDLE, DWORD, POINTER, BOOL

        LPDWORD = POINTER(DWORD)
        PIPE_NOWAIT = wintypes.DWORD(0x00000001)
        ERROR_NO_DATA = 232

        SetNamedPipeHandleState = windll.kernel32.SetNamedPipeHandleState
        SetNamedPipeHandleState.argtypes = [HANDLE, LPDWORD, LPDWORD, LPDWORD]
        SetNamedPipeHandleState.restype = BOOL

        h = msvcrt.get_osfhandle(pipefd)

        res = windll.kernel32.SetNamedPipeHandleState(h, byref(PIPE_NOWAIT), None, None)
        if res == 0:
            print(WinError())
            return False
        return True



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
