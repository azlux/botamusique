#!/usr/bin/python3
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
        var.playlist = []
        var.user = args.user
        var.music_folder = self.config.get('bot', 'music_folder')
        var.is_proxified = self.config.getboolean("bot", "is_proxified")
        self.exit = False
        self.nb_exit = 0
        self.thread = None

        interface.init_proxy()

        t = threading.Thread(target=start_web_interface)
        t.daemon = True
        t.start()

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
                path = self.config.get('bot', 'music_folder') + parameter
                if "/" in parameter:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'bad_file'))
                elif os.path.isfile(path):
                    self.launch_play_file(path)
                else:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'bad_file'))

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
                    self.send_msg_channel(var.current_music)
                else:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'not_playing'))

            elif command == self.config.get('command', 'list'):
                folder_path = self.config.get('bot', 'music_folder')
                files = [f for f in listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                if files:
                    self.mumble.users[text.actor].send_message('<br>'.join(files))
                else:
                    self.mumble.users[text.actor].send_message(self.config.get('strings', 'no_file'))
            else:
                self.mumble.users[text.actor].send_message(self.config.get('strings', 'bad_command'))

    def is_admin(self, user):
        username = self.mumble.users[user]['name']
        list_admin = self.config.get('bot', 'admin').split(';')
        if username in list_admin:
            return True
        else:
            return False

    def launch_play_file(self, path=None):
        if not path:
            path = self.config.get('bot', 'music_folder') + var.current_music
        if self.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"
        command = ["ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i', path, '-ac', '1', '-f', 's16le', '-ar', '48000', '-']
        self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
        var.current_music = path

    def loop(self):
        while not self.exit:

            while self.mumble.sound_output.get_buffer_size() > 0.5:
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
                self.launch_play_file()

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


def start_web_interface():
    interface.web.run(port=8181, host="0.0.0.0")


if __name__ == '__main__':
    botamusique = MumbleBot()
