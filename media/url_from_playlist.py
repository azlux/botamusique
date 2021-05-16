import logging
import youtube_dl
from constants import tr_cli as tr
import variables as var
from media.item import item_builders, item_loaders, item_id_generators
from media.url import URLItem, url_item_id_generator


log = logging.getLogger("bot")


def get_playlist_info(url, start_index=0, user=""):
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'verbose': var.config.getboolean('debug', 'youtube_dl')
    }

    cookie = var.config.get('youtube_dl', 'cookiefile', fallback=None)
    if cookie:
        ydl_opts['cookiefile'] = var.config.get('youtube_dl', 'cookiefile', fallback=None)

    user_agent = var.config.get('youtube_dl', 'user_agent', fallback=None)
    if user_agent:
        youtube_dl.utils.std_headers['User-Agent'] = var.config.get('youtube_dl', 'user_agent')

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        attempts = var.config.getint('bot', 'download_attempts', fallback=2)
        for i in range(attempts):
            items = []
            try:
                info = ydl.extract_info(url, download=False)
                # # if url is not a playlist but a video
                # if 'entries' not in info and 'webpage_url' in info:
                #     music = {'type': 'url',
                #              'title': info['title'],
                #              'url': info['webpage_url'],
                #              'user': user,
                #              'ready': 'validation'}
                #     items.append(music)
                #     return items

                playlist_title = info['title']
                for j in range(start_index, min(len(info['entries']),
                                                start_index + var.config.getint('bot', 'max_track_playlist'))):
                    # Unknow String if No title into the json
                    title = info['entries'][j]['title'] if 'title' in info['entries'][j] else "Unknown Title"
                    # Add youtube url if the url in the json isn't a full url
                    item_url = info['entries'][j]['url'] if info['entries'][j]['url'][0:4] == 'http' \
                        else "https://www.youtube.com/watch?v=" + info['entries'][j]['url']
                    print(info['entries'][j])

                    music = {
                        "type": "url_from_playlist",
                        "url": item_url,
                        "title": title,
                        "playlist_url": url,
                        "playlist_title": playlist_title,
                        "user": user
                    }

                    items.append(music)

            except Exception as ex:
                log.exception(ex, exc_info=True)
                continue

            return items


def playlist_url_item_builder(**kwargs):
    return PlaylistURLItem(kwargs['url'],
                           kwargs['title'],
                           kwargs['playlist_url'],
                           kwargs['playlist_title'])


def playlist_url_item_loader(_dict):
    return PlaylistURLItem("", "", "", "", _dict)


item_builders['url_from_playlist'] = playlist_url_item_builder
item_loaders['url_from_playlist'] = playlist_url_item_loader
item_id_generators['url_from_playlist'] = url_item_id_generator


class PlaylistURLItem(URLItem):
    def __init__(self, url, title, playlist_url, playlist_title, from_dict=None):
        if from_dict is None:
            super().__init__(url)
            self.title = title
            self.playlist_url = playlist_url
            self.playlist_title = playlist_title
        else:
            super().__init__("", from_dict)
            self.playlist_title = from_dict['playlist_title']
            self.playlist_url = from_dict['playlist_url']

        self.type = "url_from_playlist"

    def to_dict(self):
        tmp_dict = super().to_dict()
        tmp_dict['playlist_url'] = self.playlist_url
        tmp_dict['playlist_title'] = self.playlist_title

        return tmp_dict

    def format_debug_string(self):
        return "[url] {title} ({url}) from playlist {playlist}".format(
            title=self.title,
            url=self.url,
            playlist=self.playlist_title
        )

    def format_song_string(self, user):
        return tr("url_from_playlist_item",
                  title=self.title,
                  url=self.url,
                  playlist_url=self.playlist_url,
                  playlist=self.playlist_title,
                  user=user)

    def format_current_playing(self, user):
        display = tr("now_playing", item=self.format_song_string(user))

        if self.thumbnail:
            thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                             self.thumbnail + '"/>'
            display += "<br />" + thumbnail_html

        return display

    def display_type(self):
        return tr("url_from_playlist")
