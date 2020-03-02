import re
import logging
import json
import http.client
import struct
import requests
import traceback

log = logging.getLogger("bot")

def get_radio_server_description(url):
    global log

    p = re.compile('(https?\:\/\/[^\/]*)', re.IGNORECASE)
    res = re.search(p, url)
    base_url = res.group(1)
    url_icecast = base_url + '/status-json.xsl'
    url_shoutcast = base_url + '/stats?json=1'
    title_server = None
    try:
        r = requests.get(url_shoutcast, timeout=5)
        data = r.json()
        title_server = data['servertitle']
        return title_server
        # logging.info("TITLE FOUND SHOUTCAST: " + title_server)
    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.Timeout) as e:
        error_traceback = traceback.format_exc()
        error = error_traceback.rstrip().split("\n")[-1]
        log.debug("radio: unsuccessful attempts on fetching radio description (shoutcast): " + error)
    except ValueError:
        return False # ?

    try:
        r = requests.get(url_icecast, timeout=5)
        data = r.json()
        source = data['icestats']['source']
        if type(source) is list:
            source = source[0]
        title_server = source['server_name']
        if 'server_description' in source:
            title_server += ' - ' + source['server_description']
        # logging.info("TITLE FOUND ICECAST: " + title_server)
        return title_server
    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.Timeout) as e:
        error_traceback = traceback.format_exc()
        error = error_traceback.rstrip().split("\n")[-1]
        log.debug("radio: unsuccessful attempts on fetching radio description (icecast): " + error)

    return url


def get_radio_title(url):
    try:
        r = requests.get(url, headers={'Icy-MetaData': '1'}, stream=True, timeout=5)
        icy_metaint_header = int(r.headers['icy-metaint'])
        r.raw.read(icy_metaint_header)

        metadata_length = struct.unpack('B', r.raw.read(1))[0] * 16  # length byte
        metadata = r.raw.read(metadata_length).rstrip(b'\0')
        logging.info(metadata)
        # extract title from the metadata
        m = re.search(br"StreamTitle='([^']*)';", metadata)
        if m:
            title = m.group(1)
            if title:
                return title.decode()
    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
        pass
    return url
