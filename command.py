# coding=utf-8
import logging
import os.path
import pymumble.pymumble_py3 as pymumble
import re

import constants
import media.file
import media.playlist
import media.radio
import media.system
import media.url
import util
import variables as var
from librb import radiobrowser
from database import Database


def register_all_commands(bot):
    bot.register_command(constants.commands('joinme'), cmd_joinme)
    bot.register_command(constants.commands('user_ban'), cmd_user_ban)
    bot.register_command(constants.commands('user_unban'), cmd_user_unban)
    bot.register_command(constants.commands('url_ban'), cmd_url_ban)
    bot.register_command(constants.commands('url_unban'), cmd_url_unban)
    bot.register_command(constants.commands('play'), cmd_play)
    bot.register_command(constants.commands('pause'), cmd_pause)
    bot.register_command(constants.commands('play_file'), cmd_play_file)
    bot.register_command(constants.commands('play_file_match'), cmd_play_file_match)
    bot.register_command(constants.commands('play_url'), cmd_play_url)
    bot.register_command(constants.commands('play_playlist'), cmd_play_playlist)
    bot.register_command(constants.commands('play_radio'), cmd_play_radio)
    bot.register_command(constants.commands('rb_query'), cmd_rb_query)
    bot.register_command(constants.commands('rb_play'), cmd_rb_play)
    bot.register_command(constants.commands('help'), cmd_help)
    bot.register_command(constants.commands('stop'), cmd_stop)
    bot.register_command(constants.commands('clear'), cmd_clear)
    bot.register_command(constants.commands('kill'), cmd_kill)
    bot.register_command(constants.commands('update'), cmd_update)
    bot.register_command(constants.commands('stop_and_getout'), cmd_stop_and_getout)
    bot.register_command(constants.commands('volume'), cmd_volume)
    bot.register_command(constants.commands('ducking'), cmd_ducking)
    bot.register_command(constants.commands('ducking_threshold'), cmd_ducking_threshold)
    bot.register_command(constants.commands('ducking_volume'), cmd_ducking_volume)
    bot.register_command(constants.commands('current_music'), cmd_current_music)
    bot.register_command(constants.commands('skip'), cmd_skip)
    bot.register_command(constants.commands('remove'), cmd_remove)
    bot.register_command(constants.commands('list_file'), cmd_list_file)
    bot.register_command(constants.commands('queue'), cmd_queue)
    bot.register_command(constants.commands('random'), cmd_random)
    bot.register_command(constants.commands('mode'), cmd_mode)
    bot.register_command(constants.commands('drop_database'), cmd_drop_database)

def send_multi_lines(bot, lines, text):
    msg = ""
    br = ""
    for newline in lines:
        msg += br
        br = "<br>"
        if len(msg) + len(newline) > 5000:
            bot.send_msg(msg, text)
            msg = ""
        msg += newline

    bot.send_msg(msg, text)

# ---------------- Commands ------------------


def cmd_joinme(bot, user, text, command, parameter):
    bot.mumble.users.myself.move_in(
        bot.mumble.users[text.actor]['channel_id'], token=parameter)


def cmd_user_ban(bot, user, text, command, parameter):
    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.user_ban(parameter))
        else:
            bot.mumble.users[text.actor].send_text_message(util.get_user_ban())
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))
    return


def cmd_user_unban(bot, user, text, command, parameter):
    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.user_unban(parameter))
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))
    return


def cmd_url_ban(bot, user, text, command, parameter):
    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.url_ban(util.get_url_from_input(parameter)))
        else:
            bot.mumble.users[text.actor].send_text_message(util.get_url_ban())
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))
    return


def cmd_url_unban(bot, user, text, command, parameter):
    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.url_unban(util.get_url_from_input(parameter)))
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))
    return


def cmd_play(bot, user, text, command, parameter):
    if var.playlist.length() > 0:
        if parameter is not None:
            if parameter.isdigit() and int(parameter) > 0 and int(parameter) <= len(var.playlist):
                bot.interrupt_playing()
                bot.launch_music(int(parameter) - 1)
            else:
                bot.send_msg(constants.strings('invalid_index', index=parameter), text)

        elif bot.is_pause:
            bot.resume()
        else:
            bot.send_msg(util.format_current_playing(), text)
    else:
        bot.is_pause = False
        bot.send_msg(constants.strings('queue_empty'), text)


def cmd_pause(bot, user, text, command, parameter):
    bot.pause()
    bot.send_msg(constants.strings('paused'))


def cmd_play_file(bot, user, text, command, parameter):
    music_folder = var.config.get('bot', 'music_folder')
    # if parameter is {index}
    if parameter.isdigit():
        files = util.get_recursive_filelist_sorted(music_folder)
        if int(parameter) < len(files):
            filename = files[int(parameter)].replace(music_folder, '')
            music = {'type': 'file',
                     'path': filename,
                     'user': user}
            logging.info("cmd: add to playlist: " + filename)
            music = var.playlist.append(music)
            bot.send_msg(constants.strings('file_added', item=util.format_song_string(music)), text)

    # if parameter is {path}
    else:
        # sanitize "../" and so on
        path = os.path.abspath(os.path.join(music_folder, parameter))
        if not path.startswith(os.path.abspath(music_folder)):
            bot.send_msg(constants.strings('no_file'), text)
            return

        if os.path.isfile(path):
            music = {'type': 'file',
                     'path': parameter,
                     'user': user}
            logging.info("cmd: add to playlist: " + parameter)
            music = var.playlist.append(music)
            bot.send_msg(constants.strings('file_added', item=util.format_song_string(music)), text)
            return

        # if parameter is {folder}
        elif os.path.isdir(path):
            if parameter != '.' and parameter != './':
                if not parameter.endswith("/"):
                    parameter += "/"
            else:
                parameter = ""

            files = util.get_recursive_filelist_sorted(music_folder)
            music_library = util.Dir(music_folder)
            for file in files:
                music_library.add_file(file)

            files = music_library.get_files(parameter)
            msgs = [constants.strings('multiple_file_added')]
            count = 0

            for file in files:
                count += 1
                music = {'type': 'file',
                         'path': file,
                         'user': user}
                logging.info("cmd: add to playlist: " + file)
                music = var.playlist.append(music)

                msgs.append("{} ({})".format(music['title'], music['path']))

            if count != 0:
                send_multi_lines(bot, msgs, text)
            else:
                bot.send_msg(constants.strings('no_file'), text)

        else:
            # try to do a partial match
            files = util.get_recursive_filelist_sorted(music_folder)
            matches = [(index, file) for index, file in enumerate(files) if parameter.lower() in file.lower()]
            if len(matches) == 0:
                bot.send_msg(constants.strings('no_file'), text)
            elif len(matches) == 1:
                music = {'type': 'file',
                         'path': matches[0][1],
                         'user': user}
                logging.info("cmd: add to playlist: " + matches[0][1])
                music = var.playlist.append(music)
                bot.send_msg(constants.strings('file_added', item=util.format_song_string(music)), text)
            else:
                msgs = [ constants.strings('multiple_matches')]
                for match in matches:
                    msgs.append("<b>{:0>3d}</b> - {:s}".format(match[0], match[1]))
                send_multi_lines(bot, msgs, text)


def cmd_play_file_match(bot, user, text, command, parameter):
    music_folder = var.config.get('bot', 'music_folder')
    if parameter is not None:
        files = util.get_recursive_filelist_sorted(music_folder)
        msgs = [ constants.strings('multiple_file_added')]
        count = 0
        try:
            for file in files:
                match = re.search(parameter, file)
                if match:
                    count += 1
                    music = {'type': 'file',
                             'path': file,
                             'user': user}
                    logging.info("cmd: add to playlist: " + file)
                    music = var.playlist.append(music)

                    msgs.append("{} ({})".format(music['title'], music['path']))

            if count != 0:
                send_multi_lines(bot, msgs, text)
            else:
                bot.send_msg(constants.strings('no_file'), text)

        except re.error as e:
            msg = constants.strings('wrong_pattern', error=str(e))
            bot.send_msg(msg, text)
    else:
        bot.send_msg(constants.strings('bad_parameter', command))


def cmd_play_url(bot, user, text, command, parameter):
    music = {'type': 'url',
             # grab the real URL
             'url': util.get_url_from_input(parameter),
             'user': user,
             'ready': 'validation'}

    music = bot.validate_music(music)
    if music:
        var.playlist.append(music)
        logging.info("cmd: add to playlist: " + music['url'])
        bot.send_msg(constants.strings('file_added', item=util.format_song_string(music)), text)
        if var.playlist.length() == 2:
            # If I am the second item on the playlist. (I am the next one!)
            bot.async_download_next()
    else:
        bot.send_msg(constants.strings('unable_download'), text)


def cmd_play_playlist(bot, user, text, command, parameter):
    offset = 0  # if you want to start the playlist at a specific index
    try:
        offset = int(parameter.split(" ")[-1])
    except ValueError:
        pass

    url = util.get_url_from_input(parameter)
    logging.debug("cmd: fetching media info from playlist url %s" % url)
    items = media.playlist.get_playlist_info(url=url, start_index=offset, user=user)
    if len(items) > 0:
        var.playlist.extend(items)
        for music in items:
            logging.info("cmd: add to playlist: " + util.format_debug_song_string(music))


def cmd_play_radio(bot, user, text, command, parameter):
    if not parameter:
        all_radio = var.config.items('radio')
        msg = constants.strings('preconfigurated_radio')
        for i in all_radio:
            comment = ""
            if len(i[1].split(maxsplit=1)) == 2:
                comment = " - " + i[1].split(maxsplit=1)[1]
            msg += "<br />" + i[0] + comment
        bot.send_msg(msg, text)
    else:
        if var.config.has_option('radio', parameter):
            parameter = var.config.get('radio', parameter)
            parameter = parameter.split()[0]
        url = util.get_url_from_input(parameter)
        if url:
            music = {'type': 'radio',
                     'url': url,
                     'user': user}
            var.playlist.append(music)
            logging.info("cmd: add to playlist: " + music['url'])
            bot.async_download_next()
        else:
            bot.send_msg(constants.strings('bad_url'))


def cmd_rb_query(bot, user, text, command, parameter):
    logging.info('cmd: Querying radio stations')
    if not parameter:
        logging.debug('rbquery without parameter')
        msg = constants.strings('rb_query_empty')
        bot.send_msg(msg, text)
    else:
        logging.debug('cmd: Found query parameter: ' + parameter)
        # bot.send_msg('Searching for stations - this may take some seconds...', text)
        rb_stations = radiobrowser.getstations_byname(parameter)
        msg = constants.strings('rb_query_result')
        msg += '\n<table><tr><th>!rbplay ID</th><th>Station Name</th><th>Genre</th><th>Codec/Bitrate</th><th>Country</th></tr>'
        if not rb_stations:
            logging.debug('cmd: No matches found for rbquery ' + parameter)
            bot.send_msg('Radio-Browser found no matches for ' + parameter, text)
        else:
            for s in rb_stations:
                stationid = s['id']
                stationname = s['stationname']
                country = s['country']
                codec = s['codec']
                bitrate = s['bitrate']
                genre = s['genre']
                # msg += f'<tr><td>{stationid}</td><td>{stationname}</td><td>{genre}</td><td>{codec}/{bitrate}</td><td>{country}</td></tr>'
                msg += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s/%s</td><td>%s</td></tr>' % (
                    stationid, stationname, genre, codec, bitrate, country)
            msg += '</table>'
            # Full message as html table
            if len(msg) <= 5000:
                bot.send_msg(msg, text)
            # Shorten message if message too long (stage I)
            else:
                logging.debug('Result too long stage I')
                msg = constants.strings('rb_query_result') + ' (shortened L1)'
                msg += '\n<table><tr><th>!rbplay ID</th><th>Station Name</th></tr>'
                for s in rb_stations:
                    stationid = s['id']
                    stationname = s['stationname']
                    # msg += f'<tr><td>{stationid}</td><td>{stationname}</td>'
                    msg += '<tr><td>%s</td><td>%s</td>' % (stationid, stationname)
                msg += '</table>'
                if len(msg) <= 5000:
                    bot.send_msg(msg, text)
                # Shorten message if message too long (stage II)
                else:
                    logging.debug('Result too long stage II')
                    msg = constants.strings('rb_query_result') + ' (shortened L2)'
                    msg += '!rbplay ID - Station Name'
                    for s in rb_stations:
                        stationid = s['id']
                        stationname = s['stationname'][:12]
                        # msg += f'{stationid} - {stationname}'
                        msg += '%s - %s' % (stationid, stationname)
                    if len(msg) <= 5000:
                        bot.send_msg(msg, text)
                    # Message still too long
                    else:
                        bot.send_msg('Query result too long to post (> 5000 characters), please try another query.',
                                     text)


def cmd_rb_play(bot, user, text, command, parameter):
    logging.debug('cmd: Play a station by ID')
    if not parameter:
        logging.debug('rbplay without parameter')
        msg = constants.strings('rb_play_empty')
        bot.send_msg(msg, text)
    else:
        logging.debug('cmd: Retreiving url for station ID ' + parameter)
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
        logging.debug('cmd: Added station to playlist %s' % stationname)
        bot.send_msg(msg, text)
        url = radiobrowser.geturl_byid(parameter)
        if url != "-1":
            logging.info('cmd: Found url: ' + url)
            music = {'type': 'radio',
                     'title': stationname,
                     'artist': homepage,
                     'url': url,
                     'user': user}
            var.playlist.append(music)
            logging.info("cmd: add to playlist: " + music['url'])
            bot.async_download_next()
        else:
            logging.info('cmd: No playable url found.')
            msg += "No playable url found for this station, please try another station."
            bot.send_msg(msg, text)


def cmd_help(bot, user, text, command, parameter):
    bot.send_msg(constants.strings('help'), text)
    if bot.is_admin(user):
        bot.send_msg(constants.strings('admin_help'), text)


def cmd_stop(bot, user, text, command, parameter):
    bot.stop()
    bot.send_msg(constants.strings('stopped'), text)


def cmd_clear(bot, user, text, command, parameter):
    bot.clear()
    bot.send_msg(constants.strings('cleared'), text)


def cmd_kill(bot, user, text, command, parameter):
    if bot.is_admin(user):
        bot.pause()
        bot.exit = True
    else:
        bot.mumble.users[text.actor].send_text_message(
            constants.strings('not_admin'))


def cmd_update(bot, user, text, command, parameter):
    if bot.is_admin(user):
        bot.mumble.users[text.actor].send_text_message(
            constants.strings('start_updating'))
        msg = util.update(bot.version)
        bot.mumble.users[text.actor].send_text_message(msg)
    else:
        bot.mumble.users[text.actor].send_text_message(
            constants.strings('not_admin'))


def cmd_stop_and_getout(bot, user, text, command, parameter):
    bot.stop()
    if bot.channel:
        bot.mumble.channels.find_by_name(bot.channel).move_in()


def cmd_volume(bot, user, text, command, parameter):
    # The volume is a percentage
    if parameter is not None and parameter.isdigit() and 0 <= int(parameter) <= 100:
        bot.volume_set = float(float(parameter) / 100)
        bot.send_msg(constants.strings('change_volume',
            volume=int(bot.volume_set * 100), user=bot.mumble.users[text.actor]['name']), text)
        var.db.set('bot', 'volume', str(bot.volume_set))
        logging.info('cmd: volume set to %d' % (bot.volume_set * 100))
    else:
        bot.send_msg(constants.strings('current_volume', volume=int(bot.volume_set * 100)), text)


def cmd_ducking(bot, user, text, command, parameter):
    if parameter == "" or parameter == "on":
        bot.is_ducking = True
        var.db.set('bot', 'ducking', True)
        bot.ducking_volume = var.config.getfloat("bot", "ducking_volume", fallback=0.05)
        bot.ducking_threshold = var.config.getint("bot", "ducking_threshold", fallback=5000)
        bot.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED,
                                          bot.ducking_sound_received)
        bot.mumble.set_receive_sound(True)
        logging.info('cmd: ducking is on')
        msg = "Ducking on."
        bot.send_msg(msg, text)
    elif parameter == "off":
        bot.is_ducking = False
        bot.mumble.set_receive_sound(False)
        var.db.set('bot', 'ducking', False)
        msg = "Ducking off."
        logging.info('cmd: ducking is off')
        bot.send_msg(msg, text)


def cmd_ducking_threshold(bot, user, text, command, parameter):
    if parameter is not None and parameter.isdigit():
        bot.ducking_threshold = int(parameter)
        var.db.set('bot', 'ducking_threshold', str(bot.ducking_threshold))
        msg = "Ducking threshold set to %d." % bot.ducking_threshold
        bot.send_msg(msg, text)
    else:
        msg = "Current ducking threshold is %d." % bot.ducking_threshold
        bot.send_msg(msg, text)


def cmd_ducking_volume(bot, user, text, command, parameter):
    # The volume is a percentage
    if parameter is not None and parameter.isdigit() and 0 <= int(parameter) <= 100:
        bot.ducking_volume = float(float(parameter) / 100)
        bot.send_msg(constants.strings('change_ducking_volume',
            volume=int(bot.ducking_volume * 100), user=bot.mumble.users[text.actor]['name']), text)
        # var.db.set('bot', 'volume', str(bot.volume_set))
        var.db.set('bot', 'ducking_volume', str(bot.ducking_volume))
        logging.info('cmd: volume on ducking set to %d' % (bot.ducking_volume * 100))
    else:
        bot.send_msg(constants.strings('current_ducking_volume', volume=int(bot.ducking_volume * 100)), text)


def cmd_current_music(bot, user, text, command, parameter):
    reply = ""
    if var.playlist.length() > 0:
        bot.send_msg(util.format_current_playing())
    else:
        reply = constants.strings('not_playing')
    bot.send_msg(reply, text)


def cmd_skip(bot, user, text, command, parameter):
    if var.playlist.length() > 0:
        bot.stop()
        bot.launch_music()
        bot.async_download_next()
    else:
        bot.send_msg(constants.strings('queue_empty'), text)


def cmd_remove(bot, user, text, command, parameter):
    # Allow to remove specific music into the queue with a number
    if parameter is not None and parameter.isdigit() and int(parameter) > 0 \
            and int(parameter) <= var.playlist.length():

        index = int(parameter) - 1

        removed = None
        if index == var.playlist.current_index:
            removed = var.playlist.remove(index)

            if index < len(var.playlist):
                if not bot.is_pause:
                    bot.interrupt_playing()
                    var.playlist.current_index -= 1
                    # then the bot will move to next item

            else: # if item deleted is the last item of the queue
                var.playlist.current_index -= 1
                if not bot.is_pause:
                    bot.interrupt_playing()
        else:
            removed = var.playlist.remove(index)

        # the Title isn't here if the music wasn't downloaded
        bot.send_msg(constants.strings('removing_item',
            item=removed['title'] if 'title' in removed else removed['url']), text)

        logging.info("cmd: delete from playlist: " + str(removed['path'] if 'path' in removed else removed['url']))
    else:
        bot.send_msg(constants.strings('bad_parameter', command=command))


def cmd_list_file(bot, user, text, command, parameter):
    folder_path = var.config.get('bot', 'music_folder')

    files = util.get_recursive_filelist_sorted(folder_path)
    msgs = [ "<br> <b>Files available:</b>" if not parameter else "<br> <b>Matched files:</b>" ]
    try:
        count = 0
        for index, file in enumerate(files):
            if parameter:
                match = re.search(parameter, file)
                if not match:
                    continue

            count += 1
            msgs.append("<b>{:0>3d}</b> - {:s}".format(index, file))

        if count != 0:
            send_multi_lines(bot, msgs, text)
        else:
            bot.send_msg(constants.strings('no_file'), text)

    except re.error as e:
        msg = constants.strings('wrong_pattern', error=str(e))
        bot.send_msg(msg, text)


def cmd_queue(bot, user, text, command, parameter):
    if len(var.playlist) == 0:
        msg = constants.strings('queue_empty')
        bot.send_msg(msg, text)
    else:
        msgs = [ constants.strings('queue_contents')]
        for i, value in enumerate(var.playlist):
            newline = ''
            if i == var.playlist.current_index:
                newline = '<b>{} ▶ ({}) {} ◀</b>'.format(i + 1, value['type'],
                                                           value['title'] if 'title' in value else value['url'])
            else:
                newline = '<b>{}</b> ({}) {}'.format(i + 1, value['type'],
                                                     value['title'] if 'title' in value else value['url'])

            msgs.append(newline)

        send_multi_lines(bot, msgs, text)

def cmd_random(bot, user, text, command, parameter):
    bot.interrupt_playing()
    var.playlist.randomize()

def cmd_mode(bot, user, text, command, parameter):
    if not parameter:
        bot.send_msg(constants.strings("current_mode", mode=var.playlist.mode), text)
        return
    if not parameter in ["one-shot", "repeat", "random"]:
        bot.send_msg(constants.strings('unknown_mode', mode=parameter), text)
    else:
        var.db.set('playlist', 'playback_mode', parameter)
        var.playlist.set_mode(parameter)
        logging.info("command: playback mode changed to %s." % parameter)
        bot.send_msg(constants.strings("change_mode", mode=var.playlist.mode,
                                       user=bot.mumble.users[text.actor]['name']), text)
        if parameter == "random":
            bot.stop()
            var.playlist.randomize()
            bot.launch_music(0)


def cmd_drop_database(bot, user, text, command, parameter):
    var.db.drop_table()
    var.db = Database(var.dbfile)
    bot.send_msg(constants.strings('database_dropped'), text)
