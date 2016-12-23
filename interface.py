#!/usr/bin/python3

from flask import Flask, render_template, request
import variables as var
import os.path
from os import listdir
import random

web = Flask(__name__)


@web.route("/", methods=['GET', 'POST'])
def index():
    folder_path = var.music_folder
    files = {}
    dirs = [f for f in listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    for director in dirs:
        files[director] = [f for f in listdir(folder_path + director) if os.path.isfile(os.path.join(folder_path + director, f))]

    if request.method == 'POST':
        if 'add_music' in request.form and ".." not in request.form['add_music']:
            var.playlist.append(request.form['add_music'])
        if 'add_folder' in request.form and ".." not in request.form['add_folder']:
            var.playlist.extend(files[request.form['add_folder']])
        elif 'delete_music' in request.form:
            var.playlist.remove(request.form['delete_music'])
        elif 'action' in request.form:
            action = request.form['action']
            if action == "randomize":
                random.shuffle(var.playlist)
    if var.current_music:
        current_music = var.current_music[len(var.music_folder):]
    else:
        current_music = None

    return render_template('index.html',
                           current_music=current_music,
                           user=var.user,
                           playlist=var.playlist,
                           all_files=files
                           )


if __name__ == '__main__':
    web.run(port=8181, host="0.0.0.0")
