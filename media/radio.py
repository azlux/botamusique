import re
import urllib.request
import urllib.error
import logging
import json
import http.client
import struct


def get_radio_server_description(url):
    p = re.compile('(https?\:\/\/[^\/]*)', re.IGNORECASE)
    res = re.search(p, url)
    base_url = res.group(1)
    url_icecast = base_url + '/status-json.xsl'
    url_shoutcast = base_url + '/stats?json=1'
    title_server = None
    try:
        request = urllib.request.Request(url_shoutcast)
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode("utf-8"))
        title_server = data['servertitle']
        # logging.info("TITLE FOUND SHOUTCAST: " + title_server)
    except urllib.error.HTTPError:
        pass
    except http.client.BadStatusLine:
        pass
    except ValueError:
        return False

    if not title_server:
        try:
            request = urllib.request.Request(url_icecast)
            response = urllib.request.urlopen(request)
            response_data = response.read().decode('utf-8', errors='ignore')
            if response_data:
                data = json.loads(response_data, strict=False)
                source = data['icestats']['source']
                if type(source) is list:
                    source = source[0]
                title_server = source['server_name']
                if 'server_description' in source:
                    title_server += ' - ' + source['server_description']
                # logging.info("TITLE FOUND ICECAST: " + title_server)
                if not title_server:
                    title_server = url
        except urllib.error.URLError:
            title_server = url
        except http.client.BadStatusLine:
            pass
    return title_server


def get_radio_title(url):
    request = urllib.request.Request(url, headers={'Icy-MetaData': 1})
    try:

        response = urllib.request.urlopen(request)
        icy_metaint_header = int(response.headers['icy-metaint'])
        if icy_metaint_header is not None:
            response.read(icy_metaint_header)

            metadata_length = struct.unpack('B', response.read(1))[0] * 16  # length byte
            metadata = response.read(metadata_length).rstrip(b'\0')
            logging.info(metadata)
            # extract title from the metadata
            m = re.search(br"StreamTitle='([^']*)';", metadata)
            if m:
                title = m.group(1)
                if title:
                    return title.decode()
    except (urllib.error.URLError, urllib.error.HTTPError, http.client.BadStatusLine):
        pass
    return 'Unknown title'
