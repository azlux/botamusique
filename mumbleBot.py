#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import time
import sys
import math
import re
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
import command
import media.url
import media.file
import media.playlist
import media.radio
import media.system
from librb import radiobrowser
from media.playlist import PlayList

"""
FORMAT OF A MUSIC INTO THE PLAYLIST
type : url
    url
    title
    path
    duration
    artist
    thumbnail
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
    artist
    duration
    thumbnail
    user
"""

version = 5


class MumbleBot:
    def __init__(self, args):
        signal.signal(signal.SIGINT, self.ctrl_caught)
        self.cmd_handle = {}
        self.volume_set = var.config.getfloat('bot', 'volume')
        if db.has_option('bot', 'volume'):
            self.volume_set = var.db.getfloat('bot', 'volume')

        self.volume = self.volume_set

        self.channel = args.channel

        if args.verbose:
            root.setLevel(logging.DEBUG)
            logging.debug("Starting in DEBUG loglevel")
        elif args.quiet:
            root.setLevel(logging.ERROR)
            logging.error("Starting in ERROR loglevel")

        var.playlist = PlayList()

        var.user = args.user
        var.music_folder = var.config.get('bot', 'music_folder')
        var.is_proxified = var.config.getboolean(
            "webinterface", "is_web_proxified")
        self.exit = False
        self.nb_exit = 0
        self.thread = None
        self.is_playing = False
        self.is_pause = False
        self.playhead = -1
        self.song_start_at = -1

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
        self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, self.message_received)

        self.mumble.set_codec_profile("audio")
        self.mumble.start()  # start the mumble thread
        self.mumble.is_ready()  # wait for the connection
        self.set_comment()
        self.mumble.users.myself.unmute()  # by sure the user is not muted
        if self.channel:
            self.mumble.channels.find_by_name(self.channel).move_in()
        self.mumble.set_bandwidth(200000)

        self.is_ducking = False
        self.on_ducking = False
        self.ducking_release = time.time()
        if var.config.getboolean("bot", "ducking"):
            self.is_ducking = True
            self.ducking_volume = var.config.getfloat("bot", "ducking_volume", fallback=0.05)
            self.ducking_threshold = var.config.getfloat("bot", "ducking_threshold", fallback=5000)
            self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, self.ducking_sound_received)
            self.mumble.set_receive_sound(True)

    # Set the CTRL+C shortcut
    def ctrl_caught(self, signal, frame):
        logging.info(
            "\nSIGINT caught, quitting, {} more to kill".format(2 - self.nb_exit))
        self.exit = True
        self.clear()
        if self.nb_exit > 1:
            logging.info("Forced Quit")
            sys.exit(0)
        self.nb_exit += 1

    def register_command(self, cmd, handle):
        cmds = cmd.split(",")
        for command in cmds:
            command = command.strip()
            if command:
                self.cmd_handle[command] = handle
                logging.debug("bot: command added: " + command)

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

            logging.info('bot: received command ' + command + ' - ' + parameter + ' by ' + user)

            # Anti stupid guy function
            if not self.is_admin(user) and not var.config.getboolean('bot', 'allow_other_channel_message') and self.mumble.users[text.actor]['channel_id'] != self.mumble.users.myself['channel_id']:
                self.mumble.users[text.actor].send_text_message(
                    var.config.get('strings', 'not_in_my_channel'))
                return

            if not self.is_admin(user) and not var.config.getboolean('bot', 'allow_private_message') and text.session:
                self.mumble.users[text.actor].send_text_message(
                    var.config.get('strings', 'pm_not_allowed'))
                return

            for i in var.db.items("user_ban"):
                if user.lower() == i[0]:
                    self.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'user_ban'))
                    return

            if parameter:
                for i in var.db.items("url_ban"):
                    if self.get_url_from_input(parameter.lower()) == i[0]:
                        self.mumble.users[text.actor].send_text_message(
                            var.config.get('strings', 'url_ban'))
                        return


            if command in self.cmd_handle:
                self.cmd_handle[command](self, user, text, command, parameter)
            else:
                # try partial match
                cmds = self.cmd_handle.keys()
                matches = []
                for cmd in cmds:
                    if cmd.startswith(command):
                        matches.append(cmd)

                if len(matches) == 1:
                    logging.info("bot: {:s} matches {:s}".format(command, matches[0]))
                    self.cmd_handle[matches[0]](self, user, text, command, parameter)
                elif len(matches) > 1:
                    self.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'which_command') % "<br>".join(matches))
                else:
                    self.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'bad_command') % command)


    @staticmethod
    def is_admin(user):
        list_admin = var.config.get('bot', 'admin').strip().split(';')
        if user in list_admin:
            return True
        else:
            return False

    @staticmethod
    def next():
        logging.debug("bot: Next into the queue")
        return var.playlist.next()

    def launch_music(self, index=-1):
        uri = ""
        music = None
        if var.playlist.length() == 0:
            return

        if index == -1:
            music = var.playlist.current_item()
        else:
            music = var.playlist.jump(index)

        logging.info("bot: play music " + str(music['path'] if 'path' in music else music['url']))
        if music["type"] == "url":
            # Delete older music is the tmp folder is too big
            media.system.clear_tmp_folder(var.config.get(
                'bot', 'tmp_folder'), var.config.getint('bot', 'tmp_folder_max_size'))

            # Check if the music is ready to be played
            if music["ready"] == "downloading":
                return
            elif music["ready"] != "yes":
                logging.info("bot: current music isn't ready, downloading...")
                music = self.download_music()
                if not music:
                    logging.info("bot: removing music from the playlist: %s" % music['url'])
                    var.playlist.remove()
                    return
            uri = music['path']

        elif music["type"] == "file":
            uri = var.config.get('bot', 'music_folder') + \
                var.playlist.current_item()["path"]

        elif music["type"] == "radio":
            uri = music["url"]
            if 'title' not in music:
                logging.info("bot: fetching radio server description")
                title = media.radio.get_radio_server_description(uri)
                music["title"] = title

        if var.config.getboolean('bot', 'announce_current_music'):
            self.send_msg(var.config.get('strings', 'now_playing') + util.format_current_playing())

        if var.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"

        command = ("ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i',
                   uri, '-ac', '1', '-f', 's16le', '-ar', '48000', '-')
        logging.info("bot: execute ffmpeg command: " + " ".join(command))
        # The ffmpeg process is a thread
        self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
        self.is_playing = True
        self.is_pause = False
        self.song_start_at = -1
        self.playhead = 0
        self.last_volume_cycle_time = time.time()

    def download_music(self, index=-1):
        if index == -1:
            index = var.playlist.current_index
        music = var.playlist.playlist[index]

        if music['type'] != 'url':
            # then no need to download
            return music

        url = music['url']

        if music['ready'] == "validation":
            logging.info("bot: verifying the duration of url (%s) %s " % (music['title'], url))

            music = media.url.get_url_info(music)
            if music:
                if music['duration'] > var.config.getint('bot', 'max_track_duration'):
                    # Check the length, useful in case of playlist, it wasn't checked before)
                    logging.info(
                        "the music " + music["url"] + " has a duration of " + music['duration'] + "s -- too long")
                    self.send_msg(var.config.get('strings', 'too_long'))
                    return False
                else:
                    music['ready'] = "no"
            else:
                logging.error("bot: error while fetching info from the URL")
                self.send_msg(var.config.get('strings', 'unable_download'))
                return False

        if music['ready'] == "no":
            # download the music
            music['ready'] = "downloading"

            url = music['url']
            url_hash = hashlib.md5(url.encode()).hexdigest()

            logging.info("bot: downloading url (%s) %s " % (music['title'], url))

            path = var.config.get('bot', 'tmp_folder') + url_hash + ".%(ext)s"
            mp3 = path.replace(".%(ext)s", ".mp3")
            music['path'] = mp3

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
                'strings', "download_in_progress") % music['title'])

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                for i in range(2):  # Always try 2 times
                    try:
                        ydl.extract_info(url)
                        if 'ready' in music and music['ready'] == "downloading":
                            music['ready'] = "yes"
                            music = util.get_music_tag_info(music)
                    except youtube_dl.utils.DownloadError:
                        pass
                    else:
                        break
            var.playlist.playlist[index] = music
            return music

    def resume(self):
        music = var.playlist.current_item()

        if var.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"

        if music["type"] != "radio":
            logging.info("bot: resume music at %.2f seconds" % self.playhead)

            uri = ""
            if music["type"] == "url":
                uri = music['path']

            elif music["type"] == "file":
                uri = var.config.get('bot', 'music_folder') + \
                      var.playlist.current_item()["path"]

            command = ("ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-ss', "%f" % self.playhead, '-i',
                       uri, '-ac', '1', '-f', 's16le', '-ar', '48000', '-')

        else:
            logging.info("bot: resume radio")
            uri = music["url"]
            command = ("ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i',
                       uri, '-ac', '1', '-f', 's16le', '-ar', '48000', '-')

        if var.config.getboolean('bot', 'announce_current_music'):
            self.send_msg(var.config.get('strings', 'now_playing') + util.format_current_playing())

        logging.info("bot: execute ffmpeg command: " + " ".join(command))
        # The ffmpeg process is a thread
        self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
        self.is_playing = True
        self.is_pause = False
        self.song_start_at = -1
        self.last_volume_cycle_time = time.time()


    def async_download_next(self):
        # Function start if the next music isn't ready
        # Do nothing in case the next music is already downloaded
        logging.info("bot: Async download next asked ")
        if len(var.playlist.playlist) > 1 and var.playlist.next_item()['type'] == 'url' \
                and var.playlist.next_item()['ready'] in ["no", "validation"]:
            th = threading.Thread(
                target=self.download_music, kwargs={'index': var.playlist.next_index()})
        else:
            return
        logging.info("bot: Start downloading next in thread")
        th.daemon = True
        th.start()

    def volume_cycle(self):
        delta = time.time() - self.last_volume_cycle_time

        if self.on_ducking and self.ducking_release < time.time():
            self._clear_pymumble_soundqueue()
            self.on_ducking = False

        if delta > 0.001:
            if self.is_ducking and self.on_ducking:
                self.volume = (self.volume - self.ducking_volume) * math.exp(- delta / 0.2) + self.ducking_volume
            else:
                self.volume = self.volume_set - (self.volume_set - self.volume) * math.exp(- delta / 0.5)

        self.last_volume_cycle_time = time.time()

    def ducking_sound_received(self, user, sound):
        if audioop.rms(sound.pcm, 2) > self.ducking_threshold:
            if self.on_ducking is False:
                logging.debug("bot: ducking triggered")
                self.on_ducking = True
            self.ducking_release = time.time() + 1 # ducking release after 1s


    # Main loop of the Bot
    def loop(self):
        raw_music = ""
        while not self.exit and self.mumble.is_alive():

            while self.mumble.sound_output.get_buffer_size() > 0.5 and not self.exit:
                # If the buffer isn't empty, I cannot send new music part, so I wait
                time.sleep(0.01)
            if self.thread:
                # I get raw from ffmpeg thread
                # move playhead forward
                if self.song_start_at == -1:
                    self.song_start_at = time.time() - self.playhead
                self.playhead = time.time() - self.song_start_at

                raw_music = self.thread.stdout.read(480)
                if raw_music:
                    # Adjust the volume and send it to mumble
                    self.volume_cycle()
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
                if not self.is_pause and len(var.playlist.playlist) > 0:
                    if var.playlist.current_item()['type'] in ['radio', 'file'] \
                            or (var.playlist.current_item()['type'] == 'url' and var.playlist.current_item()['ready'] not in ['downloading']):
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

    def clear(self):
        # Kill the ffmpeg thread and empty the playlist
        if self.thread:
            self.thread.kill()
            self.thread = None
        var.playlist.clear()
        self.is_playing = False
        logging.info("bot: music stopped. playlist trashed.")

    def stop(self):
        # Kill the ffmpeg thread
        if self.thread:
            self.thread.kill()
            self.thread = None
        self.is_playing = False
        self.is_pause = True
        self.song_start_at = -1
        self.playhead = 0
        self.next()
        logging.info("bot: music stopped.")

    def pause(self):
        # Kill the ffmpeg thread
        if self.thread:
            self.thread.kill()
            self.thread = None
        self.is_playing = False
        self.is_pause = True
        self.song_start_at = -1
        logging.info("bot: music paused at %.2f seconds." % self.playhead)

    def set_comment(self):
        self.mumble.users.myself.comment(var.config.get('bot', 'comment'))

    def send_msg(self, msg, text=None):
        msg = msg.encode('utf-8', 'ignore').decode('utf-8')
        # text if the object message, contain information if direct message or channel message
        if not text or not text.session:
            own_channel = self.mumble.channels[self.mumble.users.myself['channel_id']]
            own_channel.send_text_message(msg)
        else:
            self.mumble.users[text.actor].send_text_message(msg)

    # TODO: this is a temporary workaround for issue #44 of pymumble.
    def _clear_pymumble_soundqueue(self):
        for id, user in self.mumble.users.items():
            user.sound.lock.acquire()
            user.sound.queue.clear()
            user.sound.lock.release()
        logging.debug("bot: pymumble soundqueue cleared.")



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
        ['configuration.default.ini', args.config], encoding='utf-8')



    db = configparser.ConfigParser(
        interpolation=None, allow_no_value=True, delimiters='²')
    db.read(var.dbfile, encoding='utf-8')

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

    # Setup logger
    root = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    root.setLevel(logging.INFO)

    logfile = var.config.get('bot', 'logfile')

    handler = None
    if logfile:
        handler = logging.FileHandler(logfile)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Start the bot, loop.
    var.botamusique = MumbleBot(args)
    command.register_all_commands(var.botamusique)
    var.botamusique.loop()
