class commands:
    PLAY_FILE = "file, f"
    PLAY_FILE_MATCH = "filematch, fm"
    PLAY_URL = "url"
    PLAY_RADIO = "radio"
    PLAY_PLAYLIST = "playlist"
    RB_QUERY = "rbquery"
    RB_PLAY = "rbplay"
    HELP = "help"
    PAUSE = "pause"
    PLAY = "p, play"
    STOP = "stop"
    REMOVE = "rm"
    CLEAR = "clear"
    SKIP = "skip"
    CURRENT_MUSIC = "np, now"
    VOLUME = "volume"
    KILL = "kill"
    STOP_AND_GETOUT = "oust"
    JOINME = "joinme"
    QUEUE = "queue"
    REPEAT = "repeat"
    RANDOM = "random"
    UPDATE = "update"
    LIST_FILE = "listfile"
    USER_BAN = "userban"
    USER_UNBAN = "userunban"
    URL_BAN = "urlban"
    URL_UNBAN = "urlunban"
    DUCKING = "duck"
    DUCKING_THRESHOLD = "duckthres"
    DUCKING_VOLUME = "duckv"
    DROP_DATABASE = "dropdatabase"


class strings:
    CURRENT_VOLUME = "Current volume: %d%%"
    CURRENT_DUCKING_VOLUME = "Volume on ducking: %d%%"
    CHANGE_VOLUME = "Volume set to %d%% by %s"
    CHANGE_DUCKING_VOLUME = "Volume on ducking set to %d%% by %s"
    BAD_COMMAND = "%s: command not found"
    BAD_PARAMETER = "%s: invalid parameter"
    ERROR_EXECUTING_COMMAND = "%s: Command failed with error: %s."
    NOT_ADMIN = "You are not an admin!"
    NOT_PLAYING = "Nothing is playing right now"
    NO_FILE = "File not found"
    WRONG_PATTERN = "Invalid regex: %s"
    FILE_ADDED = "Files add to playlist:"
    BAD_URL = "Bad URL requested"
    PRECONFIGURATED_RADIO = "Pre-configured Radio available"
    UNABLE_DOWNLOAD = "Error while downloading music..."
    WHICH_COMMAND = "Do you mean <br> %s"
    MULTIPLE_MATCHES = "Track not found! Possible candidates:"
    QUEUE_CONTENTS = "Items on the playlist:"
    QUEUE_EMPTY = "Playlist is empty!"
    NOW_PLAYING = "Now playing %s<br />%s"
    NOT_IN_MY_CHANNEL = "You're not in my channel, command refused!"
    PM_NOT_ALLOWED = "Private message aren't allowed."
    TOO_LONG = "This music is too long, skip!"
    DOWNLOAD_IN_PROGRESS = "Download of %s in progress"
    REMOVING_ITEM = "Removed entry %s from playlist"
    USER_BAN = "You are banned, not allowed to do that!"
    URL_BAN = "This url is banned!"
    RB_QUERY_RESULT = "This is the result of your query, send !rbplay 'ID' to play a station"
    RB_PLAY_EMPTY = "Please specify a radio station ID!"
    PAUSED = "Music paused."
    STOPPED = "Music stopped."
    CLEARED = "Playlist emptied."
    DATABASE_DROPPED = "Database dropped. All records have gone."
    NEW_VERSION_FOUND = "<h3>Update Available!</h3> New version of botamusique is available, send <i>!update</i> to update!"
    START_UPDATING = "Start updating..."
    HELP = '''
<h3>Commands</h3>
<b>Control</b>
<ul>
<li> <b>!play </b> (or <b>!p</b>) [{num}] - resume from pausing / start to play (the num-th song is num is given) </li>
<li> <b>!<u>pa</u>use </b> - pause </li>
<li> <b>!<u>st</u>op </b> - stop playing </li>
<li> <b>!<u>sk</u>ip </b> - jump to the next song </li>
<li> <b>!<u>v</u>olume </b> {volume} - get or change the volume (from 0 to 100) </li>
<li> <b>!duck </b> on/off - enable or disable ducking function </li>
<li> <b>!duckv </b> - set the volume of the bot when ducking is activated </li>
<li> <b>!<u>duckt</u>hres </b> - set the threshold of volume to activate ducking (3000 by default) </li>
</ul>
<b>Playlist</b>
<ul>
<li> <b>!<u>n</u>ow </b> (or <b>!np</b>) - display the current song </li>
<li> <b>!<u>q</u>ueue </b> - display items in the playlist </li>
<li> <b>!file </b>(or <b>!f</b>) {path/folder/index/keyword} - append file to the playlist by its path or index returned by !listfile </li>
<li> <b>!<u>filem</u>atch </b>(or <b>!fm</b>) {pattern} - add all files that match regex {pattern} </li>
<li> <b>!<u>ur</u>l </b> {url} - append youtube or soundcloud music to the playlist </li>
<li> <b>!<u>playl</u>ist </b> {url} [{offset}] - append items in a youtube or soundcloud playlist, and start with the {offset}-th item </li>
<li> <b>!rm </b> {num} - remove the num-th song on the playlist </li>
<li> <b>!<u>rep</u>eat </b> [{num}] - repeat current song {num} (1 by default) times.</li>
<li> <b>!<u>ran</u>dom </b> - randomize the playlist.</li>
<li> <b>!<u>rad</u>io </b> {url} - append a radio {url} to the playlist </li>
<li> <b>!<u>rbq</u>uery </b> {keyword} - query http://www.radio-browser.info for a radio station </li>
<li> <b>!<u>rbp</u>lay </b> {id} - play a radio station with {id} (eg. !rbplay 96746) </li>
<li> <b>!<u>l</u>istfile </b> [{pattern}] - display list of available files (that match the regex pattern if {pattern} is given) </li>
<li> <b>!<u>o</u>ust </b> - stop playing and go to default channel </li>
</ul>
<b>Other</b>
<ul>
<li> <b>!<u>j</u>oinme </b> - join your own channel </li>
</ul>
'''
    ADMIN_HELP = '''
<h3>Admin command</h3>
<ul>
<li><b>!<u>k</u>ill </b> - kill the bot</li>
<li><b>!<u>up</u>date </b> - update the bot</li>
<li><b>!<u>userb</u>an </b> {user}  - ban a user</li>
<li><b>!<u>useru</u>nban </b> {user}  - unban a user</li>
<li><b>!<u>urlb</u>an </b> {url}  - ban an url</li>
<li><b>!<u>urlu</u>nban </b> {url}  - unban an url</li>
<li><b>!dropdatabase</b> - clear the entire database, YOU SHOULD KNOW WHAT YOU ARE DOING.</li>
</ul>
'''
