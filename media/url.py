import threading
import logging
import os
import hashlib
import traceback
from PIL import Image
import youtube_dl
import glob
from io import BytesIO
import base64

import constants
import media
import variables as var
from media.item import BaseItem, item_builders, item_loaders, item_id_generators
import media.system

log = logging.getLogger("bot")

def url_item_builder(bot, **kwargs):
    return URLItem(bot, kwargs['url'])

def url_item_loader(bot, _dict):
    return URLItem(bot, "", _dict)

def url_item_id_generator(**kwargs):
    return hashlib.md5(kwargs['url'].encode()).hexdigest()

item_builders['url'] = url_item_builder
item_loaders['url'] = url_item_loader
item_id_generators['url'] = url_item_id_generator


class URLItem(BaseItem):
    def __init__(self, bot, url, from_dict=None):
        self.validating_lock = threading.Lock()
        if from_dict is None:
            super().__init__(bot)
            self.url = url if url[-1] != "/" else url[:-1]
            self.title = ''
            self.duration = 0
            self.id = hashlib.md5(url.encode()).hexdigest()
            self.path = var.tmp_folder + self.id + ".mp3"
            self.thumbnail = ''
        else:
            super().__init__(bot, from_dict)
            self.url = from_dict['url']
            self.duration = from_dict['duration']
            self.path = from_dict['path']
            self.title = from_dict['title']
            self.thumbnail = from_dict['thumbnail']

        self.downloading = False
        self.type = "url"

    def uri(self):
        return self.path

    def is_ready(self):
        if self.downloading or self.ready != 'yes':
            return False
        if self.ready == 'yes' and not os.path.exists(self.path):
            self.log.info(
                "url: music file missed for %s" % self.format_debug_string())
            self.ready = 'validated'
            return False

        return True

    def validate(self):
        self.validating_lock.acquire()
        if self.ready in ['yes', 'validated']:
            return True

        if self.ready == 'failed':
            return False

        if os.path.exists(self.path):
            self.ready = "yes"
            return True

        # avoid multiple process validating in the meantime
        info = self._get_info_from_url()
        self.validating_lock.release()

        if not info:
            return False

        if self.duration > var.config.getint('bot', 'max_track_duration') != 0:
            # Check the length, useful in case of playlist, it wasn't checked before)
            log.info(
                "url: " + self.url + " has a duration of " + str(self.duration) + " min -- too long")
            self.send_client_message(constants.strings('too_long', song=self.title))
            return False
        else:
            self.ready = "validated"
            self.version += 1 # notify wrapper to save me
            return True

    # Run in a other thread
    def prepare(self):
        if not self.downloading:
            assert self.ready == 'validated'
            return self._download()
        else:
            assert self.ready == 'yes'
            return True

    def _get_info_from_url(self):
        self.log.info("url: fetching metadata of url %s " % self.url)
        ydl_opts = {
            'noplaylist': True
        }
        succeed = False
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            attempts = var.config.getint('bot', 'download_attempts', fallback=2)
            for i in range(attempts):
                try:
                    info = ydl.extract_info(self.url, download=False)
                    self.duration = info['duration'] / 60
                    self.title = info['title']
                    succeed = True
                    return True
                except youtube_dl.utils.DownloadError:
                    pass

        if not succeed:
            self.ready = 'failed'
            self.log.error("url: error while fetching info from the URL")
            self.send_client_message(constants.strings('unable_download'))
            return False

    def _download(self):
        media.system.clear_tmp_folder(var.tmp_folder, var.config.getint('bot', 'tmp_folder_max_size'))

        self.downloading = True
        base_path = var.tmp_folder + self.id
        save_path = base_path + ".%(ext)s"
        mp3_path = base_path + ".mp3"

        # Download only if music is not existed
        self.ready = "preparing"

        self.log.info("bot: downloading url (%s) %s " % (self.title, self.url))
        ydl_opts = ""

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': save_path,
            'noplaylist': True,
            'writethumbnail': True,
            'updatetime': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'},
                {'key': 'FFmpegMetadata'}]
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            attempts = var.config.getint('bot', 'download_attempts', fallback=2)
            download_succeed = False
            for i in range(attempts):
                self.log.info("bot: download attempts %d / %d" % (i+1, attempts))
                try:
                    info = ydl.extract_info(self.url)
                    download_succeed = True
                    break
                except:
                    error_traceback = traceback.format_exc().split("During")[0]
                    error = error_traceback.rstrip().split("\n")[-1]
                    self.log.error("bot: download failed with error:\n %s" % error)

            if download_succeed:
                self.path = mp3_path
                self.ready = "yes"
                self.log.info(
                    "bot: finished downloading url (%s) %s, saved to %s." % (self.title, self.url, self.path))
                self.downloading = False
                self._read_thumbnail_from_file(base_path + ".jpg")
                self.version += 1 # notify wrapper to save me
                return True
            else:
                for f in glob.glob(base_path + "*"):
                    os.remove(f)
                self.send_client_message(constants.strings('unable_download'))
                self.ready = "failed"
                self.downloading = False
                return False

    def _read_thumbnail_from_file(self, path_thumbnail):
        if os.path.isfile(path_thumbnail):
            im = Image.open(path_thumbnail)
            self.thumbnail = self._prepare_thumbnail(im)

    def _prepare_thumbnail(self, im):
        im.thumbnail((100, 100), Image.ANTIALIAS)
        buffer = BytesIO()
        im = im.convert('RGB')
        im.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def to_dict(self):
        dict = super().to_dict()
        dict['type'] = 'url'
        dict['url'] = self.url
        dict['duration'] = self.duration
        dict['path'] = self.path
        dict['title'] = self.title
        dict['thumbnail'] = self.thumbnail

        return dict


    def format_debug_string(self):
        return "[url] {title} ({url})".format(
            title=self.title,
            url=self.url
        )

    def format_song_string(self, user):
        return constants.strings("url_item",
                                    title=self.title,
                                    url=self.url,
                                    user=user)

    def format_current_playing(self, user):
        display = constants.strings("now_playing", item=self.format_song_string(user))

        if self.thumbnail:
            thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                             self.thumbnail + '"/>'
            display += "<br />" +  thumbnail_html

        return display

    def format_short_string(self):
        return self.title if self.title.strip() else self.url

    def display_type(self):
        return constants.strings("url")
