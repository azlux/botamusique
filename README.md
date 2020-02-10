# botamusique

Botamusique is a mumble bot who plays music on a mumble channel.
Predicted functionalities will be those people would expect from any classic music player.

botamusique can play:
- Radio stations from url
- Radio stations from http://www.radio-browser.info API (query from > 24k stations)
- Youtube/Soundcloud URL (everything supported by youtube-dl)
- Music in local folders (which can be uploaded through a web interface)

-----
## Menu
1. [Web Interface](#web-interface)
2. [Installation](#installation)
3. [Update](#udpate)
4. [Generate a certificate](#optional-generate-a-certificate)
5. [Starting the bot](#starting-the-bot)
6. [Custom commands](#custom-commands)
7. [Known issues](#known-issues)
8. [Contributors](#contributors)


### Web interface
**Disabled by default.** You need to enable it in `configuration.ini`.
It works, and we are still making it better.

You need to create a folder for all your songs. Organize your songs by subfolder.
The main folder needs to be set in `configuration.ini` (with a '/' at the end).

### Installation
1. You need python3 with opuslib and protobuf (look at the requirement of pymumble).
2. The Bot uses ffmpeg, so you know what you have to do if ffmpeg isn't in your package manager. I personally use [this repository](http://repozytorium.mati75.eu/) on my raspberry.

To install botamusique (**recommended**, stable and with build-in auto-update support):
```
curl -Lo botamusique.tar.gz https://azlux.fr/botamusique/sources.tar.gz
tar -xzf botamusique.tar.gz
cd botamusique
python3 -m venv venv
venv/bin/pip install wheel
venv/bin/pip install -r requirements.txt
```

For the version of the master branch, you can use Git installation commands (no build-in auto-update support):
```
apt install python3-venv ffmpeg libjpeg-dev zlibc zlib1g zlib1g-dev
git clone --recurse-submodules https://github.com/azlux/botamusique.git
cd botamusique
python3 -m venv venv
venv/bin/pip install wheel
venv/bin/pip install -r requirements.txt
```

### Update
If using the recommended install, you can send `!update` to the bot (command by default).

If using git, you need to update manually:
```
git pull --all
git submodule update
venv/bin/pip install --upgrade -r requirements.txt
```


### (Optional) Generate a certificate
`$ openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout botamusique.pem -out botamusique.pem -subj "/CN=botamusique"`

### Starting the bot
`$ venv/bin/python mumbleBot.py -s HOST -u BOTNAME -P PASSWORD -p PORT -c CHANNEL -C /path/to/botamusique.pem`

The bot listens the 8181 port so you should properly set the forwarding rules in you NAT configuration to let other peoples access the web interface. (DISABLED)

If you want information about autoStart and auto-Restart the bot, [you can have help on the wiki.](https://github.com/azlux/botamusique/wiki/AutoStart---AutoRestart)

### Configuration
You can copy the file `configuration.default.ini` into `configuration.ini` and customize all variable. Everything can be changed but don't remove the default file.

Sections explained:
- `server`: configuration about the server and bot name. This is overridden by the `./mumbleBot.py` parameters.
- `bot`: basic configuration of the bot, eg. comment, folder, default volume, etc.
- `webinterface`: basic configuration about the interface (disabled by default)
- `command`: you can customize the command you want for each action (if you put `help = helpme` , the bot will respond to `!helpme` )
- `radio`: here you can provide a list of default radio ( I can play a jazz radio with the command `!radio jazz`)
- `strings`: you can customize all string the bot can say.
- `debug`: option to activate ffmpeg or pymumble debug. (Can be very verbose)

### Known Issues

During installation, you may encounter the following error:
```
ImportError: libtiff.so.5: cannot open shared object file: No such file or directory
```
You need to install a missing library: `apt install libtiff5`

---

In the beginning, you may encounter the following error even if you have installed all requirements:
```
Exception: Could not find opus library. Make sure it is installed.
```
You need to install the opus codec (not embedded in all system): `apt install libopus0`

### Contributors
If you want to participate, You're welcome to fork and submit pull requests (fixes and new features).

The following people joined the collaborators for a faster development, big thanks:
- @slipenbois
- @mertkutay

Feel free to ask me if you want to help actively without using pull requests.
