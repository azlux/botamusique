import youtube_dl
import variables as var


def get_playlist_info(url, start_index=0, user=""):
    items = []
    ydl_opts = {
        'extract_flat': 'in_playlist'
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        attempts = var.config.getint('bot', 'download_attempts', fallback=2)
        for i in range(attempts):
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
                for j in range(start_index, min(len(info['entries']), start_index + var.config.getint('bot', 'max_track_playlist'))):
                    print(info['entries'][j])
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
            except:
                pass

    return items
