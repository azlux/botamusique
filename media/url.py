import json
import logging
import re
import subprocess
import variables as var
import urllib

def build_dict(info, user="", start=0, end=-1):
    music = {
        'type': 'url',
        'url': info['webpage_url'],
        'user': user,
        'start': start,
        'end': end,
        'duration': info['duration'] / 60,
        'title': info['title'],
        'thumbnail': info['thumbnail']
    }
    for f in info['formats']:
        if f['format_id'] == info['format_id']:
            music['path'] = f['url']
            break
    return music

def get_time(qs, key):
     d = urllib.parse.parse_qs(qs)
     if key in d and len(d[key]) > 0:
         mins = re.match(r'([\d\.]+)m', d[key][0])
         mins = float(mins[1]) if mins else 0
         secs = re.match(r'([\d\.]+)s', d[key][0])
         secs = float(secs[1]) if secs else 0
         return mins * 60 + secs
     return None

def get_component_time(components, key):
    return get_time(components.query, key) or get_time(components.fragment, key)

ytdl_opts = ['-J', '-x', '-f', 'bestaudio/best']

def get_url_info(url, user=""):

    for i in range(2):
        try:
            args =  [var.config.get('bot', 'ytdl_path'), '--no-playlist'] + ytdl_opts + [url]
            logging.debug('youtube-dl command: ' + str(args))
            info = json.loads(subprocess.check_output(args))

            if info.get('_type') == 'playlist':
                entries = [build_dict(t, user) for t in info['entries']]
                for entry in entries:
                    entry.update({
                        'from_playlist': True,
                        'playlist_title': info['title'],
                        'playlist_url': url})
                    return entries

            components = urllib.parse.urlparse(url)
            start = get_component_time(components, 't') or get_component_time(components, 'start') or 0
            length = get_component_time(components, 'l') or get_component_time(components, 'length')
            end = start + length if length is not None else (get_component_time(components, 'end') or -1)

            return [build_dict(info, user, start, end)]
        except subprocess.CalledProcessError as e:
            print(e)
        except json.JSONDecodeError as e:
            print(e)
        except KeyError as e:
            print(e)
        except TypeError as e:
            print(e)
    return None
