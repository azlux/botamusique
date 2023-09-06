#!/usr/bin/python3
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, send_file, Response, jsonify, abort, session
from werkzeug.utils import secure_filename

import variables as var
import util
import math
import os
import os.path
import errno
from typing import Type
import media
import json
from media.item import dicts_to_items, dict_to_item, BaseItem
from media.file import FileItem
from media.url import URLItem
from media.url_from_playlist import PlaylistURLItem
from media.radio import RadioItem
from media.cache import get_cached_wrapper_from_scrap, get_cached_wrapper_by_id, get_cached_wrappers_by_tags, \
    get_cached_wrapper
from database import MusicDatabase, Condition
import logging
import time


class ReverseProxied(object):
    """Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        real_ip = environ.get('HTTP_X_REAL_IP', '')
        if real_ip:
            environ['REMOTE_ADDR'] = real_ip
        return self.app(environ, start_response)


root_dir = os.path.dirname(__file__)
web = Flask(__name__, template_folder=os.path.join(root_dir, "web/templates"))
#web.config['TEMPLATES_AUTO_RELOAD'] = True
log = logging.getLogger("bot")
user = 'Remote Control'


def init_proxy():
    global web
    if var.is_proxified:
        web.wsgi_app = ReverseProxied(web.wsgi_app)


# https://stackoverflow.com/questions/29725217/password-protect-one-webpage-in-flask-app


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """

    if username == var.config.get("webinterface", "user") and password == var.config.get("webinterface", "password"):
        return True

    web_users = json.loads(var.db.get("privilege", "web_access", fallback='[]'))
    if username in web_users:
        user_dict = json.loads(var.db.get("user", username, fallback='{}'))
        if 'password' in user_dict and 'salt' in user_dict and \
                util.verify_password(password, user_dict['password'], user_dict['salt']):
            return True

    return False


def authenticate():
    """Sends a 401 response that enables basic auth"""
    global log
    return Response('Could not verify your access level for that URL.\n'
                    'You have to login with proper credentials', 401,
                    {'WWW-Authenticate': 'Basic realm="Login Required"'})


bad_access_count = {}
banned_ip = []


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        global log, user, bad_access_count, banned_ip

        if request.remote_addr in banned_ip:
            abort(403)

        auth_method = var.config.get("webinterface", "auth_method")

        if auth_method == 'password':
            auth = request.authorization
            if auth:
                user = auth.username
                if not check_auth(auth.username, auth.password):
                    if request.remote_addr in bad_access_count:
                        bad_access_count[request.remote_addr] += 1
                        log.info(f"web: failed login attempt, user: {auth.username}, from ip {request.remote_addr}."
                                 f"{bad_access_count[request.remote_addr]} attempts.")
                        if bad_access_count[request.remote_addr] > var.config.getint("webinterface", "max_attempts",
                                                                                     fallback=10):
                            banned_ip.append(request.remote_addr)
                            log.info(f"web: access banned for {request.remote_addr}")
                    else:
                        bad_access_count[request.remote_addr] = 1
                        log.info(f"web: failed login attempt, user: {auth.username}, from ip {request.remote_addr}.")
                    return authenticate()
            else:
                return authenticate()
        if auth_method == 'token':
            if 'user' in session and 'token' not in request.args:
                user = session['user']
                return f(*args, **kwargs)
            elif 'token' in request.args:
                token = request.args.get('token')
                token_user = var.db.get("web_token", token, fallback=None)
                if token_user is not None:
                    user = token_user

                    user_info = var.db.get("user", user, fallback=None)
                    user_dict = json.loads(user_info)
                    user_dict['IP'] = request.remote_addr
                    var.db.set("user", user, json.dumps(user_dict))

                    log.debug(
                        f"web: new user access, token validated for the user: {token_user}, from ip {request.remote_addr}.")
                    session['token'] = token
                    session['user'] = token_user
                    return f(*args, **kwargs)

            if request.remote_addr in bad_access_count:
                bad_access_count[request.remote_addr] += 1
                log.info(f"web: bad token from ip {request.remote_addr}, "
                         f"{bad_access_count[request.remote_addr]} attempts.")
                if bad_access_count[request.remote_addr] > var.config.getint("webinterface", "max_attempts"):
                    banned_ip.append(request.remote_addr)
                    log.info(f"web: access banned for {request.remote_addr}")
            else:
                bad_access_count[request.remote_addr] = 1
                log.info(f"web: bad token from ip {request.remote_addr}.")

            return render_template(f'need_token.{var.language}.html',
                                   name=var.config.get('bot', 'username'),
                                   command=f"{var.config.get('commands', 'command_symbol')[0]}"
                                           f"{var.config.get('commands', 'requests_webinterface_access')}")

        return f(*args, **kwargs)

    return decorated


def tag_color(tag):
    num = hash(tag) % 8
    if num == 0:
        return "primary"
    elif num == 1:
        return "secondary"
    elif num == 2:
        return "success"
    elif num == 3:
        return "danger"
    elif num == 4:
        return "warning"
    elif num == 5:
        return "info"
    elif num == 6:
        return "light"
    elif num == 7:
        return "dark"


def build_tags_color_lookup():
    color_lookup = {}
    for tag in var.music_db.query_all_tags():
        color_lookup[tag] = tag_color(tag)

    return color_lookup


def get_all_dirs():
    dirs = ["."]
    paths = var.music_db.query_all_paths()
    for path in paths:
        pos = 0
        while True:
            pos = path.find("/", pos + 1)
            if pos == -1:
                break
            folder = path[:pos]
            if folder not in dirs:
                dirs.append(folder)

    return dirs


@web.route("/", methods=['GET'])
@requires_auth
def index():
    return open(os.path.join(root_dir, f"web/templates/index.{var.language}.html"), "r").read()


@web.route("/playlist", methods=['GET'])
@requires_auth
def playlist():
    if len(var.playlist) == 0:
        return jsonify({
            'items': [],
            'current_index': -1,
            'length': 0,
            'start_from': 0
        })

    DEFAULT_DISPLAY_COUNT = 11
    _from = 0
    _to = 10

    if 'range_from' in request.args and 'range_to' in request.args:
        _from = int(request.args['range_from'])
        _to = int(request.args['range_to'])
    else:
        if var.playlist.current_index - int(DEFAULT_DISPLAY_COUNT / 2) > 0:
            _from = var.playlist.current_index - int(DEFAULT_DISPLAY_COUNT / 2)
            _to = _from - 1 + DEFAULT_DISPLAY_COUNT

    tags_color_lookup = build_tags_color_lookup()  # TODO: cached this?
    items = []

    for index, item_wrapper in enumerate(var.playlist[_from: _to + 1]):
        tag_tuples = []
        for tag in item_wrapper.item().tags:
            tag_tuples.append([tag, tags_color_lookup[tag]])

        item: Type[BaseItem] = item_wrapper.item()

        title = item.format_title()
        artist = "??"
        path = ""
        duration = 0
        if isinstance(item, FileItem):
            path = item.path
            if item.artist:
                artist = item.artist
            duration = item.duration
        elif isinstance(item, URLItem):
            path = f" <a href=\"{item.url}\"><i>{item.url}</i></a>"
            duration = item.duration
        elif isinstance(item, PlaylistURLItem):
            path = f" <a href=\"{item.url}\"><i>{item.url}</i></a>"
            artist = f" <a href=\"{item.playlist_url}\"><i>{item.playlist_title}</i></a>"
            duration = item.duration
        elif isinstance(item, RadioItem):
            path = f" <a href=\"{item.url}\"><i>{item.url}</i></a>"

        thumb = ""
        if item.type != 'radio' and item.thumbnail:
            thumb = f"data:image/PNG;base64,{item.thumbnail}"
        else:
            thumb = "static/image/unknown-album.png"

        items.append({
            'index': _from + index,
            'id': item.id,
            'type': item.display_type(),
            'path': path,
            'title': title,
            'artist': artist,
            'thumbnail': thumb,
            'tags': tag_tuples,
            'duration': duration
        })

    return jsonify({
        'items': items,
        'current_index': var.playlist.current_index,
        'length': len(var.playlist),
        'start_from': _from
    })


def status():
    if len(var.playlist) > 0:
        return jsonify({'ver': var.playlist.version,
                        'current_index': var.playlist.current_index,
                        'empty': False,
                        'play': not var.bot.is_pause,
                        'mode': var.playlist.mode,
                        'volume': var.bot.volume_helper.plain_volume_set,
                        'playhead': var.bot.playhead
                        })

    else:
        return jsonify({'ver': var.playlist.version,
                        'current_index': var.playlist.current_index,
                        'empty': True,
                        'play': not var.bot.is_pause,
                        'mode': var.playlist.mode,
                        'volume': var.bot.volume_helper.plain_volume_set,
                        'playhead': 0
                        })


@web.route("/post", methods=['POST'])
@requires_auth
def post():
    global log

    payload = request.get_json() if request.is_json else request.form
    if payload:
        log.debug("web: Post request from %s: %s" % (request.remote_addr, str(payload)))

        if 'add_item_at_once' in payload:
            music_wrapper = get_cached_wrapper_by_id(payload['add_item_at_once'], user)
            if music_wrapper:
                var.playlist.insert(var.playlist.current_index + 1, music_wrapper)
                log.info('web: add to playlist(next): ' + music_wrapper.format_debug_string())
                if not var.bot.is_pause:
                    var.bot.interrupt()
                else:
                    var.bot.is_pause = False
            else:
                abort(404)

        if 'add_item_bottom' in payload:
            music_wrapper = get_cached_wrapper_by_id(payload['add_item_bottom'], user)

            if music_wrapper:
                var.playlist.append(music_wrapper)
                log.info('web: add to playlist(bottom): ' + music_wrapper.format_debug_string())
            else:
                abort(404)

        elif 'add_item_next' in payload:
            music_wrapper = get_cached_wrapper_by_id(payload['add_item_next'], user)
            if music_wrapper:
                var.playlist.insert(var.playlist.current_index + 1, music_wrapper)
                log.info('web: add to playlist(next): ' + music_wrapper.format_debug_string())
            else:
                abort(404)

        elif 'add_url' in payload:
            music_wrapper = get_cached_wrapper_from_scrap(type='url', url=payload['add_url'], user=user)
            var.playlist.append(music_wrapper)

            log.info("web: add to playlist: " + music_wrapper.format_debug_string())
            if len(var.playlist) == 2:
                # If I am the second item on the playlist. (I am the next one!)
                var.bot.async_download_next()

        elif 'add_radio' in payload:
            url = payload['add_radio']
            music_wrapper = get_cached_wrapper_from_scrap(type='radio', url=url, user=user)
            var.playlist.append(music_wrapper)

            log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())

        elif 'delete_music' in payload:
            music_wrapper = var.playlist[int(payload['delete_music'])]
            log.info("web: delete from playlist: " + music_wrapper.format_debug_string())

            if len(var.playlist) >= int(payload['delete_music']):
                index = int(payload['delete_music'])

                if index == var.playlist.current_index:
                    var.playlist.remove(index)

                    if index < len(var.playlist):
                        if not var.bot.is_pause:
                            var.bot.interrupt()
                            var.playlist.current_index -= 1
                            # then the bot will move to next item

                    else:  # if item deleted is the last item of the queue
                        var.playlist.current_index -= 1
                        if not var.bot.is_pause:
                            var.bot.interrupt()
                else:
                    var.playlist.remove(index)

        elif 'play_music' in payload:
            music_wrapper = var.playlist[int(payload['play_music'])]
            log.info("web: jump to: " + music_wrapper.format_debug_string())

            if len(var.playlist) >= int(payload['play_music']):
                var.bot.play(int(payload['play_music']))
                time.sleep(0.1)
        elif 'move_playhead' in payload:
            if float(payload['move_playhead']) < var.playlist.current_item().item().duration:
                log.info(f"web: move playhead to {float(payload['move_playhead'])} s.")
                var.bot.play(var.playlist.current_index, float(payload['move_playhead']))

        elif 'delete_item_from_library' in payload:
            _id = payload['delete_item_from_library']
            var.playlist.remove_by_id(_id)
            item = var.cache.get_item_by_id(_id)

            if os.path.isfile(item.uri()):
                log.info("web: delete file " + item.uri())
                os.remove(item.uri())

            var.cache.free_and_delete(_id)
            time.sleep(0.1)

        elif 'add_tag' in payload:
            music_wrappers = get_cached_wrappers_by_tags([payload['add_tag']], user)
            for music_wrapper in music_wrappers:
                log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())
            var.playlist.extend(music_wrappers)

        elif 'action' in payload:
            action = payload['action']
            if action == "random":
                if var.playlist.mode != "random":
                    var.playlist = media.playlist.get_playlist("random", var.playlist)
                else:
                    var.playlist.randomize()
                var.bot.interrupt()
                var.db.set('playlist', 'playback_mode', "random")
                log.info("web: playback mode changed to random.")
            if action == "one-shot":
                var.playlist = media.playlist.get_playlist("one-shot", var.playlist)
                var.db.set('playlist', 'playback_mode', "one-shot")
                log.info("web: playback mode changed to one-shot.")
            if action == "repeat":
                var.playlist = media.playlist.get_playlist("repeat", var.playlist)
                var.db.set('playlist', 'playback_mode', "repeat")
                log.info("web: playback mode changed to repeat.")
            if action == "autoplay":
                var.playlist = media.playlist.get_playlist("autoplay", var.playlist)
                var.db.set('playlist', 'playback_mode', "autoplay")
                log.info("web: playback mode changed to autoplay.")
            if action == "rescan":
                var.cache.build_dir_cache()
                var.music_db.manage_special_tags()
                log.info("web: Local file cache refreshed.")
            elif action == "stop":
                if var.config.getboolean("bot", "clear_when_stop_in_oneshot") \
                        and var.playlist.mode == 'one-shot':
                    var.bot.clear()
                else:
                    var.bot.stop()
            elif action == "next":
                if not var.bot.is_pause:
                    var.bot.interrupt()
                else:
                    var.playlist.next()
                    var.bot.wait_for_ready = True
            elif action == "pause":
                var.bot.pause()
            elif action == "resume":
                var.bot.resume()
            elif action == "clear":
                var.bot.clear()
            elif action == "volume_up":
                if var.bot.volume_helper.plain_volume_set + 0.03 < 1.0:
                    var.bot.volume_helper.set_volume(var.bot.volume_helper.plain_volume_set + 0.03)
                else:
                    var.bot.volume_helper.set_volume(1.0)
                var.db.set('bot', 'volume', str(var.bot.volume_helper.plain_volume_set))
                log.info("web: volume up to %d" % (var.bot.volume_helper.plain_volume_set * 100))
            elif action == "volume_down":
                if var.bot.volume_helper.plain_volume_set - 0.03 > 0:
                    var.bot.volume_helper.set_volume(var.bot.unconverted_volume - 0.03)
                else:
                    var.bot.volume_helper.set_volume(1.0)
                var.db.set('bot', 'volume', str(var.bot.volume_helper.plain_volume_set))
                log.info("web: volume down to %d" % (var.bot.volume_helper.plain_volume_set * 100))
            elif action == "volume_set_value":
                if 'new_volume' in payload:
                    if float(payload['new_volume']) > 1:
                        var.bot.volume_helper.set_volume(1.0)
                    elif float(payload['new_volume']) < 0:
                        var.bot.volume_helper.set_volume(0)
                    else:
                        # value for new volume is between 0 and 1, round to two decimal digits
                        var.bot.volume_helper.set_volume(round(float(payload['new_volume']), 2))

                    var.db.set('bot', 'volume', str(var.bot.volume_helper.plain_volume_set))
                    log.info("web: volume set to %d" % (var.bot.volume_helper.plain_volume_set * 100))

    return status()


def build_library_query_condition(form):
    try:
        condition = Condition()

        types = form['type'].split(",")
        sub_cond = Condition()
        for type in types:
            sub_cond.or_equal("type", type)
        condition.and_sub_condition(sub_cond)

        if form['type'] == 'file':
            folder = form['dir']
            if folder == ".":
                folder = ""
            if not folder.endswith('/') and folder:
                folder += '/'
            condition.and_like('path', folder + '%')

        tags = form['tags'].split(",")
        for tag in tags:
            if tag:
                condition.and_like("tags", f"%{tag},%", case_sensitive=False)

        _keywords = form['keywords'].split(" ")
        keywords = []
        for kw in _keywords:
            if kw:
                keywords.append(kw)

        for keyword in keywords:
            condition.and_like("keywords", f"%{keyword}%", case_sensitive=False)

        condition.order_by('create_at', desc=True)

        return condition
    except KeyError:
        abort(400)


@web.route("/library/info", methods=['GET'])
@requires_auth
def library_info():
    global log

    while var.cache.dir_lock.locked():
        time.sleep(0.1)

    tags = var.music_db.query_all_tags()
    max_upload_file_size = util.parse_file_size(var.config.get("webinterface", "max_upload_file_size"))

    return jsonify(dict(
        dirs=get_all_dirs(),
        upload_enabled=var.config.getboolean("webinterface", "upload_enabled") or var.bot.is_admin(user),
        delete_allowed=var.config.getboolean("bot", "delete_allowed") or var.bot.is_admin(user),
        tags=tags,
        max_upload_file_size=max_upload_file_size
    ))


@web.route("/library", methods=['POST'])
@requires_auth
def library():
    global log
    ITEM_PER_PAGE = 10

    payload = request.form if request.form else request.json
    if payload:
        log.debug("web: Post request from %s: %s" % (request.remote_addr, str(payload)))

        if payload['action'] in ['add', 'query', 'delete']:
            condition = build_library_query_condition(payload)

            total_count = 0
            try:
                total_count = var.music_db.query_music_count(condition)
            except sqlite3.OperationalError:
                pass

            if not total_count:
                return jsonify({
                    'items': [],
                    'total_pages': 0,
                    'active_page': 0
                })

            if payload['action'] == 'add':
                items = dicts_to_items(var.music_db.query_music(condition))
                music_wrappers = []
                for item in items:
                    music_wrapper = get_cached_wrapper(item, user)
                    music_wrappers.append(music_wrapper)

                    log.info("cmd: add to playlist: " + music_wrapper.format_debug_string())

                var.playlist.extend(music_wrappers)

                return redirect("./", code=302)
            elif payload['action'] == 'delete':
                if var.config.getboolean("bot", "delete_allowed"):
                    items = dicts_to_items(var.music_db.query_music(condition))
                    for item in items:
                        var.playlist.remove_by_id(item.id)
                        item = var.cache.get_item_by_id(item.id)

                        if os.path.isfile(item.uri()):
                            log.info("web: delete file " + item.uri())
                            os.remove(item.uri())

                        var.cache.free_and_delete(item.id)

                    if len(os.listdir(var.music_folder + payload['dir'])) == 0:
                        os.rmdir(var.music_folder + payload['dir'])

                    time.sleep(0.1)
                    return redirect("./", code=302)
                else:
                    abort(403)
            else:
                page_count = math.ceil(total_count / ITEM_PER_PAGE)

                current_page = int(payload['page']) if 'page' in payload else 1
                if current_page <= page_count:
                    condition.offset((current_page - 1) * ITEM_PER_PAGE)
                else:
                    current_page = 1

                condition.limit(ITEM_PER_PAGE)
                items = dicts_to_items(var.music_db.query_music(condition))

                results = []
                for item in items:
                    result = {'id': item.id, 'title': item.title, 'type': item.display_type(),
                              'tags': [(tag, tag_color(tag)) for tag in item.tags]}
                    if item.type != 'radio' and item.thumbnail:
                        result['thumb'] = f"data:image/PNG;base64,{item.thumbnail}"
                    else:
                        result['thumb'] = "static/image/unknown-album.png"

                    if item.type == 'file':
                        result['path'] = item.path
                        result['artist'] = item.artist
                    else:
                        result['path'] = item.url
                        result['artist'] = "??"

                    results.append(result)

                return jsonify({
                    'items': results,
                    'total_pages': page_count,
                    'active_page': current_page
                })
        elif payload['action'] == 'edit_tags':
            tags = list(dict.fromkeys(payload['tags'].split(",")))  # remove duplicated items
            if payload['id'] in var.cache:
                music_wrapper = get_cached_wrapper_by_id(payload['id'], user)
                music_wrapper.clear_tags()
                music_wrapper.add_tags(tags)
                var.playlist.version += 1
            else:
                item = var.music_db.query_music_by_id(payload['id'])
                item['tags'] = tags
                var.music_db.insert_music(item)
            return redirect("./", code=302)

    else:
        abort(400)


@web.route('/upload', methods=["POST"])
@requires_auth
def upload():
    global log

    if not var.config.getboolean("webinterface", "upload_enabled"):
        abort(403)

    file = request.files['file']
    if not file:
        abort(400)

    filename = file.filename
    if filename == '':
        abort(400)

    targetdir = request.form['targetdir'].strip()
    if targetdir == '':
        targetdir = 'uploads/'
    elif '../' in targetdir:
        abort(403)

    log.info('web: Uploading file from %s:' % request.remote_addr)
    log.info('web: - filename: ' + filename)
    log.info('web: - targetdir: ' + targetdir)
    log.info('web: - mimetype: ' + file.mimetype)

    if "audio" in file.mimetype or "video" in file.mimetype:
        storagepath = os.path.abspath(os.path.join(var.music_folder, targetdir))
        if not storagepath.startswith(os.path.abspath(var.music_folder)):
            abort(403)

        try:
            os.makedirs(storagepath)
        except OSError as ee:
            if ee.errno != errno.EEXIST:
                log.error(f'web: failed to create directory {storagepath}')
                abort(500)

        filepath = os.path.join(storagepath, filename)
        log.info('web: - file saved at: ' + filepath)
        if os.path.exists(filepath):
            return 'File existed!', 409

        file.save(filepath)
    else:
        log.error(f'web: unsupported file type {file.mimetype}! File was not saved.')
        return 'Unsupported media type!', 415

    return '', 200


@web.route('/download', methods=["GET"])
@requires_auth
def download():
    global log

    if 'id' in request.args and request.args['id']:
        item = dicts_to_items(var.music_db.query_music(
            Condition().and_equal('id', request.args['id'])))[0]

        requested_file = item.uri()
        log.info('web: Download of file %s requested from %s:' % (requested_file, request.remote_addr))

        try:
            return send_file(requested_file, as_attachment=True)
        except Exception as e:
            log.exception(e)
            abort(404)

    else:
        condition = build_library_query_condition(request.args)
        items = dicts_to_items(var.music_db.query_music(condition))

        zipfile = util.zipdir([item.uri() for item in items])

        try:
            return send_file(zipfile, as_attachment=True)
        except Exception as e:
            log.exception(e)
            abort(404)

    return abort(400)


if __name__ == '__main__':
    web.run(port=8181, host="127.0.0.1")
