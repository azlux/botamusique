import logging
import os
import re
from io import BytesIO
import base64
import hashlib
import mutagen
from PIL import Image
import json

import util
import variables as var
from media.item import BaseItem, item_builders, item_loaders, item_id_generators
import constants

'''
type : file
    id
    path
    title
    artist
    duration
    thumbnail
    user
'''


def file_item_builder(bot, **kwargs):
    return FileItem(bot, kwargs['path'])


def file_item_loader(bot, _dict):
    return FileItem(bot, "", _dict)


def file_item_id_generator(**kwargs):
    return hashlib.md5(kwargs['path'].encode()).hexdigest()


item_builders['file'] = file_item_builder
item_loaders['file'] = file_item_loader
item_id_generators['file'] = file_item_id_generator


class FileItem(BaseItem):
    def __init__(self, bot, path, from_dict=None):
        if not from_dict:
            super().__init__(bot)
            self.path = path
            self.title = ""
            self.artist = ""
            self.thumbnail = None
            self.id = hashlib.md5(path.encode()).hexdigest()
            if os.path.exists(self.uri()):
                self._get_info_from_tag()
                self.ready = "yes"
        else:
            super().__init__(bot, from_dict)
            self.path = from_dict['path']
            self.title = from_dict['title']
            self.artist = from_dict['artist']
            self.thumbnail = from_dict['thumbnail']
            if not self.validate():
                self.ready = "failed"

        self.type = "file"

    def uri(self):
        return var.music_folder + self.path if self.path[0] != "/" else self.path

    def is_ready(self):
        return True

    def validate(self):
        if not os.path.exists(self.uri()):
            self.log.info(
                "file: music file missed for %s" % self.format_debug_string())
            self.send_client_message(constants.strings('file_missed', file=self.path))
            return False

        # self.version += 1 # 0 -> 1, notify the wrapper to save me when validate() is visited the first time
        self.ready = "yes"
        return True

    def _get_info_from_tag(self):
        match = re.search("(.+)\.(.+)", self.uri())
        assert match is not None

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
                tags = mutagen.File(self.uri())
                if 'TIT2' in tags:
                    self.title = tags['TIT2'].text[0]
                if 'TPE1' in tags:  # artist
                    self.artist = tags['TPE1'].text[0]

                if im is None:
                    if "APIC:" in tags:
                        im = Image.open(BytesIO(tags["APIC:"].data))

            elif ext == "m4a" or ext == "m4b" or ext == "mp4" or ext == "m4p":
                # title: ©nam (\xa9nam)
                # artist: ©ART
                # album: ©alb
                # cover artwork: covr
                tags = mutagen.File(self.uri())
                if '©nam' in tags:
                    self.title = tags['©nam'][0]
                if '©ART' in tags:  # artist
                    self.artist = tags['©ART'][0]

                if im is None:
                    if "covr" in tags:
                        im = Image.open(BytesIO(tags["covr"][0]))

            if im:
                self.thumbnail = self._prepare_thumbnail(im)
        except:
            pass

        if not self.title:
            self.title = os.path.basename(file_no_ext)

    def _prepare_thumbnail(self, im):
        im.thumbnail((100, 100), Image.ANTIALIAS)
        buffer = BytesIO()
        im = im.convert('RGB')
        im.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def to_dict(self):
        dict = super().to_dict()
        dict['type'] = 'file'
        dict['path'] = self.path
        dict['title'] = self.title
        dict['artist'] = self.artist
        dict['thumbnail'] = self.thumbnail
        return dict

    def format_debug_string(self):
        return "[file] {descrip} ({path})".format(
            descrip=self.format_short_string(),
            path=self.path
        )

    def format_song_string(self, user):
        return constants.strings("file_item",
                                 title=self.title,
                                 artist=self.artist if self.artist else '??',
                                 user=user
                                 )

    def format_current_playing(self, user):
        display = constants.strings("now_playing", item=self.format_song_string(user))
        if self.thumbnail:
            thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                             self.thumbnail + '"/>'
            display += "<br />" + thumbnail_html

        return display

    def format_short_string(self):
        title = self.title if self.title else self.path
        if self.artist:
            return self.artist + " - " + title
        else:
            return title

    def display_type(self):
        return constants.strings("file")
