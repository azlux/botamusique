#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import time
import sys
import math
import signal
import configparser
import audioop
import subprocess as sp
import argparse
import os
import os.path
import pymumble_py3 as pymumble
import pymumble_py3.constants
import variables as var
import logging
import logging.handlers
import traceback
from packaging import version

import util
import command
import constants
from database import SettingsDatabase, MusicDatabase
import media.system
from media.item import ValidationFailedError, PreparationFailedError
from media.playlist import BasePlaylist
from media.cache import MusicCache


class MumbleBot:
    version = '6.3'

    def __init__(self, args):
        self.log = logging.getLogger("bot")
        self.log.info("bot: botamusique version %s, starting..." % self.version)
        signal.signal(signal.SIGINT, self.ctrl_caught)
        self.cmd_handle = {}
        self.volume_set = var.config.getfloat('bot', 'volume')
        if var.db.has_option('bot', 'volume'):
            self.volume_set = var.db.getfloat('bot', 'volume')

        self.volume = self.volume_set

        if args.channel:
            self.channel = args.channel
        else:
            self.channel = var.config.get("server", "channel", fallback=None)

        var.user = args.user
        var.music_folder = util.solve_filepath(var.config.get('bot', 'music_folder'))
        var.tmp_folder = util.solve_filepath(var.config.get('bot', 'tmp_folder'))
        var.is_proxified = var.config.getboolean(
            "webinterface", "is_web_proxified")
        self.exit = False
        self.nb_exit = 0
        self.thread = None
        self.thread_stderr = None
        self.is_pause = False
        self.pause_at_id = ""
        self.playhead = -1
        self.song_start_at = -1
        self.last_ffmpeg_err = ""
        self.read_pcm_size = 0
        # self.download_threads = []
        self.wait_for_ready = False  # flag for the loop are waiting for download to complete in the other thread

        if var.config.getboolean("webinterface", "enabled"):
            wi_addr = var.config.get("webinterface", "listening_addr")
            wi_port = var.config.getint("webinterface", "listening_port")
            tt = threading.Thread(
                target=start_web_interface, name="WebThread", args=(wi_addr, wi_port))
            tt.daemon = True
            self.log.info('Starting web interface on {}:{}'.format(wi_addr, wi_port))
            tt.start()

        if var.config.getboolean("bot", "auto_check_update"):
            th = threading.Thread(target=self.check_update, name="UpdateThread")
            th.daemon = True
            th.start()

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

        if args.channel:
            self.channel = args.channel
        else:
            self.channel = var.config.get("server", "channel")

        if args.certificate:
            certificate = args.certificate
        else:
            certificate = util.solve_filepath(var.config.get("server", "certificate"))

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

        if self.mumble.connected >= pymumble_py3.constants.PYMUMBLE_CONN_STATE_FAILED:
            exit()

        self.set_comment()
        self.mumble.users.myself.unmute()  # by sure the user is not muted
        self.join_channel()
        self.mumble.set_bandwidth(200000)

        self.is_ducking = False
        self.on_ducking = False
        self.ducking_release = time.time()

        if not var.db.has_option("bot", "ducking") and var.config.getboolean("bot", "ducking", fallback=False)\
                or var.config.getboolean("bot", "ducking"):
            self.is_ducking = True
            self.ducking_volume = var.config.getfloat("bot", "ducking_volume", fallback=0.05)
            self.ducking_volume = var.db.getfloat("bot", "ducking_volume", fallback=self.ducking_volume)
            self.ducking_threshold = var.config.getfloat("bot", "ducking_threshold", fallback=5000)
            self.ducking_threshold = var.db.getfloat("bot", "ducking_threshold", fallback=self.ducking_threshold)
            self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED,
                                               self.ducking_sound_received)
            self.mumble.set_receive_sound(True)

        if var.config.get("bot", "when_nobody_in_channel") not in ['pause', 'pause_resume', 'stop', 'nothing']:
            self.log.warn('Config "when_nobody_in_channel" is not on of "pause", "pause_resume", "stop" or "nothing", falling back to "nothing".')

        if var.config.get("bot", "when_nobody_in_channel", fallback='nothing') in ['pause', 'pause_resume', 'stop']:
            self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_USERREMOVED, self.users_changed)
            self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_USERUPDATED, self.users_changed)
        
        # Debug use
        self._loop_status = 'Idle'
        self._display_rms = False
        self._max_rms = 0

        self.redirect_ffmpeg_log = var.config.getboolean('debug', 'redirect_ffmpeg_log', fallback=True)

    # Set the CTRL+C shortcut
    def ctrl_caught(self, signal, frame):

        self.log.info(
            "\nSIGINT caught, quitting, {} more to kill".format(2 - self.nb_exit))
        self.exit = True
        self.pause()
        if self.nb_exit > 1:
            self.log.info("Forced Quit")
            sys.exit(0)
        self.nb_exit += 1

        if var.config.getboolean('bot', 'save_playlist', fallback=True) \
                and var.config.get("bot", "save_music_library", fallback=True):
            self.log.info("bot: save playlist into database")
            var.playlist.save()

    def check_update(self):
        self.log.debug("update: checking for updates...")
        new_version = util.new_release_version()
        if version.parse(new_version) > version.parse(self.version):
            self.log.info("update: new version %s found, current installed version %s." % (new_version, self.version))
            self.send_channel_msg(constants.strings('new_version_found'))
        else:
            self.log.debug("update: no new version found.")

    def register_command(self, cmd, handle, no_partial_match=False, access_outside_channel=False):
        cmds = cmd.split(",")
        for command in cmds:
            command = command.strip()
            if command:
                self.cmd_handle[command] = {'handle': handle,
                                            'partial_match': not no_partial_match,
                                            'access_outside_channel': access_outside_channel}
                self.log.debug("bot: command added: " + command)

    def set_comment(self):
        self.mumble.users.myself.comment(var.config.get('bot', 'comment'))

    def join_channel(self):
        if self.channel:
            if '/' in self.channel:
                self.mumble.channels.find_by_tree(self.channel.split('/')).move_in()
            else:
                self.mumble.channels.find_by_name(self.channel).move_in()

    # =======================
    #         Message
    # =======================

    # All text send to the chat is analysed by this function
    def message_received(self, text):
        message = text.message.strip()
        user = self.mumble.users[text.actor]['name']

        if var.config.getboolean('commands', 'split_username_at_space'):
            # in can you use https://github.com/Natenom/mumblemoderator-module-collection/tree/master/os-suffixes ,
            # you want to split the username
            user = user.split()[0]

        if message[0] in var.config.get('commands', 'command_symbol'):
            # remove the symbol from the message
            message = message[1:].split(' ', 1)

            # use the first word as a command, the others one as  parameters
            if len(message) > 0:
                command = message[0].lower()
                parameter = ''
                if len(message) > 1:
                    parameter = message[1].rstrip()
            else:
                return

            self.log.info('bot: received command ' + command + ' - ' + parameter + ' by ' + user)

            # Anti stupid guy function
            if not self.is_admin(user) and not var.config.getboolean('bot', 'allow_private_message') and text.session:
                self.mumble.users[text.actor].send_text_message(
                    constants.strings('pm_not_allowed'))
                return

            for i in var.db.items("user_ban"):
                if user.lower() == i[0]:
                    self.mumble.users[text.actor].send_text_message(
                        constants.strings('user_ban'))
                    return

            if not self.is_admin(user) and parameter:
                input_url = util.get_url_from_input(parameter)
                if input_url:
                    for i in var.db.items("url_ban"):
                        if input_url == i[0]:
                            self.mumble.users[text.actor].send_text_message(
                                constants.strings('url_ban'))
                            return

            command_exc = ""
            try:
                if command in self.cmd_handle:
                    command_exc = command

                    if not self.cmd_handle[command]['access_outside_channel'] \
                            and not self.is_admin(user) \
                            and not var.config.getboolean('bot', 'allow_other_channel_message') \
                            and self.mumble.users[text.actor]['channel_id'] != self.mumble.users.myself['channel_id']:
                        self.mumble.users[text.actor].send_text_message(
                            constants.strings('not_in_my_channel'))
                        return

                    self.cmd_handle[command]['handle'](self, user, text, command, parameter)
                else:
                    # try partial match
                    cmds = self.cmd_handle.keys()
                    matches = []
                    for cmd in cmds:
                        if cmd.startswith(command) and self.cmd_handle[cmd]['partial_match']:
                            matches.append(cmd)

                    if len(matches) == 1:
                        self.log.info("bot: {:s} matches {:s}".format(command, matches[0]))
                        command_exc = matches[0]

                        if not self.cmd_handle[command_exc]['access_outside_channel'] \
                                and not self.is_admin(user) \
                                and not var.config.getboolean('bot', 'allow_other_channel_message') \
                                and self.mumble.users[text.actor]['channel_id'] != self.mumble.users.myself[
                                'channel_id']:
                            self.mumble.users[text.actor].send_text_message(
                                constants.strings('not_in_my_channel'))
                            return

                        self.cmd_handle[command_exc]['handle'](self, user, text, command_exc, parameter)
                    elif len(matches) > 1:
                        self.mumble.users[text.actor].send_text_message(
                            constants.strings('which_command', commands="<br>".join(matches)))
                    else:
                        self.mumble.users[text.actor].send_text_message(
                            constants.strings('bad_command', command=command))
            except:
                error_traceback = traceback.format_exc()
                error = error_traceback.rstrip().split("\n")[-1]
                self.log.error("bot: command %s failed with error: %s\n" % (command_exc, error_traceback))
                self.send_msg(constants.strings('error_executing_command', command=command_exc, error=error), text)

    def send_msg(self, msg, text):
        msg = msg.encode('utf-8', 'ignore').decode('utf-8')
        # text if the object message, contain information if direct message or channel message
        self.mumble.users[text.actor].send_text_message(msg)


    def send_channel_msg(self, msg):
        msg = msg.encode('utf-8', 'ignore').decode('utf-8')
        own_channel = self.mumble.channels[self.mumble.users.myself['channel_id']]
        own_channel.send_text_message(msg)

    def is_admin(self, user):
        list_admin = var.config.get('bot', 'admin').rstrip().split(';')
        if user in list_admin:
            return True
        else:
            return False

    # =======================
    #         Users changed
    # =======================

    def users_changed(self, user, message):
        own_channel = self.mumble.channels[self.mumble.users.myself['channel_id']]
        # only check if there is one more user currently in the channel
        # else when the music is paused and somebody joins, music would start playing again
        if len(own_channel.get_users()) == 2:
            if var.config.get("bot", "when_nobody_in_channel") == "pause_resume":
                self.resume()
            elif var.config.get("bot", "when_nobody_in_channel") == "pause":
                self.send_channel_msg(constants.strings("auto_paused"))

        elif len(own_channel.get_users()) == 1: 
            # if the bot is the only user left in the channel
            self.log.info('bot: Other users in the channel left. Stopping music now.')

            if var.config.get("bot", "when_nobody_in_channel") == "stop":
                self.clear()
            else:
                self.pause()

    # =======================
    #   Launch and Download
    # =======================

    def launch_music(self):
        if var.playlist.is_empty():
            return
        assert self.wait_for_ready is False

        music_wrapper = var.playlist.current_item()
        uri = music_wrapper.uri()

        self.log.info("bot: play music " + music_wrapper.format_debug_string())

        if var.config.getboolean('bot', 'announce_current_music'):
            self.send_channel_msg(music_wrapper.format_current_playing())

        if var.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"

        command = ("ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-i',
                   uri, '-ac', '1', '-f', 's16le', '-ar', '48000', '-')
        self.log.debug("bot: execute ffmpeg command: " + " ".join(command))

        # The ffmpeg process is a thread
        # prepare pipe for catching stderr of ffmpeg
        if self.redirect_ffmpeg_log:
            pipe_rd, pipe_wd = util.pipe_no_wait()  # Let the pipe work in non-blocking mode
            self.thread_stderr = os.fdopen(pipe_rd)
        else:
            pipe_rd, pipe_wd = None, None

        self.thread = sp.Popen(command, stdout=sp.PIPE, stderr=pipe_wd, bufsize=480)
        self.is_pause = False
        self.read_pcm_size = 0
        self.song_start_at = -1
        self.playhead = 0
        self.last_volume_cycle_time = time.time()

    def async_download_next(self):
        # Function start if the next music isn't ready
        # Do nothing in case the next music is already downloaded
        self.log.debug("bot: Async download next asked ")
        while var.playlist.next_item() and var.playlist.next_item().type in ['url', 'url_from_playlist']:
            # usually, all validation will be done when adding to the list.
            # however, for performance consideration, youtube playlist won't be validate when added.
            # the validation has to be done here.
            next = var.playlist.next_item()
            try:
                next.validate()
                if not next.is_ready():
                    self.async_download(next)

                break
            except ValidationFailedError as e:
                self.send_channel_msg(e.msg)
                var.playlist.remove_by_id(next.id)
                var.cache.free_and_delete(next.id)

    def async_download(self, item):
        th = threading.Thread(
            target=self._download, name="Prepare-" + item.id[:7], args=(item,))
        self.log.info("bot: start preparing item in thread: %s" % item.format_debug_string())
        th.daemon = True
        th.start()
        return th

    def _download(self, item):
        ver = item.version
        try:
            item.prepare()
        except PreparationFailedError as e:
            self.send_channel_msg(e.msg)
            return False

        if item.version > ver:
            var.playlist.version += 1

    # =======================
    #          Loop
    # =======================

    # Main loop of the Bot
    def loop(self):
        raw_music = ""
        while not self.exit and self.mumble.is_alive():

            while self.thread and self.mumble.sound_output.get_buffer_size() > 0.5 and not self.exit:
                # If the buffer isn't empty, I cannot send new music part, so I wait
                self._loop_status = 'Wait for buffer %.3f' % self.mumble.sound_output.get_buffer_size()
                time.sleep(0.01)

            if self.thread:
                # I get raw from ffmpeg thread
                # move playhead forward
                self._loop_status = 'Reading raw'
                if self.song_start_at == -1:
                    self.song_start_at = time.time() - self.playhead
                self.playhead = time.time() - self.song_start_at

                raw_music = self.thread.stdout.read(480)
                self.read_pcm_size += 480

                if self.redirect_ffmpeg_log:
                    try:
                        self.last_ffmpeg_err = self.thread_stderr.readline()
                        if self.last_ffmpeg_err:
                            self.log.debug("ffmpeg: " + self.last_ffmpeg_err.strip("\n"))
                    except:
                        pass

                if raw_music:
                    # Adjust the volume and send it to mumble
                    self.volume_cycle()
                    self.mumble.sound_output.add_sound(
                        audioop.mul(raw_music, 2, self.volume))
                else:
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

            if not self.is_pause and (self.thread is None or self.thread.poll() is not None):
                # ffmpeg thread has gone. indicate that last song has finished, or something is wrong.
                if self.read_pcm_size < 481 and len(var.playlist) > 0 and var.playlist.current_index != -1 \
                        and self.last_ffmpeg_err:
                    current = var.playlist.current_item()
                    self.log.error("bot: cannot play music %s", current.format_debug_string())
                    self.log.error("bot: with ffmpeg error: %s", self.last_ffmpeg_err)
                    self.last_ffmpeg_err = ""

                    self.send_channel_msg(constants.strings('unable_play', item=current.format_title()))
                    var.playlist.remove_by_id(current.id)
                    var.cache.free_and_delete(current.id)

                # move to the next song.
                if not self.wait_for_ready: # if wait_for_ready flag is not true, move to the next song.
                    if var.playlist.next():
                        current = var.playlist.current_item()
                        try:
                            current.validate()
                            if not current.is_ready():
                                self.log.info("bot: current music isn't ready, start downloading.")
                                self.async_download(current)
                                self.send_channel_msg(
                                    constants.strings('download_in_progress', item=current.format_title()))
                            self.wait_for_ready = True

                        except ValidationFailedError as e:
                            self.send_channel_msg(e.msg)
                            var.playlist.remove_by_id(current.id)
                            var.cache.free_and_delete(current.id)
                    else:
                        self._loop_status = 'Empty queue'
                else: # if wait_for_ready flag is true, means the pointer is already pointing to target song. start playing
                    current = var.playlist.current_item()
                    if current:
                        if current.is_ready():
                            self.wait_for_ready = False
                            self.launch_music()
                            self.async_download_next()
                        elif current.is_failed():
                            var.playlist.remove_by_id(current.id)
                            self.wait_for_ready = False
                        else:
                            self._loop_status = 'Wait for the next item to be ready'
                    else:
                        self.wait_for_ready = False

        while self.mumble.sound_output.get_buffer_size() > 0:
            # Empty the buffer before exit
            time.sleep(0.01)
        time.sleep(0.5)

        if self.exit:
            self._loop_status = "exited"
            if var.config.getboolean('bot', 'save_playlist', fallback=True) \
                    and var.config.get("bot", "save_music_library", fallback=True):
                self.log.info("bot: save playlist into database")
                var.playlist.save()

    def volume_cycle(self):
        delta = time.time() - self.last_volume_cycle_time

        if self.on_ducking and self.ducking_release < time.time():
            self.on_ducking = False
            self._max_rms = 0

        if delta > 0.001:
            if self.is_ducking and self.on_ducking:
                self.volume = (self.volume - self.ducking_volume) * math.exp(- delta / 0.2) + self.ducking_volume
            else:
                self.volume = self.volume_set - (self.volume_set - self.volume) * math.exp(- delta / 0.5)

        self.last_volume_cycle_time = time.time()

    def ducking_sound_received(self, user, sound):
        rms = audioop.rms(sound.pcm, 2)
        self._max_rms = max(rms, self._max_rms)
        if self._display_rms:
            if rms < self.ducking_threshold:
                print('%6d/%6d  ' % (rms, self._max_rms) + '-'*int(rms/200), end='\r')
            else:
                print('%6d/%6d  ' % (rms, self._max_rms) + '-'*int(self.ducking_threshold/200)
                      + '+'*int((rms - self.ducking_threshold)/200), end='\r')

        if rms > self.ducking_threshold:
            if self.on_ducking is False:
                self.log.debug("bot: ducking triggered")
                self.on_ducking = True
            self.ducking_release = time.time() + 1  # ducking release after 1s

    # =======================
    #      Play Control
    # =======================

    def clear(self):
        # Kill the ffmpeg thread and empty the playlist
        if self.thread:
            self.thread.kill()
            self.thread = None
        var.playlist.clear()
        self.wait_for_ready = False
        self.log.info("bot: music stopped. playlist trashed.")

    def stop(self):
        self.interrupt()
        self.is_pause = True
        var.playlist.next()
        self.wait_for_ready = True
        self.log.info("bot: music stopped.")

    def interrupt(self):
        # Kill the ffmpeg thread
        if self.thread:
            self.thread.kill()
            self.thread = None
        self.song_start_at = -1
        self.playhead = 0

    def pause(self):
        # Kill the ffmpeg thread
        if self.thread:
            self.pause_at_id = var.playlist.current_item().id
            self.thread.kill()
            self.thread = None
        self.is_pause = True
        self.song_start_at = -1
        self.log.info("bot: music paused at %.2f seconds." % self.playhead)

    def resume(self):
        if var.playlist.current_index == -1:
            var.playlist.next()

        music_wrapper = var.playlist.current_item()

        if not music_wrapper or not music_wrapper.id == self.pause_at_id or not music_wrapper.is_ready():
            self.is_pause = False
            self.playhead = 0
            return

        if var.config.getboolean('debug', 'ffmpeg'):
            ffmpeg_debug = "debug"
        else:
            ffmpeg_debug = "warning"

        self.log.info("bot: resume music at %.2f seconds" % self.playhead)

        uri = music_wrapper.uri()

        command = ("ffmpeg", '-v', ffmpeg_debug, '-nostdin', '-ss', "%f" % self.playhead, '-i',
                   uri, '-ac', '1', '-f', 's16le', '-ar', '48000', '-')

        if var.config.getboolean('bot', 'announce_current_music'):
            self.send_channel_msg(var.playlist.current_item().format_current_playing())

        self.log.info("bot: execute ffmpeg command: " + " ".join(command))
        # The ffmpeg process is a thread
        # prepare pipe for catching stderr of ffmpeg
        if self.redirect_ffmpeg_log:
            pipe_rd, pipe_wd = util.pipe_no_wait()  # Let the pipe work in non-blocking mode
            self.thread_stderr = os.fdopen(pipe_rd)
        else:
            pipe_rd, pipe_wd = None, None

        self.thread = sp.Popen(command, stdout=sp.PIPE, stderr=pipe_wd, bufsize=480)
        self.last_volume_cycle_time = time.time()
        self.pause_at_id = ""
        self.is_pause = False


def start_web_interface(addr, port):
    global formatter
    import interface

    # setup logger
    werkzeug_logger = logging.getLogger('werkzeug')
    logfile = util.solve_filepath(var.config.get('webinterface', 'web_logfile'))
    if logfile:
        handler = logging.handlers.RotatingFileHandler(logfile, mode='a', maxBytes=10240)  # Rotate after 10KB
    else:
        handler = logging.StreamHandler()

    werkzeug_logger.addHandler(handler)

    interface.init_proxy()
    interface.web.env = 'development'
    interface.web.run(port=port, host=addr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Bot for playing music on Mumble')

    # General arguments
    parser.add_argument("--config", dest='config', type=str, default='configuration.ini',
                        help='Load configuration from this file. Default: configuration.ini')
    parser.add_argument("--db", dest='db', type=str,
                        default=None, help='database file. Default: database.db')

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

    config = configparser.ConfigParser(interpolation=None, allow_no_value=True)
    parsed_configs = config.read([util.solve_filepath('configuration.default.ini'), util.solve_filepath(args.config)],
                                 encoding='utf-8')
    var.dbfile = args.db if args.db is not None else util.solve_filepath(
        config.get("bot", "database_path", fallback="database.db"))

    if len(parsed_configs) == 0:
        logging.error('Could not read configuration from file \"{}\"'.format(args.config))
        sys.exit()

    var.config = config
    var.db = SettingsDatabase(var.dbfile)

    # Setup logger

    bot_logger = logging.getLogger("bot")
    formatter = logging.Formatter('[%(asctime)s %(levelname)s %(threadName)s] %(message)s', "%b %d %H:%M:%S")
    bot_logger.setLevel(logging.INFO)

    if args.verbose:
        bot_logger.setLevel(logging.DEBUG)
        bot_logger.debug("Starting in DEBUG loglevel")
    elif args.quiet:
        bot_logger.setLevel(logging.ERROR)
        bot_logger.error("Starting in ERROR loglevel")

    logfile = util.solve_filepath(var.config.get('bot', 'logfile'))
    handler = None
    if logfile:
        print(f"Redirecting stdout and stderr to log file: {logfile}")
        handler = logging.handlers.RotatingFileHandler(logfile, mode='a', maxBytes=10240)  # Rotate after 10KB
        sys.stdout = util.LoggerIOWrapper(bot_logger, logging.INFO, fallback_io_buffer=sys.stdout.buffer)
        sys.stderr = util.LoggerIOWrapper(bot_logger, logging.ERROR, fallback_io_buffer=sys.stderr.buffer)
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    bot_logger.addHandler(handler)
    logging.getLogger("root").addHandler(handler)
    var.bot_logger = bot_logger

    if var.config.get("bot", "save_music_library", fallback=True):
        var.music_db = MusicDatabase(var.dbfile)
    else:
        var.music_db = MusicDatabase(":memory:")

    var.cache = MusicCache(var.music_db)

    # load playback mode
    playback_mode = None
    if var.db.has_option("playlist", "playback_mode"):
        playback_mode = var.db.get('playlist', 'playback_mode')
    else:
        playback_mode = var.config.get('bot', 'playback_mode', fallback="one-shot")

    if playback_mode in ["one-shot", "repeat", "random", "autoplay"]:
        var.playlist = media.playlist.get_playlist(playback_mode)
    else:
        raise KeyError("Unknown playback mode '%s'" % playback_mode)

    var.bot = MumbleBot(args)
    command.register_all_commands(var.bot)

    if var.config.get("bot", "refresh_cache_on_startup", fallback=True):
        var.cache.build_dir_cache()

    # load playlist
    if var.config.getboolean('bot', 'save_playlist', fallback=True):
        var.bot_logger.info("bot: load playlist from previous session")
        var.playlist.load()

    # Start the main loop.
    var.bot.loop()

