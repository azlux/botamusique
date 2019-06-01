import youtube_dl
import urllib
import re

def build_dict(info, user="", start=0):
    music = {
        'type': 'url',
        'url': info['webpage_url'],
        'user': user,
        'start': start,
        'duration': info['duration'] / 60,
        'title': info['title'],
        'thumbnail': info['thumbnail']
    }
    for f in info['formats']:
        if f['format_id'] == info['format_id']:
            music['path'] = f['url']
            break
    return music

def get_start_time(qs):
     d = urllib.parse.parse_qs(qs)
     if 't' in d and len(d['t']) > 0:
         mins = re.match(r'(\d+)m', d['t'][0])
         mins = int(mins[1]) if mins else 0
         secs = re.match(r'(\d+)s', d['t'][0])
         secs = int(secs[1]) if secs else 0
         return mins * 60 + secs
     return 0

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

                components = urllib.parse.urlparse(url)
                start = get_start_time(components.query) or get_start_time(components.fragment)

                return [build_dict(info, user, start)]
            except youtube_dl.utils.DownloadError as e:
                print(e)
            except KeyError as e:
                print(e)
            except TypeError as e:
                print(e)
    return None
