import json
import subprocess
import variables as var
import media.url


def get_playlist_info(url, start_index=1, user=""):
    musics = media.url.get_url_info(url, user)
    if musics:
        return musics[(start_index-1):var.config.getint('bot', 'max_track_playlist')]
    return None
