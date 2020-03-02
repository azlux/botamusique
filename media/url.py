import youtube_dl
import variables as var


def get_url_info(music):
    ydl_opts = {
        'noplaylist': True
    }
    music['duration'] = 0
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for i in range(2):
            try:
                info = ydl.extract_info(music['url'], download=False)
                music['duration'] = info['duration'] / 60
                music['title'] = info['title']
            except youtube_dl.utils.DownloadError:
                pass
            except KeyError:
                return music
            else:
                return music
    return False
