import json
import random
import threading
import logging
import random

import variables as var
from media.file import FileItem
from media.url import URLItem
from media.url_from_playlist import PlaylistURLItem
from media.radio import RadioItem
from database import MusicDatabase
from media.library import MusicLibrary

class PlaylistItemWrapper:
    def __init__(self, lib, id, type, user):
        self.lib = lib
        self.id = id
        self.user = user
        self.type = type
        self.log = logging.getLogger("bot")
        self.version = 0

    def item(self):
        return self.lib[self.id]

    def to_dict(self):
        dict = self.item().to_dict()
        dict['user'] = self.user
        return dict

    def validate(self):
        ret = self.item().validate()
        if ret and self.item().version > self.version:
            self.version = self.item().version
            self.lib.save(self.id)
        return ret

    def prepare(self):
        ret = self.item().prepare()
        if ret and self.item().version > self.version:
            self.version = self.item().version
            self.lib.save(self.id)
        return ret

    def async_prepare(self):
        th = threading.Thread(
            target=self.prepare, name="Prepare-" + self.id[:7])
        self.log.info(
            "%s: start preparing item in thread: " % self.item().type + self.format_debug_string())
        th.daemon = True
        th.start()
        return th

    def uri(self):
        return self.item().uri()

    def add_tags(self, tags):
        self.item().add_tags(tags)
        if self.item().version > self.version:
            self.version = self.item().version
            self.lib.save(self.id)

    def remove_tags(self, tags):
        self.item().remove_tags(tags)
        if self.item().version > self.version:
            self.version = self.item().version
            self.lib.save(self.id)

    def clear_tags(self):
        self.item().clear_tags()
        if self.item().version > self.version:
            self.version = self.item().version
            self.lib.save(self.id)

    def is_ready(self):
        return self.item().is_ready()

    def is_failed(self):
        return self.item().is_failed()

    def format_current_playing(self):
        return self.item().format_current_playing(self.user)

    def format_song_string(self):
        return self.item().format_song_string(self.user)

    def format_short_string(self):
        return self.item().format_short_string()

    def format_debug_string(self):
        return self.item().format_debug_string()

    def display_type(self):
        return self.item().display_type()


def get_item_wrapper(bot, **kwargs):
    item = var.library.get_item(bot, **kwargs)
    if 'user' not in kwargs:
        raise KeyError("Which user added this song?")
    return PlaylistItemWrapper(var.library, item.id, kwargs['type'], kwargs['user'])

def get_item_wrapper_by_id(bot, id, user):
    item = var.library.get_item_by_id(bot, id)
    if item:
        return PlaylistItemWrapper(var.library, item.id, item.type, user)
    else:
        return None

def get_item_wrappers_by_tags(bot, tags, user):
    items = var.library.get_items_by_tags(bot, tags)
    ret = []
    for item in items:
        ret.append(PlaylistItemWrapper(var.library, item.id, item.type, user))
    return ret

def get_playlist(mode, _list=None, index=None):
    if _list and index is None:
        index = _list.current_index

    if _list is None:
        if mode == "one-shot":
            return OneshotPlaylist()
        elif mode == "repeat":
            return RepeatPlaylist()
        elif mode == "random":
            return RandomPlaylist()
        elif mode == "autoplay":
            return AutoPlaylist()
    else:
        if mode == "one-shot":
            return OneshotPlaylist().from_list(_list, index)
        elif mode == "repeat":
            return RepeatPlaylist().from_list(_list, index)
        elif mode == "random":
            return RandomPlaylist().from_list(_list, index)
        elif mode == "autoplay":
            return AutoPlaylist().from_list(_list, index)
    raise

class BasePlaylist(list):
    def __init__(self):
        super().__init__()
        self.current_index = -1
        self.version = 0  # increase by one after each change
        self.mode = "base"  # "repeat", "random"
        self.pending_items = []
        self.log = logging.getLogger("bot")
        self.validating_thread_lock = threading.Lock()

    def is_empty(self):
        return True if len(self) == 0 else False

    def from_list(self, _list, current_index):
        self.version += 1
        super().clear()
        self.extend(_list)
        self.current_index = current_index

        return self

    def append(self, item: PlaylistItemWrapper):
        self.version += 1
        super().append(item)
        self.pending_items.append(item)
        self.start_async_validating()

        return item

    def insert(self, index, item):
        self.version += 1

        if index == -1:
            index = self.current_index

        super().insert(index, item)

        if index <= self.current_index:
            self.current_index += 1

        self.pending_items.append(item)
        self.start_async_validating()

        return item

    def extend(self, items):
        self.version += 1
        super().extend(items)
        self.pending_items.extend(items)
        self.start_async_validating()
        return items

    def next(self):
        if len(self) == 0:
            return False

        self.version += 1

        if self.current_index < len(self) - 1:
            self.current_index += 1
            return self[self.current_index]
        else:
            return False

    def point_to(self, index):
        self.version += 1
        if -1 <= index < len(self):
            self.current_index = index

    def find(self, id):
        for index, wrapper in enumerate(self):
            if wrapper.item.id == id:
                return index
        return None

    def __delitem__(self, key):
        return self.remove(key)

    def remove(self, index):
        self.version += 1
        if index > len(self) - 1:
            return False

        removed = self[index]
        super().__delitem__(index)

        if self.current_index > index:
            self.current_index -= 1

        # reference counter
        counter = 0
        for wrapper in self:
            if wrapper.id == removed.id:
                counter += 1

        if counter == 0:
            var.library.free(removed.id)
        return removed

    def remove_by_id(self, id):
        self.version += 1
        to_be_removed = []
        for index, wrapper in enumerate(self):
            if wrapper.id == id:
                to_be_removed.append(index)

        for index in to_be_removed:
            self.remove(index)

    def current_item(self):
        if len(self) == 0:
            return False

        return self[self.current_index]

    def next_index(self):
        if self.current_index < len(self) - 1:
            return self.current_index + 1
        else:
            return False

    def next_item(self):
        if self.current_index < len(self) - 1:
            return self[self.current_index + 1]
        else:
            return False

    def randomize(self):
        # current_index will lose track after shuffling, thus we take current music out before shuffling
        #current = self.current_item()
        #del self[self.current_index]

        random.shuffle(self)

        #self.insert(0, current)
        self.current_index = -1
        self.version += 1

    def clear(self):
        self.version += 1
        self.current_index = -1
        var.library.free_all()
        super().clear()

    def save(self):
        var.db.remove_section("playlist_item")
        assert self.current_index is not None
        var.db.set("playlist", "current_index", self.current_index)

        for index, music in enumerate(self):
            var.db.set("playlist_item", str(index), json.dumps({'id': music.id, 'user': music.user }))

    def load(self):
        current_index = var.db.getint("playlist", "current_index", fallback=-1)
        if current_index == -1:
            return

        items = var.db.items("playlist_item")
        if items:
            music_wrappers = []
            items.sort(key=lambda v: int(v[0]))
            for item in items:
                item = json.loads(item[1])
                music_wrapper = get_item_wrapper_by_id(var.bot, item['id'], item['user'])
                if music_wrapper:
                    music_wrappers.append(music_wrapper)
            self.from_list(music_wrappers, current_index)

    def _debug_print(self):
        print("===== Playlist(%d)=====" % self.current_index)
        for index, item_wrapper in enumerate(self):
            if index == self.current_index:
                print("-> %d %s" % (index, item_wrapper.format_debug_string()))
            else:
                print("%d %s" % (index, item_wrapper.format_debug_string()))
        print("=====     End     =====")

    def start_async_validating(self):
        if not self.validating_thread_lock.locked():
            th = threading.Thread(target=self._check_valid, name="Validating")
            th.daemon = True
            th.start()

    def _check_valid(self):
        self.log.debug("playlist: start validating...")
        self.validating_thread_lock.acquire()
        while len(self.pending_items) > 0:
            item = self.pending_items.pop()
            self.log.debug("playlist: validating %s" % item.format_debug_string())
            if not item.validate() or item.is_failed():
                self.log.debug("playlist: validating failed.")
                var.library.delete(item.id)
                self.remove_by_id(item.id)

        self.log.debug("playlist: validating finished.")
        self.validating_thread_lock.release()


class OneshotPlaylist(BasePlaylist):
    def __init__(self):
        super().__init__()
        self.mode = "one-shot"
        self.current_index = -1

    def from_list(self, _list, current_index):
        if len(_list) > 0:
            if current_index > -1:
                for i in range(current_index):
                    _list.pop(0)
                return super().from_list(_list, 0)
            return super().from_list(_list, -1)
        return self

    def next(self):
        if len(self) == 0:
            return False

        self.version += 1

        if len(self) > 0:
            if self.current_index != -1:
                super().__delitem__(self.current_index)
                if len(self) == 0:
                    return False
            else:
                self.current_index = 0
            return self[0]

        else:
            self.clear()
            return False

    def next_index(self):
        if len(self) > 1:
            return 1
        else:
            return False

    def next_item(self):
        if len(self) > 1:
            return self[1]
        else:
            return False

    def point_to(self, index):
        self.version += 1
        self.current_index = -1
        for i in range(index + 1):
            super().__delitem__(0)


class RepeatPlaylist(BasePlaylist):
    def __init__(self):
        super().__init__()
        self.mode = "repeat"

    def next(self):
        if len(self) == 0:
            return False

        self.version += 1

        if self.current_index < len(self) - 1:
            self.current_index += 1
            return self[self.current_index]
        else:
            self.current_index = 0
            return self[0]

    def next_index(self):
        if self.current_index < len(self) - 1:
            return self.current_index + 1
        else:
            return 0

    def next_item(self):
        return self[self.next_index()]


class RandomPlaylist(BasePlaylist):
    def __init__(self):
        super().__init__()
        self.mode = "random"

    def from_list(self, _list, current_index):
        self.version += 1
        random.shuffle(_list)
        return super().from_list(_list, -1)

    def next(self):
        if len(self) == 0:
            return False

        self.version += 1

        if self.current_index < len(self) - 1:
            self.current_index += 1
            return self[self.current_index]
        else:
            self.randomize()
            self.current_index = 0
            return self[0]


class AutoPlaylist(BasePlaylist):
    def __init__(self):
        super().__init__()
        self.mode = "autoplay"

    def refresh(self):
        _list = []
        ids = var.music_db.query_all_ids()
        for _ in range(20):
            _list.append(get_item_wrapper_by_id(var.bot, ids[random.randint(0, len(ids)-1)], 'AutoPlay'))
        self.from_list(_list, -1)

    # def from_list(self, _list, current_index):
    #     self.version += 1
    #     self.refresh()
    #     return self

    def clear(self):
        super().clear()
        self.refresh()

    def next(self):
        if len(self) == 0:
            self.refresh()
            return False

        self.version += 1

        if self.current_index < len(self) - 1:
            self.current_index += 1
            return self[self.current_index]
        else:
            self.refresh()
            self.current_index = 0
            return self[0]
