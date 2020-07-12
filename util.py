#!/usr/bin/python3
# coding=utf-8

import hashlib
import magic
import os
import io
import sys
import variables as var
import zipfile
import re
import subprocess as sp
import logging
import youtube_dl
from importlib import reload
from sys import platform
import traceback
import requests
from packaging import version

log = logging.getLogger("bot")


def solve_filepath(path):
    if not path:
        return ''

    if path[0] == '/':
        return path
    else:
        mydir = os.path.dirname(os.path.realpath(__file__))
        return mydir + '/' + path


def get_recursive_file_list_sorted(path):
    filelist = []
    for root, dirs, files in os.walk(path, topdown=True, onerror=None, followlinks=True):
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

            try:
                mime = magic.from_file(fullpath, mime=True)
                if 'audio' in mime or 'audio' in magic.from_file(fullpath).lower() or 'video' in mime:
                    filelist.append(relroot + file)
            except:
                pass

    filelist.sort()
    return filelist


# - zips files
# - returns the absolute path of the created zip file
# - zip file will be in the applications tmp folder (according to configuration)
# - format of the filename itself = prefix_hash.zip
#       - prefix can be controlled by the caller
#       - hash is a sha1 of the string representation of the directories' contents (which are
#           zipped)
def zipdir(files, zipname_prefix=None):
    zipname = var.tmp_folder
    if zipname_prefix and '../' not in zipname_prefix:
        zipname += zipname_prefix.strip().replace('/', '_') + '_'

    _hash = hashlib.sha1(str(files).encode()).hexdigest()
    zipname += _hash + '.zip'

    if os.path.exists(zipname):
        return zipname

    zipf = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)

    for file_to_add in files:
        if not os.access(file_to_add, os.R_OK):
            continue
        if file_to_add in var.config.get('bot', 'ignored_files'):
            continue

        add_file_as = os.path.basename(file_to_add)
        zipf.write(file_to_add, add_file_as)

    zipf.close()
    return zipname


def get_user_ban():
    res = "List of ban hash"
    for i in var.db.items("user_ban"):
        res += "<br/>" + i[0]
    return res


def new_release_version(target):
    if target == "testing":
        r = requests.get("https://packages.azlux.fr/botamusique/testing-version")
    else:
        r = requests.get("https://packages.azlux.fr/botamusique/version")
    v = r.text
    return v.rstrip()


def fetch_changelog():
    r = requests.get("https://packages.azlux.fr/botamusique/changelog")
    c = r.text
    return c


def update(current_version):
    global log

    target = var.config.get('bot', 'target_version')
    new_version = new_release_version(target)
    msg = ""
    if target == "git":
        msg = "git install, I do nothing"

    elif (target == "stable" and version.parse(new_version) > version.parse(current_version)) or \
            (target == "testing" and version.parse(new_version) != version.parse(current_version)):
        log.info('update: new version, start updating...')
        tp = sp.check_output(['/usr/bin/env', 'bash', 'update.sh', target]).decode()
        log.debug(tp)
        log.info('update: update pip libraries dependencies')
        sp.check_output([var.config.get('bot', 'pip3_path'), 'install', '--upgrade', '-r', 'requirements.txt']).decode()
        msg = "New version installed, please restart the bot."

    log.info('update: starting update youtube-dl via pip3')
    tp = sp.check_output([var.config.get('bot', 'pip3_path'), 'install', '--upgrade', 'youtube-dl']).decode()
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
    res = "List of ban:"
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


def pipe_no_wait():
    """ Generate a non-block pipe used to fetch the STDERR of ffmpeg.
    """

    if platform == "linux" or platform == "linux2" or platform == "darwin" or platform.startswith("openbsd"):
        import fcntl
        import os

        pipe_rd = 0
        pipe_wd = 0

        if hasattr(os, "pipe2"):
            pipe_rd, pipe_wd = os.pipe2(os.O_NONBLOCK)
        else:
            pipe_rd, pipe_wd = os.pipe()

            try:
                fl = fcntl.fcntl(pipe_rd, fcntl.F_GETFL)
                fcntl.fcntl(pipe_rd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            except:
                print(sys.exc_info()[1])
                return None, None
        return pipe_rd, pipe_wd

    elif platform == "win32":
        # https://stackoverflow.com/questions/34504970/non-blocking-read-on-os-pipe-on-windows
        import msvcrt
        import os

        from ctypes import windll, byref, wintypes, WinError, POINTER
        from ctypes.wintypes import HANDLE, DWORD, BOOL

        pipe_rd, pipe_wd = os.pipe()

        LPDWORD = POINTER(DWORD)
        PIPE_NOWAIT = wintypes.DWORD(0x00000001)
        ERROR_NO_DATA = 232

        SetNamedPipeHandleState = windll.kernel32.SetNamedPipeHandleState
        SetNamedPipeHandleState.argtypes = [HANDLE, LPDWORD, LPDWORD, LPDWORD]
        SetNamedPipeHandleState.restype = BOOL

        h = msvcrt.get_osfhandle(pipe_rd)

        res = windll.kernel32.SetNamedPipeHandleState(h, byref(PIPE_NOWAIT), None, None)
        if res == 0:
            print(WinError())
            return None, None
        return pipe_rd, pipe_wd


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


# Parse the html from the message to get the URL

def get_url_from_input(string):
    string = string.strip()
    if not (string.startswith("http") or string.startswith("HTTP")):
        res = re.search('href="(.+?)"', string, flags=re.IGNORECASE)
        if res:
            string = res.group(1)
        else:
            return False

    match = re.search("(http|https)://(\S*)?/(\S*)", string, flags=re.IGNORECASE)
    if match:
        url = match[1].lower() + "://" + match[2].lower() + "/" + match[3]
        return url
    else:
        return False


def youtube_search(query):
    global log

    try:
        results = None
        r = requests.get("https://www.youtube.com/results", params={'search_query': query}, timeout=5)
        results = re.findall(r"(watch\?v=(?P<videoid>[^\"\r\n]*)\".*?title=\"(?P<title>[^\r\n\"]*)\".*?(?:user|channel)[^>]*"
                             r">(?P<uploader>[^<\"\n\r]*)<)|(\"videoId\":\"(?P<videoid2>[^\"]*)\").*?\"title\":{\"runs\":\[{"
                             r"\"text\":\"(?P<title2>[^\"]*)\".*?\"ownerText\":{\"runs\":\[{\"text\":\"(?P<uploader2>[^\"]*)"
                             r"\"", r.text)  # (catch1, id1, title1, uploader1, catch2, id2, title2, uploader2,)

        if len(results) > 0:
            finalResults = None
            finalResults = []
            if results[0][0] != "":
                for entry in results:
                    finalResults.append([entry[1], entry[2], entry[3]])
            else:
                for entry in results:
                    finalResults.append([entry[5], entry[6], entry[7]])
            return finalResults

    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.Timeout):
        error_traceback = traceback.format_exc().split("During")[0]
        log.error("util: youtube query failed with error:\n %s" % error_traceback)
        return False


def get_media_duration(path):
    command = ("ffprobe", "-v", "quiet", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", path)
    process = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
    stdout, stderr = process.communicate()

    try:
        if not stderr:
            return float(stdout)
        else:
            return 0
    except ValueError:
        return 0


def parse_time(human):
    match = re.search("(?:(\d\d):)?(?:(\d\d):)?(\d+(?:\.\d*)?)", human, flags=re.IGNORECASE)
    if match:
        if match[1] is None and match[2] is None:
            return float(match[3])
        elif match[2] is None:
            return float(match[3]) + 60 * int(match[1])
        else:
            return float(match[3]) + 60 * int(match[2]) + 3600 * int(match[1])
    else:
        raise ValueError("Invalid time string given.")


def parse_file_size(human):
    units = {"B": 1, "KB": 1024, "MB": 1024 * 1024, "GB": 1024 * 1024 * 1024, "TB": 1024 * 1024 * 1024 * 1024,
             "K": 1024, "M": 1024 * 1024, "G": 1024 * 1024 * 1024, "T": 1024 * 1024 * 1024 * 1024}
    match = re.search("(\d+(?:\.\d*)?)\s*([A-Za-z]+)", human, flags=re.IGNORECASE)
    if match:
        num = float(match[1])
        unit = match[2].upper()
        if unit in units:
            return int(num * units[unit])

    raise ValueError("Invalid file size given.")


def get_salted_password_hash(password):
    salt = os.urandom(10)
    hashed = hashlib.pbkdf2_hmac('sha1', password.encode("utf-8"), salt, 100000)

    return hashed.hex(), salt.hex()


def verify_password(password, salted_hash, salt):
    hashed = hashlib.pbkdf2_hmac('sha1', password.encode("utf-8"), bytearray.fromhex(salt), 100000)
    if hashed.hex() == salted_hash:
        return True
    return False


def get_supported_language():
    lang_files = os.listdir('lang')
    lang_list = []
    for lang_file in lang_files:
        match = re.search("([a-z]{2}_[A-Z]{2})\.json", lang_file)
        if match:
            lang_list.append(match[1])

    return lang_list


class LoggerIOWrapper(io.TextIOWrapper):
    def __init__(self, logger: logging.Logger, logging_level, fallback_io_buffer):
        super().__init__(fallback_io_buffer, write_through=True)
        self.logger = logger
        self.logging_level = logging_level

    def write(self, text):
        if isinstance(text, bytes):
            msg = text.decode('utf-8').rstrip()
            self.logger.log(self.logging_level, msg)
            super().write(msg + "\n")
        else:
            self.logger.log(self.logging_level, text.rstrip())
            super().write(text + "\n")


class VolumeHelper:
    def __init__(self, plain_volume=0, ducking_plain_volume=0):
        self.plain_volume_set = 0
        self.plain_ducking_volume_set = 0
        self.volume_set = 0
        self.ducking_volume_set = 0

        self.real_volume = 0

        self.set_volume(plain_volume)
        self.set_ducking_volume(ducking_plain_volume)

    def set_volume(self, plain_volume):
        self.volume_set = self._convert_volume(plain_volume)
        self.plain_volume_set = plain_volume

    def set_ducking_volume(self, plain_volume):
        self.ducking_volume_set = self._convert_volume(plain_volume)
        self.plain_ducking_volume_set = plain_volume

    def _convert_volume(self, volume):
        if volume == 0:
            return 0

        # convert input of 0~1 into -35~5 dB
        dB = -35 + volume * 40

        # Some dirty trick to stretch the function, to make to be 0 when input is -35 dB
        return (10 ** (dB / 20) - 10 ** (-35 / 20)) / (1 - 10 ** (-35 / 20))
