import logging
import threading
import os
import re
from io import BytesIO
import base64
import hashlib
import mutagen
from PIL import Image

import util
import variables as var

"""
FORMAT OF A MUSIC INTO THE PLAYLIST
type : url
    id
    url
    title
    path
    duration
    artist
    thumbnail
    user
    ready (validation, no, downloading, yes, failed)
    from_playlist (yes,no)
    playlist_title
    playlist_url

type : radio
    id
    url
    name
    current_title
    user

"""

class BaseItem:
    def __init__(self, bot, from_dict=None):
        self.bot = bot
        self.log = logging.getLogger("bot")
        self.type = "base"

        if from_dict is None:
            self.id = ""
            self.ready = "pending" # pending - is_valid() -> validated - prepare() -> yes, failed
        else:
            self.id = from_dict['id']
            self.ready = from_dict['ready']

    def is_ready(self):
        return True if self.ready == "yes" else False

    def is_failed(self):
        return True if self.ready == "failed" else False

    def validate(self):
        return False

    def uri(self):
        raise

    def async_prepare(self):
        th = threading.Thread(
            target=self.prepare, name="Prepare-" + self.id[:7])
        self.log.info(
            "%s: start preparing item in thread: " % self.type + self.format_debug_string())
        th.daemon = True
        th.start()
        #self.download_threads.append(th)
        return th

    def prepare(self):
        return True

    def play(self):
        pass

    def format_song_string(self, user):
        return self.id

    def format_current_playing(self, user):
        return self.id

    def format_debug_string(self):
        return self.id

    def display_type(self):
        return ""

    def send_client_message(self, msg):
        self.bot.send_msg(msg)

    def to_dict(self):
        return {"type" : "base", "id": self.id, "ready": self.ready}


