# botamusique

Botamusique is a mumble bot which goal is to allow users to listen music together with its audio output.
Predicted functionalities will be ones you could expect from any classic music player.

Bot the can play :
- Radio station from url
- Radio station from http://www.radio-browser.info API (query from > 24k stations)
- Youtube/Soundcloud URL (everything supported by youtube-dl)
- Local folder (disabled, I need to work on the web interface)

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
* Disabled by default. It's working but ugly (I'm not a web developer).

You need to create a folder for all your music. Organize your music by subfolder.
The main folder needs to be declared in the config (with a '/' at the end)
You can enable the web interface into the configuration.ini file.

### Installation
1. You need python 3 with opuslib and protobuf (look at the requirement of pymumble)
2. The Bot uses ffmpeg, so you know what you have to do if ffmpeg isn't in your package manager. I personally use [this repository](http://repozytorium.mati75.eu/) on my raspberry.

To Install botamusique (stable and build-in auto-update):
```
curl -Lo botamusique.tar.gz https://azlux.fr/botamusique/sources.tar.gz
tar -xzf botamusique.tar.gz
cd botamusique
python3 -m venv venv
venv/bin/pip install wheel
venv/bin/pip install -r requirements.txt
```

For the master version, you can use Git installation commands (no build-in auto-update allowed):
```
apt install python3-venv ffmpeg libjpeg-dev zlibc zlib1g zlib1g-dev
git clone --recurse-submodules https://github.com/azlux/botamusique.git
cd botamusique
python3 -m venv venv
venv/bin/pip install wheel
venv/bin/pip install -r requirements.txt
```

### Update
If using the recommanded install, you can send to the bot `!update`(command by default)

If using git, you need to make the update manually:
```
git pull --all
git submodule update
venv/bin/pip install --upgrade -r requirements.txt
```


### (Optional) Generate a certificate
`$ openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout botamusique.pem -out botamusique.pem -subj "/CN=botamusique"`

### Starting the bot
`$ venv/bin/python mumbleBot.py -s HOST -u BOTNAME -P PASSWORD -p PORT -c CHANNEL -C /path/to/botamusique.pem`

The bot listen to the 8181 port so you should redirect to this one in you NAT configuration to let others peoples access the web interface. (DISABLED)

If you want information about autoStart and auto-Restart the bot, [you can have help on the wiki.](https://github.com/azlux/botamusique/wiki/AutoStart---AutoRestart)

### Custom commands
You can copy the file `configuration.default.ini` to `configuration.ini` and customize all variable. Everything can be change but don't remove the default file.

you have the section :
- server : configuration about the server and bot name. This is overrided by the `./mumbleBot.py` parameters.
- bot : basic configuration of the bot : comment, folder, volume at start ....
- webinterface : basic configuration about the interface (disabled by default)
- command : you can customize the command you want for each action (if you put `help = helpme` , the bot will response to `!helpme` )
- radio : here you can have a list of default radio ( I can play a jazz radio with the command `!radio jazz`)
- rbquery : search http://www.radio-browser.info API for listed radio stations - eg: `!rbquery nora`
- rbplay : Play a specific radio station by ID (from rbquery) - eg: `!rbplay 96748`
- strings : you can customize all string the bot can say.
- debug : option to activate ffmpeg or pymumble debug. (Can be very verbose)

### Known Issues

During installation, you can have the error:
```
ImportError: libtiff.so.5: cannot open shared object file: No such file or directory
```
You need to install a missing system librairie: `apt install libtiff5`

### Contributors
If you want to participate, You're welcome to fork and pull requests (fixes and new features).

The following people joined the collaborators for a faster development, big thanks:
- @slipenbois
- @mertkutay

Feel free to ask me if you want to help activelly without using pull requests. 
