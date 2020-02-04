import youtube_dl
import variables as var

class PlayList:
    playlist = []
    current_index = 0

    def append(self, item):
        self.playlist.append(item)

    def insert(self, index, item):
        if index == -1:
            index = self.current_index

        self.playlist.insert(index, item)

        if index <= self.current_index:
            self.current_index += 1

    def length(self):
        return len(self.playlist)

    def extend(self, items):
        self.playlist.extend(items)

    def next(self):
        if len(self.playlist) == 0:
            return False

        self.current_index = self.next_index()

        return self.playlist[self.current_index]

    def update(self, item, index=-1):
        if index == -1:
            index = self.current_index
        self.playlist[index] = item

    def remove(self, index=-1):
        if index > len(self.playlist) - 1:
            return False

        if index == -1:
            index = self.current_index
        del self.playlist[index]

        if self.current_index <= index:
            self.next()

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
        self.current_index = index
        return self.playlist[index]

    def clear(self):
        self.playlist = []
        self.current_index = 0


def get_playlist_info(url, start_index=0, user=""):
    ydl_opts = {
        'extract_flat': 'in_playlist'
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for i in range(2):
            try:
                info = ydl.extract_info(url, download=False)
                playlist_title = info['title']
                for j in range(start_index, min(len(info['entries']), start_index + var.config.getint('bot', 'max_track_playlist'))):
                    # Unknow String if No title into the json
                    title = info['entries'][j]['title'] if 'title' in info['entries'][j] else "Unknown Title"
                    # Add youtube url if the url in the json isn't a full url
                    url = info['entries'][j]['url'] if info['entries'][j]['url'][0:4] == 'http' else "https://www.youtube.com/watch?v=" + info['entries'][j]['url']

                    # append the music to a list of futur music to play
                    music = {'type': 'url',
                             'title': title,
                             'url': url,
                             'user': user,
                             'from_playlist': True,
                             'playlist_title': playlist_title,
                             'playlist_url': url,
                             'ready': 'validation'}
                    var.playlist.append(music)
            except youtube_dl.utils.DownloadError:
                pass
            else:
                return True
    return False


def get_music_info(index=0):
    ydl_opts = {
        'playlist_items': str(index)
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for i in range(2):
            try:
                info = ydl.extract_info(var.playlist.playlist[index]['url'], download=False)
                # Check if the Duration is longer than the config
                if var.playlist[index]['current_index'] == index:
                    var.playlist[index]['current_duration'] = info['entries'][0]['duration'] / 60
                    var.playlist[index]['current_title'] = info['entries'][0]['title']
                # Check if the Duration of the next music is longer than the config (async download)
                elif var.playlist[index]['current_index'] == index - 1:
                    var.playlist[index]['next_duration'] = info['entries'][0]['duration'] / 60
                    var.playlist[index]['next_title'] = info['entries'][0]['title']
            except youtube_dl.utils.DownloadError:
                pass
            else:
                return True
    return False
