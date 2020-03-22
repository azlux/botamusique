# coding=utf-8
import logging
import pymumble.pymumble_py3 as pymumble
import re

import constants
import media.system
import util
import variables as var
from librb import radiobrowser
from database import SettingsDatabase, MusicDatabase
from media.item import item_id_generators, dict_to_item, dicts_to_items
from media.cache import get_cached_wrapper_from_scrap, get_cached_wrapper_by_id, get_cached_wrappers_by_tags, \
    get_cached_wrapper
from media.url_from_playlist import get_playlist_info

log = logging.getLogger("bot")


def register_all_commands(bot):
    bot.register_command(constants.commands('joinme'), cmd_joinme, no_partial_match=False, access_outside_channel=True)
    bot.register_command(constants.commands('user_ban'), cmd_user_ban, no_partial_match=True)
    bot.register_command(constants.commands('user_unban'), cmd_user_unban, no_partial_match=True)
    bot.register_command(constants.commands('url_ban_list'), cmd_url_ban_list, no_partial_match=True)
    bot.register_command(constants.commands('url_ban'), cmd_url_ban, no_partial_match=True)
    bot.register_command(constants.commands('url_unban'), cmd_url_unban, no_partial_match=True)
    bot.register_command(constants.commands('play'), cmd_play)
    bot.register_command(constants.commands('pause'), cmd_pause)
    bot.register_command(constants.commands('play_file'), cmd_play_file)
    bot.register_command(constants.commands('play_file_match'), cmd_play_file_match)
    bot.register_command(constants.commands('play_url'), cmd_play_url)
    bot.register_command(constants.commands('play_playlist'), cmd_play_playlist)
    bot.register_command(constants.commands('play_radio'), cmd_play_radio)
    bot.register_command(constants.commands('play_tag'), cmd_play_tags)
    bot.register_command(constants.commands('rb_query'), cmd_rb_query)
    bot.register_command(constants.commands('rb_play'), cmd_rb_play)
    bot.register_command(constants.commands('yt_search'), cmd_yt_search)
    bot.register_command(constants.commands('yt_play'), cmd_yt_play)
    bot.register_command(constants.commands('help'), cmd_help, no_partial_match=False, access_outside_channel=True)
    bot.register_command(constants.commands('stop'), cmd_stop)
    bot.register_command(constants.commands('clear'), cmd_clear)
    bot.register_command(constants.commands('kill'), cmd_kill)
    bot.register_command(constants.commands('update'), cmd_update, no_partial_match=True)
    bot.register_command(constants.commands('stop_and_getout'), cmd_stop_and_getout)
    bot.register_command(constants.commands('volume'), cmd_volume)
    bot.register_command(constants.commands('ducking'), cmd_ducking)
    bot.register_command(constants.commands('ducking_threshold'), cmd_ducking_threshold)
    bot.register_command(constants.commands('ducking_volume'), cmd_ducking_volume)
    bot.register_command(constants.commands('current_music'), cmd_current_music)
    bot.register_command(constants.commands('skip'), cmd_skip)
    bot.register_command(constants.commands('last'), cmd_last)
    bot.register_command(constants.commands('remove'), cmd_remove)
    bot.register_command(constants.commands('list_file'), cmd_list_file)
    bot.register_command(constants.commands('queue'), cmd_queue)
    bot.register_command(constants.commands('random'), cmd_random)
    bot.register_command(constants.commands('repeat'), cmd_repeat)
    bot.register_command(constants.commands('mode'), cmd_mode)
    bot.register_command(constants.commands('add_tag'), cmd_add_tag)
    bot.register_command(constants.commands('remove_tag'), cmd_remove_tag)
    bot.register_command(constants.commands('find_tagged'), cmd_find_tagged)
    bot.register_command(constants.commands('search'), cmd_search_library)
    bot.register_command(constants.commands('add_from_shortlist'), cmd_shortlist)
    bot.register_command(constants.commands('delete_from_library'), cmd_delete_from_library)
    bot.register_command(constants.commands('drop_database'), cmd_drop_database, no_partial_match=True)
    bot.register_command(constants.commands('rescan'), cmd_refresh_cache, no_partial_match=True)

    # Just for debug use
    bot.register_command('rtrms', cmd_real_time_rms, True)
    bot.register_command('loop', cmd_loop_state, True)
    bot.register_command('item', cmd_item, True)


def send_multi_lines(bot, lines, text, linebreak="<br />"):
    global log

    msg = ""
    br = ""
    for newline in lines:
        msg += br
        br = linebreak
        if bot.mumble.get_max_message_length()\
                    and (len(msg) + len(newline)) > (bot.mumble.get_max_message_length() - 4):  # 4 == len("<br>")
            bot.send_msg(msg, text)
            msg = ""
        msg += newline

    bot.send_msg(msg, text)


# ---------------- Variables -----------------

song_shortlist = []


# ---------------- Commands ------------------

def cmd_joinme(bot, user, text, command, parameter):
    global log

    bot.mumble.users.myself.move_in(
        bot.mumble.users[text.actor]['channel_id'], token=parameter)


def cmd_user_ban(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.user_ban(parameter))
        else:
            bot.mumble.users[text.actor].send_text_message(util.get_user_ban())
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))
    return


def cmd_user_unban(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.user_unban(parameter))
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))
    return


def cmd_url_ban(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.url_ban(util.get_url_from_input(parameter)))

            id = item_id_generators['url'](url=parameter)
            var.cache.free_and_delete(id)
            var.playlist.remove_by_id(id)
        else:
            if var.playlist.current_item() and var.playlist.current_item().type == 'url':
                item = var.playlist.current_item().item()
                bot.mumble.users[text.actor].send_text_message(util.url_ban(util.get_url_from_input(item.url)))
                var.cache.free_and_delete(item.id)
                var.playlist.remove_by_id(item.id)
            else:
                bot.send_msg(constants.strings('bad_parameter', command=command))
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))
    return


def cmd_url_ban_list(bot, user, text, command, parameter):
    if bot.is_admin(user):
        bot.mumble.users[text.actor].send_text_message(util.get_url_ban())
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))
    return


def cmd_url_unban(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        if parameter:
            bot.mumble.users[text.actor].send_text_message(util.url_unban(util.get_url_from_input(parameter)))
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))
    return


def cmd_play(bot, user, text, command, parameter):
    global log

    if len(var.playlist) > 0:
        if parameter:
            if parameter.isdigit() and 1 <= int(parameter) <= len(var.playlist):
                # First "-1" transfer 12345 to 01234, second "-1"
                # point to the previous item. the loop will next to
                # the one you want
                var.playlist.point_to(int(parameter) - 1 - 1)

                if not bot.is_pause:
                    bot.interrupt()
                else:
                    bot.is_pause = False
            else:
                bot.send_msg(constants.strings('invalid_index', index=parameter), text)

        elif bot.is_pause:
            bot.resume()
        else:
            bot.send_msg(var.playlist.current_item().format_current_playing(), text)
    else:
        bot.is_pause = False
        bot.send_msg(constants.strings('queue_empty'), text)


def cmd_pause(bot, user, text, command, parameter):
    global log

    bot.pause()
    bot.send_msg(constants.strings('paused'))


def cmd_play_file(bot, user, text, command, parameter, do_not_refresh_cache=False):
    global log, song_shortlist

    # if parameter is {index}
    if parameter.isdigit():
        files = var.cache.files
        if int(parameter) < len(files):
            music_wrapper = get_cached_wrapper_by_id(bot, var.cache.file_id_lookup[files[int(parameter)]], user)
            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            bot.send_msg(constants.strings('file_added', item=music_wrapper.format_song_string()))
            return

    # if parameter is {path}
    else:
        # sanitize "../" and so on
        # path = os.path.abspath(os.path.join(var.music_folder, parameter))
        # if not path.startswith(os.path.abspath(var.music_folder)):
        #     bot.send_msg(constants.strings('no_file'), text)
        #     return

        if parameter in var.cache.files:
            music_wrapper = get_cached_wrapper_from_scrap(bot, type='file', path=parameter, user=user)
            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            bot.send_msg(constants.strings('file_added', item=music_wrapper.format_song_string()))
            return

        # if parameter is {folder}
        files = var.cache.dir.get_files(parameter)
        if files:
            folder = parameter
            if not folder.endswith('/'):
                folder += '/'

            msgs = [constants.strings('multiple_file_added')]
            count = 0

            for file in files:
                count += 1
                music_wrapper = get_cached_wrapper_by_id(bot, var.cache.file_id_lookup[folder + file], user)
                var.playlist.append(music_wrapper)
                log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
                msgs.append("{} ({})".format(music_wrapper.item().title, music_wrapper.item().path))

            if count != 0:
                send_multi_lines(bot, msgs, None)
                return

        else:
            # try to do a partial match
            files = var.cache.files
            matches = [file for file in files if parameter.lower() in file.lower()]
            if len(matches) == 1:
                file = matches[0]
                music_wrapper = get_cached_wrapper_by_id(bot, var.cache.file_id_lookup[file], user)
                var.playlist.append(music_wrapper)
                log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
                bot.send_msg(constants.strings('file_added', item=music_wrapper.format_song_string()))
                return
            elif len(matches) > 1:
                msgs = [constants.strings('multiple_matches')]
                song_shortlist = []
                for index, match in enumerate(matches):
                    id = var.cache.file_id_lookup[match]
                    music_dict = var.music_db.query_music_by_id(id)
                    item = dict_to_item(bot, music_dict)

                    song_shortlist.append(music_dict)

                    msgs.append("<b>{:d}</b> - <b>{:s}</b> ({:s})".format(
                        index + 1, item.title, match))
                send_multi_lines(bot, msgs, text)
                return

    if do_not_refresh_cache:
        bot.send_msg(constants.strings("no_file"), text)
    else:
        var.cache.build_dir_cache(bot)
        cmd_play_file(bot, user, text, command, parameter, do_not_refresh_cache=True)


def cmd_play_file_match(bot, user, text, command, parameter, do_not_refresh_cache=False):
    global log

    if parameter:
        files = var.cache.files
        msgs = [constants.strings('multiple_file_added') + "<ul>"]
        count = 0
        try:
            music_wrappers = []
            for file in files:
                match = re.search(parameter, file)
                if match and match[0]:
                    count += 1
                    music_wrapper = get_cached_wrapper_by_id(bot, var.cache.file_id_lookup[file], user)
                    music_wrappers.append(music_wrapper)
                    log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
                    msgs.append("<li><b>{}</b> ({})</li>".format(music_wrapper.item().title,
                                                                 file[:match.span()[0]]
                                                                 + "<b style='color:pink'>"
                                                                 + file[match.span()[0]: match.span()[1]]
                                                                 + "</b>"
                                                                 + file[match.span()[1]:]
                                                                 ))

            if count != 0:
                msgs.append("</ul>")
                var.playlist.extend(music_wrappers)
                send_multi_lines(bot, msgs, None, "")
            else:
                if do_not_refresh_cache:
                    bot.send_msg(constants.strings("no_file"), text)
                else:
                    var.cache.build_dir_cache(bot)
                    cmd_play_file_match(bot, user, text, command, parameter, do_not_refresh_cache=True)

        except re.error as e:
            msg = constants.strings('wrong_pattern', error=str(e))
            bot.send_msg(msg, text)
    else:
        bot.send_msg(constants.strings('bad_parameter', command=command))


def cmd_play_url(bot, user, text, command, parameter):
    global log

    url = util.get_url_from_input(parameter)
    if url:
        music_wrapper = get_cached_wrapper_from_scrap(bot, type='url', url=url, user=user)
        var.playlist.append(music_wrapper)

        log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
        bot.send_msg(constants.strings('file_added', item=music_wrapper.format_song_string()))
        if len(var.playlist) == 2:
            # If I am the second item on the playlist. (I am the next one!)
            bot.async_download_next()
    else:
        bot.send_msg(constants.strings('bad_parameter', command=command))


def cmd_play_playlist(bot, user, text, command, parameter):
    global log

    offset = 0  # if you want to start the playlist at a specific index
    try:
        offset = int(parameter.split(" ")[-1])
    except ValueError:
        pass

    url = util.get_url_from_input(parameter)
    log.debug("cmd: fetching media info from playlist url %s" % url)
    items = get_playlist_info(url=url, start_index=offset, user=user)
    if len(items) > 0:
        items = var.playlist.extend(list(map(
            lambda item: get_cached_wrapper_from_scrap(bot, **item), items)))
        for music in items:
            log.info("cmd: add to playlist: " + music.format_debug_string())
    else:
        bot.send_msg(constants.strings("playlist_fetching_failed"), text)


def cmd_play_radio(bot, user, text, command, parameter):
    global log

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
            music_wrapper = get_cached_wrapper_from_scrap(bot, type='radio', url=url, user=user)

            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            bot.send_msg(constants.strings('file_added', item=music_wrapper.format_song_string()))
        else:
            bot.send_msg(constants.strings('bad_url'))


def cmd_rb_query(bot, user, text, command, parameter):
    global log

    log.info('cmd: Querying radio stations')
    if not parameter:
        log.debug('rbquery without parameter')
        msg = constants.strings('rb_query_empty')
        bot.send_msg(msg, text)
    else:
        log.debug('cmd: Found query parameter: ' + parameter)
        # bot.send_msg('Searching for stations - this may take some seconds...', text)
        rb_stations = radiobrowser.getstations_byname(parameter)
        msg = constants.strings('rb_query_result')
        msg += '\n<table><tr><th>!rbplay ID</th><th>Station Name</th><th>Genre</th><th>Codec/Bitrate</th><th>Country</th></tr>'
        if not rb_stations:
            log.debug('cmd: No matches found for rbquery ' + parameter)
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
                log.debug('Result too long stage I')
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
                    log.debug('Result too long stage II')
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
    global log

    log.debug('cmd: Play a station by ID')
    if not parameter:
        log.debug('rbplay without parameter')
        msg = constants.strings('rb_play_empty')
        bot.send_msg(msg, text)
    else:
        log.debug('cmd: Retreiving url for station ID ' + parameter)
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
        log.debug('cmd: Added station to playlist %s' % stationname)
        bot.send_msg(msg, text)
        url = radiobrowser.geturl_byid(parameter)
        if url != "-1":
            log.info('cmd: Found url: ' + url)
            music_wrapper = get_cached_wrapper_from_scrap(bot, type='radio', url=url, name=stationname, user=user)
            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            bot.async_download_next()
        else:
            log.info('cmd: No playable url found.')
            msg += "No playable url found for this station, please try another station."
            bot.send_msg(msg, text)


yt_last_result = []
yt_last_page = 0  # TODO: if we keep adding global variables, we need to consider sealing all commands up into classes.


def cmd_yt_search(bot, user, text, command, parameter):
    global log, yt_last_result, yt_last_page, song_shortlist
    item_per_page = 5

    if parameter:
        # if next page
        if parameter.startswith("-n"):
            yt_last_page += 1
            if len(yt_last_result) > yt_last_page * item_per_page:
                song_shortlist = [{'type': 'url',
                                   'url': "https://www.youtube.com/watch?v=" + result[0],
                                   'title': result[1]
                                   } for result in yt_last_result[yt_last_page * item_per_page: item_per_page]]
                msg = _yt_format_result(yt_last_result, yt_last_page * item_per_page, item_per_page)
                bot.send_msg(constants.strings('yt_result', result_table=msg), text)
            else:
                bot.send_msg(constants.strings('yt_no_more'))

        # if query
        else:
            results = util.youtube_search(parameter)
            if results:
                yt_last_result = results
                yt_last_page = 0
                song_shortlist = [{'type': 'url', 'url': "https://www.youtube.com/watch?v=" + result[0]}
                                  for result in results[0: item_per_page]]
                msg = _yt_format_result(results, 0, item_per_page)
                bot.send_msg(constants.strings('yt_result', result_table=msg), text)
            else:
                bot.send_msg(constants.strings('yt_query_error'))
    else:
        bot.send_msg(constants.strings('bad_parameter', command=command), text)


def _yt_format_result(results, start, count):
    msg = '<table><tr><th width="10%">Index</th><th>Title</th><th width="20%">Uploader</th></tr>'
    for index, item in enumerate(results[start:start+count]):
        msg += '<tr><td>{index:d}</td><td>{title}</td><td>{uploader}</td></tr>'.format(
            index=index + 1, title=item[1], uploader=item[2])
    msg += '</table>'

    return msg


def cmd_yt_play(bot, user, text, command, parameter):
    global log, yt_last_result, yt_last_page

    if parameter:
        results = util.youtube_search(parameter)
        if results:
            yt_last_result = results
            yt_last_page = 0
            url = "https://www.youtube.com/watch?v=" + yt_last_result[0][0]
            cmd_play_url(bot, user, text, command, url)
        else:
            bot.send_msg(constants.strings('yt_query_error'))
    else:
        bot.send_msg(constants.strings('bad_parameter', command=command), text)


def cmd_help(bot, user, text, command, parameter):
    global log
    bot.send_msg(constants.strings('help'), text)
    if bot.is_admin(user):
        bot.send_msg(constants.strings('admin_help'), text)


def cmd_stop(bot, user, text, command, parameter):
    global log

    if var.config.getboolean("bot", "clear_when_stop_in_oneshot", fallback=False) \
            and var.playlist.mode == 'one-shot':
        cmd_clear(bot, user, text, command, parameter)
    else:
        bot.stop()
    bot.send_msg(constants.strings('stopped'), text)


def cmd_clear(bot, user, text, command, parameter):
    global log

    bot.clear()
    bot.send_msg(constants.strings('cleared'), text)


def cmd_kill(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        bot.pause()
        bot.exit = True
    else:
        bot.mumble.users[text.actor].send_text_message(
            constants.strings('not_admin'))


def cmd_update(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        bot.mumble.users[text.actor].send_text_message(
            constants.strings('start_updating'))
        msg = util.update(bot.version)
        bot.mumble.users[text.actor].send_text_message(msg)
    else:
        bot.mumble.users[text.actor].send_text_message(
            constants.strings('not_admin'))


def cmd_stop_and_getout(bot, user, text, command, parameter):
    global log

    bot.stop()
    if var.playlist.mode == "one-shot":
        var.playlist.clear()

    bot.join_channel()


def cmd_volume(bot, user, text, command, parameter):
    global log

    # The volume is a percentage
    if parameter and parameter.isdigit() and 0 <= int(parameter) <= 100:
        bot.volume_set = float(float(parameter) / 100)
        bot.send_msg(constants.strings('change_volume',
                     volume=int(bot.volume_set * 100), user=bot.mumble.users[text.actor]['name']))
        var.db.set('bot', 'volume', str(bot.volume_set))
        log.info('cmd: volume set to %d' % (bot.volume_set * 100))
    else:
        bot.send_msg(constants.strings('current_volume', volume=int(bot.volume_set * 100)), text)


def cmd_ducking(bot, user, text, command, parameter):
    global log

    if parameter == "" or parameter == "on":
        bot.is_ducking = True
        var.db.set('bot', 'ducking', True)
        bot.ducking_volume = var.config.getfloat("bot", "ducking_volume", fallback=0.05)
        bot.ducking_threshold = var.config.getint("bot", "ducking_threshold", fallback=5000)
        bot.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED,
                                          bot.ducking_sound_received)
        bot.mumble.set_receive_sound(True)
        log.info('cmd: ducking is on')
        msg = "Ducking on."
        bot.send_msg(msg, text)
    elif parameter == "off":
        bot.is_ducking = False
        bot.mumble.set_receive_sound(False)
        var.db.set('bot', 'ducking', False)
        msg = "Ducking off."
        log.info('cmd: ducking is off')
        bot.send_msg(msg, text)


def cmd_ducking_threshold(bot, user, text, command, parameter):
    global log

    if parameter and parameter.isdigit():
        bot.ducking_threshold = int(parameter)
        var.db.set('bot', 'ducking_threshold', str(bot.ducking_threshold))
        msg = "Ducking threshold set to %d." % bot.ducking_threshold
        bot.send_msg(msg, text)
    else:
        msg = "Current ducking threshold is %d." % bot.ducking_threshold
        bot.send_msg(msg, text)


def cmd_ducking_volume(bot, user, text, command, parameter):
    global log

    # The volume is a percentage
    if parameter and parameter.isdigit() and 0 <= int(parameter) <= 100:
        bot.ducking_volume = float(float(parameter) / 100)
        bot.send_msg(constants.strings('change_ducking_volume',
                     volume=int(bot.ducking_volume * 100), user=bot.mumble.users[text.actor]['name']), text)
        # var.db.set('bot', 'volume', str(bot.volume_set))
        var.db.set('bot', 'ducking_volume', str(bot.ducking_volume))
        log.info('cmd: volume on ducking set to %d' % (bot.ducking_volume * 100))
    else:
        bot.send_msg(constants.strings('current_ducking_volume', volume=int(bot.ducking_volume * 100)), text)


def cmd_current_music(bot, user, text, command, parameter):
    global log

    if len(var.playlist) > 0:
        bot.send_msg(var.playlist.current_item().format_current_playing(), text)
    else:
        bot.send_msg(constants.strings('not_playing'), text)


def cmd_skip(bot, user, text, command, parameter):
    global log

    bot.interrupt()

    if len(var.playlist) == 0:
        bot.send_msg(constants.strings('queue_empty'), text)


def cmd_last(bot, user, text, command, parameter):
    global log

    if len(var.playlist) > 0:
        bot.interrupt()
        var.playlist.point_to(len(var.playlist) - 1 - 1)
    else:
        bot.send_msg(constants.strings('queue_empty'), text)


def cmd_remove(bot, user, text, command, parameter):
    global log

    # Allow to remove specific music into the queue with a number
    if parameter and parameter.isdigit() and 0 < int(parameter) <= len(var.playlist):

        index = int(parameter) - 1

        if index == var.playlist.current_index:
            removed = var.playlist[index]
            bot.send_msg(constants.strings('removing_item',
                                           item=removed.format_short_string()), text)
            log.info("cmd: delete from playlist: " + removed.format_debug_string())

            var.playlist.remove(index)

            if index < len(var.playlist):
                if not bot.is_pause:
                    bot.interrupt()
                    var.playlist.current_index -= 1
                    # then the bot will move to next item

            else:  # if item deleted is the last item of the queue
                var.playlist.current_index -= 1
                if not bot.is_pause:
                    bot.interrupt()
        else:
            var.playlist.remove(index)

    else:
        bot.send_msg(constants.strings('bad_parameter', command=command), text)


def cmd_list_file(bot, user, text, command, parameter):
    global log

    files = var.cache.files
    msgs = [constants.strings("multiple_file_found")]
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
    global log

    if len(var.playlist) == 0:
        msg = constants.strings('queue_empty')
        bot.send_msg(msg, text)
    else:
        msgs = [constants.strings('queue_contents')]
        for i, music in enumerate(var.playlist):
            tags = ''
            if len(music.item().tags) > 0:
                tags = "<sup>{}</sup>".format(", ".join(music.item().tags))
            if i == var.playlist.current_index:
                newline = "<b style='color:orange'>{} ({}) {} </b> {}".format(i + 1, music.display_type(),
                                                                              music.format_short_string(), tags)
            else:
                newline = '<b>{}</b> ({}) {} {}'.format(i + 1, music.display_type(),
                                                        music.format_short_string(), tags)

            msgs.append(newline)

        send_multi_lines(bot, msgs, text)


def cmd_random(bot, user, text, command, parameter):
    global log

    bot.interrupt()
    var.playlist.randomize()


def cmd_repeat(bot, user, text, command, parameter):
    global log

    repeat = 1
    if parameter and parameter.isdigit():
        repeat = int(parameter)

    music = var.playlist.current_item()
    for _ in range(repeat):
        var.playlist.insert(
            var.playlist.current_index + 1,
            music
        )
        log.info("bot: add to playlist: " + music.format_debug_string())

    bot.send_msg(constants.strings("repeat", song=music.format_song_string(), n=str(repeat)), text)


def cmd_mode(bot, user, text, command, parameter):
    global log

    if not parameter:
        bot.send_msg(constants.strings("current_mode", mode=var.playlist.mode), text)
        return
    if parameter not in ["one-shot", "repeat", "random", "autoplay"]:
        bot.send_msg(constants.strings('unknown_mode', mode=parameter), text)
    else:
        var.db.set('playlist', 'playback_mode', parameter)
        var.playlist = media.playlist.get_playlist(parameter, var.playlist)
        log.info("command: playback mode changed to %s." % parameter)
        bot.send_msg(constants.strings("change_mode", mode=var.playlist.mode,
                                       user=bot.mumble.users[text.actor]['name']), text)
        if parameter == "random":
            bot.interrupt()
            bot.launch_music()


def cmd_play_tags(bot, user, text, command, parameter):
    if not parameter:
        bot.send_msg(constants.strings('bad_parameter', command=command), text)
        return

    msgs = [constants.strings('multiple_file_added') + "<ul>"]
    count = 0

    tags = parameter.split(",")
    tags = list(map(lambda t: t.strip(), tags))
    music_wrappers = get_cached_wrappers_by_tags(bot, tags, user)
    for music_wrapper in music_wrappers:
        count += 1
        log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
        msgs.append("<li><b>{}</b> (<i>{}</i>)</li>".format(music_wrapper.item().title, ", ".join(music_wrapper.item().tags)))

    if count != 0:
        msgs.append("</ul>")
        var.playlist.extend(music_wrappers)
        send_multi_lines(bot, msgs, None, "")
    else:
        bot.send_msg(constants.strings("no_file"), text)


def cmd_add_tag(bot, user, text, command, parameter):
    global log

    params = parameter.split()
    if len(params) == 2:
        index = params[0]
        tags = list(map(lambda t: t.strip(), params[1].split(",")))
    elif len(params) == 1:
        index = str(var.playlist.current_index + 1)
        tags = list(map(lambda t: t.strip(), params[0].split(",")))
    else:
        bot.send_msg(constants.strings('bad_parameter', command=command), text)
        return

    if tags[0]:
        if index.isdigit() and 1 <= int(index) <= len(var.playlist):
            var.playlist[int(index) - 1].add_tags(tags)
            log.info("cmd: add tags %s to song %s" % (", ".join(tags),
                                                      var.playlist[int(index) - 1].format_debug_string()))
            bot.send_msg(constants.strings("added_tags",
                                           tags=", ".join(tags),
                                           song=var.playlist[int(index) - 1].format_short_string()), text)
            return

        elif index == "*":
            for item in var.playlist:
                item.add_tags(tags)
                log.info("cmd: add tags %s to song %s" % (", ".join(tags),
                                                          item.format_debug_string()))
            bot.send_msg(constants.strings("added_tags_to_all", tags=", ".join(tags)), text)
            return

    bot.send_msg(constants.strings('bad_parameter', command=command), text)


def cmd_remove_tag(bot, user, text, command, parameter):
    global log

    params = parameter.split()

    if len(params) == 2:
        index = params[0]
        tags = list(map(lambda t: t.strip(), params[1].split(",")))
    elif len(params) == 1:
        index = str(var.playlist.current_index + 1)
        tags = list(map(lambda t: t.strip(), params[0].split(",")))
    else:
        bot.send_msg(constants.strings('bad_parameter', command=command), text)
        return

    if tags[0]:
        if index.isdigit() and 1 <= int(index) <= len(var.playlist):
            if tags[0] != "*":
                var.playlist[int(index) - 1].remove_tags(tags)
                log.info("cmd: remove tags %s from song %s" % (", ".join(tags),
                                                               var.playlist[int(index) - 1].format_debug_string()))
                bot.send_msg(constants.strings("removed_tags",
                                               tags=", ".join(tags),
                                               song=var.playlist[int(index) - 1].format_short_string()), text)
                return
            else:
                var.playlist[int(index) - 1].clear_tags()
                log.info("cmd: clear tags from song %s" % (var.playlist[int(index) - 1].format_debug_string()))
                bot.send_msg(constants.strings("cleared_tags",
                                               song=var.playlist[int(index) - 1].format_short_string()), text)
                return

        elif index == "*":
            if tags[0] != "*":
                for item in var.playlist:
                    item.remove_tags(tags)
                    log.info("cmd: remove tags %s from song %s" % (", ".join(tags),
                                                                   item.format_debug_string()))
                bot.send_msg(constants.strings("removed_tags_from_all", tags=", ".join(tags)), text)
                return
            else:
                for item in var.playlist:
                    item.clear_tags()
                    log.info("cmd: clear tags from song %s" % (item.format_debug_string()))
                bot.send_msg(constants.strings("cleared_tags_from_all"), text)
                return

    bot.send_msg(constants.strings('bad_parameter', command=command), text)


def cmd_find_tagged(bot, user, text, command, parameter):
    global song_shortlist

    if not parameter:
        bot.send_msg(constants.strings('bad_parameter', command=command), text)
        return

    msgs = [constants.strings('multiple_file_found') + "<ul>"]
    count = 0

    tags = parameter.split(",")
    tags = list(map(lambda t: t.strip(), tags))

    music_dicts = var.music_db.query_music_by_tags(tags)
    song_shortlist = music_dicts
    items = dicts_to_items(bot, music_dicts)

    for i, item in enumerate(items):
        count += 1
        msgs.append("<li><b>{:d}</b> - <b>{}</b> (<i>{}</i>)</li>".format(i+1, item.title, ", ".join(item.tags)))

    if count != 0:
        msgs.append("</ul>")
        msgs.append(constants.strings("shortlist_instruction"))
        send_multi_lines(bot, msgs, text, "")
    else:
        bot.send_msg(constants.strings("no_file"), text)


def cmd_search_library(bot, user, text, command, parameter):
    global song_shortlist
    if not parameter:
        bot.send_msg(constants.strings('bad_parameter', command=command), text)
        return

    msgs = [constants.strings('multiple_file_found') + "<ul>"]
    count = 0

    _keywords = parameter.split(" ")
    keywords = []
    for kw in _keywords:
        if kw:
            keywords.append(kw)

    music_dicts = var.music_db.query_music_by_keywords(keywords)
    if music_dicts:
        items = dicts_to_items(bot, music_dicts)
        song_shortlist = music_dicts

        if len(items) == 1:
            music_wrapper = get_cached_wrapper(items[0], user)
            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            bot.send_msg(constants.strings('file_added', item=music_wrapper.format_song_string()))
        else:
            for item in items:
                count += 1
                if len(item.tags) > 0:
                    msgs.append("<li><b>{:d}</b> - [{}] <b>{}</b> (<i>{}</i>)</li>".format(count, item.display_type(), item.title, ", ".join(item.tags)))
                else:
                    msgs.append("<li><b>{:d}</b> - [{}] <b>{}</b> </li>".format(count, item.display_type(), item.title, ", ".join(item.tags)))

            if count != 0:
                msgs.append("</ul>")
                msgs.append(constants.strings("shortlist_instruction"))
                send_multi_lines(bot, msgs, text, "")
            else:
                bot.send_msg(constants.strings("no_file"), text)
    else:
        bot.send_msg(constants.strings("no_file"), text)


def cmd_shortlist(bot, user, text, command, parameter):
    global song_shortlist, log
    try:
        indexes = [int(i) for i in parameter.split(" ")]
    except ValueError:
        bot.send_msg(constants.strings('bad_parameter', command=command), text)
        return

    if len(indexes) > 1:
        msgs = [constants.strings('multiple_file_added') + "<ul>"]
        for index in indexes:
            if 1 <= index <= len(song_shortlist):
                kwargs = song_shortlist[index - 1]
                kwargs['user'] = user
                music_wrapper = get_cached_wrapper_from_scrap(bot, **kwargs)
                var.playlist.append(music_wrapper)
                log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
                msgs.append("<li>[{}] <b>{}</b></li>".format(music_wrapper.item().type, music_wrapper.item().title))
            else:
                bot.send_msg(constants.strings('bad_parameter', command=command), text)
                return

        msgs.append("</ul>")
        send_multi_lines(bot, msgs, None, "")
        return
    elif len(indexes) == 1:
        index = indexes[0]
        if 1 <= index <= len(song_shortlist):
            kwargs = song_shortlist[index - 1]
            kwargs['user'] = user
            music_wrapper = get_cached_wrapper_from_scrap(bot, **kwargs)
            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            bot.send_msg(constants.strings('file_added', item=music_wrapper.format_song_string()))
            return

    bot.send_msg(constants.strings('bad_parameter', command=command), text)


def cmd_delete_from_library(bot, user, text, command, parameter):
    global song_shortlist, log
    try:
        indexes = [int(i) for i in parameter.split(" ")]
    except ValueError:
        bot.send_msg(constants.strings('bad_parameter', command=command), text)
        return

    if len(indexes) > 1:
        msgs = [constants.strings('multiple_file_added') + "<ul>"]
        count = 0
        for index in indexes:
            if 1 <= index <= len(song_shortlist):
                music_dict = song_shortlist[index - 1]
                if 'id' in music_dict:
                    music_wrapper = get_cached_wrapper_by_id(bot, music_dict['id'], user)
                    log.info("cmd: remove from library: " + music_wrapper.format_debug_string())
                    msgs.append("<li>[{}] <b>{}</b></li>".format(music_wrapper.item().type, music_wrapper.item().title))
                    var.playlist.remove_by_id(music_dict['id'])
                    var.cache.free_and_delete(music_dict['id'])
                    count += 1
            else:
                bot.send_msg(constants.strings('bad_parameter', command=command), text)
                return

        if count == 0:
            bot.send_msg(constants.strings('bad_parameter', command=command), text)
            return

        msgs.append("</ul>")
        send_multi_lines(bot, msgs, None, "")
        return
    elif len(indexes) == 1:
        index = indexes[0]
        if 1 <= index <= len(song_shortlist):
            music_dict = song_shortlist[index - 1]
            if 'id' in music_dict:
                music_wrapper = get_cached_wrapper_by_id(bot, music_dict['id'], user)
                bot.send_msg(constants.strings('file_deleted', item=music_wrapper.format_song_string()), text)
                log.info("cmd: remove from library: " + music_wrapper.format_debug_string())
                var.playlist.remove_by_id(music_dict['id'])
                var.cache.free_and_delete(music_dict['id'])
                return

    bot.send_msg(constants.strings('bad_parameter', command=command), text)


def cmd_drop_database(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        var.db.drop_table()
        var.db = SettingsDatabase(var.dbfile)
        var.music_db.drop_table()
        var.music_db = MusicDatabase(var.dbfile)
        log.info("command: database dropped.")
        bot.send_msg(constants.strings('database_dropped'), text)
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))


def cmd_refresh_cache(bot, user, text, command, parameter):
    global log
    if bot.is_admin(user):
        var.cache.build_dir_cache(bot)
        log.info("command: Local file cache refreshed.")
        bot.send_msg(constants.strings('cache_refreshed'), text)
    else:
        bot.mumble.users[text.actor].send_text_message(constants.strings('not_admin'))


# Just for debug use
def cmd_real_time_rms(bot, user, text, command, parameter):
    bot._display_rms = not bot._display_rms


def cmd_loop_state(bot, user, text, command, parameter):
    print(bot._loop_status)


def cmd_item(bot, user, text, command, parameter):
    print(bot.wait_for_downloading)
    print(var.playlist.current_item().to_dict())
