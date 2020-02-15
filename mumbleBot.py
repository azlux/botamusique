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
import re
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
            if command == var.config.get('command', 'play'):
                if var.playlist.length() > 0:
                    if parameter is not None and parameter.isdigit() and int(parameter) > 0 \
                            and int(parameter) < len(var.playlist.playlist):
                        self.stop()
                        self.launch_music(int(parameter))
                    elif self.is_pause:
                        self.resume()
                        self.send_msg(self.formatted_current_playing())
                    else:
                        self.send_msg(var.config.get('strings', 'not_playing'), text)
                else:
                    self.send_msg(var.config.get('strings', 'queue_empty'), text)

            elif command == var.config.get('command', 'pause'):
                self.pause()
                self.send_msg(var.config.get('strings', 'paused'))

            elif command == var.config.get('command', 'play_file') and parameter:

                music_folder = var.config.get('bot', 'music_folder')
                # if parameter is {index}
                if parameter.isdigit():
                    files = util.get_recursive_filelist_sorted(music_folder)
                    filename = files[int(parameter)].replace(music_folder, '')
                    music = {'type': 'file',
                             'path': filename,
                             'user': user}
                    logging.info("bot: add to playlist: " + filename)
                    var.playlist.append(music)

                # if parameter is {path}
                else:
                    # sanitize "../" and so on
                    path = os.path.abspath(os.path.join(music_folder, parameter))
                    if not path.startswith(os.path.abspath(music_folder)):
                        self.send_msg(var.config.get(
                            'strings', 'no_file'), text)
                        return

                    if os.path.isfile(path):
                        music = {'type': 'file',
                                 'path': parameter,
                                 'user': user}
                        logging.info("bot: add to playlist: " + parameter)
                        music = var.playlist.append(music)
                        self.send_msg(var.config.get(
                            'strings', 'file_added') % music['title'], text)
                        return

                    # if parameter is {folder}
                    elif os.path.isdir(path):
                        if not parameter.endswith('/'):
                            parameter += '/'

                        files = util.get_recursive_filelist_sorted(music_folder)
                        music_library = util.Dir(music_folder)
                        for file in files:
                            music_library.add_file(file)

                        files = music_library.get_files(parameter)

                        files = list(map(lambda file:
                            {'type': 'file', 'path': os.path.join(parameter, file), 'user': 'Web'}, files))

                        logging.info("web: add to playlist: " + " ,".join([file['path'] for file in files]))
                        files = var.playlist.extend(files)
                        self.send_msg(var.config.get(
                            'strings', 'file_added') % "<br> ".join([file['title'] for file in files]),
                                      text)
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
                            logging.info("bot: add to playlist: " + matches[0])
                            var.playlist.append(music)
                        else:
                            msg = var.config.get(
                                'strings', 'multiple_matches') + '<br />'
                            msg += '<br />'.join(matches)
                            self.send_msg(msg, text)

            elif command == var.config.get('command', 'play_url') and parameter:
                music = {'type': 'url',
                         # grab the real URL
                         'url': self.get_url_from_input(parameter),
                         'user': user,
                         'ready': 'validation'}

                if media.url.get_url_info(music):
                    if music['duration'] > var.config.getint('bot', 'max_track_duration'):
                        self.send_msg(var.config.get(
                            'strings', 'too_long'), text)
                    else:
                        for i in var.db.options("url_ban"):
                            if music['url'] == i:
                                self.mumble.users[text.actor].send_text_message(
                                    var.config.get('strings', 'url_ban'))
                                return
                        music['ready'] = "no"
                        var.playlist.append(music)
                        logging.info("bot: add to playlist: " + music['url'])
                        self.async_download_next()
                else:
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
                        logging.info("bot: add to playlist: " + music['url'])
                        self.async_download_next()
                    else:
                        self.send_msg(var.config.get('strings', 'bad_url'))
            # query http://www.radio-browser.info API for a radio station
            elif command == var.config.get('command', 'rb_query'):
                logging.info('bot: Querying radio stations')
                if not parameter:
                    logging.debug('rbquery without parameter')
                    msg = var.config.get('strings', 'rb_query_empty')
                    self.send_msg(msg, text)
                else:
                    logging.debug('bot: Found query parameter: ' + parameter)
                    # self.send_msg('Searching for stations - this may take some seconds...', text)
                    rb_stations = radiobrowser.getstations_byname(parameter)
                    msg = var.config.get('strings', 'rb_query_result') + " :"
                    msg += '\n<table><tr><th>!rbplay ID</th><th>Station Name</th><th>Genre</th><th>Codec/Bitrate</th><th>Country</th></tr>'
                    if not rb_stations:
                        logging.debug('bot: No matches found for rbquery ' + parameter)
                        self.send_msg('Radio-Browser found no matches for ' + parameter, text)
                    else:
                        for s in rb_stations:
                            stationid = s['id']
                            stationname = s['stationname']
                            country = s['country']
                            codec = s['codec']
                            bitrate = s['bitrate']
                            genre = s['genre']
                            # msg += f'<tr><td>{stationid}</td><td>{stationname}</td><td>{genre}</td><td>{codec}/{bitrate}</td><td>{country}</td></tr>'
                            msg += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s/%s</td><td>%s</td></tr>' % (stationid, stationname, genre, codec, bitrate, country)
                        msg += '</table>'
                        # Full message as html table
                        if len(msg) <= 5000:
                            self.send_msg(msg, text)
                        # Shorten message if message too long (stage I)
                        else:
                            logging.debug('Result too long stage I')
                            msg = var.config.get('strings', 'rb_query_result') + " :" + ' (shortened L1)'
                            msg += '\n<table><tr><th>!rbplay ID</th><th>Station Name</th></tr>'
                            for s in rb_stations:
                                stationid = s['id']
                                stationname = s['stationname']
                                # msg += f'<tr><td>{stationid}</td><td>{stationname}</td>'
                                msg += '<tr><td>%s</td><td>%s</td>' % (stationid, stationname)
                            msg += '</table>'
                            if len(msg) <= 5000:
                                self.send_msg(msg, text)
                            # Shorten message if message too long (stage II)
                            else:
                                logging.debug('Result too long stage II')
                                msg = var.config.get('strings', 'rb_query_result') + " :" + ' (shortened L2)'
                                msg += '!rbplay ID - Station Name'
                                for s in rb_stations:
                                    stationid = s['id']
                                    stationname = s['stationname'][:12]
                                    # msg += f'{stationid} - {stationname}'
                                    msg += '%s - %s' % (stationid, stationname)
                                if len(msg) <= 5000:
                                    self.send_msg(msg, text)
                                # Message still too long
                                else:
                                    self.send_msg('Query result too long to post (> 5000 characters), please try another query.', text)
            # Play a secific station (by id) from http://www.radio-browser.info API
            elif command == var.config.get('command', 'rb_play'):
                logging.debug('bot: Play a station by ID')
                if not parameter:
                    logging.debug('rbplay without parameter')
                    msg = var.config.get('strings', 'rb_play_empty')
                    self.send_msg(msg, text)
                else:
                    logging.debug('bot: Retreiving url for station ID ' + parameter)
                    rstation = radiobrowser.getstationname_byid(parameter)
                    stationname = rstation[0]['name']
                    country = rstation[0]['country']
                    codec = rstation[0]['codec']
                    bitrate = rstation[0]['bitrate']
                    genre = rstation[0]['tags']
                    homepage = rstation[0]['homepage']
                    msg = 'Radio station added to playlist:'
                    # msg += '<table><tr><th>ID</th><th>Station Name</th><th>Genre</th><th>Codec/Bitrate</th><th>Country</th><th>Homepage</th></tr>' + \
                    #       f'<tr><td>{parameter}</td><td>{stationname}</td><td>{genre}</td><td>{codec}/{bitrate}</td><td>{country}</td><td>{homepage}</td></tr></table>'
                    msg += '<table><tr><th>ID</th><th>Station Name</th><th>Genre</th><th>Codec/Bitrate</th><th>Country</th><th>Homepage</th></tr>' + \
                          '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s/%s</td><td>%s</td><td>%s</td></tr></table>' \
                           % (parameter, stationname, genre, codec, bitrate, country, homepage)
                    logging.debug('bot: Added station to playlist %s' % stationname)
                    self.send_msg(msg, text)
                    url = radiobrowser.geturl_byid(parameter)
                    if url != "-1":
                        logging.info('bot: Found url: ' + url)
                        music = {'type': 'radio',
                                 'title': stationname,
                                 'artist': homepage,
                                 'url': url,
                                 'user': user}
                        var.playlist.append(music)
                        logging.info("bot: add to playlist: " + music['url'])
                        self.async_download_next()
                    else:
                        logging.info('bot: No playable url found.')
                        msg += "No playable url found for this station, please try another station."
                        self.send_msg(msg, text)

            elif command == var.config.get('command', 'help'):
                self.send_msg(var.config.get('strings', 'help'), text)
                if self.is_admin(user):
                    self.send_msg(var.config.get(
                        'strings', 'admin_help'), text)

            elif command == var.config.get('command', 'stop'):
                self.stop()
                self.send_msg(var.config.get(
                    'strings', 'stopped'), text)

            elif command == var.config.get('command', 'clear'):
                self.clear()
                self.send_msg(var.config.get(
                    'strings', 'cleared'), text)

            elif command == var.config.get('command', 'kill'):
                if self.is_admin(user):
                    self.clear()
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
                    self.volume_set = float(float(parameter) / 100)
                    self.send_msg(var.config.get('strings', 'change_volume') % (
                        int(self.volume_set * 100), self.mumble.users[text.actor]['name']), text)
                    var.db.set('bot', 'volume', str(self.volume_set))
                    logging.info('bot: volume set to %d' % (self.volume_set * 100))
                else:
                    self.send_msg(var.config.get(
                        'strings', 'current_volume') % int(self.volume_set * 100), text)

            elif command == var.config.get('command', 'ducking'):
                if parameter == "" or parameter == "on":
                    self.is_ducking = True
                    self.ducking_volume = var.config.getfloat("bot", "ducking_volume", fallback=0.05)
                    self.ducking_threshold = var.config.getint("bot", "ducking_threshold", fallback=5000)
                    self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED,
                                                       self.ducking_sound_received)
                    self.mumble.set_receive_sound(True)
                    logging.info('bot: ducking is on')
                    msg = "Ducking on."
                    self.send_msg(msg, text)
                elif parameter == "off":
                    self.is_ducking = False
                    self.mumble.set_receive_sound(False)
                    msg = "Ducking off."
                    logging.info('bot: ducking is off')
                    self.send_msg(msg, text)

            elif command == var.config.get('command', 'ducking_threshold'):
                if parameter is not None and parameter.isdigit():
                    self.ducking_threshold = int(parameter)
                    msg = "Ducking threshold set to %d." % self.ducking_threshold
                    self.send_msg(msg, text)
                else:
                    msg = "Current ducking threshold is %d." % self.ducking_threshold
                    self.send_msg(msg, text)

            elif command == var.config.get('command', 'ducking_volume'):
                # The volume is a percentage
                if parameter is not None and parameter.isdigit() and 0 <= int(parameter) <= 100:
                    self.ducking_volume = float(float(parameter) / 100)
                    self.send_msg(var.config.get('strings', 'change_ducking_volume') % (
                        int(self.ducking_volume * 100), self.mumble.users[text.actor]['name']), text)
                    #var.db.set('bot', 'volume', str(self.volume_set))
                    logging.info('bot: volume on ducking set to %d' % (self.ducking_volume * 100))
                else:
                    self.send_msg(var.config.get(
                        'strings', 'current_ducking_volume') % int(self.ducking_volume * 100), text)

            elif command == var.config.get('command', 'current_music'):
                reply = ""
                if len(var.playlist.playlist) > 0:
                    reply = self.formatted_current_playing()
                else:
                    reply = var.config.get('strings', 'not_playing')

                self.send_msg(reply, text)

            elif command == var.config.get('command', 'skip'):
                if self.next():  # Is no number send, just skip the current music
                    self.launch_music()
                    self.async_download_next()
                else:
                    self.send_msg(var.config.get(
                        'strings', 'queue_empty'), text)

            elif command == var.config.get('command', 'remove'):
                # Allow to remove specific music into the queue with a number
                if parameter is not None and parameter.isdigit() and int(parameter) > 0 \
                    and int(parameter) < len(var.playlist.playlist):

                    removed = var.playlist.delete(int(parameter))

                    # the Title isn't here if the music wasn't downloaded
                    self.send_msg(var.config.get('strings', 'removing_item') % (
                        removed['title'] if 'title' in removed else removed['url']), text)
                else:
                    self.send_msg(var.config.get('strings', 'no_possible'), text)

            elif command == var.config.get('command', 'list_file'):
                folder_path = var.config.get('bot', 'music_folder')

                files = util.get_recursive_filelist_sorted(folder_path)
                if files:
                    msg = "<br> <b>Files available:</b>"
                    for index, files in enumerate(files):
                        newline = "<br> <b>{:0>3d}</b> - {:s}".format(index, files)
                        if len(msg) + len(newline) > 5000:
                            self.send_msg(msg, text)
                            msg = ""
                        msg +=  newline

                    self.send_msg(msg, text)
                else:
                    self.send_msg(var.config.get('strings', 'no_file'), text)

            elif command == var.config.get('command', 'queue'):
                if len(var.playlist.playlist) <= 1:
                    msg = var.config.get('strings', 'queue_empty')
                else:
                    msg = var.config.get(
                        'strings', 'queue_contents') + '<br />'
                    i = 1
                    for value in var.playlist.playlist:
                        msg += '[{}] ({}) {}<br />'.format(i, value['type'], value['title'] if 'title' in value else value['url'])
                        i += 1

                self.send_msg(msg, text)

            elif command == var.config.get('command', 'repeat'):
                var.playlist.append(var.playlist.current_item())
                music = var.playlist.current_item()
                if music['type'] == 'file':
                    logging.info("bot: add to playlist: " + music['path'])
                else:
                    logging.info("bot: add to playlist: " + music['url'])

            else:
                self.mumble.users[text.actor].send_text_message( command + ": " +  \
                    var.config.get('strings', 'bad_command'))

    def formatted_current_playing(self):
        if var.playlist.length() > 0:
            reply = ""
            current_music = var.playlist.current_item()
            source = current_music["type"]
            if source == "radio":
                reply = "[radio] {title} on {url} by {user}".format(
                    title=media.radio.get_radio_title(
                        current_music["url"]),
                    url=current_music["title"],
                    user=current_music["user"]
                )
            elif source == "url" and 'from_playlist' in current_music:
                thumbnail_html = ''
                if 'thumbnail' in current_music:
                    thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                                     current_music['thumbnail'] + '"/>'
                reply = "[playlist] {title} (from the playlist <a href=\"{url}\">{playlist}</a> by {user} <br> {thumb}".format(
                    title=current_music["title"],
                    url=current_music["playlist_url"],
                    playlist=current_music["playlist_title"],
                    user=current_music["user"],
                    thumb=thumbnail_html
                )
            elif source == "url":
                thumbnail_html = ''
                if 'thumbnail' in current_music:
                    thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                                     current_music['thumbnail'] + '"/>'
                reply = "[url] <a href=\"{url}\">{title}</a> by {user} <br> {thumb}".format(
                    title=current_music["title"],
                    url=current_music["url"],
                    user=current_music["user"],
                    thumb=thumbnail_html
                )
            elif source == "file":
                thumbnail_html = ''
                if 'thumbnail' in current_music:
                    thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                                     current_music['thumbnail'] + '"/>'
                reply = "[file] {title} by {user} <br> {thumb}".format(
                    title=current_music['artist'] + ' - ' + current_music['title'],
                    user=current_music["user"],
                    thumb=thumbnail_html
                )
            else:
                logging.error(current_music)
            return reply
        else:
            return None

    @staticmethod
    def is_admin(user):
        list_admin = var.config.get('bot', 'admin').split(';')
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
                logging.info("Current music wasn't ready, Downloading...")
                self.download_music()
                if music == False:
                    var.playlist.remove()
                    return
            uri = music['path']

            music = var.playlist.current_item()

            thumbnail_html = ''
            if 'thumbnail' in music:
                thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                                 music['thumbnail'] + '"/>'
            display = ''
            if 'artist' in music:
                display = music['artist'] + ' - '
            if 'title' in music:
                display += music['title']

            if var.config.getboolean('bot', 'announce_current_music'):
                self.send_msg(var.config.get(
                    'strings', 'now_playing') % (display, thumbnail_html))

        elif music["type"] == "file":
            uri = var.config.get('bot', 'music_folder') + \
                var.playlist.current_item()["path"]

            music = var.playlist.current_item()

            thumbnail_html = ''
            if 'thumbnail' in music:
                thumbnail_html = '<img width="80" src="data:image/jpge;base64,' + \
                                 music['thumbnail'] + '"/>'
            display = ''
            if 'artist' in music:
                display = music['artist'] + ' - '
            if 'title' in music:
                display += music['title']

            if var.config.getboolean('bot', 'announce_current_music'):
                self.send_msg(var.config.get(
                    'strings', 'now_playing') % (display, thumbnail_html))

        elif music["type"] == "radio":
            uri = music["url"]
            if 'title' not in music:
                logging.info("bot: fetching radio server description")
                title = media.radio.get_radio_server_description(uri)
                music["title"] = title

            if var.config.getboolean('bot', 'announce_current_music'):
                self.send_msg(var.config.get('strings', 'now_playing') %
                              (music["title"], "URL: " + uri))

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
        self.last_volume_cycle_time = time.time()

    def download_music(self, index=-1):
        if index == -1:
            index = var.playlist.current_index

        music = var.playlist.playlist[index]
        if music['type'] == 'url' and music['ready'] == "validation":
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
                logging.error("Error while fetching info from the URL")
                self.send_msg(var.config.get('strings', 'unable_download'))
                return False

        if music['type'] == 'url' and music['ready'] == "no":
            # download the music
            music['ready'] = "downloading"

            url = music['url']
            url_hash = hashlib.md5(url.encode()).hexdigest()

            logging.info("bot: Download url:" + url)
            logging.debug(music)

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

            logging.info("Information before start downloading: " +
                         str(music['title']))
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


        logging.info("bot: execute ffmpeg command: " + " ".join(command))
        # The ffmpeg process is a thread
        self.thread = sp.Popen(command, stdout=sp.PIPE, bufsize=480)
        self.is_playing = True
        self.is_pause = False
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

        if self.ducking_release < time.time():
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
                            or (var.playlist.current_item()['type'] == 'url' and var.playlist.current_item()['ready'] not in ['validation', 'downloading']):
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
    var.botamusique.loop()
