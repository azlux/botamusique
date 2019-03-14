import youtube_dl
import variables as var
import media.url


def get_playlist_info(url, start_index=1, user=""):
    ydl_opts = {
        'extract_flat': 'in_playlist'
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        musics = []
        for i in range(2):
            try:
                info = ydl.extract_info(url, download=False)
                playlist_title = info['title']
                for j in range(start_index, start_index + var.config.getint('bot', 'max_track_playlist')):
                    music = media.url.build_dict(info, user)
                    music.update({
                        'from_playlist': True,
                        'playlist_title': playlist_title,
                        'playlist_url': url})
                    musics.append(music)
            except youtube_dl.utils.DownloadError:
                pass
            else:
                return musics
    return None

