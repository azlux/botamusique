# botamusique

======

Botamusique is a mumble bot which goal is to allow users to listen music together with its audio output.
Predicted functionalities will be ones you could expect from any classic music player.

Bot the can play :
- Radio url
- Youtube/Soundcloud URL (everything supported by youtube-dl)
- Local folder (disabled, I need to work on the web interface)

#### Web interface
* Disable * I need to work on it. Since I use this bot for radio, youtube/soundcloud and folder music, the web interace isn't ready.

You need to create a folder for all your music. Organize your music by subfolder.
The main folder needs to be declared in the config (with a '/' at the end)

#### Installation
1. You need python 3 with opuslib and protobuf (look at the requirement of pymumble)
2. The Bot uses ffmpeg, so you know what you have to do if ffmpeg isn't in your package manager. I personally use [this repository](http://repozytorium.mati75.eu/) on my raspberry.

Example installation commands for Debian and Ubuntu:
```
# apt install python3-venv
# apt install ffmpeg
$ git clone --recurse-submodules https://github.com/azlux/botamusique.git
$ cd botamusique
$ python -m venv venv
$ venv/bin/pip install -r requirements.txt
```

#### Starting the bot
`$ venv/bin/python mumbleBot.py -s HOST -u BOTNAME -P PASSWORD -p PORT -c CHANNEL`

The bot listen to the 8181 port so you should redirect to this one in you NAT configuration to let others peoples access the web interface. (DISABLED)

#### Custom commands
You can copy the file `configuration.default.ini` to `configuration.ini` and customize all variable.
you have the section :
- bot : basic configuration of the bot : comment, folder, volume at start ....
- command : you can customize the command you want for each action (if you put `help = helpme` , the bot will response to `!helpme` )
- radio : here you can have a list of default radio ( I can play a jazz radio with the command `!radio jazz`)
- strings : you can customize all string the bot can say.


2.TODO list

### TODOLIST

Check the issue #3
