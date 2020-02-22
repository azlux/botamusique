import youtube_dl
import variables as var
import util
import random
import json

class PlayList:
    playlist = []
    current_index = 0
    version = 0 # increase by one after each change

    def append(self, item):
        self.version += 1
        item = util.get_music_tag_info(item)
        self.playlist.append(item)

        return item

    def insert(self, index, item):
        self.version += 1

        if index == -1:
            index = self.current_index

        item = util.get_music_tag_info(item)
        self.playlist.insert(index, item)

        if index <= self.current_index:
            self.current_index += 1

        return item

    def length(self):
        return len(self.playlist)

    def extend(self, items):
        self.version += 1
        items = list(map(
            lambda item: util.get_music_tag_info(item),
            items))
        self.playlist.extend(items)
        return items

    def next(self):
        self.version += 1
        if len(self.playlist) == 0:
            return False

        self.current_index = self.next_index()

        return self.playlist[self.current_index]

    def update(self, item, index=-1):
        self.version += 1
        if index == -1:
            index = self.current_index
        self.playlist[index] = item

    def remove(self, index=-1):
        self.version += 1
        if index > len(self.playlist) - 1:
            return False

        if index == -1:
            index = self.current_index

        removed = self.playlist[index]
        del self.playlist[index]

        if self.current_index > index:
            self.current_index -= 1

        return removed

    def current_item(self):
        return self.playlist[self.current_index]

    def next_index(self):
        if len(self.playlist) == 0:
            return False

        if self.current_index < len(self.playlist) - 1:
            return self.current_index + 1
        else:
            return 0

    def next_item(self):
        if len(self.playlist) == 0:
            return False

        return self.playlist[self.next_index()]

    def jump(self, index):
        self.version += 1
        self.current_index = index
        return self.playlist[index]

    def randomize(self):
        # current_index will lose track after shuffling, thus we take current music out before shuffling
        #current = self.current_item()
        #del self.playlist[self.current_index]

        random.shuffle(self.playlist)

        #self.playlist.insert(0, current)
        self.current_index = 0
        self.version += 1

    def clear(self):
        self.version += 1
        self.playlist = []
        self.current_index = 0

    def save(self):
        var.db.remove_section("playlist_item")
        var.db.set("playlist", "current_index", self.current_index)
        for index, item in enumerate(self.playlist):
            var.db.set("playlist_item", str(index), json.dumps(item))

    def load(self):
        current_index = var.db.getint("playlist", "current_index", fallback=-1)
        if current_index == -1:
            return

        items = list(var.db.items("playlist_item"))
        items.sort(key=lambda v: int(v[0]))
        self.playlist = list(map(lambda v: json.loads(v[1]), items))
        self.current_index = current_index


def get_playlist_info(url, start_index=0, user=""):
    items = []
    ydl_opts = {
        'extract_flat': 'in_playlist'
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for i in range(2):
            try:
                info = ydl.extract_info(url, download=False)
                # if url is not a playlist but a video
                if 'entries' not in info and 'webpage_url' in info:
                    music = {'type': 'url',
                             'title': info['title'],
                             'url': info['webpage_url'],
                             'user': user,
                             'ready': 'validation'}
                    items.append(music)
                    return items

                playlist_title = info['title']
                for j in range(start_index, min(len(info['entries']), start_index + var.config.getint('bot', 'max_track_playlist'))):
                    # Unknow String if No title into the json
                    title = info['entries'][j]['title'] if 'title' in info['entries'][j] else "Unknown Title"
                    # Add youtube url if the url in the json isn't a full url
                    url = info['entries'][j]['url'] if info['entries'][j]['url'][0:4] == 'http' else "https://www.youtube.com/watch?v=" + info['entries'][j]['url']

                    music = {'type': 'url',
                             'title': title,
                             'url': url,
                             'user': user,
                             'from_playlist': True,
                             'playlist_title': playlist_title,
                             'playlist_url': url,
                             'ready': 'validation'}
                    items.append(music)
            except youtube_dl.utils.DownloadError:
                pass

    return items

# def get_music_info(index=0):
#     ydl_opts = {
#         'playlist_items': str(index)
#     }
#     with youtube_dl.YoutubeDL(ydl_opts) as ydl:
#         for i in range(2):
#             try:
#                 info = ydl.extract_info(var.playlist.playlist[index]['url'], download=False)
#                 # Check if the Duration is longer than the config
#                 if var.playlist[index]['current_index'] == index:
#                     var.playlist[index]['current_duration'] = info['entries'][0]['duration'] / 60
#                     var.playlist[index]['current_title'] = info['entries'][0]['title']
#                 # Check if the Duration of the next music is longer than the config (async download)
#                 elif var.playlist[index]['current_index'] == index - 1:
#                     var.playlist[index]['next_duration'] = info['entries'][0]['duration'] / 60
#                     var.playlist[index]['next_title'] = info['entries'][0]['title']
#             except youtube_dl.utils.DownloadError:
#                 pass
#             else:
#                 return True
#     return False
