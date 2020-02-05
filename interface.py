#!/usr/bin/python3

from functools import wraps
from flask import Flask, render_template, request, redirect, send_file, Response
import variables as var
import util
from datetime import datetime
import os
import os.path
import shutil
import random
from werkzeug.utils import secure_filename
import errno
import media
import logging
import time


class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the
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
    '''

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


web = Flask(__name__)


def init_proxy():
    global web
    if var.is_proxified:
        web.wsgi_app = ReverseProxied(web.wsgi_app)

# https://stackoverflow.com/questions/29725217/password-protect-one-webpage-in-flask-app

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == var.config.get("webinterface", "user") and password == var.config.get("webinterface", "password")

def authenticate():
    """Sends a 401 response that enables basic auth"""
    logging.info("Web Interface login failed.")
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if var.config.getboolean("webinterface", "require_auth") and (not auth or not check_auth(auth.username, auth.password)):
            if auth:
                logging.info("Web Interface login attempt, user: %s" % auth.username)
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@web.route("/", methods=['GET', 'POST'])
@requires_auth
def index():
    folder_path = var.music_folder
    files = util.get_recursive_filelist_sorted(var.music_folder)
    music_library = util.Dir(folder_path)
    for file in files:
        music_library.add_file(file)

    if request.method == 'POST':
        logging.debug("Post request: "+ str(request.form))
        if 'add_file_bottom' in request.form and ".." not in request.form['add_file_bottom']:
            path = var.config.get('bot', 'music_folder') + request.form['add_file_bottom']
            if os.path.isfile(path):
                item = {'type': 'file',
                        'path' : request.form['add_file_bottom'],
                        'title' : 'Unknown',
                        'user' : 'Web'}
                var.playlist.append(var.botamusique.get_music_tag_info(item, path))
                logging.info('web: add to playlist(bottom): ' + item['path'])

        elif 'add_file_next' in request.form and ".." not in request.form['add_file_next']:
            path = var.config.get('bot', 'music_folder') + request.form['add_file_next']
            if os.path.isfile(path):
                item = {'type': 'file',
                        'path' : request.form['add_file_next'],
                        'title' : 'Unknown',
                        'user' : 'Web'}
                var.playlist.insert(
                    var.playlist.current_index + 1,
                    var.botamusique.get_music_tag_info(item, var.config.get('bot', 'music_folder') + item['path'])
                )
                logging.info('web: add to playlist(next): ' + item['path'])

        elif ('add_folder' in request.form and ".." not in request.form['add_folder']) or ('add_folder_recursively' in request.form and ".." not in request.form['add_folder_recursively']):
            try:
                folder = request.form['add_folder']
            except:
                folder = request.form['add_folder_recursively']

            if not folder.endswith('/'):
                folder += '/'

            print('folder:', folder)

            if os.path.isdir(var.config.get('bot', 'music_folder') + folder):
                if 'add_folder_recursively' in request.form:
                    files = music_library.get_files_recursively(folder)
                else:
                    files = music_library.get_files(folder)

                files = list(map(lambda file: var.botamusique.get_music_tag_info({'type':'file','path': os.path.join(folder, file), 'user':'Web'}, \
                                                                                 var.config.get('bot', 'music_folder') + os.path.join(folder, file)), files))

                logging.info("web: add to playlist: " + " ,".join([file['path'] for file in files]))
                var.playlist.extend(files)

        elif 'add_url' in request.form:
            var.playlist.append({'type':'url',
                                'url': request.form['add_url'],
                                'user': 'Web',
                                'ready': 'validation'})
            logging.info("web: add to playlist: " + request.form['add_url'])
            media.url.get_url_info()
            var.playlist.playlist[-1]['ready'] = "no"

        elif 'add_radio' in request.form:
            var.playlist.append({'type': 'radio',
                                'path': request.form['add_radio'],
                                'user': "Web"})
            logging.info("web: add to playlist: " + request.form['add_radio'])

        elif 'delete_music' in request.form:
            logging.info("web: delete from playlist: " + var.playlist.playlist[int(request.form['delete_music'])]['path'])
            if len(var.playlist.playlist) >= int(request.form['delete_music']):
                if var.playlist.current_index == int(request.form['delete_music']):
                    var.botamusique.pause()
                    var.playlist.remove(int(request.form['delete_music']))
                    var.botamusique.launch_music()
                else:
                    var.playlist.remove(int(request.form['delete_music']))

        elif 'play_music' in request.form:
            logging.info("web: jump to: " + var.playlist.playlist[int(request.form['play_music'])]['path'])
            if len(var.playlist.playlist) >= int(request.form['play_music']):
                var.botamusique.pause()
                var.botamusique.launch_music(int(request.form['play_music']))

        elif 'delete_music_file' in request.form and ".." not in request.form['delete_music_file']:
            path = var.config.get('bot', 'music_folder') + request.form['delete_music_file']
            if os.path.isfile(path):
                logging.info("web: delete file " + path)
                os.remove(path)

        elif 'delete_folder' in request.form and ".." not in request.form['delete_folder']:
            path = var.config.get('bot', 'music_folder') + request.form['delete_folder']
            if os.path.isdir(path):
                logging.info("web: delete folder " + path)
                shutil.rmtree(path)
                time.sleep(0.1)

        elif 'action' in request.form:
            action = request.form['action']
            if action == "randomize":
                random.shuffle(var.playlist.playlist)
            elif action == "stop":
                var.botamusique.pause()
            elif action == "clear":
                var.botamusique.stop()
            elif action == "volume_up":
                if var.botamusique.volume + 0.03 < 1.0:
                    var.botamusique.volume = var.botamusique.volume + 0.03
                else:
                    var.botamusique.volume = 1.0
                logging.info("web: volume up to %d" % (var.botamusique.volume * 100))
            elif action == "volume_down":
                if var.botamusique.volume - 0.03 > 0:
                    var.botamusique.volume = var.botamusique.volume - 0.03
                else:
                    var.botamusique.volume = 0
                logging.info("web: volume down to %d" % (var.botamusique.volume * 100))

    return render_template('index.html',
                           all_files=files,
                           music_library=music_library,
                           os=os,
                           playlist=var.playlist,
                           user=var.user
                           )


@web.route('/upload', methods=["POST"])
def upload():
    file = request.files['file']
    if not file:
        return redirect("./", code=406)

    #filename = secure_filename(file.filename).strip()
    filename = file.filename
    if filename == '':
        return redirect("./", code=406)

    targetdir = request.form['targetdir'].strip()
    if targetdir == '':
        targetdir = 'uploads/'
    elif '../' in targetdir:
        return redirect("./", code=406)

    logging.info('Uploading file:')
    logging.info(' - filename:', filename)
    logging.info(' - targetdir:', targetdir)
    logging.info(' - mimetype:', file.mimetype)

    if "audio" in file.mimetype:
        storagepath = os.path.abspath(os.path.join(var.music_folder, targetdir))
        print('storagepath:',storagepath)
        if not storagepath.startswith(os.path.abspath(var.music_folder)):
            return redirect("./", code=406)

        try:
            os.makedirs(storagepath)
        except OSError as ee:
            if ee.errno != errno.EEXIST:
                return redirect("./", code=500)

        filepath = os.path.join(storagepath, filename)
        logging.info(' - filepath: ', filepath)
        if os.path.exists(filepath):
            return redirect("./", code=406)

        file.save(filepath)
        return redirect("./", code=302)
    else:
        return redirect("./", code=409)


@web.route('/download', methods=["GET"])
def download():
    if 'file' in request.args:
        requested_file = request.args['file']
        if '../' not in requested_file:
            folder_path = var.music_folder
            files = util.get_recursive_filelist_sorted(var.music_folder)

            if requested_file in files:
                filepath = os.path.join(folder_path, requested_file)
                try:
                    return send_file(filepath, as_attachment=True)
                except Exception as e:
                    self.log.exception(e)
                    self.Error(400)
    elif 'directory' in request.args:
        requested_dir = request.args['directory']
        folder_path = var.music_folder
        requested_dir_fullpath = os.path.abspath(os.path.join(folder_path, requested_dir)) + '/'
        if requested_dir_fullpath.startswith(folder_path):
            if os.path.samefile(requested_dir_fullpath, folder_path):
                prefix = 'all'
            else:
                prefix = secure_filename(os.path.relpath(requested_dir_fullpath, folder_path))
            zipfile = util.zipdir(requested_dir_fullpath, prefix)
            try:
                return send_file(zipfile, as_attachment=True)
            except Exception as e:
                self.log.exception(e)
                self.Error(400)

    return redirect("./", code=400)


if __name__ == '__main__':
    web.run(port=8181, host="127.0.0.1")
