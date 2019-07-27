#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import time
import sys
import signal
import configparser
import audioop
import subprocess as sp
import argparse
import os.path
import pymumble.pymumble_py3 as pymumble
import interface
import variables as var
import hashlib
import youtube_dl
import logging
import util
import base64
from PIL import Image
from io import BytesIO
from mutagen.easyid3 import EasyID3
import re
import media.url
import media.file
import media.playlist
import media.radio
import media.system
from librb import radiobrowser

"""
FORMAT OF A MUSIC INTO THE PLAYLIST
type : url
    url
    title
    path
    duration
    thundnail
    user
    ready (validation, no, downloading, yes)
    from_playlist (yes,no)
    playlist_title
    playlist_url

type : radio
    url
    name
    current_title
    user

type : file
    path
    title
    duration
    user
"""

version = 2


class MumbleBot:
    def __init__(self, args):
        signal.signal(signal.SIGINT, self.ctrl_caught)
        self.volume = var.config.getfloat('bot', 'volume')
        if db.has_option('bot', 'volume'):
            self.volume = var.db.getfloat('bot', 'volume')

        self.channel = args.channel

        # Set specific format for the log
        FORMAT = '%(asctime)s: %(message)s'
        if args.verbose:
            logging.basicConfig(
                format=FORMAT, level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
            logging.debug("Starting in DEBUG loglevel")
        elif args.quiet:
            logging.basicConfig(
                format=FORMAT, level=logging.ERROR, datefmt='%Y-%m-%d %H:%M:%S')
            logging.error("Starting in ERROR loglevel")
        else:
            logging.basicConfig(
                format=FORMAT, level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
            logging.info("Starting in INFO loglevel")

        # the playlist is... a list (Surprise !!)
        var.playlist = []

        var.user = args.user
        var.music_folder = var.config.get('bot', 'music_folder')
        var.is_proxified = var.config.getboolean(
            "webinterface", "is_web_proxified")
        self.exit = False
        self.nb_exit = 0
        self.thread = None
        self.is_playing = False

        if var.config.getboolean("webinterface", "enabled"):
            wi_addr = var.config.get("webinterface", "listening_addr")
            wi_port = var.config.getint("webinterface", "listening_port")
            interface.init_proxy()
            tt = threading.Thread(
                target=start_web_interface, args=(wi_addr, wi_port))
            tt.daemon = True
            tt.start()

        if args.host:
            host = args.host
        else:
            host = var.config.get("server", "host")

        if args.port:
            port = args.port
        else:
            port = var.config.getint("server", "port")

        if args.password:
            password = args.password
        else:
            password = var.config.get("server", "password")

        if args.certificate:
            certificate = args.certificate
        else:
            certificate = var.config.get("server", "certificate")

        if args.tokens:
            tokens = args.tokens
        else:
            tokens = var.config.get("server", "tokens")
            tokens = tokens.split(',')

        if args.user:
            self.username = args.user
        else:
            self.username = var.config.get("bot", "username")

        self.mumble = pymumble.Mumble(host, user=self.username, port=port, password=password, tokens=tokens,
                                      debug=var.config.getboolean('debug', 'mumbleConnection'), certfile=certificate)
        self.mumble.callbacks.set_callback(
            "text_received", self.message_received)

        self.mumble.set_codec_profile("audio")
        self.mumble.start()  # start the mumble thread
        self.mumble.is_ready()  # wait for the connection
        self.set_comment()
        self.mumble.users.myself.unmute()  # by sure the user is not muted
        if self.channel:
            self.mumble.channels.find_by_name(self.channel).move_in()
        self.mumble.set_bandwidth(200000)

        self.loop()

    # Set the CTRL+C shortcut
    def ctrl_caught(self, signal, frame):
        logging.info(
            "\nSIGINT caught, quitting, {} more to kill".format(2 - self.nb_exit))
        self.exit = True
        self.stop()
        if self.nb_exit > 1:
            logging.info("Forced Quit")
            sys.exit(0)
        self.nb_exit += 1

    # All text send to the chat is analysed by this function
    def message_received(self, text):

        message = text.message.strip()
        user = self.mumble.users[text.actor]['name']

        if var.config.getboolean('command', 'split_username_at_space'):
            # in can you use https://github.com/Natenom/mumblemoderator-module-collection/tree/master/os-suffixes , you want to split the username
            user = user.split()[0]

        if message[0] == var.config.get('command', 'command_symbol'):
            # remove the symbol from the message
            message = message[1:].split(' ', 1)

            # use the first word as a command, the others one as  parameters
            if len(message) > 0:
                command = message[0]
                parameter = ''
                if len(message) > 1:
                    parameter = message[1]

            else:
                return

            logging.info(command + ' - ' + parameter + ' by ' + user)

            if command == var.config.get('command', 'joinme'):
                self.mumble.users.myself.move_in(
                    self.mumble.users[text.actor]['channel_id'], token=parameter)
                return

            # Anti stupid guy function
            if not self.is_admin(user) and not var.config.getboolean('bot', 'allow_other_channel_message') and self.mumble.users[text.actor]['channel_id'] != self.mumble.users.myself['channel_id']:
                self.mumble.users[text.actor].send_text_message(
                    var.config.get('strings', 'not_in_my_channel'))
                return

            if not self.is_admin(user) and not var.config.getboolean('bot', 'allow_private_message') and text.session:
                self.mumble.users[text.actor].send_text_message(
                    var.config.get('strings', 'pm_not_allowed'))
                return

            ###
            # Admin command
            ###
            for i in var.db.items("user_ban"):
                if user.lower() == i[0]:
                    self.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'user_ban'))
                    return

            if command == var.config.get('command', 'user_ban'):
                if self.is_admin(user):
                    if parameter:
                        self.mumble.users[text.actor].send_text_message(
                            util.user_ban(parameter))
                    else:
                        self.mumble.users[text.actor].send_text_message(
                            util.get_user_ban())
                else:
                    self.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'not_admin'))
                return

            elif command == var.config.get('command', 'user_unban'):
                if self.is_admin(user):
                    if parameter:
                        self.mumble.users[text.actor].send_text_message(
                            util.user_unban(parameter))
                else:
                    self.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'not_admin'))
                return

            elif command == var.config.get('command', 'url_ban'):
                if self.is_admin(user):
                    if parameter:
                        self.mumble.users[text.actor].send_text_message(
                            util.url_ban(self.get_url_from_input(parameter)))
                    else:
                        self.mumble.users[text.actor].send_text_message(
                            util.get_url_ban())
                else:
                    self.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'not_admin'))
                return

            elif command == var.config.get('command', 'url_unban'):
                if self.is_admin(user):
                    if parameter:
                        self.mumble.users[text.actor].send_text_message(
                            util.url_unban(self.get_url_from_input(parameter)))
                else:
                    self.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'not_admin'))
                return

            if parameter:
                for i in var.db.items("url_ban"):
                    if self.get_url_from_input(parameter.lower()) == i[0]:
                        self.mumble.users[text.actor].send_text_message(
                            var.config.get('strings', 'url_ban'))
                        return

            ###
            # everyday commands
            ###
            if command == var.config.get('command', 'play_file') and parameter:
                music_folder = var.config.get('bot', 'music_folder')
                # sanitize "../" and so on
                path = os.path.abspath(os.path.join(music_folder, parameter))
                if path.startswith(music_folder):
                    if os.path.isfile(path):
                        filename = path.replace(music_folder, '')
                        music = {'type': 'file',
                                 'path': filename,
                                 'user': user}
                        var.playlist.append(music)
                    else:
                        # try to do a partial match
                        matches = [file for file in util.get_recursive_filelist_sorted(
                            music_folder) if parameter.lower() in file.lower()]
                        if len(matches) == 0:
                            self.send_msg(var.config.get(
                                'strings', 'no_file'), text)
                        elif len(matches) == 1:
                            music = {'type': 'file',
                                     'path': matches[0],
                                     'user': user}
                            var.playlist.append(music)
                        else:
                            msg = var.config.get(
                                'strings', 'multiple_matches') + '<br />'
                            msg += '<br />'.join(matches)
                            self.send_msg(msg, text)
                else:
                    self.send_msg(var.config.get('strings', 'bad_file'), text)
                self.async_download_next()

            elif command == var.config.get('command', 'play_url') and parameter:
                music = {'type': 'url',
                         # grab the real URL
                         'url': self.get_url_from_input(parameter),
                         'user': user,
                         'ready': 'validation'}
                var.playlist.append(music)

                if media.url.get_url_info():
                    if var.playlist[-1]['duration'] > var.config.getint('bot', 'max_track_duration'):
                        var.playlist.pop()
                        self.send_msg(var.config.get(
                            'strings', 'too_long'), text)
                    else:
                        for i in var.db.options("url_ban"):
                            if var.playlist[-1]['url'] == i:
                                self.mumble.users[text.actor].send_text_message(
                                    var.config.get('strings', 'url_ban'))
                                var.playlist.pop()
                                return
                        var.playlist[-1]['ready'] = "no"
                        self.async_download_next()
                else:
                    var.playlist.pop()
                    self.send_msg(var.config.get(
                        'strings', 'unable_download'), text)

            elif command == var.config.get('command', 'play_playlist') and parameter:
                offset = 1  # if you want to start the playlist at a specific index
                try:
                    offset = int(parameter.split(" ")[-1])
                except ValueError:
                    pass
                if media.playlist.get_playlist_info(url=self.get_url_from_input(parameter), start_index=offset, user=user):
                    self.async_download_next()

            elif command == var.config.get('command', 'play_radio'):
                if not parameter:
                    all_radio = var.config.items('radio')
                    msg = var.config.get(
                        'strings', 'preconfigurated_radio') + " :"
                    for i in all_radio:
                        comment = ""
                        if len(i[1].split(maxsplit=1)) == 2:
                            comment = " - " + i[1].split(maxsplit=1)[1]
                        msg += "<br />" + i[0] + comment
                    self.send_msg(msg, text)
                else:
                    if var.config.has_option('radio', parameter):
                        parameter = var.config.get('radio', parameter)
                        parameter = parameter.split()[0]
                    url = self.get_url_from_input(parameter)
                    if url:
                        music = {'type': 'radio',
                                 'url': url,
                                 'user': user}
                        var.playlist.append(music)
                        self.async_download_next()
                    else:
                        self.send_msg(var.config.get('strings', 'bad_url'))
            # query http://www.radio-browser.info API for a radio station
            elif command == var.config.get('command', 'rb_query'):
                logging.info('Querying radio stations')
                if not parameter:
                    logging.debug('rbquery without parameter')
                    msg += 'You have to add a query text to search for a specific radio station.'
                    self.send_msg(msg, text)
                else:
                    logging.debug('Found query parameter: ' + parameter)
                    self.send_msg('Searching for stations - this may take some seconds...', text)
                    rb_stations = radiobrowser.getstations_byname(parameter)
                    msg = var.config.get('strings', 'rbqueryresult') + " :"
                    msg += '\n<table><tr><th>ID</th><th>Station Name</th></tr>'
                    if not rb_stations:
                        self.send_msg('No results for ' + parameter, text)
                    else:
                        for s in rb_stations:
                            msg += '<tr><td>' + s['id'] + '</td><td>' + s['stationname'] + '</td></tr>'
                        msg += '</table>'
                        self.send_msg(msg, text)
            # Play a secific station (by id) from http://www.radio-browser.info API
            elif command == var.config.get('command', 'rb_play'):
                logging.debug('Play a station by ID')
                if not parameter:
                    logging.debug('rbplay without parameter')
                    msg += 'Please enter a station ID from rbquery. Example: !rbplay 96748'
                    self.send_msg(msg, text)
                else:
                    logging.debug('Retreiving url for station ID ' + parameter)
                    url = radiobrowser.geturl_byid(parameter)
                    if url != "-1":
                        logging.info('Found url: ' + url)
                        music = {'type': 'radio',
			                     'url': url,
			                     'user': user}
                        var.playlist.append(music)
                        self.async_download_next()
                    else:
                        logging.info('No playable url found.')
                        msg += "No playable url found for this station, please try another station."
                        self.send_msg(msg, text)

            elif command == var.config.get('command', 'help'):
                self.send_msg(var.config.get('strings', 'help'), text)
                if self.is_admin(user):
                    self.send_msg(var.config.get(
                        'strings', 'admin_help'), text)

            elif command == var.config.get('command', 'stop'):
                self.stop()

            elif command == var.config.get('command', 'kill'):
                if self.is_admin(user):
                    self.stop()
                    self.exit = True
                else:
                    self.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'not_admin'))

            elif command == var.config.get('command', 'update'):
                if self.is_admin(user):
                    self.mumble.users[text.actor].send_text_message(
                        "Starting the update")
                    # Need to be improved
                    msg = util.update(version)
                    self.mumble.users[text.actor].send_text_message(msg)
                else:
                    self.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'not_admin'))

            elif command == var.config.get('command', 'stop_and_getout'):
                self.stop()
                if self.channel:
                    self.mumble.channels.find_by_name(self.channel).move_in()

            elif command == var.config.get('command', 'volume'):
                # The volume is a percentage
                if parameter is not None and parameter.isdigit() and 0 <= int(parameter) <= 100:
                    self.volume = float(float(parameter) / 100)
                    self.send_msg(var.config.get('strings', 'change_volume') % (
                        int(self.volume * 100), self.mumble.users[text.actor]['name']), text)
                    var.db.set('bot', 'volume', str(self.volume))
                else:
                    self.send_msg(var.config.get(
                        'strings', 'current_volume') % int(self.volume * 100), text)

            elif command == var.config.get('command', 'current_music'):
                if len(var.playlist) > 0:
                    source = var.playlist[0]["type"]
                    if source == "radio":
                        reply = "[radio] {title} on {url} by {user}".format(
                            title=media.radio.get_radio_title(
                                var.playlist[0]["url"]),
                            url=var.playlist[0]["title"],
                            user=var.playlist[0]["user"]
                        )
                    elif source == "url" and 'from_playlist' in var.playlist[0]:
                        reply = "[playlist] {title} (from the playlist <a href=\"{url}\">{playlist}</a> by {user}".format(
                            title=var.playlist[0]["title"],
                            url=var.playlist[0]["playlist_url"],
                            playlist=var.playlist[0]["playlist_title"],
                            user=var.playlist[0]["user"]
                        )
                    elif source == "url":
                        reply = "[url] {title} (<a href=\"{url}\">{url}</a>) by {user}".format(
                            title=var.playlist[0]["title"],
                            url=var.playlist[0]["url"],
                            user=var.playlist[0]["user"]
                        )
                    elif source == "file":
                        reply = "[file] {title} by {user}".format(
                            title=var.playlist[0]["title"],
                            user=var.playlist[0]["user"])
                    else:
                        reply = "ERROR"
                        logging.error(var.playlist)
                else:
                    reply = var.config.get('strings', 'not_playing')

                self.send_msg(reply, text)

            elif command == var.config.get('command', 'skip'):
                # Allow to remove specific music into the queue with a number
                if parameter is not None and parameter.isdigit() and int(parameter) > 0:
                    if int(parameter) < len(var.playlist):
                        removed = var.playlist.pop(int(parameter))

                        # the Title isn't here if the music wasn't downloaded
                        self.send_msg(var.config.get('strings', 'removing_item') % (
                            removed['title'] if 'title' in removed else removed['url']), text)
                    else:
                        self.send_msg(var.config.get(
                            'strings', 'no_possible'), text)
                elif self.next():  # Is no number send, just skip the current music
                    self.launch_music()
                    self.async_download_next()
                else:
                    self.send_msg(var.config.get(
                        'strings', 'queue_empty'), text)
                    self.stop()

            elif command == var.config.get('command', 'list'):
                folder_path = var.config.get('bot', 'music_folder')

                files = util.get_recursive_filelist_sorted(folder_path)
                if files:
                    self.send_msg('<br>'.join(files), text)
                else:
                    self.send_msg(var.config.get('strings', 'no_file'), text)

            elif command == var.config.get('command', 'queue'):
                if len(var.playlist) <= 1:
                    msg = var.config.get('strings', 'queue_empty')
                else:
                    msg = var.config.get(
                        'strings', 'queue_contents') + '<br />'
                    i = 1
                    for value in var.playlist[1:]:
                        msg += '[{}] ({}) {}<br />'.format(i, value['type'],
                                                           value['title'] if 'title' in value else value['url'])
                        i += 1

                self.send_msg(msg, text)

            elif command == var.config.get('command', 'repeat'):
                var.playlist.append(var.playlist[0])

            else:
                self.mumble.users[text.actor].send_text_message(
                    var.config.get('strings', 'bad_command'))

    @staticmethod
    def is_admin(user):
        list_admin = var.config.get('bot', 'admin').split(';')
        if user in list_admin:
            return True
        else:
            return False

    @staticmethod
    def next():
        logging.debug("Next into the queue")
        if len(var.playlist) > 1:
            var.playlist.pop(0)
            return True
        elif len(var.playlist) == 1:
            var.playlist.pop(0)
            return False
        else:
            return False

    def launch_music(self):
        uri = ""
        logging.debug("launch_music asked" + str(var.playlist[0]))
        if var.playlist[0]["type"] == "url":
            # Delete older music is the tmp folder is too big
            media.system.clear_tmp_folder(var.config.get(
                'bot', 'tmp_folder'), var.config.getint('bot', 'tmp_folder_max_size'))

            # Check if the music is ready to be played
            if var.playlist[0]["ready"] == "downloading":
                return
            elif var.playlist[0]["ready"] != "yes":
                logging.info("Current music wasn't ready, Downloading...")
                self.download_music(index=0)

            # get the Path
            uri = var.playlist[0]['path']
            if os.path.isfile(uri):
                audio = EasyID3(uri)
                title = ""
                if audio["title"]:
                    # take the title from the file tag
                    title = audio["title"][0]

                # Remove .mp3 and add .jpg
                path_thumbnail = var.playlist[0]['path'][:-4] + '.jpg'
                thumbnail_html = ""
                if os.path.isfile(path_thumbnail):
                    # Create the image message
                    im = Image.open(path_thumbnail)
                    im.thumbnail((100, 100), Image.ANTIALIAS)
                    buffer = BytesIO()
                    im.save(buffer, format="JPEG")
                    thumbnail_base64 = base64.b64encode(buffer.getvalue())
                    thumbnail_html = '<img - src="data:image/PNG;base64,' + \
                        thumbnail_base64.decode() + '"/>'

                logging.debug("Thunbail data " + thumbnail_html)
                if var.config.getboolean('bot', 'announce_current_music'):
                    self.send_msg(var.config.get(
                        'strings', 'now_playing') % (title, thumbnail_html))
            else:
                logging.error("Error with the path during launch_music")
                pass

        elif var.playlist[0]["type"] == "file":
            uri = var.config.get('bot', 'music_folder') + \
                var.playlist[0]["path"]

        elif var.playlist[0]["type"] == "radio":
            uri = var.playlist[0]["url"]
            title = media.radio.get_radio_server_description(uri)
            var.playlist[0]["title"] = title
            if var.config.getboolean('bot', 'announce_current_music'):
                self.send_msg(var.config.get('strings', 'now_playing') %
                              (title, "URL : " + uri))

        if var.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"

        command = ("ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i',
                   uri, '-ac', '1', '-f', 's16le', '-ar', '48000', '-')
        logging.info("FFmpeg command : " + " ".join(command))
        # The ffmpeg process is a thread
        self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
        self.is_playing = True

    def download_music(self, index):
        if var.playlist[index]['type'] == 'url' and var.playlist[index]['ready'] == "validation":
            if media.url.get_url_info(index=index):
                if var.playlist[index]['duration'] > var.config.getint('bot', 'max_track_duration'):
                    # Check the length, useful in case of playlist, it wasn't checked before)
                    var.playlist.pop()
                    logging.info(
                        "the music " + var.playlist[index]["url"] + " has a duration of " + var.playlist[index]['duration'] + "s -- too long")
                    self.send_msg(var.config.get('strings', 'too_long'))
                    return
                else:
                    var.playlist[index]['ready'] = "no"
            else:
                var.playlist.pop(index)
                logging.error("Error while fetching info from the URL")
                self.send_msg(var.config.get('strings', 'unable_download'))

        if var.playlist[index]['type'] == 'url' and var.playlist[index]['ready'] == "no":
            # download the music
            var.playlist[index]['ready'] = "downloading"

            logging.debug("Download index:" + str(index))
            logging.debug(var.playlist[index])

            url = var.playlist[index]['url']
            url_hash = hashlib.md5(url.encode()).hexdigest()

            path = var.config.get('bot', 'tmp_folder') + url_hash + ".%(ext)s"
            mp3 = path.replace(".%(ext)s", ".mp3")
            var.playlist[index]['path'] = mp3

            # if os.path.isfile(mp3):
            #    audio = EasyID3(mp3)
            #    var.playlist[index]['title'] = audio["title"][0]
            ydl_opts = ""

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': path,
                'noplaylist': True,
                'writethumbnail': True,
                'updatetime': False,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'},
                    {'key': 'FFmpegMetadata'}]
            }
            self.send_msg(var.config.get(
                'strings', "download_in_progress") % var.playlist[index]['title'])

            logging.info("Information before start downloading :" +
                         str(var.playlist[index]))
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                for i in range(2):  # Always try 2 times
                    try:
                        ydl.extract_info(url)
                        if 'ready' in var.playlist[index] and var.playlist[index]['ready'] == "downloading":
                            var.playlist[index]['ready'] = "yes"
                    except youtube_dl.utils.DownloadError:
                        pass
                    else:
                        break
            return

    def async_download_next(self):
        # Function start if the next music isn't ready
        # Do nothing in case the next music is already downloaded
        logging.info("Async download next asked")
        if len(var.playlist) > 1 and var.playlist[1]['type'] == 'url' and var.playlist[1]['ready'] in ["no", "validation"]:
            th = threading.Thread(
                target=self.download_music, kwargs={'index': 1})
        else:
            return
        logging.info("Start downloading next in thread")
        th.daemon = True
        th.start()

    @staticmethod
    # Parse the html from the message to get the URL
    def get_url_from_input(string):
        if string.startswith('http'):
            return string
        p = re.compile('href="(.+?)"', re.IGNORECASE)
        res = re.search(p, string)
        if res:
            return res.group(1)
        else:
            return False

    # Main loop of the Bot
    def loop(self):
        raw_music = ""
        while not self.exit and self.mumble.isAlive():

            while self.mumble.sound_output.get_buffer_size() > 0.5 and not self.exit:
                # If the buffer isn't empty, I cannot send new music part, so I wait
                time.sleep(0.01)
            if self.thread:
                # I get raw from ffmpeg thread
                raw_music = self.thread.stdout.read(480)
                if raw_music:
                    # Adjust the volume and send it to mumble
                    self.mumble.sound_output.add_sound(
                        audioop.mul(raw_music, 2, self.volume))
                else:
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

            if self.thread is None or not raw_music:
                # Not music into the buffet
                if self.is_playing:
                    # get next music
                    self.is_playing = False
                    self.next()
                if len(var.playlist) > 0:
                    if var.playlist[0]['type'] in ['radio', 'file'] \
                            or (var.playlist[0]['type'] == 'url' and var.playlist[0]['ready'] not in ['validation', 'downloading']):
                        # Check if the music can be start before launch the music
                        self.launch_music()
                        self.async_download_next()

        while self.mumble.sound_output.get_buffer_size() > 0:
            # Empty the buffer before exit
            time.sleep(0.01)
        time.sleep(0.5)

        if self.exit:
            # The db is not fixed config like url/user ban and volume
            util.write_db()

    def stop(self):
        # Kill the ffmpeg thread and empty the playlist
        if self.thread:
            self.thread.kill()
            self.thread = None
        var.playlist = []
        self.is_playing = False

    def set_comment(self):
        self.mumble.users.myself.comment(var.config.get('bot', 'comment'))

    def send_msg(self, msg, text=None):
        # text if the object message, contain information if direct message or channel message
        if not text or not text.session:
            own_channel = self.mumble.channels[self.mumble.users.myself['channel_id']]
            own_channel.send_text_message(msg)
        else:
            self.mumble.users[text.actor].send_text_message(msg)


def start_web_interface(addr, port):
    logging.info('Starting web interface on {}:{}'.format(addr, port))
    interface.web.run(port=port, host=addr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Bot for playing music on Mumble')

    # General arguments
    parser.add_argument("--config", dest='config', type=str, default='configuration.ini',
                        help='Load configuration from this file. Default: configuration.ini')
    parser.add_argument("--db", dest='db', type=str,
                        default='db.ini', help='database file. Default db.ini')

    parser.add_argument("-q", "--quiet", dest="quiet",
                        action="store_true", help="Only Error logs")
    parser.add_argument("-v", "--verbose", dest="verbose",
                        action="store_true", help="Show debug log")

    # Mumble arguments
    parser.add_argument("-s", "--server", dest="host",
                        type=str, help="Hostname of the Mumble server")
    parser.add_argument("-u", "--user", dest="user",
                        type=str, help="Username for the bot")
    parser.add_argument("-P", "--password", dest="password",
                        type=str, help="Server password, if required")
    parser.add_argument("-T", "--tokens", dest="tokens",
                        type=str, help="Server tokens, if required")
    parser.add_argument("-p", "--port", dest="port",
                        type=int, help="Port for the Mumble server")
    parser.add_argument("-c", "--channel", dest="channel",
                        type=str, help="Default channel for the bot")
    parser.add_argument("-C", "--cert", dest="certificate",
                        type=str, default=None, help="Certificate file")

    args = parser.parse_args()
    var.dbfile = args.db
    config = configparser.ConfigParser(interpolation=None, allow_no_value=True)
    parsed_configs = config.read(
        ['configuration.default.ini', args.config], encoding='latin-1')

    db = configparser.ConfigParser(
        interpolation=None, allow_no_value=True, delimiters='²')
    db.read(var.dbfile, encoding='latin-1')

    if 'url_ban' not in db.sections():
        db.add_section('url_ban')
    if 'bot' not in db.sections():
        db.add_section('bot')
    if 'user_ban' not in db.sections():
        db.add_section('user_ban')

    if len(parsed_configs) == 0:
        logging.error('Could not read configuration from file \"{}\"'.format(
            args.config), file=sys.stderr)
        sys.exit()

    var.config = config
    var.db = db
    botamusique = MumbleBot(args)
