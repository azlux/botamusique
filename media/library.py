import logging

from database import MusicDatabase
from media.item import item_builders, item_loaders, item_id_generators
from media.file import FileItem
from media.url import URLItem
from media.url_from_playlist import PlaylistURLItem
from media.radio import RadioItem
from database import MusicDatabase
import variables as var


class MusicLibrary(dict):
    def __init__(self, db: MusicDatabase):
        super().__init__()
        self.db = db
        self.log = logging.getLogger("bot")

    def get_item_by_id(self, bot, id):
        if id in self:
            return self[id]

        # if not cached, query the database
        item = self.fetch(bot, id)
        if item is not None:
            self[id] = item
            self.log.debug("library: music found in database: %s" % item.format_debug_string())
            return item

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

    def delete(self, id):
        self.db.delete_music(id=id)

    def free(self, id):
        if id in self:
            del self[id]

    def free_all(self):
        self.clear()
