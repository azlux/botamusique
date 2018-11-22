import youtube_dl
import variables as var


def get_url_info():
    ydl_opts = {
        'noplaylist': True
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for i in range(2):
            try:
                print(var.playlist)
                info = ydl.extract_info(var.playlist[-1]['url'], download=False)
                var.playlist[-1]['duration'] = info['duration'] / 60
                var.playlist[-1]['title'] = info['title']
            except youtube_dl.utils.DownloadError:
                pass
            else:
                return True
    return False
