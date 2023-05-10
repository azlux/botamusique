<div align="center">
<img src="static/image/logo.png" alt="botamusique" width="200px" />
<h1>botamusique</h1>
</div>

Botamusique is a [Mumble](https://www.mumble.info/) music bot.
Predicted functionalities will be those people would expect from any classic music player.

[![Build Status](https://ci.azlux.fr/api/badges/azlux/botamusique/status.svg)](https://ci.azlux.fr/azlux/botamusique)

## Features

1. **Support multiple music sources:**
    - Music files in local folders (which can be uploaded through the web interface).
    - Youtube/Soundcloud URLs and playlists (everything supported by youtube-dl).
    - Radio stations from URL and http://www.radio-browser.info API.
2. **Modern and powerful web remote control interface.** Powered by Flask. Which supports:
    - Playlist management.
    - Music library management, including uploading, browsing all files and edit tags, etc.
3. **Powerful command system.** Commands and words the bot says are fully customizable. Support partial-match for commands.
4. **Ducking.** The bot would automatically lower its volume if people are talking.
5. **Stereo sound.** After Mumble 1.4.0, stereo output support has been added. Our bot is designed to work nicely with it naturally.
6. **Multilingual support.** A list of supported languages can be found below.


## Screenshots

![botamusique in Mumble channel](https://user-images.githubusercontent.com/2306637/75210917-68fbf680-57bd-11ea-9cf8-c0871edff13f.jpg)

![botamusique web interface](https://user-images.githubusercontent.com/2306637/77822763-b4911f80-7130-11ea-9bc5-83c36c995ab9.png)

-----
## Quick Start Guide
1. [Installation](#installation)
1. [Configuration](#configuration)
1. [Run the bot](#run-the-bot)
1. [Operate the bot](#operate-the-bot)
1. [Update](#update)
1. [Known issues](#known-issues)
1. [Contributors](#contributors)

## Installation

### Dependencies
1. Install python. We require a python version of 3.6 or higher.
1. Install [Opus Codec](https://www.opus-codec.org/) (which should be already installed if you installed Mumble or Murmur, or you may try to install `opus-tools` with your package manager).
1. Install ffmpeg. If ffmpeg isn't in your package manager, you may need to find another source. I personally use [this repository](http://repozytorium.mati75.eu/) on my raspberry.


### Docker
See https://github.com/azlux/botamusique/wiki/Docker-install

Both stable and nightly (developing) builds are available!

### Manual install

**Stable release (recommended)**

This is current stable version, with auto-update support. To install the stable release, run these lines in your terminal:
```
curl -Lo botamusique.tar.gz http://packages.azlux.fr/botamusique/sources-stable.tar.gz
tar -xzf botamusique.tar.gz
cd botamusique
python3 -m venv venv
venv/bin/pip install wheel
venv/bin/pip install -r requirements.txt
```

**Nightly build (developing version)**
<details>
  <summary>Click to expand!</summary>

This build reflects any newest change in the master branch, with auto-update support baked in. This version follow all commits into the master branch.
```
curl -Lo botamusique.tar.gz http://packages.azlux.fr/botamusique/sources-testing.tar.gz
tar -xzf botamusique.tar.gz
cd botamusique
python3 -m venv venv
venv/bin/pip install wheel
venv/bin/pip install -r requirements.txt
```
</details>

**Build from source code**
<details>
  <summary>Click to expand!</summary>

You can checkout the master branch of our repo and compile everything by yourself.
We will test new features in the master branch, maybe sometimes post some hotfixes.
Please be noted that the builtin auto-update support doesn't track this version.
If you have no idea what these descriptions mean to you, we recommend you install the stable version above.
```
git clone https://github.com/azlux/botamusique.git
cd botamusique
python3 -m venv venv
venv/bin/pip install wheel
venv/bin/pip install -r requirements.txt
(cd web && npm install && npm run build)
venv/bin/python3 ./scripts/translate_templates.py --lang-dir lang/ --template-dir templates/
```
</details>

## Configuration
Please copy `configuration.example.ini` into `configuration.ini`, follow the instructions in that file and uncomment options you would like to modify. Not all sections are needed. You may just keep the options that matter to you. For example, if you only would like to set `host`, all you need you is keep 
```
[server]
host=xxxxxx
```
in your `configuration.ini`.

Please DO NOT MODIFY `configuration.default.ini`, since if the bot realizes one option is undefined in `configuration.ini`, it will look into `configuration.default.ini` for the default value of that option. This file will be constantly overridden in each update.

We list some basic settings for you to quickly get things working.

### Basic settings
1. Usually, the first thing is to set the Murmur server you'd like the bot to connect to. You may also specify which channel the bot stays, and tokens used by the bot.
```
[server]
host = 127.0.0.1
port = 64738
```

2. You need to specify a folder that stores your music files. The bot will look for music and upload files into that folder. You also need to specify a temporary folder to store music file downloads from URLs.
```
[bot]
music_folder = music_folder/
tmp_folder = /tmp/
```

3. **Web interface is disabled by default** for performance and security reasons. It is extremely powerful, so we encourage you to have a try. To enable it, set
```
[webinterface]
enabled = True
```

Default binding address is
```
listening_addr = 127.0.0.1
listening_port = 8181
```

You can access the web interface through http://127.0.0.1:8181 if you keep it unchanged.

Note: Listening to address `127.0.0.1` will only accept requests from localhost. _If you would like to connect from the public internet, you need to set it to `0.0.0.0`, and set up username and password to impose access control._ In addition, if the bot is behind a router, you should also properly set forwarding rules in you NAT configuration to forward requests to the bot.

4. The default language is English, but you can change it in `[bot]` section:
```
[bot]
language=en_US
```

Available translations can be found inside `lang/` folder. Currently, options are

 - `en_US`, English
 - `es_ES`, Spanish
 - `fr_FR`, French
 - `it_IT`, Italian
 - `ja_JP`, Japanese
 - `zh_CN`, Chinese

5. Generate a certificate (Optional, but recommended)

By default, murmur server uses certificates to identify users. Without a valid certificate, you wouldn't able to register the bot into your Murmur server. Some server even refused users without a certificate. Therefore, it is recommended to generate a certificate for the bot. If you have a certificate (for say, `botmusique.pem` in the folder of the bot), you can specify its location in
```
[server]
certificate=botamusique.pem
```

If you don't have a certificate, you may generate one by:
`openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout botamusique.pem -out botamusique.pem -subj "/CN=botamusique"`


### Sections explained
- `server`: configuration about the server. Will be overridden by the `./mumbleBot.py` parameters.
- `bot`: basic configuration of the bot, eg. name, comment, folder, default volume, etc.
- `webinterface`: basic configuration about the web interface.
- `commands`: you can customize the command you want for each action (eg. put `help = helpme` , the bot will respond to `!helpme`)
- `radio`: a list of default radio (eg. play a jazz radio with the command `!radio jazz`)
- `debug`: option to activate ffmpeg or pymumble debug output.


## Run the bot
If you have set up everything in your `configuration.ini`, you can
`venv/bin/python mumbleBot.py --config configuration.ini`

Or you can
`venv/bin/python mumbleBot.py -s HOST -u BOTNAME -P PASSWORD -p PORT -c CHANNEL -C /path/to/botamusique.pem`

If you want information about auto-starting and auto-restarting of the bot, you can check out the wiki page [Run botamusique as a daemon In the background](https://github.com/azlux/botamusique/wiki/Run-botamusique-as-a-daemon-In-the-background).

**For the detailed manual of using botamusique, please see the [wiki](https://github.com/azlux/botamusique/wiki).**

## Operate the bot

You can control the bot by both commands sent by text message and the web interface.

By default, all commands start with `!`. You can type `!help` in the text message to see the full list of commands supported, or see the examples on the [wiki page](https://github.com/azlux/botamusique/wiki/Command-Help-and-Examples).

The web interface can be used if you'd like an intuitive way of interacting with the bot. Through it is fairly straightforward, a walk-through can be found on the [wiki page](https://github.com/azlux/botamusique/wiki/Web-interface-walk-through).

## Update

If you enable `auto_check_update`, the bot will check for updates every time it starts.
If you are using the recommended install, you can send `!update` to the bot (command by default).

If you are using git, you need to update manually:
```
git pull --all
git submodule update
venv/bin/pip install --upgrade -r requirements.txt
```


## Known issues

1. During installation, you may encounter the following error:
```
ImportError: libtiff.so.5: cannot open shared object file: No such file or directory
```
You need to install a missing library: `apt install libtiff5`

2. In the beginning, you may encounter the following error even if you have installed all requirements:
```
Exception: Could not find opus library. Make sure it is installed.
```
You need to install the opus codec (not embedded in all system): `apt install libopus0`

3. MacOS Users may encounter the following error:
```
ImportError: failed to find libmagic.  Check your installation
```
This is caused by missing `libmagic` binaries and can be solved by
```bash
brew install libmagic

```
One may also install `python-magic-bin` instead of `python-magic`.

5. If you have a large amount of music files (>1000), it may take some time for the bot to boot, since
it will build up the cache for the music library on booting. You may want to disable this auto-scanning by
setting ``refresh_cache_on_startup=False`` in `[bot]` section and control the scanning manually by
``!rescan`` command and the *Rescan Files* button on the web interface.

6. Alpine Linux requires some extra dependencies during the installation (in order to compile Pillow):
```
python3-dev musl-lib libmagic jpeg-dev zlib-dev gcc
```
For more information, see [#122](https://github.com/azlux/botamusique/issues/122).

## _I need help!_

If you ran into some problems in using the bot, or discovered bugs and want to talk to us, you may

 - Start a new issue,
 - Ask in the Matrix channel of Mumble [#mumble:matrix.org](https://matrix.to/#/#mumble:matrix.org) (we are usually there to help).

## Contributors
If you want to help us develop, you're welcome to fork and submit pull requests (fixes and new features).
We are looking for people helping us translating the bot. If you'd like to add a new language or fix errors in existed translations,
feel free to catch us in the IRC channel #mumble, or just email us!

The following people joined as collaborators for a faster development, big thanks to them:
- @TerryGeng
- @mertkutay

Feel free to ask me if you want to help actively without using pull requests.
