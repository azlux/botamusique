# coding=utf-8
import logging
import secrets
import datetime
import json
import re
import pymumble_py3 as pymumble

from constants import tr_cli as tr
from constants import commands
import interface
import util
import variables as var
from pyradios import RadioBrowser
from database import SettingsDatabase, MusicDatabase, Condition
import media.playlist
from media.item import item_id_generators, dict_to_item, dicts_to_items, ValidationFailedError
from media.cache import get_cached_wrapper_from_scrap, get_cached_wrapper_by_id, get_cached_wrappers_by_tags, \
    get_cached_wrapper, get_cached_wrappers, get_cached_wrapper_from_dict, get_cached_wrappers_from_dicts
from media.url_from_playlist import get_playlist_info

log = logging.getLogger("bot")


def register_all_commands(bot):
    bot.register_command(commands('add_from_shortlist'), cmd_shortlist)
    bot.register_command(commands('add_tag'), cmd_add_tag)
    bot.register_command(commands('change_user_password'), cmd_user_password, no_partial_match=True)
    bot.register_command(commands('clear'), cmd_clear)
    bot.register_command(commands('current_music'), cmd_current_music)
    bot.register_command(commands('delete_from_library'), cmd_delete_from_library)
    bot.register_command(commands('ducking'), cmd_ducking)
    bot.register_command(commands('ducking_threshold'), cmd_ducking_threshold)
    bot.register_command(commands('ducking_volume'), cmd_ducking_volume)
    bot.register_command(commands('find_tagged'), cmd_find_tagged)
    bot.register_command(commands('help'), cmd_help, no_partial_match=False, access_outside_channel=True)
    bot.register_command(commands('joinme'), cmd_joinme, access_outside_channel=True)
    bot.register_command(commands('last'), cmd_last)
    bot.register_command(commands('list_file'), cmd_list_file)
    bot.register_command(commands('mode'), cmd_mode)
    bot.register_command(commands('pause'), cmd_pause)
    bot.register_command(commands('play'), cmd_play)
    bot.register_command(commands('play_file'), cmd_play_file)
    bot.register_command(commands('play_file_match'), cmd_play_file_match)
    bot.register_command(commands('play_playlist'), cmd_play_playlist)
    bot.register_command(commands('play_radio'), cmd_play_radio)
    bot.register_command(commands('play_tag'), cmd_play_tags)
    bot.register_command(commands('play_url'), cmd_play_url)
    bot.register_command(commands('queue'), cmd_queue)
    bot.register_command(commands('random'), cmd_random)
    bot.register_command(commands('rb_play'), cmd_rb_play)
    bot.register_command(commands('rb_query'), cmd_rb_query)
    bot.register_command(commands('remove'), cmd_remove)
    bot.register_command(commands('remove_tag'), cmd_remove_tag)
    bot.register_command(commands('repeat'), cmd_repeat)
    bot.register_command(commands('requests_webinterface_access'), cmd_web_access)
    bot.register_command(commands('rescan'), cmd_refresh_cache, no_partial_match=True)
    bot.register_command(commands('search'), cmd_search_library)
    bot.register_command(commands('skip'), cmd_skip)
    bot.register_command(commands('stop'), cmd_stop)
    bot.register_command(commands('stop_and_getout'), cmd_stop_and_getout)
    bot.register_command(commands('version'), cmd_version, no_partial_match=True)
    bot.register_command(commands('volume'), cmd_volume)
    bot.register_command(commands('yt_play'), cmd_yt_play)
    bot.register_command(commands('yt_search'), cmd_yt_search)

    # admin command
    bot.register_command(commands('add_webinterface_user'), cmd_web_user_add, admin=True)
    bot.register_command(commands('drop_database'), cmd_drop_database, no_partial_match=True, admin=True)
    bot.register_command(commands('kill'), cmd_kill, admin=True)
    bot.register_command(commands('list_webinterface_user'), cmd_web_user_list, admin=True)
    bot.register_command(commands('remove_webinterface_user'), cmd_web_user_remove, admin=True)
    bot.register_command(commands('max_volume'), cmd_max_volume, admin=True)
    bot.register_command(commands('update'), cmd_update, no_partial_match=True, admin=True)
    bot.register_command(commands('url_ban'), cmd_url_ban, no_partial_match=True, admin=True)
    bot.register_command(commands('url_ban_list'), cmd_url_ban_list, no_partial_match=True, admin=True)
    bot.register_command(commands('url_unban'), cmd_url_unban, no_partial_match=True, admin=True)
    bot.register_command(commands('url_unwhitelist'), cmd_url_unwhitelist, no_partial_match=True, admin=True)
    bot.register_command(commands('url_whitelist'), cmd_url_whitelist, no_partial_match=True, admin=True)
    bot.register_command(commands('url_whitelist_list'), cmd_url_whitelist_list, no_partial_match=True, admin=True)
    bot.register_command(commands('user_ban'), cmd_user_ban, no_partial_match=True, admin=True)
    bot.register_command(commands('user_unban'), cmd_user_unban, no_partial_match=True, admin=True)

    # Just for debug use
    bot.register_command('rtrms', cmd_real_time_rms, True)
    # bot.register_command('loop', cmd_loop_state, True)
    # bot.register_command('item', cmd_item, True)


def send_multi_lines(bot, lines, text, linebreak="<br />"):
    global log

    msg = ""
    br = ""
    for newline in lines:
        msg += br
        br = linebreak
        if bot.mumble.get_max_message_length() \
                and (len(msg) + len(newline)) > (bot.mumble.get_max_message_length() - 4):  # 4 == len("<br>")
            bot.send_msg(msg, text)
            msg = ""
        msg += newline

    bot.send_msg(msg, text)


def send_multi_lines_in_channel(bot, lines, linebreak="<br />"):
    global log

    msg = ""
    br = ""
    for newline in lines:
        msg += br
        br = linebreak
        if bot.mumble.get_max_message_length() \
                and (len(msg) + len(newline)) > (bot.mumble.get_max_message_length() - 4):  # 4 == len("<br>")
            bot.send_channel_msg(msg)
            msg = ""
        msg += newline

    bot.send_channel_msg(msg)


def send_item_added_message(bot, wrapper, index, text):
    if index == var.playlist.current_index + 1:
        bot.send_msg(tr('file_added', item=wrapper.format_song_string()) +
                     tr('position_in_the_queue', position=tr('next_to_play')), text)
    elif index == len(var.playlist) - 1:
        bot.send_msg(tr('file_added', item=wrapper.format_song_string()) +
                     tr('position_in_the_queue', position=tr('last_song_on_the_queue')), text)
    else:
        bot.send_msg(tr('file_added', item=wrapper.format_song_string()) +
                     tr('position_in_the_queue', position=f"{index + 1}/{len(var.playlist)}."), text)


# ---------------- Variables -----------------

ITEMS_PER_PAGE = 50

song_shortlist = []


# ---------------- Commands ------------------

def cmd_joinme(bot, user, text, command, parameter):
    global log

    bot.mumble.users.myself.move_in(
        bot.mumble.users[text.actor]['channel_id'], token=parameter)


def cmd_user_ban(bot, user, text, command, parameter):
    global log

    if parameter:
        var.db.set("user_ban", parameter, None)
        bot.send_msg(tr("user_ban_success", user=parameter), text)
    else:
        ban_list = "<ul>"
        for i in var.db.items("url_ban"):
            ban_list += "<li>" + i[0] + "</li>"
        ban_list += "</ul>"
        bot.send_msg(tr("user_ban_list", list=ban_list), text)


def cmd_user_unban(bot, user, text, command, parameter):
    global log

    if parameter and var.db.has_option("user_ban", parameter):
        var.db.remove_option("user_ban", parameter)
        bot.send_msg(tr("user_unban_success", user=parameter), text)


def cmd_url_ban(bot, user, text, command, parameter):
    global log

    url = util.get_url_from_input(parameter)
    if url:
        _id = item_id_generators['url'](url=url)
        var.cache.free_and_delete(_id)
        var.playlist.remove_by_id(_id)
    else:
        if var.playlist.current_item() and var.playlist.current_item().type == 'url':
            item = var.playlist.current_item().item()
            url = item.url
            var.cache.free_and_delete(item.id)
            var.playlist.remove_by_id(item.id)
        else:
            bot.send_msg(tr('bad_parameter', command=command), text)
            return

    # Remove from the whitelist first
    if var.db.has_option('url_whitelist', url):
        var.db.remove_option("url_whitelist", url)
        bot.send_msg(tr("url_unwhitelist_success", url=url), text)

    if not var.db.has_option('url_ban', url):
        var.db.set("url_ban", url, None)
    bot.send_msg(tr("url_ban_success", url=url), text)


def cmd_url_ban_list(bot, user, text, command, parameter):
    ban_list = "<ul>"
    for i in var.db.items("url_ban"):
        ban_list += "<li>" + i[0] + "</li>"
    ban_list += "</ul>"

    bot.send_msg(tr("url_ban_list", list=ban_list), text)


def cmd_url_unban(bot, user, text, command, parameter):
    url = util.get_url_from_input(parameter)
    if url:
        var.db.remove_option("url_ban", url)
        bot.send_msg(tr("url_unban_success", url=url), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_url_whitelist(bot, user, text, command, parameter):
    url = util.get_url_from_input(parameter)
    if url:
        # Unban first
        if var.db.has_option('url_ban', url):
            var.db.remove_option("url_ban", url)
            bot.send_msg(tr("url_unban_success"), text)

        # Then add to whitelist
        if not var.db.has_option('url_whitelist', url):
            var.db.set("url_whitelist", url, None)
        bot.send_msg(tr("url_whitelist_success", url=url), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_url_whitelist_list(bot, user, text, command, parameter):
    ban_list = "<ul>"
    for i in var.db.items("url_whitelist"):
        ban_list += "<li>" + i[0] + "</li>"
    ban_list += "</ul>"

    bot.send_msg(tr("url_whitelist_list", list=ban_list), text)


def cmd_url_unwhitelist(bot, user, text, command, parameter):
    url = util.get_url_from_input(parameter)
    if url:
        var.db.remove_option("url_whitelist", url)
        bot.send_msg(tr("url_unwhitelist_success"), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_play(bot, user, text, command, parameter):
    global log

    params = parameter.split()
    index = -1
    start_at = 0
    if len(params) > 0:
        if params[0].isdigit() and 1 <= int(params[0]) <= len(var.playlist):
            index = int(params[0])
        else:
            bot.send_msg(tr('invalid_index', index=parameter), text)
            return

        if len(params) > 1:
            try:
                start_at = util.parse_time(params[1])
            except ValueError:
                bot.send_msg(tr('bad_parameter', command=command), text)
                return

    if len(var.playlist) > 0:
        if index != -1:
            bot.play(int(index) - 1, start_at)

        elif bot.is_pause:
            bot.resume()
        else:
            bot.send_msg(var.playlist.current_item().format_current_playing(), text)
    else:
        bot.is_pause = False
        bot.send_msg(tr('queue_empty'), text)


def cmd_pause(bot, user, text, command, parameter):
    global log

    bot.pause()
    bot.send_channel_msg(tr('paused'))


def cmd_play_file(bot, user, text, command, parameter, do_not_refresh_cache=False):
    global log, song_shortlist

    # assume parameter is a path
    music_wrappers = get_cached_wrappers_from_dicts(var.music_db.query_music(Condition().and_equal('path', parameter)), user)
    if music_wrappers:
        var.playlist.append(music_wrappers[0])
        log.info("cmd: add to playlist: " + music_wrappers[0].format_debug_string())
        send_item_added_message(bot, music_wrappers[0], len(var.playlist) - 1, text)
        return

    # assume parameter is a folder
    music_wrappers = get_cached_wrappers_from_dicts(var.music_db.query_music(Condition()
                                                                             .and_equal('type', 'file')
                                                                             .and_like('path', parameter + '%')), user)
    if music_wrappers:
        msgs = [tr('multiple_file_added')]

        for music_wrapper in music_wrappers:
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            msgs.append("<b>{:s}</b> ({:s})".format(music_wrapper.item().title, music_wrapper.item().path))

        var.playlist.extend(music_wrappers)

        send_multi_lines_in_channel(bot, msgs)
        return

    # try to do a partial match
    matches = var.music_db.query_music(Condition()
                                       .and_equal('type', 'file')
                                       .and_like('path', '%' + parameter + '%', case_sensitive=False))
    if len(matches) == 1:
        music_wrapper = get_cached_wrapper_from_dict(matches[0], user)
        var.playlist.append(music_wrapper)
        log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
        send_item_added_message(bot, music_wrapper, len(var.playlist) - 1, text)
        return
    elif len(matches) > 1:
        song_shortlist = matches
        msgs = [tr('multiple_matches')]
        for index, match in enumerate(matches):
            msgs.append("<b>{:d}</b> - <b>{:s}</b> ({:s})".format(
                index + 1, match['title'], match['path']))
        msgs.append(tr("shortlist_instruction"))
        send_multi_lines(bot, msgs, text)
        return

    if do_not_refresh_cache:
        bot.send_msg(tr("no_file"), text)
    else:
        var.cache.build_dir_cache()
        cmd_play_file(bot, user, text, command, parameter, do_not_refresh_cache=True)


def cmd_play_file_match(bot, user, text, command, parameter, do_not_refresh_cache=False):
    global log

    if parameter:
        file_dicts = var.music_db.query_music(Condition().and_equal('type', 'file'))
        msgs = [tr('multiple_file_added') + "<ul>"]
        try:
            count = 0
            music_wrappers = []
            for file_dict in file_dicts:
                file = file_dict['title']
                match = re.search(parameter, file)
                if match and match[0]:
                    count += 1
                    music_wrapper = get_cached_wrapper(dict_to_item(file_dict), user)
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
                send_multi_lines_in_channel(bot, msgs, "")
            else:
                if do_not_refresh_cache:
                    bot.send_msg(tr("no_file"), text)
                else:
                    var.cache.build_dir_cache()
                    cmd_play_file_match(bot, user, text, command, parameter, do_not_refresh_cache=True)

        except re.error as e:
            msg = tr('wrong_pattern', error=str(e))
            bot.send_msg(msg, text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_play_url(bot, user, text, command, parameter):
    global log

    url = util.get_url_from_input(parameter)
    if url:
        music_wrapper = get_cached_wrapper_from_scrap(type='url', url=url, user=user)
        var.playlist.append(music_wrapper)

        log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
        send_item_added_message(bot, music_wrapper, len(var.playlist) - 1, text)

        if len(var.playlist) == 2:
            # If I am the second item on the playlist. (I am the next one!)
            bot.async_download_next()
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_play_playlist(bot, user, text, command, parameter):
    global log

    offset = 0  # if you want to start the playlist at a specific index
    try:
        offset = int(parameter.split(" ")[-1])
    except ValueError:
        pass

    url = util.get_url_from_input(parameter)
    if url:
        log.debug(f"cmd: fetching media info from playlist url {url}")
        items = get_playlist_info(url=url, start_index=offset, user=user)
        if len(items) > 0:
            items = var.playlist.extend(list(map(lambda item: get_cached_wrapper_from_scrap(**item), items)))
            for music in items:
                log.info("cmd: add to playlist: " + music.format_debug_string())
        else:
            bot.send_msg(tr("playlist_fetching_failed"), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_play_radio(bot, user, text, command, parameter):
    global log

    if not parameter:
        all_radio = var.config.items('radio')
        msg = tr('preconfigurated_radio')
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
            music_wrapper = get_cached_wrapper_from_scrap(type='radio', url=url, user=user)

            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            send_item_added_message(bot, music_wrapper, len(var.playlist) - 1, text)
        else:
            bot.send_msg(tr('bad_url'), text)


def cmd_rb_query(bot, user, text, command, parameter):
    global log

    log.info('cmd: Querying radio stations')
    if not parameter:
        log.debug('rbquery without parameter')
        msg = tr('rb_query_empty')
        bot.send_msg(msg, text)
    else:
        log.debug('cmd: Found query parameter: ' + parameter)
        rb = RadioBrowser()
        rb_stations = rb.search(name=parameter, name_exact=False)
        msg = tr('rb_query_result')
        msg += '\n<table><tr><th>!rbplay ID</th><th>Station Name</th><th>Genre</th><th>Codec/Bitrate</th><th>Country</th></tr>'
        if not rb_stations:
            log.debug(f"cmd: No matches found for rbquery {parameter}")
            bot.send_msg(f"Radio-Browser found no matches for {parameter}", text)
        else:
            for s in rb_stations:
                station_id = s['stationuuid']
                station_name = s['name']
                country = s['countrycode']
                codec = s['codec']
                bitrate = s['bitrate']
                genre = s['tags']
                msg += f"<tr><td>{station_id}</td><td>{station_name}</td><td>{genre}</td><td>{codec}/{bitrate}</td><td>{country}</td></tr>"
            msg += '</table>'
            # Full message as html table
            if len(msg) <= 5000:
                bot.send_msg(msg, text)
            # Shorten message if message too long (stage I)
            else:
                log.debug('Result too long stage I')
                msg = tr('rb_query_result') + ' (shortened L1)'
                msg += '\n<table><tr><th>!rbplay ID</th><th>Station Name</th></tr>'
                for s in rb_stations:
                    station_id = s['stationuuid']
                    station_name = s['name']
                    msg += f'<tr><td>{station_id}</td><td>{station_name}</td>'
                msg += '</table>'
                if len(msg) <= 5000:
                    bot.send_msg(msg, text)
                # Shorten message if message too long (stage II)
                else:
                    log.debug('Result too long stage II')
                    msg = tr('rb_query_result') + ' (shortened L2)'
                    msg += '!rbplay ID - Station Name'
                    for s in rb_stations:
                        station_id = s['stationuuid']
                        station_name = s['name'][:12]
                        msg += f'{station_id} - {station_name}'
                    if len(msg) <= 5000:
                        bot.send_msg(msg, text)
                    # Message still too long
                    else:
                        bot.send_msg('Query result too long to post (> 5000 characters), please try another query.', text)


def cmd_rb_play(bot, user, text, command, parameter):
    global log

    log.debug('cmd: Play a station by ID')
    if not parameter:
        log.debug('rbplay without parameter')
        msg = tr('rb_play_empty')
        bot.send_msg(msg, text)
    else:
        log.debug('cmd: Retreiving url for station ID ' + parameter)
        rb = RadioBrowser()
        rstation = rb.station_by_uuid(parameter)
        stationname = rstation[0]['name']
        country = rstation[0]['countrycode']
        codec = rstation[0]['codec']
        bitrate = rstation[0]['bitrate']
        genre = rstation[0]['tags']
        homepage = rstation[0]['homepage']
        url = rstation[0]['url']
        msg = 'Radio station added to playlist:'

        msg += '<table><tr><th>ID</th><th>Station Name</th><th>Genre</th><th>Codec/Bitrate</th><th>Country</th><th>Homepage</th></tr>' + \
               f"<tr><td>{parameter}</td><td>{stationname}</td><td>{genre}</td><td>{codec}/{bitrate}</td><td>{country}</td><td>{homepage}</td></tr></table>"
        log.debug(f'cmd: Added station to playlist {stationname}')
        bot.send_msg(msg, text)
        if url != "-1":
            log.info('cmd: Found url: ' + url)
            music_wrapper = get_cached_wrapper_from_scrap(type='radio', url=url, name=stationname, user=user)
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
                                   } for result in yt_last_result[yt_last_page * item_per_page: (yt_last_page * item_per_page) + item_per_page]]
                msg = _yt_format_result(yt_last_result, yt_last_page * item_per_page, item_per_page)
                bot.send_msg(tr('yt_result', result_table=msg), text)
            else:
                bot.send_msg(tr('yt_no_more'), text)

        # if query
        else:
            results = util.youtube_search(parameter)
            if results:
                yt_last_result = results
                yt_last_page = 0
                song_shortlist = [{'type': 'url', 'url': "https://www.youtube.com/watch?v=" + result[0]}
                                  for result in results[0: item_per_page]]
                msg = _yt_format_result(results, 0, item_per_page)
                bot.send_msg(tr('yt_result', result_table=msg), text)
            else:
                bot.send_msg(tr('yt_query_error'), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def _yt_format_result(results, start, count):
    msg = '<table><tr><th width="10%">Index</th><th>Title</th><th width="20%">Uploader</th></tr>'
    for index, item in enumerate(results[start:start + count]):
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
            bot.send_msg(tr('yt_query_error'), text)
    else:
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_help(bot, user, text, command, parameter):
    global log
    bot.send_msg(tr('help'), text)
    if bot.is_admin(user):
        bot.send_msg(tr('admin_help'), text)


def cmd_stop(bot, user, text, command, parameter):
    global log

    if var.config.getboolean("bot", "clear_when_stop_in_oneshot") \
            and var.playlist.mode == 'one-shot':
        cmd_clear(bot, user, text, command, parameter)
    else:
        bot.stop()
    bot.send_msg(tr('stopped'), text)


def cmd_clear(bot, user, text, command, parameter):
    global log

    bot.clear()
    bot.send_msg(tr('cleared'), text)


def cmd_kill(bot, user, text, command, parameter):
    global log

    bot.pause()
    bot.exit = True


def cmd_update(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        bot.mumble.users[text.actor].send_text_message(
            tr('start_updating'))
        msg = util.update(bot.version)
        bot.mumble.users[text.actor].send_text_message(msg)
    else:
        bot.mumble.users[text.actor].send_text_message(
            tr('not_admin'))


def cmd_stop_and_getout(bot, user, text, command, parameter):
    global log

    bot.stop()
    if var.playlist.mode == "one-shot":
        var.playlist.clear()

    bot.join_channel()


def cmd_volume(bot, user, text, command, parameter):
    global log

    # The volume is a percentage
    max_vol = min(int(var.config.getfloat('bot', 'max_volume') * 100), 100.0)
    if var.db.has_option('bot', 'max_volume'):
        max_vol = float(var.db.get('bot', 'max_volume')) * 100.0
    if parameter and parameter.isdigit() and 0 <= int(parameter) <= 100:
        if int(parameter) <= max_vol:
            vol = int(parameter)
            bot.send_msg(tr('change_volume', volume=int(parameter), user=bot.mumble.users[text.actor]['name']), text)
        else:
            vol = max_vol
            bot.send_msg(tr('max_volume', max=int(vol)), text)
        bot.volume_helper.set_volume(float(vol) / 100.0)
        var.db.set('bot', 'volume', str(float(vol) / 100.0))
        log.info(f'cmd: volume set to {float(vol) / 100.0}')
    else:
        bot.send_msg(tr('current_volume', volume=int(bot.volume_helper.plain_volume_set * 100)), text)

def cmd_max_volume(bot, user, text, command, parameter):
    global log
    
    if parameter and parameter.isdigit() and 0 <= int(parameter) <= 100:
        max_vol = float(parameter) / 100.0
        var.db.set('bot', 'max_volume', float(parameter) / 100.0)
        bot.send_msg(tr('change_max_volume', max=parameter, user=bot.mumble.users[text.actor]['name']), text)
        if int(bot.volume_helper.plain_volume_set) > max_vol:
            bot.volume_helper.set_volume(max_vol)
        log.info(f'cmd: max volume set to {max_vol}')
    else:
        max_vol = var.config.getfloat('bot', 'max_volume') * 100.0
        if var.db.has_option('bot', 'max_volume'):
            max_vol = var.db.getfloat('bot', 'max_volume') * 100.0
        bot.send_msg(tr('current_max_volume', max=int(max_vol)), text)
        
def cmd_ducking(bot, user, text, command, parameter):
    global log

    if parameter == "" or parameter == "on":
        bot.is_ducking = True
        var.db.set('bot', 'ducking', True)
        bot.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, bot.ducking_sound_received)
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
        msg = f"Ducking threshold set to {bot.ducking_threshold}."
        bot.send_msg(msg, text)
    else:
        msg = f"Current ducking threshold is {bot.ducking_threshold}."
        bot.send_msg(msg, text)


def cmd_ducking_volume(bot, user, text, command, parameter):
    global log

    # The volume is a percentage
    if parameter and parameter.isdigit() and 0 <= int(parameter) <= 100:
        bot.volume_helper.set_ducking_volume(float(parameter) / 100.0)
        bot.send_msg(tr('change_ducking_volume', volume=parameter, user=bot.mumble.users[text.actor]['name']), text)
        var.db.set('bot', 'ducking_volume', float(parameter) / 100.0)
        log.info(f'cmd: volume on ducking set to {parameter}')
    else:
        bot.send_msg(tr('current_ducking_volume', volume=int(bot.volume_helper.plain_ducking_volume_set * 100)), text)


def cmd_current_music(bot, user, text, command, parameter):
    global log

    if len(var.playlist) > 0:
        bot.send_msg(var.playlist.current_item().format_current_playing(), text)
    else:
        bot.send_msg(tr('not_playing'), text)


def cmd_skip(bot, user, text, command, parameter):
    global log

    if not bot.is_pause:
        bot.interrupt()
    else:
        var.playlist.next()
        bot.wait_for_ready = True

    if len(var.playlist) == 0:
        bot.send_msg(tr('queue_empty'), text)


def cmd_last(bot, user, text, command, parameter):
    global log

    if len(var.playlist) > 0:
        bot.interrupt()
        var.playlist.point_to(len(var.playlist) - 1 - 1)
    else:
        bot.send_msg(tr('queue_empty'), text)


def cmd_remove(bot, user, text, command, parameter):
    global log

    # Allow to remove specific music into the queue with a number
    if parameter and parameter.isdigit() and 0 < int(parameter) <= len(var.playlist):

        index = int(parameter) - 1

        if index == var.playlist.current_index:
            removed = var.playlist[index]
            bot.send_msg(tr('removing_item',
                                      item=removed.format_title()), text)
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
        bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_list_file(bot, user, text, command, parameter):
    global song_shortlist

    files = var.music_db.query_music(Condition()
                                     .and_equal('type', 'file')
                                     .order_by('path'))

    song_shortlist = files

    msgs = [tr("multiple_file_found") + "<ul>"]
    try:
        count = 0
        for index, file in enumerate(files):
            if parameter:
                match = re.search(parameter, file['path'])
                if not match:
                    continue

            count += 1
            if count > ITEMS_PER_PAGE:
                break
            msgs.append("<li><b>{:d}</b> - <b>{:s}</b> ({:s})</li>".format(index + 1, file['title'], file['path']))

        if count != 0:
            msgs.append("</ul>")
            if count > ITEMS_PER_PAGE:
                msgs.append(tr("records_omitted"))
            msgs.append(tr("shortlist_instruction"))
            send_multi_lines(bot, msgs, text, "")
        else:
            bot.send_msg(tr("no_file"), text)

    except re.error as e:
        msg = tr('wrong_pattern', error=str(e))
        bot.send_msg(msg, text)


def cmd_queue(bot, user, text, command, parameter):
    global log

    if len(var.playlist) == 0:
        msg = tr('queue_empty')
        bot.send_msg(msg, text)
    else:
        msgs = [tr('queue_contents')]
        for i, music in enumerate(var.playlist):
            tags = ''
            if len(music.item().tags) > 0:
                tags = "<sup>{}</sup>".format(", ".join(music.item().tags))
            if i == var.playlist.current_index:
                newline = "<b style='color:orange'>{} ({}) {} </b> {}".format(i + 1, music.display_type(),
                                                                              music.format_title(), tags)
            else:
                newline = '<b>{}</b> ({}) {} {}'.format(i + 1, music.display_type(),
                                                        music.format_title(), tags)

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
    if music:
        for _ in range(repeat):
            var.playlist.insert(
                var.playlist.current_index + 1,
                music
            )
            log.info("bot: add to playlist: " + music.format_debug_string())

        bot.send_channel_msg(tr("repeat", song=music.format_song_string(), n=str(repeat)))
    else:
        bot.send_msg(tr("queue_empty"), text)


def cmd_mode(bot, user, text, command, parameter):
    global log

    if not parameter:
        bot.send_msg(tr("current_mode", mode=var.playlist.mode), text)
        return
    if parameter not in ["one-shot", "repeat", "random", "autoplay"]:
        bot.send_msg(tr('unknown_mode', mode=parameter), text)
    else:
        var.db.set('playlist', 'playback_mode', parameter)
        var.playlist = media.playlist.get_playlist(parameter, var.playlist)
        log.info(f"command: playback mode changed to {parameter}.")
        bot.send_msg(tr("change_mode", mode=var.playlist.mode,
                                  user=bot.mumble.users[text.actor]['name']), text)
        if parameter == "random":
            bot.interrupt()


def cmd_play_tags(bot, user, text, command, parameter):
    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    msgs = [tr('multiple_file_added') + "<ul>"]
    count = 0

    tags = parameter.split(",")
    tags = list(map(lambda t: t.strip(), tags))
    music_wrappers = get_cached_wrappers_by_tags(tags, user)
    for music_wrapper in music_wrappers:
        count += 1
        log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
        msgs.append("<li><b>{}</b> (<i>{}</i>)</li>".format(music_wrapper.item().title, ", ".join(music_wrapper.item().tags)))

    if count != 0:
        msgs.append("</ul>")
        var.playlist.extend(music_wrappers)
        send_multi_lines_in_channel(bot, msgs, "")
    else:
        bot.send_msg(tr("no_file"), text)


def cmd_add_tag(bot, user, text, command, parameter):
    global log

    params = parameter.split(" ", 1)
    index = 0
    tags = []

    if len(params) == 2 and params[0].isdigit():
        index = params[0]
        tags = list(map(lambda t: t.strip(), params[1].split(",")))
    elif len(params) == 2 and params[0] == "*":
        index = "*"
        tags = list(map(lambda t: t.strip(), params[1].split(",")))
    else:
        index = str(var.playlist.current_index + 1)
        tags = list(map(lambda t: t.strip(), parameter.split(",")))

    if tags[0]:
        if index.isdigit() and 1 <= int(index) <= len(var.playlist):
            var.playlist[int(index) - 1].add_tags(tags)
            log.info(f"cmd: add tags {', '.join(tags)} to song {var.playlist[int(index) - 1].format_debug_string()}")
            bot.send_msg(tr("added_tags",
                                      tags=", ".join(tags),
                                      song=var.playlist[int(index) - 1].format_title()), text)
            return

        elif index == "*":
            for item in var.playlist:
                item.add_tags(tags)
                log.info(f"cmd: add tags {', '.join(tags)} to song {item.format_debug_string()}")
            bot.send_msg(tr("added_tags_to_all", tags=", ".join(tags)), text)
            return

    bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_remove_tag(bot, user, text, command, parameter):
    global log

    params = parameter.split(" ", 1)
    index = 0
    tags = []

    if len(params) == 2 and params[0].isdigit():
        index = params[0]
        tags = list(map(lambda t: t.strip(), params[1].split(",")))
    elif len(params) == 2 and params[0] == "*":
        index = "*"
        tags = list(map(lambda t: t.strip(), params[1].split(",")))
    else:
        index = str(var.playlist.current_index + 1)
        tags = list(map(lambda t: t.strip(), parameter.split(",")))

    if tags[0]:
        if index.isdigit() and 1 <= int(index) <= len(var.playlist):
            if tags[0] != "*":
                var.playlist[int(index) - 1].remove_tags(tags)
                log.info(f"cmd: remove tags {', '.join(tags)} from song {var.playlist[int(index) - 1].format_debug_string()}")
                bot.send_msg(tr("removed_tags",
                                          tags=", ".join(tags),
                                          song=var.playlist[int(index) - 1].format_title()), text)
                return
            else:
                var.playlist[int(index) - 1].clear_tags()
                log.info(f"cmd: clear tags from song {var.playlist[int(index) - 1].format_debug_string()}")
                bot.send_msg(tr("cleared_tags",
                                          song=var.playlist[int(index) - 1].format_title()), text)
                return

        elif index == "*":
            if tags[0] != "*":
                for item in var.playlist:
                    item.remove_tags(tags)
                    log.info(f"cmd: remove tags {', '.join(tags)} from song {item.format_debug_string()}")
                bot.send_msg(tr("removed_tags_from_all", tags=", ".join(tags)), text)
                return
            else:
                for item in var.playlist:
                    item.clear_tags()
                    log.info(f"cmd: clear tags from song {item.format_debug_string()}")
                bot.send_msg(tr("cleared_tags_from_all"), text)
                return

    bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_find_tagged(bot, user, text, command, parameter):
    global song_shortlist

    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    msgs = [tr('multiple_file_found') + "<ul>"]
    count = 0

    tags = parameter.split(",")
    tags = list(map(lambda t: t.strip(), tags))

    music_dicts = var.music_db.query_music_by_tags(tags)
    song_shortlist = music_dicts

    for i, music_dict in enumerate(music_dicts):
        item = dict_to_item(music_dict)
        count += 1
        if count > ITEMS_PER_PAGE:
            break
        msgs.append("<li><b>{:d}</b> - <b>{}</b> (<i>{}</i>)</li>".format(i + 1, item.title, ", ".join(item.tags)))

    if count != 0:
        msgs.append("</ul>")
        if count > ITEMS_PER_PAGE:
            msgs.append(tr("records_omitted"))
        msgs.append(tr("shortlist_instruction"))
        send_multi_lines(bot, msgs, text, "")
    else:
        bot.send_msg(tr("no_file"), text)


def cmd_search_library(bot, user, text, command, parameter):
    global song_shortlist
    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    msgs = [tr('multiple_file_found') + "<ul>"]
    count = 0

    _keywords = parameter.split(" ")
    keywords = []
    for kw in _keywords:
        if kw:
            keywords.append(kw)

    music_dicts = var.music_db.query_music_by_keywords(keywords)
    if music_dicts:
        items = dicts_to_items(music_dicts)
        song_shortlist = music_dicts

        if len(items) == 1:
            music_wrapper = get_cached_wrapper(items[0], user)
            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            send_item_added_message(bot, music_wrapper, len(var.playlist) - 1, text)
        else:
            for item in items:
                count += 1
                if count > ITEMS_PER_PAGE:
                    break
                if len(item.tags) > 0:
                    msgs.append("<li><b>{:d}</b> - [{}] <b>{}</b> (<i>{}</i>)</li>".format(count, item.display_type(), item.title, ", ".join(item.tags)))
                else:
                    msgs.append("<li><b>{:d}</b> - [{}] <b>{}</b> </li>".format(count, item.display_type(), item.title, ", ".join(item.tags)))

            if count != 0:
                msgs.append("</ul>")
                if count > ITEMS_PER_PAGE:
                    msgs.append(tr("records_omitted"))
                msgs.append(tr("shortlist_instruction"))
                send_multi_lines(bot, msgs, text, "")
            else:
                bot.send_msg(tr("no_file"), text)
    else:
        bot.send_msg(tr("no_file"), text)


def cmd_shortlist(bot, user, text, command, parameter):
    global song_shortlist, log
    if parameter.strip() == "*":
        msgs = [tr('multiple_file_added') + "<ul>"]
        music_wrappers = []
        for kwargs in song_shortlist:
            kwargs['user'] = user
            music_wrapper = get_cached_wrapper_from_scrap(**kwargs)
            music_wrappers.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            msgs.append("<li>[{}] <b>{}</b></li>".format(music_wrapper.item().type, music_wrapper.item().title))

        var.playlist.extend(music_wrappers)

        msgs.append("</ul>")
        send_multi_lines_in_channel(bot, msgs, "")
        return

    try:
        indexes = [int(i) for i in parameter.split(" ")]
    except ValueError:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    if len(indexes) > 1:
        msgs = [tr('multiple_file_added') + "<ul>"]
        music_wrappers = []
        for index in indexes:
            if 1 <= index <= len(song_shortlist):
                kwargs = song_shortlist[index - 1]
                kwargs['user'] = user
                music_wrapper = get_cached_wrapper_from_scrap(**kwargs)
                music_wrappers.append(music_wrapper)
                log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
                msgs.append("<li>[{}] <b>{}</b></li>".format(music_wrapper.item().type, music_wrapper.item().title))
            else:
                var.playlist.extend(music_wrappers)
                bot.send_msg(tr('bad_parameter', command=command), text)
                return

        var.playlist.extend(music_wrappers)

        msgs.append("</ul>")
        send_multi_lines_in_channel(bot, msgs, "")
        return
    elif len(indexes) == 1:
        index = indexes[0]
        if 1 <= index <= len(song_shortlist):
            kwargs = song_shortlist[index - 1]
            kwargs['user'] = user
            music_wrapper = get_cached_wrapper_from_scrap(**kwargs)
            var.playlist.append(music_wrapper)
            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            send_item_added_message(bot, music_wrapper, len(var.playlist) - 1, text)
            return

    bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_delete_from_library(bot, user, text, command, parameter):
    global song_shortlist, log

    if not var.config.getboolean("bot", "delete_allowed"):
        bot.mumble.users[text.actor].send_text_message(tr('not_admin'))
        return

    try:
        indexes = [int(i) for i in parameter.split(" ")]
    except ValueError:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    if len(indexes) > 1:
        msgs = [tr('multiple_file_added') + "<ul>"]
        count = 0
        for index in indexes:
            if 1 <= index <= len(song_shortlist):
                music_dict = song_shortlist[index - 1]
                if 'id' in music_dict:
                    music_wrapper = get_cached_wrapper_by_id(music_dict['id'], user)
                    log.info("cmd: remove from library: " + music_wrapper.format_debug_string())
                    msgs.append("<li>[{}] <b>{}</b></li>".format(music_wrapper.item().type, music_wrapper.item().title))
                    var.playlist.remove_by_id(music_dict['id'])
                    var.cache.free_and_delete(music_dict['id'])
                    count += 1
            else:
                bot.send_msg(tr('bad_parameter', command=command), text)
                return

        if count == 0:
            bot.send_msg(tr('bad_parameter', command=command), text)
            return

        msgs.append("</ul>")
        send_multi_lines_in_channel(bot, msgs, "")
        return
    elif len(indexes) == 1:
        index = indexes[0]
        if 1 <= index <= len(song_shortlist):
            music_dict = song_shortlist[index - 1]
            if 'id' in music_dict:
                music_wrapper = get_cached_wrapper_by_id(music_dict['id'], user)
                bot.send_msg(tr('file_deleted', item=music_wrapper.format_song_string()), text)
                log.info("cmd: remove from library: " + music_wrapper.format_debug_string())
                var.playlist.remove_by_id(music_dict['id'])
                var.cache.free_and_delete(music_dict['id'])
                return

    bot.send_msg(tr('bad_parameter', command=command), text)


def cmd_drop_database(bot, user, text, command, parameter):
    global log

    if bot.is_admin(user):
        var.db.drop_table()
        var.db = SettingsDatabase(var.settings_db_path)
        var.music_db.drop_table()
        var.music_db = MusicDatabase(var.settings_db_path)
        log.info("command: database dropped.")
        bot.send_msg(tr('database_dropped'), text)
    else:
        bot.mumble.users[text.actor].send_text_message(tr('not_admin'))


def cmd_refresh_cache(bot, user, text, command, parameter):
    global log
    if bot.is_admin(user):
        var.cache.build_dir_cache()
        log.info("command: Local file cache refreshed.")
        bot.send_msg(tr('cache_refreshed'), text)
    else:
        bot.mumble.users[text.actor].send_text_message(tr('not_admin'))


def cmd_web_access(bot, user, text, command, parameter):
    auth_method = var.config.get("webinterface", "auth_method")

    if auth_method == 'token':
        interface.banned_ip = []
        interface.bad_access_count = {}

        user_info = var.db.get("user", user, fallback='{}')
        user_dict = json.loads(user_info)
        if 'token' in user_dict:
            var.db.remove_option("web_token", user_dict['token'])

        token = secrets.token_urlsafe(5)
        user_dict['token'] = token
        user_dict['token_created'] = str(datetime.datetime.now())
        user_dict['last_ip'] = ''
        var.db.set("web_token", token, user)
        var.db.set("user", user, json.dumps(user_dict))

        access_address = var.config.get("webinterface", "access_address") + "/?token=" + token
    else:
        access_address = var.config.get("webinterface", "access_address")

    bot.send_msg(tr('webpage_address', address=access_address), text)


def cmd_user_password(bot, user, text, command, parameter):
    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    user_info = var.db.get("user", user, fallback='{}')
    user_dict = json.loads(user_info)
    user_dict['password'], user_dict['salt'] = util.get_salted_password_hash(parameter)

    var.db.set("user", user, json.dumps(user_dict))

    bot.send_msg(tr('user_password_set'), text)


def cmd_web_user_add(bot, user, text, command, parameter):
    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    auth_method = var.config.get("webinterface", "auth_method")

    if auth_method == 'password':
        web_users = json.loads(var.db.get("privilege", "web_access", fallback='[]'))
        if parameter not in web_users:
            web_users.append(parameter)
        var.db.set("privilege", "web_access", json.dumps(web_users))
        bot.send_msg(tr('web_user_list', users=", ".join(web_users)), text)
    else:
        bot.send_msg(tr('command_disabled', command=command), text)


def cmd_web_user_remove(bot, user, text, command, parameter):
    if not parameter:
        bot.send_msg(tr('bad_parameter', command=command), text)
        return

    auth_method = var.config.get("webinterface", "auth_method")

    if auth_method == 'password':
        web_users = json.loads(var.db.get("privilege", "web_access", fallback='[]'))
        if parameter in web_users:
            web_users.remove(parameter)
        var.db.set("privilege", "web_access", json.dumps(web_users))
        bot.send_msg(tr('web_user_list', users=", ".join(web_users)), text)
    else:
        bot.send_msg(tr('command_disabled', command=command), text)


def cmd_web_user_list(bot, user, text, command, parameter):
    auth_method = var.config.get("webinterface", "auth_method")

    if auth_method == 'password':
        web_users = json.loads(var.db.get("privilege", "web_access", fallback='[]'))
        bot.send_msg(tr('web_user_list', users=", ".join(web_users)), text)
    else:
        bot.send_msg(tr('command_disabled', command=command), text)


def cmd_version(bot, user, text, command, parameter):
    bot.send_msg(tr('report_version', version=bot.get_version()), text)


# Just for debug use
def cmd_real_time_rms(bot, user, text, command, parameter):
    bot._display_rms = not bot._display_rms


def cmd_loop_state(bot, user, text, command, parameter):
    print(bot._loop_status)


def cmd_item(bot, user, text, command, parameter):
    var.playlist._debug_print()
