import logging
import os.path
import pymumble.pymumble_py3 as pymumble
import re
import time
import configparser

import interface
import media.file
import media.playlist
import media.radio
import media.system
import media.url
import util
import variables as var
from librb import radiobrowser
from media.playlist import PlayList


def register_all_commands(bot):
    bot.register_command(var.config.get('command', 'joinme'), cmd_joinme)
    bot.register_command(var.config.get('command', 'user_ban'), cmd_user_ban)
    bot.register_command(var.config.get('command', 'user_unban'), cmd_user_unban)
    bot.register_command(var.config.get('command', 'url_ban'), cmd_url_ban)
    bot.register_command(var.config.get('command', 'url_unban'), cmd_url_unban)
    bot.register_command(var.config.get('command', 'play'), cmd_play)
    bot.register_command(var.config.get('command', 'pause'), cmd_pause)
    bot.register_command(var.config.get('command', 'play_file'), cmd_play_file)
    bot.register_command(var.config.get('command', 'play_file_match'), cmd_play_file_match)
    bot.register_command(var.config.get('command', 'play_url'), cmd_play_url)
    bot.register_command(var.config.get('command', 'play_playlist'), cmd_play_playlist)
    bot.register_command(var.config.get('command', 'play_radio'), cmd_play_radio)
    bot.register_command(var.config.get('command', 'rb_query'), cmd_rb_query)
    bot.register_command(var.config.get('command', 'rb_play'), cmd_rb_play)
    bot.register_command(var.config.get('command', 'help'), cmd_help)
    bot.register_command(var.config.get('command', 'stop'), cmd_stop)
    bot.register_command(var.config.get('command', 'clear'), cmd_clear)
    bot.register_command(var.config.get('command', 'kill'), cmd_kill)
    bot.register_command(var.config.get('command', 'update'), cmd_update)
    bot.register_command(var.config.get('command', 'stop_and_getout'), cmd_stop_and_getout)
    bot.register_command(var.config.get('command', 'volume'), cmd_volume)
    bot.register_command(var.config.get('command', 'ducking'), cmd_ducking)
    bot.register_command(var.config.get('command', 'ducking_threshold'), cmd_ducking_threshold)
    bot.register_command(var.config.get('command', 'ducking_volume'), cmd_ducking_volume)
    bot.register_command(var.config.get('command', 'current_music'), cmd_current_music)
    bot.register_command(var.config.get('command', 'skip'), cmd_skip)
    bot.register_command(var.config.get('command', 'remove'), cmd_remove)
    bot.register_command(var.config.get('command', 'list_file'), cmd_list_file)
    bot.register_command(var.config.get('command', 'queue'), cmd_queue)

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


def formatted_current_playing():
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


# ---------------- Commands ------------------


def cmd_joinme(bot, user, text, command, parameter):
    bot.mumble.users.mybot.move_in(
        bot.mumble.users[text.actor]['channel_id'], token=parameter)
    return


def cmd_user_ban(bot, user, text, command, parameter):
    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.user_ban(parameter))
        else:
            bot.mumble.users[text.actor].send_text_message(util.get_user_ban())
    else:
        bot.mumble.users[text.actor].send_text_message(var.config.get('strings', 'not_admin'))
    return


def cmd_user_unban(bot, user, text, command, parameter):
    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.user_unban(parameter))
    else:
        bot.mumble.users[text.actor].send_text_message(var.config.get('strings', 'not_admin'))
    return


def cmd_url_ban(bot, user, text, command, parameter):
    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.url_ban(bot.get_url_from_input(parameter)))
        else:
            bot.mumble.users[text.actor].send_text_message(util.get_url_ban())
    else:
        bot.mumble.users[text.actor].send_text_message(var.config.get('strings', 'not_admin'))
    return


def cmd_url_unban(bot, user, text, command, parameter):
    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.url_unban(bot.get_url_from_input(parameter)))
    else:
        bot.mumble.users[text.actor].send_text_message(var.config.get('strings', 'not_admin'))
    return


def cmd_play(bot, user, text, command, parameter):
    if var.playlist.length() > 0:
        if parameter is not None and parameter.isdigit() and int(parameter) > 0 \
                and int(parameter) <= len(var.playlist.playlist):
            bot.stop()
            bot.launch_music(int(parameter) - 1)
        elif bot.is_pause:
            bot.resume()
            bot.send_msg(formatted_current_playing())
        else:
            bot.send_msg(var.config.get('strings', 'not_playing'), text)
    else:
        bot.send_msg(var.config.get('strings', 'queue_empty'), text)


def cmd_pause(bot, user, text, command, parameter):
    bot.pause()
    bot.send_msg(var.config.get('strings', 'paused'))


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
            logging.info("bot: add to playlist: " + filename)
            var.playlist.append(music)
            bot.send_msg(var.config.get('strings', 'file_added') + music['title'], text)

    # if parameter is {path}
    else:
        # sanitize "../" and so on
        path = os.path.abspath(os.path.join(music_folder, parameter))
        if not path.startswith(os.path.abspath(music_folder)):
            bot.send_msg(var.config.get('strings', 'no_file'), text)
            return

        if os.path.isfile(path):
            music = {'type': 'file',
                     'path': parameter,
                     'user': user}
            logging.info("bot: add to playlist: " + parameter)
            music = var.playlist.append(music)
            bot.send_msg(var.config.get('strings', 'file_added') + music['title'], text)
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

            files = list(map(lambda file:
                             {'type': 'file', 'path': os.path.join(parameter, file), 'user': user}, files))

            logging.info("web: add to playlist: " + " ,".join([file['path'] for file in files]))
            files = var.playlist.extend(files)
            bot.send_msg(var.config.get('strings', 'file_added')
                         + "<br> ".join([file['title'] for file in files]), text)
        else:
            # try to do a partial match
            files = util.get_recursive_filelist_sorted(music_folder)
            matches = [(index, file) for index, file in enumerate(files) if parameter.lower() in file.lower()]
            if len(matches) == 0:
                bot.send_msg(var.config.get(
                    'strings', 'no_file'), text)
            elif len(matches) == 1:
                music = {'type': 'file',
                         'path': matches[0][1],
                         'user': user}
                logging.info("bot: add to playlist: " + matches[0][1])
                music = var.playlist.append(music)
                bot.send_msg(var.config.get( 'strings', 'file_added')
                             + "{} ({})".format(music['title'], music['path']), text)
            else:
                msgs = [ var.config.get('strings', 'multiple_matches') ]
                for match in matches:
                    msgs.append("<b>{:0>3d}</b> - {:s}".format(match[0], match[1]))
                send_multi_lines(bot, msgs, text)


def cmd_play_file_match(bot, user, text, command, parameter):
    music_folder = var.config.get('bot', 'music_folder')
    if parameter is not None:
        files = util.get_recursive_filelist_sorted(music_folder)
        msgs = [ var.config.get('strings', 'file_added') ]
        count = 0
        try:
            for file in files:
                match = re.search(parameter, file)
                if match:
                    count += 1
                    music = {'type': 'file',
                             'path': file,
                             'user': user}
                    logging.info("bot: add to playlist: " + file)
                    music = var.playlist.append(music)

                    msgs.append("{} ({})".format(music['title'], music['path']))

            if count != 0:
                send_multi_lines(bot, msgs, text)
            else:
                bot.send_msg(var.config.get('strings', 'no_file'), text)

        except re.error as e:
            msg = var.config.get('strings', 'wrong_pattern') % str(e)
            bot.send_msg(msg, text)
    else:
        bot.send_msg(var.config.get('strings', 'wrong_parameter') % command)


def cmd_play_url(bot, user, text, command, parameter):
    music = {'type': 'url',
             # grab the real URL
             'url': bot.get_url_from_input(parameter),
             'user': user,
             'ready': 'validation'}

    if media.url.get_url_info(music):
        if music['duration'] > var.config.getint('bot', 'max_track_duration'):
            bot.send_msg(var.config.get(
                'strings', 'too_long'), text)
        else:
            for i in var.db.options("url_ban"):
                if music['url'] == i:
                    bot.mumble.users[text.actor].send_text_message(
                        var.config.get('strings', 'url_ban'))
                    return
            music['ready'] = "no"
            var.playlist.append(music)
            logging.info("bot: add to playlist: " + music['url'])
            bot.async_download_next()
    else:
        bot.send_msg(var.config.get(
            'strings', 'unable_download'), text)


def cmd_play_playlist(bot, user, text, command, parameter):
    offset = 1  # if you want to start the playlist at a specific index
    try:
        offset = int(parameter.split(" ")[-1])
    except ValueError:
        pass
    if media.playlist.get_playlist_info(url=bot.get_url_from_input(parameter), start_index=offset, user=user):
        bot.async_download_next()


def cmd_play_radio(bot, user, text, command, parameter):
    if not parameter:
        all_radio = var.config.items('radio')
        msg = var.config.get(
            'strings', 'preconfigurated_radio') + " :"
        for i in all_radio:
            comment = ""
            if len(i[1].split(maxsplit=1)) == 2:
                comment = " - " + i[1].split(maxsplit=1)[1]
            msg += "<br />" + i[0] + comment
        bot.send_msg(msg, text)
    else:
        if var.config.has_option('radio', command, parameter):
            parameter = var.config.get('radio', parameter)
            parameter = parameter.split()[0]
        url = bot.get_url_from_input(parameter)
        if url:
            music = {'type': 'radio',
                     'url': url,
                     'user': user}
            var.playlist.append(music)
            logging.info("bot: add to playlist: " + music['url'])
            bot.async_download_next()
        else:
            bot.send_msg(var.config.get('strings', 'bad_url'))


def cmd_rb_query(bot, user, text, command, parameter):
    logging.info('bot: Querying radio stations')
    if not parameter:
        logging.debug('rbquery without parameter')
        msg = var.config.get('strings', 'rb_query_empty')
        bot.send_msg(msg, text)
    else:
        logging.debug('bot: Found query parameter: ' + parameter)
        # bot.send_msg('Searching for stations - this may take some seconds...', text)
        rb_stations = radiobrowser.getstations_byname(parameter)
        msg = var.config.get('strings', 'rb_query_result') + " :"
        msg += '\n<table><tr><th>!rbplay ID</th><th>Station Name</th><th>Genre</th><th>Codec/Bitrate</th><th>Country</th></tr>'
        if not rb_stations:
            logging.debug('bot: No matches found for rbquery ' + parameter)
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
                msg = var.config.get('strings', 'rb_query_result') + " :" + ' (shortened L1)'
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
                    msg = var.config.get('strings', 'rb_query_result') + " :" + ' (shortened L2)'
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
    logging.debug('bot: Play a station by ID')
    if not parameter:
        logging.debug('rbplay without parameter')
        msg = var.config.get('strings', 'rb_play_empty')
        bot.send_msg(msg, text)
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
        bot.send_msg(msg, text)
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
            bot.async_download_next()
        else:
            logging.info('bot: No playable url found.')
            msg += "No playable url found for this station, please try another station."
            bot.send_msg(msg, text)


def cmd_help(bot, user, text, command, parameter):
    bot.send_msg(var.config.get('strings', 'help'), text)
    if bot.is_admin(user):
        bot.send_msg(var.config.get(
            'strings', 'admin_help'), text)


def cmd_stop(bot, user, text, command, parameter):
    bot.stop()
    bot.send_msg(var.config.get( 'strings', 'stopped'), text)


def cmd_clear(bot, user, text, command, parameter):
    bot.clear()
    bot.send_msg(var.config.get(
        'strings', 'cleared'), text)


def cmd_kill(bot, user, text, command, parameter):
    if bot.is_admin(user):
        bot.clear()
        bot.exit = True
    else:
        bot.mumble.users[text.actor].send_text_message(
            var.config.get('strings', 'not_admin'))


def cmd_update(bot, user, text, command, parameter):
    if bot.is_admin(user):
        bot.mumble.users[text.actor].send_text_message(
            "Starting the update")
        # Need to be improved
        msg = util.update(version)
        bot.mumble.users[text.actor].send_text_message(msg)
    else:
        bot.mumble.users[text.actor].send_text_message(
            var.config.get('strings', 'not_admin'))


def cmd_stop_and_getout(bot, user, text, command, parameter):
    bot.stop()
    if bot.channel:
        bot.mumble.channels.find_by_name(bot.channel).move_in()


def cmd_volume(bot, user, text, command, parameter):
    # The volume is a percentage
    if parameter is not None and parameter.isdigit() and 0 <= int(parameter) <= 100:
        bot.volume_set = float(float(parameter) / 100)
        bot.send_msg(var.config.get('strings', 'change_volume') % (
            int(bot.volume_set * 100), bot.mumble.users[text.actor]['name']), text)
        var.db.set('bot', 'volume', str(bot.volume_set))
        logging.info('bot: volume set to %d' % (bot.volume_set * 100))
    else:
        bot.send_msg(var.config.get(
            'strings', 'current_volume') % int(bot.volume_set * 100), text)


def cmd_ducking(bot, user, text, command, parameter):
    if parameter == "" or parameter == "on":
        bot.is_ducking = True
        bot.ducking_volume = var.config.getfloat("bot", "ducking_volume", fallback=0.05)
        bot.ducking_threshold = var.config.getint("bot", "ducking_threshold", fallback=5000)
        bot.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED,
                                          bot.ducking_sound_received)
        bot.mumble.set_receive_sound(True)
        logging.info('bot: ducking is on')
        msg = "Ducking on."
        bot.send_msg(msg, text)
    elif parameter == "off":
        bot.is_ducking = False
        bot.mumble.set_receive_sound(False)
        msg = "Ducking off."
        logging.info('bot: ducking is off')
        bot.send_msg(msg, text)


def cmd_ducking_threshold(bot, user, text, command, parameter):
    if parameter is not None and parameter.isdigit():
        bot.ducking_threshold = int(parameter)
        msg = "Ducking threshold set to %d." % bot.ducking_threshold
        bot.send_msg(msg, text)
    else:
        msg = "Current ducking threshold is %d." % bot.ducking_threshold
        bot.send_msg(msg, text)


def cmd_ducking_volume(bot, user, text, command, parameter):
    # The volume is a percentage
    if parameter is not None and parameter.isdigit() and 0 <= int(parameter) <= 100:
        bot.ducking_volume = float(float(parameter) / 100)
        bot.send_msg(var.config.get('strings', 'change_ducking_volume') % (
            int(bot.ducking_volume * 100), bot.mumble.users[text.actor]['name']), text)
        # var.db.set('bot', 'volume', str(bot.volume_set))
        logging.info('bot: volume on ducking set to %d' % (bot.ducking_volume * 100))
    else:
        bot.send_msg(var.config.get(
            'strings', 'current_ducking_volume') % int(bot.ducking_volume * 100), text)


def cmd_current_music(bot, user, text, command, parameter):
    reply = ""
    if len(var.playlist.playlist) > 0:
        reply = formatted_current_playing()
    else:
        reply = var.config.get('strings', 'not_playing')

    bot.send_msg(reply, text)


def cmd_skip(bot, user, text, command, parameter):
    if bot.next():  # Is no number send, just skip the current music
        bot.launch_music()
        bot.async_download_next()
    else:
        bot.send_msg(var.config.get(
            'strings', 'queue_empty'), text)


def cmd_remove(bot, user, text, command, parameter):
    # Allow to remove specific music into the queue with a number
    if parameter is not None and parameter.isdigit() and int(parameter) > 0 \
            and int(parameter) <= var.playlist.length():

        removed = var.playlist.remove(int(parameter) - 1)

        # the Title isn't here if the music wasn't downloaded
        bot.send_msg(var.config.get('strings', 'removing_item') % (
            removed['title'] if 'title' in removed else removed['url']), text)
    else:
        bot.send_msg(var.config.get('strings', 'wrong_parameter') % command)


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
            bot.send_msg(var.config.get('strings', 'no_file'), text)

    except re.error as e:
        msg = var.config.get('strings', 'wrong_pattern') % str(e)
        bot.send_msg(msg, text)


def cmd_queue(bot, user, text, command, parameter):
    if len(var.playlist.playlist) == 0:
        msg = var.config.get('strings', 'queue_empty')
        bot.send_msg(msg, text)
    else:
        msgs = [ var.config.get('strings', 'queue_contents') ]
        for i, value in enumerate(var.playlist.playlist):
            newline = '<b>{}</b> ({}) {}'.format(i + 1, value['type'],
                                                       value['title'] if 'title' in value else value['url'])
            msgs.append(newline)

        send_multi_lines(bot, msgs, text)
