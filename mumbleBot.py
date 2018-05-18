#!/usr/bin/python3
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


class MumbleBot:
    def __init__(self):
        signal.signal(signal.SIGINT, self.ctrl_caught)

        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read("configuration.ini", encoding='latin-1')

        parser = argparse.ArgumentParser(description='Bot for playing radio stream on Mumble')
        parser.add_argument("-s", "--server", dest="host", type=str, required=True, help="The server's hostame of a mumble server")
        parser.add_argument("-u", "--user", dest="user", type=str, required=True, help="Username you wish, Default=abot")
        parser.add_argument("-P", "--password", dest="password", type=str, default="", help="Password if server requires one")
        parser.add_argument("-p", "--port", dest="port", type=int, default=64738, help="Port for the mumble server")
        parser.add_argument("-c", "--channel", dest="channel", type=str, default="", help="Default chanel for the bot")

        args = parser.parse_args()
        self.volume = self.config.getfloat('bot', 'volume')

        self.channel = args.channel
        var.current_music = None

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
        var.music_folder = self.config.get('bot', 'music_folder')
        var.is_proxified = self.config.getboolean("bot", "is_proxified")
        self.exit = False
        self.nb_exit = 0
        self.thread = None

        interface.init_proxy()

        # t = threading.Thread(target=start_web_interface)
        # t.daemon = True
        # t.start()

        self.mumble = pymumble.Mumble(args.host, user=args.user, port=args.port, password=args.password,
                                      debug=self.config.getboolean('debug', 'mumbleConnection'))
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
        print("\ndeconnection asked")
        self.exit = True
        self.stop()
        if self.nb_exit > 1:
            print("Forced Quit")
            sys.exit(0)
        self.nb_exit += 1

    def message_received(self, text):
        message = text.message
        if message[0] == '!':
            message = message[1:].split(' ', 1)
            if len(message) > 0:
                command = message[0]
                parameter = ''
                if len(message) > 1:
                    parameter = message[1]
            else:
                return

            print(command + ' - ' + parameter + ' by ' + self.mumble.users[text.actor]['name'])

            if command == self.config.get('command', 'play_file') and parameter:
                music_folder = self.config.get('bot', 'music_folder')
                # sanitize "../" and so on
                path = os.path.abspath(os.path.join(music_folder, parameter))
                if path.startswith(music_folder):
                    if os.path.isfile(path):
                        self.launch_play_file(path)
                    else:
                        # try to do a partial match
                        matches = [file for file in self.__get_recursive_filelist_sorted(music_folder) if parameter in file]
                        if len(matches) == 1:
                            self.launch_play_file(music_folder + matches[0])
                        else:
                            msg = self.config.get('strings', 'multiple_matches') + '<br />'
                            msg += '<br />'.join(matches)
                            self.mumble.users[text.actor].send_message(msg)
                else:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'bad_file'))

            elif command == self.config.get('command', 'play_url') and parameter:
                var.playlist.append(["url", parameter])

            elif command == self.config.get('command', 'play_radio') and parameter:
                var.playlist.append(["radio", parameter])

            elif command == self.config.get('command', 'help'):
                self.send_msg_channel(self.config.get('strings', 'help'))

            elif command == self.config.get('command', 'stop'):
                self.stop()

            elif command == self.config.get('command', 'kill'):
                if self.is_admin(text.actor):
                    self.stop()
                    self.exit = True
                else:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'not_admin'))

            elif command == self.config.get('command', 'stop_and_getout'):
                self.stop()
                if self.channel:
                    self.mumble.channels.find_by_name(self.channel).move_in()

            elif command == self.config.get('command', 'joinme'):
                self.mumble.users.myself.move_in(self.mumble.users[text.actor]['channel_id'])

            elif command == self.config.get('command', 'volume'):
                if parameter is not None and parameter.isdigit() and 0 <= int(parameter) <= 100:
                    self.volume = float(float(parameter) / 100)
                    self.send_msg_channel(self.config.get('strings', 'change_volume') % (
                        int(self.volume * 100), self.mumble.users[text.actor]['name']))
                else:
                    self.send_msg_channel(self.config.get('strings', 'current_volume') % int(self.volume * 100))

            elif command == self.config.get('command', 'current_music'):
                if var.current_music is not None:
                    if var.current_music[0] == "radio":
                        self.send_msg_channel(media.get_radio_title(var.current_music[1]) + " sur " + var.current_music[2])
                    else:
                        self.send_msg_channel(var.current_music[2] + "<br />" + var.current_music[1])
                else:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'not_playing'))

            elif command == self.config.get('command', 'next'):
                var.current_music = var.playlist[0]
                var.playlist.pop(0)
                self.launch_next()
            elif command == self.config.get('command', 'list'):
                folder_path = self.config.get('bot', 'music_folder')

                files = self.__get_recursive_filelist_sorted(folder_path)
                if files :
                    self.mumble.users[text.actor].send_message('<br>'.join(files))
                else :
                     self.mumble.users[text.actor].send_message(self.config.get('strings', 'no_file'))
            else:
                self.mumble.users[text.actor].send_message(self.config.get('strings', 'bad_command'))

    def launch_play_file(self, path):
        self.stop()
        if self.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"
        command = ["ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i', path, '-ac', '1', '-f', 's16le', '-ar', '48000', '-']
        self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
        self.playing = True

    def is_admin(self, user):
        username = self.mumble.users[user]['name']
        list_admin = self.config.get('bot', 'admin').split(';')
        if username in list_admin:
            return True
        else:
            return False

    def launch_next(self):
        path = ""
        title = ""
        if var.current_music[0] == "url":
            regex = re.compile("<a href=\"(.*?)\"")
            m = regex.match(var.current_music[1])
            url = m.group(1)
            path, title = self.download_music(url)
            var.current_music[1] = url

        elif var.current_music[0] == "file":
            path = self.config.get('bot', 'music_folder') + var.current_music[1]
            title = var.current_music[1]

        elif var.current_music[0] == "radio":
            regex = re.compile("<a href=\"(.*?)\"")
            m = regex.match(var.current_music[1])
            url = m.group(1)
            var.current_music[1] = url
            path = url
            title = media.get_radio_server_description(url)

        if self.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"

        command = ["ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i', path, '-ac', '1', '-f', 's16le', '-ar', '48000', '-']
        self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
        var.current_music.append(title)
        var.current_music.append(path)

    def download_music(self, url):
        url_hash = hashlib.md5(url.encode()).hexdigest()
        path = self.config.get('bot', 'tmp_folder') + url_hash + ".mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': path,
            'noplaylist': True,
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
                    info_dict = ydl.extract_info(url, download=False)
                    video_title = info_dict['title']
                    ydl.download([url])
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

            if (self.thread is None or not raw_music) and len(var.playlist) != 0:
                var.current_music = var.playlist[0]
                var.playlist.pop(0)
                self.launch_next()

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
        self.mumble.users.myself.comment(self.config.get('bot', 'comment'))

    def send_msg_channel(self, msg, channel=None):
        if not channel:
            channel = self.mumble.channels[self.mumble.users.myself['channel_id']]
        channel.send_text_message(msg)

    def __get_recursive_filelist_sorted(self, path):
        filelist = []
        for root, dirs, files in os.walk(path):
            relroot = root.replace(path, '')
            if relroot in self.config.get('bot', 'ignored_folders'):
                continue
            if len(relroot):
                relroot += '/'
            for file in files:
                if file in self.config.get('bot', 'ignored_files'):
                    continue
                filelist.append(relroot + file)

        filelist.sort()
        return filelist


def start_web_interface():
    interface.web.run(port=8181, host="127.0.0.1")


if __name__ == '__main__':
    botamusique = MumbleBot()
