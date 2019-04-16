# botamusique

Botamusique is a mumble bot which goal is to allow users to listen music together with its audio output.
Predicted functionalities will be ones you could expect from any classic music player.

Bot the can play :
- Radio url
- Youtube/Soundcloud URL (everything supported by youtube-dl)
- Local folder (disabled, I need to work on the web interface)

-----
## Menu
1. [Web Interface](#web-interface)
2. [Installation](#installation)
3. [Generate a certificate](#optional-generate-a-certificate)
4. [Starting the bot](#starting-the-bot)
5. [Custom commands](#custom-commands)
6. [Contributors](#contributors)


### Web interface
* Disabled by default. It's working but ugly (I'm not a web developer).

You need to create a folder for all your music. Organize your music by subfolder.
The main folder needs to be declared in the config (with a '/' at the end)
You can enable the web interface into the configuration.ini file.

### Installation
1. You need python 3 with opuslib and protobuf (look at the requirement of pymumble)
2. The Bot uses ffmpeg, so you know what you have to do if ffmpeg isn't in your package manager. I personally use [this repository](http://repozytorium.mati75.eu/) on my raspberry.

Example installation commands for Debian and Ubuntu:
```
apt install python3-venv ffmpeg libjpeg-dev zlibc zlib1g zlib1g-dev
git clone --recurse-submodules https://github.com/azlux/botamusique.git
cd botamusique
python3 -m venv venv
venv/bin/pip install wheel
venv/bin/pip install -r requirements.txt
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
- strings : you can customize all string the bot can say.
- debug : option to active ffmpeg or pymumble debug. (Can be very verbose)

### Contributors
If you want to participate, You're welcome to fork and pull requests Fix et new features.

The following people joined the collaborators for a faster development, big thanks:
- @slipenbois
- @mertkutay

Feel free to ask me if you want to help activelly without using pull requests. 
