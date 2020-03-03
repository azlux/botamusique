import json
import random
import hashlib

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

type : file
    id
    path
    title
    artist
    duration
    thumbnail
    user
"""


class PlayList(list):
    current_index = -1
    version = 0 # increase by one after each change
    mode = "one-shot" # "repeat", "random"


    def __init__(self, *args):
        super().__init__(*args)

    def is_empty(self):
        return True if len(self) == 0 else False

    def set_mode(self, mode):
        # modes are "one-shot", "repeat", "random"
        self.mode = mode

        if mode == "random":
            self.randomize()

        elif mode == "one-shot" and self.current_index > 0:
            # remove items before current item
            self.version += 1
            for i in range(self.current_index):
                super().__delitem__(0)
            self.current_index = 0

    def append(self, item):
        self.version += 1
        item = util.attach_music_tag_info(item)
        super().append(item)

        return item

    def insert(self, index, item):
        self.version += 1

        if index == -1:
            index = self.current_index

        item = util.attach_music_tag_info(item)
        super().insert(index, item)

        if index <= self.current_index:
            self.current_index += 1

        return item

    def length(self):
        return len(self)

    def extend(self, items):
        self.version += 1
        items = list(map(
            lambda item: util.attach_music_tag_info(item),
            items))
        super().extend(items)
        return items

    def next(self):
        if len(self) == 0:
            return False

        self.version += 1
        #logging.debug("playlist: Next into the queue")

        if self.current_index < len(self) - 1:
            if self.mode == "one-shot" and self.current_index != -1:
                super().__delitem__(self.current_index)
            else:
                self.current_index += 1

            return self[self.current_index]
        else:
            self.current_index = 0
            if self.mode == "one-shot":
                self.clear()
                return False
            elif self.mode == "repeat":
                return self[0]
            elif self.mode == "random":
                self.randomize()
                return self[0]
            else:
                raise TypeError("Unknown playlist mode '%s'." % self.mode)

    def find(self, id):
        for index, item in enumerate(self):
            if item['id'] == id:
                return index
        return None

    def update(self, item, id):
        self.version += 1
        index = self.find(id)
        if index:
            self[index] = item
            return True
        return False

    def __delitem__(self, key):
        return self.remove(key)

    def remove(self, index=-1):
        self.version += 1
        if index > len(self) - 1:
            return False

        if index == -1:
            index = self.current_index

        removed = self[index]
        super().__delitem__(index)

        if self.current_index > index:
            self.current_index -= 1

        return removed

    def current_item(self):
        if len(self) == 0:
            return False

        return self[self.current_index]

    def current_item_downloading(self):
        if len(self) == 0:
            return False

        if self[self.current_index]['type'] == 'url' and self[self.current_index]['ready'] == 'downloading':
            return True
        return False

    def next_index(self):
        if len(self) == 0 or (len(self) == 1 and self.mode == 'one_shot'):
            return False

        if self.current_index < len(self) - 1:
            return self.current_index + 1
        else:
            return 0

    def next_item(self):
        if len(self) == 0 or (len(self) == 1 and self.mode == 'one_shot'):
            return False

        return self[self.next_index()]

    def jump(self, index):
        if self.mode == "one-shot":
            for i in range(index):
                super().__delitem__(0)
            self.current_index = 0
        else:
            self.current_index = index

        self.version += 1
        return self[self.current_index]

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
        super().clear()

    def save(self):
        var.db.remove_section("playlist_item")
        var.db.set("playlist", "current_index", self.current_index)

        for index, music in enumerate(self):
            for music in self:
                if music['type'] == 'url' and music['ready'] == 'downloading':
                    music['ready'] = 'no'

            var.db.set("playlist_item", str(index), json.dumps(music))

    def load(self):
        current_index = var.db.getint("playlist", "current_index", fallback=-1)
        if current_index == -1:
            return

        items = list(var.db.items("playlist_item"))
        items.sort(key=lambda v: int(v[0]))
        self.extend(list(map(lambda v: json.loads(v[1]), items)))

        self.current_index = current_index

    def _debug_print(self):
        print("===== Playlist(%d) ====" % self.current_index)
        for index, item in enumerate(self):
            if index == self.current_index:
                print("-> %d %s" % (index, item['title']))
            else:
                print("%d %s" % (index, item['title']))
        print("=====      End     ====")