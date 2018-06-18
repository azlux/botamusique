#!/usr/bin/env python3
from __future__ import unicode_literals

import re
import threading
import time
import sys
import signal
import configparser
import audioop
import subprocess as sp
import argparse
import os.path
from os import listdir
import pymumble.pymumble_py3 as pymumble
import interface
import variables as var
import hashlib
import youtube_dl
import media
import logging
import util
import base64
from PIL import Image
from io import BytesIO


class MumbleBot:
    def __init__(self, args):
        signal.signal(signal.SIGINT, self.ctrl_caught)

        self.volume = var.config.getfloat('bot', 'volume')
        self.channel = args.channel
        var.current_music = None

        FORMAT = '%(asctime)s: %(message)s'
        if args.quiet:
            logging.basicConfig(format=FORMAT, level=logging.ERROR, datefmt='%Y-%m-%d %H:%M:%S')
        else:
            logging.basicConfig(format=FORMAT, level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

        ######
        ## Format of the Playlist :
        ## [("<type>","<path>")]
        ## [("<radio>","<luna>"), ("<youtube>","<url>")]
        ## types : file, radio, url
        ######

        ######
        ## Format of the current_music variable
        # len(var.current_music) = 4
        # var.current_music[0] = <Type>
        # var.current_music[1] = <url> if url of radio
        # var.current_music[2] = <title>
        # var.current_music[3] = <path> if url or file

        var.playlist = []

        var.user = args.user
        var.music_folder = var.config.get('bot', 'music_folder')
        var.is_proxified = var.config.getboolean("webinterface", "is_web_proxified")
        self.exit = False
        self.nb_exit = 0
        self.thread = None

        if var.config.getboolean("webinterface", "enabled"):
            wi_addr = var.config.get("webinterface", "listening_addr")
            wi_port = var.config.getint("webinterface", "listening_port")
            interface.init_proxy()
            tt = threading.Thread(target=start_web_interface, args=(wi_addr, wi_port))
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

        if args.user:
            user = args.user
        else:
            user = var.config.get("bot", "user")

        self.mumble = pymumble.Mumble(host, user=user, port=port, password=password,
                                      debug=var.config.getboolean('debug', 'mumbleConnection'))
        self.mumble.callbacks.set_callback("text_received", self.message_received)

        self.mumble.set_codec_profile("audio")
        self.mumble.start()  # start the mumble thread
        self.mumble.is_ready()  # wait for the connection
        self.set_comment()
        self.mumble.users.myself.unmute()  # by sure the user is not muted
        if self.channel:
            self.mumble.channels.find_by_name(self.channel).move_in()
        self.mumble.set_bandwidth(200000)

        self.loop()

    def ctrl_caught(self, signal, frame):
        logging.info("\ndeconnection asked")
        self.exit = True
        self.stop()
        if self.nb_exit > 1:
            logging.info("Forced Quit")
            sys.exit(0)
        self.nb_exit += 1

    def message_received(self, text):
        message = text.message.strip()
        if message[0] == '!':
            message = message[1:].split(' ', 1)
            if len(message) > 0:
                command = message[0]
                parameter = ''
                if len(message) > 1:
                    parameter = message[1]
            else:
                return

            logging.info(command + ' - ' + parameter + ' by ' + self.mumble.users[text.actor]['name'])

            if command == var.config.get('command', 'play_file') and parameter:
                music_folder = var.config.get('bot', 'music_folder')
                # sanitize "../" and so on
                path = os.path.abspath(os.path.join(music_folder, parameter))
                if path.startswith(music_folder):
                    if os.path.isfile(path):
                        filename = path.replace(music_folder, '')
                        var.playlist.append(["file", filename])
                    else:
                        # try to do a partial match
                        matches = [file for file in util.get_recursive_filelist_sorted(music_folder) if parameter.lower() in file.lower()]
                        if len(matches) == 0:
                            self.mumble.users[text.actor].send_message(var.config.get('strings', 'no_file'))
                        elif len(matches) == 1:
                            var.playlist.append(["file", matches[0]])
                        else:
                            msg = var.config.get('strings', 'multiple_matches') + '<br />'
                            msg += '<br />'.join(matches)
                            self.mumble.users[text.actor].send_message(msg)
                else:
                    self.mumble.users[text.actor].send_message(var.config.get('strings', 'bad_file'))

            elif command == var.config.get('command', 'play_url') and parameter:
                var.playlist.append(["url", parameter])

            elif command == var.config.get('command', 'play_radio') and parameter:
                if var.config.has_option('radio', parameter):
                    parameter = var.config.get('radio', parameter)
                var.playlist.append(["radio", parameter])

            elif command == var.config.get('command', 'help'):
                self.send_msg_channel(var.config.get('strings', 'help'))

            elif command == var.config.get('command', 'stop'):
                self.stop()

            elif command == var.config.get('command', 'kill'):
                if self.is_admin(text.actor):
                    self.stop()
                    self.exit = True
                else:
                    self.mumble.users[text.actor].send_message(var.config.get('strings', 'not_admin'))

            elif command == var.config.get('command', 'stop_and_getout'):
                self.stop()
                if self.channel:
                    self.mumble.channels.find_by_name(self.channel).move_in()

            elif command == var.config.get('command', 'joinme'):
                self.mumble.users.myself.move_in(self.mumble.users[text.actor]['channel_id'])

            elif command == var.config.get('command', 'volume'):
                if parameter is not None and parameter.isdigit() and 0 <= int(parameter) <= 100:
                    self.volume = float(float(parameter) / 100)
                    self.send_msg_channel(var.config.get('strings', 'change_volume') % (
                        int(self.volume * 100), self.mumble.users[text.actor]['name']))
                else:
                    self.send_msg_channel(var.config.get('strings', 'current_volume') % int(self.volume * 100))

            elif command == var.config.get('command', 'current_music'):
                if var.current_music:
                    source = var.current_music[0]
                    if source == "radio":
                        reply = "[radio] {title} sur {url}".format(
                            title=media.get_radio_title(var.current_music[1]),
                            url=var.current_music[2]
                        )
                    elif source == "url":
                        reply = "[url] {title} (<a href=\"{url}\">{url}</a>)".format(
                            title=var.current_music[2],
                            url=var.current_music[1]
                        )
                    elif source == "file":
                        reply = "[file] {title}".format(title=var.current_music[2])
                    else:
                        reply = "(?)[{}] {} {}".format(
                            var.current_music[0],
                            var.current_music[1],
                            var.current_music[2],
                        )
                else:
                    reply = var.config.get('strings', 'not_playing')

                self.mumble.users[text.actor].send_message(reply)

            elif command == var.config.get('command', 'next'):
                if var.playlist:
                    var.current_music = [var.playlist[0][0], var.playlist[0][1], None, None]
                    var.playlist.pop(0)
                    self.launch_next()
                else:
                    self.mumble.users[text.actor].send_message(var.config.get('strings', 'queue_empty'))
                    self.stop()

            elif command == var.config.get('command', 'list'):
                folder_path = var.config.get('bot', 'music_folder')

                files = util.get_recursive_filelist_sorted(folder_path)
                if files:
                    self.mumble.users[text.actor].send_message('<br>'.join(files))
                else:
                    self.mumble.users[text.actor].send_message(var.config.get('strings', 'no_file'))

            elif command == var.config.get('command', 'queue'):
                if len(var.playlist) == 0:
                    msg = var.config.get('strings', 'queue_empty')
                else:
                    msg = var.config.get('strings', 'queue_contents') + '<br />'
                    for (type, path) in var.playlist:
                        msg += '({}) {}<br />'.format(type, path)

                self.send_msg_channel(msg)
            else:
                self.mumble.users[text.actor].send_message(var.config.get('strings', 'bad_command'))

    def launch_play_file(self, path):
        self.stop()
        if var.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"
        command = ["ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i', path, '-ac', '1', '-f', 's16le', '-ar', '48000', '-']
        self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
        self.playing = True

    def is_admin(self, user):
        username = self.mumble.users[user]['name']
        list_admin = var.config.get('bot', 'admin').split(';')
        if username in list_admin:
            return True
        else:
            return False

    def launch_next(self):
        path = ""
        title = ""
        if var.current_music[0] == "url":
            url = media.get_url(var.current_music[1])
            if not url:
                return
            media.clear_tmp_folder(var.config.get('bot', 'tmp_folder'), var.config.getint('bot', 'tmp_folder_max_size'))
            path, title = self.download_music(url)
            var.current_music[1] = url

            path_thumbnail = var.config.get('bot', 'tmp_folder') + hashlib.md5(url.encode()).hexdigest() + '.jpg'
            thumbnail_html = ""
            if os.path.isfile(path_thumbnail):
                im = Image.open(path_thumbnail)
                im.thumbnail((100, 100), Image.ANTIALIAS)
                buffer = BytesIO()
                im.save(buffer, format="JPEG")
                thumbnail_base64 = base64.b64encode(buffer.getvalue())
                thumbnail_html = '<img - src="data:image/PNG;base64,' + thumbnail_base64.decode() + '"/>'

            logging.debug(thumbnail_html)
            self.send_msg_channel(var.config.get('strings', 'now_playing') % (title, thumbnail_html))

        elif var.current_music[0] == "file":
            path = var.config.get('bot', 'music_folder') + var.current_music[1]
            title = var.current_music[1]

        elif var.current_music[0] == "radio":
            url = media.get_url(var.current_music[1])
            if not url:
                return
            var.current_music[1] = url
            path = url
            title = media.get_radio_server_description(url)

        if var.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"

        command = ["ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i', path, '-ac', '1', '-f', 's16le', '-ar', '48000', '-']
        self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
        var.current_music[2] = title
        var.current_music[3] = path

    def download_music(self, url):
        url_hash = hashlib.md5(url.encode()).hexdigest()
        path = var.config.get('bot', 'tmp_folder') + url_hash + ".mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': path,
            'noplaylist': True,
            'writethumbnail': True,
            'updatetime': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }
        video_title = ""
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            for i in range(2):
                try:
                    info_dict = ydl.extract_info(url)
                    video_title = info_dict['title']
                except youtube_dl.utils.DownloadError:
                    pass
                else:
                    break
        return path, video_title

    def loop(self):
        raw_music = ""
        while not self.exit and self.mumble.isAlive():

            while self.mumble.sound_output.get_buffer_size() > 0.5 and not self.exit:
                time.sleep(0.01)
            if self.thread:
                raw_music = self.thread.stdout.read(480)
                if raw_music:
                    self.mumble.sound_output.add_sound(audioop.mul(raw_music, 2, self.volume))
                else:
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

            if self.thread is None or not raw_music:
                if len(var.playlist) != 0:
                    var.current_music = [var.playlist[0][0], var.playlist[0][1], None, None]
                    var.playlist.pop(0)
                    self.launch_next()
                else:
                    var.current_music = None

        while self.mumble.sound_output.get_buffer_size() > 0:
            time.sleep(0.01)
        time.sleep(0.5)

    def stop(self):
        if self.thread:
            var.current_music = None
            self.thread.kill()
            self.thread = None
            var.playlist = []

    def set_comment(self):
        self.mumble.users.myself.comment(var.config.get('bot', 'comment'))

    def send_msg_channel(self, msg, channel=None):
        if not channel:
            channel = self.mumble.channels[self.mumble.users.myself['channel_id']]
        channel.send_text_message(msg)


def start_web_interface(addr, port):
    print('Starting web interface on {}:{}'.format(addr, port))
    interface.web.run(port=port, host=addr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bot for playing music on Mumble')

    # General arguments
    parser.add_argument("--config", dest='config', type=str, default='configuration.ini', help='Load configuration from this file. Default: configuration.ini')
    parser.add_argument("-q", "--quiet", dest="quiet", action="store_true", help="Only Error logs")

    # Mumble arguments
    parser.add_argument("-s", "--server", dest="host", type=str, help="The server's hostame of a mumble server")
    parser.add_argument("-u", "--user", dest="user", type=str, help="Username you wish, Default=abot")
    parser.add_argument("-P", "--password", dest="password", type=str, help="Password if server requires one")
    parser.add_argument("-p", "--port", dest="port", type=int, help="Port for the mumble server")
    parser.add_argument("-c", "--channel", dest="channel", type=str, help="Default chanel for the bot")

    args = parser.parse_args()
    config = configparser.ConfigParser(interpolation=None, allow_no_value=True)
    parsed_configs = config.read(['configuration.default.ini', args.config], encoding='latin-1')

    if len(parsed_configs) == 0:
        print('Could not read configuration from file \"{}\"'.format(args.config), file=sys.stderr)
        sys.exit()

    var.config = config
    botamusique = MumbleBot(args)
