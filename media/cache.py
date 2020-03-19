import logging
import os

import json
import threading

from media.item import item_builders, item_id_generators, dict_to_item
import media.file
import media.url
import media.url_from_playlist
import media.radio
from database import MusicDatabase, Condition
import variables as var
import util


class MusicCache(dict):
    def __init__(self, db: MusicDatabase):
        super().__init__()
        self.db = db
        self.log = logging.getLogger("bot")
        self.dir = None
        self.files = []
        self.file_id_lookup = {} # TODO: Now I see this is silly. Gonna add a column "path" in the database.
        self.dir_lock = threading.Lock()

    def get_item_by_id(self, bot, id):  # Why all these functions need a bot? Because it need the bot to send message!
        if id in self:
            return self[id]

        # if not cached, query the database
        item = self.fetch(bot, id)
        if item is not None:
            self[id] = item
            self.log.debug("library: music found in database: %s" % item.format_debug_string())
            return item
        else:
            return None
            # print(id)
            # raise KeyError("Unable to fetch item from the database! Please try to refresh the cache by !recache.")

    def get_item(self, bot, **kwargs):
        # kwargs should provide type and id, and parameters to build the item if not existed in the library.
        # if cached
        if 'id' in kwargs:
            id = kwargs['id']
        else:
            id = item_id_generators[kwargs['type']](**kwargs)

        if id in self:
            return self[id]

        # if not cached, query the database
        item = self.fetch(bot, id)
        if item is not None:
            self[id] = item
            self.log.debug("library: music found in database: %s" % item.format_debug_string())
            return item

        # if not in the database, build one
        self[id] = item_builders[kwargs['type']](bot, **kwargs)  # newly built item will not be saved immediately
        return self[id]

    def get_items_by_tags(self, bot, tags):
        music_dicts = self.db.query_music_by_tags(tags)
        items = []
        if music_dicts:
            for music_dict in music_dicts:
                id = music_dict['id']
                self[id] = dict_to_item(bot, music_dict)
                items.append(self[id])

        return items

    def fetch(self, bot, id):
        music_dicts = self.db.query_music(Condition().and_equal("id", id))
        if music_dicts:
            music_dict = music_dicts[0]
            self[id] = dict_to_item(bot, music_dict)
            return self[id]
        else:
            return None

    def save(self, id):
        self.log.debug("library: music save into database: %s" % self[id].format_debug_string())
        self.db.insert_music(self[id].to_dict())

    def free_and_delete(self, id):
        item = self.get_item_by_id(None, id)
        if item:
            self.log.debug("library: DELETE item from the database: %s" % item.format_debug_string())

            if item.type == 'file' and item.path in self.file_id_lookup:
                if item.path in self.file_id_lookup:
                    del self.file_id_lookup[item.path]
                self.files.remove(item.path)
                self.save_dir_cache()
            elif item.type == 'url':
                if os.path.exists(item.path):
                    os.remove(item.path)

            if item.id in self:
                del self[item.id]
            self.db.delete_music(Condition().and_equal("id", item.id))

    def free(self, id):
        if id in self:
            self.log.debug("library: cache freed for item: %s" % self[id].format_debug_string())
            del self[id]

    def free_all(self):
        self.log.debug("library: all cache freed")
        self.clear()

    def build_dir_cache(self, bot):
        self.dir_lock.acquire()
        self.log.info("library: rebuild directory cache")
        self.files = []
        files = util.get_recursive_file_list_sorted(var.music_folder)
        self.dir = util.Dir(var.music_folder)
        for file in files:
            item = self.fetch(bot, item_id_generators['file'](path=file))
            if not item:
                item = item_builders['file'](bot, path=file)
                self.log.debug("library: music save into database: %s" % item.format_debug_string())
                self.db.insert_music(item.to_dict())

            self.dir.add_file(file)
            self.files.append(file)
            self.file_id_lookup[file] = item.id

        self.save_dir_cache()
        self.dir_lock.release()

    def save_dir_cache(self):
        var.db.set("dir_cache", "files", json.dumps(self.file_id_lookup))

    def load_dir_cache(self, bot):
        self.dir_lock.acquire()
        self.log.info("library: load directory cache from database")
        loaded = json.loads(var.db.get("dir_cache", "files"))
        self.files = loaded.keys()
        self.file_id_lookup = loaded
        self.dir = util.Dir(var.music_folder)
        for file, id in loaded.items():
            self.dir.add_file(file)
        self.dir_lock.release()


class CachedItemWrapper:
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


# Remember!!! Get wrapper functions will automatically add items into the cache!
def get_cached_wrapper(item, user):
    var.cache[item.id] = item
    return CachedItemWrapper(var.cache, item.id, item.type, user)


def get_cached_wrapper_from_scrap(bot, **kwargs):
    item = var.cache.get_item(bot, **kwargs)
    if 'user' not in kwargs:
        raise KeyError("Which user added this song?")
    return CachedItemWrapper(var.cache, item.id, kwargs['type'], kwargs['user'])


def get_cached_wrapper_from_dict(bot, dict_from_db, user):
    item = dict_to_item(bot, dict_from_db)
    return get_cached_wrapper(item, user)


def get_cached_wrapper_by_id(bot, id, user):
    item = var.cache.get_item_by_id(bot, id)
    if item:
        return CachedItemWrapper(var.cache, item.id, item.type, user)
    else:
        return None


def get_cached_wrappers_by_tags(bot, tags, user):
    items = var.cache.get_items_by_tags(bot, tags)
    ret = []
    for item in items:
        ret.append(CachedItemWrapper(var.cache, item.id, item.type, user))
    return ret
