import youtube_dl
import variables as var


def get_playlist_info():
    ydl_opts = {
        'playlist_items': str(0)
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for i in range(2):
            try:
                info = ydl.extract_info(var.playlist[-1]['url'], download=False)
                var.playlist[-1]['playlist_title'] = info['title']
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
                info = ydl.extract_info(var.playlist[0]['url'], download=False)
                if var.playlist[0]['current_index'] == index:
                    var.playlist[0]['current_duration'] = info['entries'][0]['duration'] / 60
                    var.playlist[0]['current_title'] = info['entries'][0]['title']
                elif var.playlist[0]['current_index'] == index - 1:
                    var.playlist[0]['next_duration'] = info['entries'][0]['duration'] / 60
                    var.playlist[0]['next_title'] = info['entries'][0]['title']
            except youtube_dl.utils.DownloadError:
                pass
            else:
                return True
    return False
