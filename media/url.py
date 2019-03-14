import youtube_dl


def build_dict(info, user=""):
    music = {
        'type': 'url',
        'url': info['webpage_url'],
        'user': user,
        'duration': info['duration'] / 60,
        'title': info['title'],
        'thumbnail': info['thumbnail']
    }
    for f in info['formats']:
        if f['format_id'] == info['format_id']:
            music['path'] = f['url']
            break
    return music


def get_url_info(url, user=""):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for i in range(2):
            try:
                info = ydl.extract_info(url, download=False)

                if info.get('_type') == 'playlist':
                    entries = [build_dict(t, user) for t in info['entries']]
                    for entry in entries:
                        entry.update({
                            'from_playlist': True,
                            'playlist_title': info['title'],
                            'playlist_url': url})
                    return entries

                return [build_dict(info, user)]
            except youtube_dl.utils.DownloadError as e:
                print(e)
            except KeyError as e:
                print(e)
            except TypeError as e:
                print(e)
    return None
