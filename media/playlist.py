import youtube_dl
import variables as var


def get_playlist_info(url, start_index=1, user=""):
    ydl_opts = {
        'extract_flat': 'in_playlist'
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for i in range(2):
            try:
                info = ydl.extract_info(url, download=False)
                playlist_title = info['title']
                for j in range(start_index, start_index + var.config.getint('bot', 'max_track_playlist')):
                    music = {'type': 'url',
                             'title': info['entries'][j]['title'],
                             'url': "https://www.youtube.com/watch?v=" + info['entries'][j]['url'],
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
