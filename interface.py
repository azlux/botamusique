#!/usr/bin/python3

from flask import Flask, render_template, request, redirect, send_file
import variables as var
import util
from datetime import datetime
import os.path
import random
from werkzeug.utils import secure_filename
import errno
import media


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


@web.route("/", methods=['GET', 'POST'])
def index():
    folder_path = var.music_folder
    files = util.get_recursive_filelist_sorted(var.music_folder)
    music_library = util.Dir(folder_path)
    for file in files:
        music_library.add_file(file)

    if request.method == 'POST':
        print(request.form)
        if 'add_file' in request.form and ".." not in request.form['add_file']:
            item = {'type': 'file',
                    'path' : request.form['add_file'],
                    'user' : 'Web'}
            var.playlist.append(item)

        elif ('add_folder' in request.form and ".." not in request.form['add_folder']) or ('add_folder_recursively' in request.form and ".." not in request.form['add_folder_recursively']):
            try:
                folder = request.form['add_folder']
            except:
                folder = request.form['add_folder_recursively']

            if not folder.endswith('/'):
                folder += '/'

            print('folder:', folder)
            if 'add_folder_recursively' in request.form:
                files = music_library.get_files_recursively(folder)
            else:
                files = music_library.get_files(folder)
            files = list(map(lambda file: {'type':'file','path': os.path.join(folder, file), 'user':'Web'}, files))
            print('Adding to playlist: ', files)
            var.playlist.extend(files)

        elif 'add_url' in request.form:
            var.playlist.append({'type':'url',
                                'url': request.form['add_url'],
                                'user': 'Web',
                                'ready': 'validation'})
            media.url.get_url_info()
            var.playlist[-1]['ready'] = "no"

        elif 'add_radio' in request.form:
            var.playlist.append({'type': 'radio',
                                'path': request.form['add_radio'],
                                'user': "Web"})

        elif 'delete_music' in request.form:
            if len(var.playlist) >= request.form['delete_music']:
                var.playlist.pop(request.form['delete_music'])
        
        elif 'action' in request.form:
            action = request.form['action']
            if action == "randomize":
                random.shuffle(var.playlist)

    return render_template('index.html',
                           all_files=files,
                           music_library=music_library,
                           os=os,
                           playlist=var.playlist,
                           user=var.user)


def upload():
    file = request.files['file']
    if not file:
        return redirect("./", code=406)

    filename = secure_filename(file.filename).strip()
    if filename == '':
        return redirect("./", code=406)

    targetdir = request.form['targetdir'].strip()
    if targetdir == '':
        targetdir = 'uploads/'
    elif '../' in targetdir:
        return redirect("./", code=406)

    # print('Uploading file:')
    # print('filename:', filename)
    # print('targetdir:', targetdir)
    # print('mimetype:', file.mimetype)

    if "audio" in file.mimetype:
        storagepath = os.path.abspath(os.path.join(var.music_folder, targetdir))
        if not storagepath.startswith(var.music_folder):
            return redirect("./", code=406)

        try:
            os.makedirs(storagepath)
        except OSError as ee:
            if ee.errno != errno.EEXIST:
                return redirect("./", code=500)

        filepath = os.path.join(storagepath, filename)
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
