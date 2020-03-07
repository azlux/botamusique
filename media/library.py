import logging
from database import MusicDatabase
import json

from media.item import item_builders, item_loaders, item_id_generators
from database import MusicDatabase
import variables as var
import util


class MusicLibrary(dict):
    def __init__(self, db: MusicDatabase):
        super().__init__()
        self.db = db
        self.log = logging.getLogger("bot")
        self.dir = None
        self.files = []

    def get_item_by_id(self, bot, id): # Why all these functions need a bot? Because it need the bot to send message!
        if id in self:
            return self[id]

        # if not cached, query the database
        item = self.fetch(bot, id)
        if item is not None:
            self[id] = item
            self.log.debug("library: music found in database: %s" % item.format_debug_string())
            return item
        else:
            raise KeyError("Unable to fetch item from the database! Please try to refresh the cache by !recache.")


    def get_item(self, bot, **kwargs):
        # kwargs should provide type and id, and parameters to build the item if not existed in the library.
        # if cached
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
        self[id] = item_builders[kwargs['type']](bot, **kwargs) # newly built item will not be saved immediately
        return self[id]

    def get_items_by_tags(self, bot, tags):
        music_dicts = self.db.query_music_by_tags(tags)
        items = []
        for music_dict in music_dicts:
            id = music_dicts['id']
            type = music_dict['type']
            self[id] = item_loaders[type](bot, music_dict)
            items.append(self[id])

        return items

    def fetch(self, bot, id):
        music_dicts = self.db.query_music(id=id)
        if music_dicts:
            music_dict = music_dicts[0]
            type = music_dict['type']
            self[id] = item_loaders[type](bot, music_dict)
            return self[id]
        else:
            return None

    def save(self, id):
        self.log.debug("library: music save into database: %s" % self[id].format_debug_string())
        self.db.insert_music(self[id].to_dict())

    def delete(self, item):
        if item.type == 'file' and item.path in self.file_id_lookup:
            self.log.debug("library: DELETE item from the database: %s" % item.format_debug_string())

            if item.id in self:
                del self[item.id]
            if item.path in self.file_id_lookup:
                del self.file_id_lookup[item.path]
            self.files.remove(item.path)
            self.save_dir_cache()

        self.db.delete_music(id=item.id)

    def free(self, id):
        if id in self:
            self.log.debug("library: cache freed for item: %s" % self[id].format_debug_string())
            del self[id]

    def free_all(self):
        self.log.debug("library: all cache freed")
        self.clear()

    def build_dir_cache(self, bot):
        self.log.info("library: rebuild directory cache")
        self.files = []
        self.file_id_lookup = {}
        files = util.get_recursive_file_list_sorted(var.music_folder)
        self.dir = util.Dir(var.music_folder)
        for file in files:
            item = self.get_item(bot, type='file', path=file)
            if item.validate():
                self.dir.add_file(file)
                self.files.append(file)
                self.file_id_lookup[file] = item.id

        self.save_dir_cache()

    def save_dir_cache(self):
        var.db.set("dir_cache", "files", json.dumps(self.file_id_lookup))

    def load_dir_cache(self, bot):
        self.log.info("library: load directory cache from database")
        loaded = json.loads(var.db.get("dir_cache", "files"))
        self.files = loaded.keys()
        self.file_id_lookup = loaded
        self.dir = util.Dir(var.music_folder)
        for file, id in loaded.items():
            self.dir.add_file(file)

