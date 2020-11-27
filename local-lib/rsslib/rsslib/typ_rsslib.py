# -*- coding: utf-8 -*-

import configparser
import feedparser
from urllib.parse import urlparse
import json
import time
import hashlib

import util
from constants import tr_lib as trl, tr_cli as tr
#import variables as var


# TODO:
# commands(**kargs) since __init__ self.bot


# Index module
route_map = {}
def command(trig, no_partial_match=True, admin=True, methods=['handle']):
    def inner_decorator(f):
        if trig not in route_map:
            route_map[trig] = {}
            route_map[trig]['no_partial_match'] = no_partial_match
            route_map[trig]['admin'] = admin
            for method in methods:
                route_map[trig][method] = f
        return f
    return inner_decorator


class Rss():
    def __init__(self, bot):
        self.bot = bot
        self.load_config()
        self.result = trl('no_result', 'rsslib')
        self.new_entries = {}
        self.queued_entries = []
        self.prev_hash = ''

    @command('getrss', no_partial_match=False, admin=False)
    def cmd_getrss(self, bot, user, text, command, parameter):
        self.get_latest(skip_prev=True)
        self.send_feed(text.actor)

    @command('subrss', no_partial_match=False, admin=False)
    def cmd_subrss(self, bot, user, text, command, parameter):
        try:
            user_id = self.bot.mumble.users[text.actor]['user_id']
        except KeyError:
            self.bot.mumble.users[text.actor].send_text_message(f"I'm sorry, you need to be server registerd for this feature")
            return
        if not user_id in self.subbed_users:
            text_actor = self.resolve_registered_user(user_id)
            if text_actor:
                self.subbed_users.append(user_id)
                self.config.set('subscriptions','subbed_users', str(self.subbed_users))
                self.save_config()
                self.bot.mumble.users[text_actor].send_text_message(f'You are now subscribed to the RSS feed')
            else:
                self.bot.log.debug(f'cmd_subrss: error text_actor: "{text_actor}", user_id: {user_id}')
        else:
            self.bot.mumble.users[text.actor].send_text_message(f'You already subscribed to the RSS feed')

    @command('unsubrss', no_partial_match=False, admin=False)
    def cmd_unsubrss(self, bot, user, text, command, parameter):
        try:
            user_id = self.bot.mumble.users[text.actor]['user_id']
        except KeyError:
            self.bot.mumble.users[text.actor].send_text_message(f"I'm sorry, you need to be server registerd for this feature")
            return

        if user_id in self.subbed_users:
            self.subbed_users.remove(user_id)
            self.config.set('subscriptions','subbed_users', str(self.subbed_users))
            self.save_config()
            if not user_id in self.subbed_users:
                self.bot.mumble.users[text.actor].send_text_message(f'You unsubscribed from the RSS feed')
            else:
               self.bot.mumble.users[text.actor].send_text_message(f'Sorry, you are still subscribed to the RSS feed (Error).\n your id:{user_id}')
        else:
            self.bot.mumble.users[text.actor].send_text_message(f'You already unsubscribed from the RSS feed')

    @command('setrss')
    def cmd_urlrss(self, bot, user, text, command, parameter):
        if not parameter:
            self.bot.mumble.users[text.actor].send_text_message(tr('bad_parameter', command=command))
            return
        url = util.get_url_from_input(parameter.strip())
        if url:
            self.rss_url = url
            self.config.set('feeds','rssfeed', self.rss_url)
            self.save_config()
            self.bot.mumble.users[text.actor].send_text_message(f'The url of the RSS feed is now set to: <i>{self.rss_url}</i>')
        else:
            self.bot.mumble.users[text.actor].send_text_message(tr('bad_parameter', command=command))

    @command('stoprss')
    def cmd_stoprss(self, bot, user, text, command, parameter):
        if self.checkrss:
            self.checkrss = False
            self.bot.mumble.users[text.actor].send_text_message(f'RSS feed monitoring is now: {self.booleantext(self.checkrss)}')
        else:
            self.bot.mumble.users[text.actor].send_text_message(f'RSS feed monitoring is already: {self.booleantext(self.checkrss)}')

    @command('startrss')
    def cmd_startrss(self, bot, user, text, command, parameter):
        if not self.checkrss:
            self.checkrss = True
            self.bot.mumble.users[text.actor].send_text_message(f'RSS feed monitoring is now: {self.booleantext(self.checkrss)}')
        else:
            self.bot.mumble.users[text.actor].send_text_message(f'RSS feed monitoring is already: {self.booleantext(self.checkrss)}')

    def booleantext(self, value):
        if value:
            return 'On'
        else:
            return 'Off'

    def resolve_registered_user(self, user_id):
        for user in self.bot.mumble.users:
            if self.bot.mumble.users[user]['session'] == self.bot.mumble.users.myself['session']:
                continue
            try:
                if self.bot.mumble.users[user]['user_id'] == user_id:
                    return self.bot.mumble.users[user]['session']
            except KeyError: # Unregisterd
                continue
        return False

    def send_feed(self, text_actor=None):
        # Send to rss channel and subsribed users or specified user
        rss_channel = self.bot.mumble.channels[self.rss_channel_id]
        if text_actor == None:
            # To subbed users
            for user_id in self.subbed_users:
                text_actor = self.resolve_registered_user(user_id)
                if text_actor:
                    # Skip if user in my channel
                    if self.bot.mumble.users[text_actor]['channel_id'] == self.rss_channel_id:
                        pass
                    else:
                        self.bot.mumble.users[text_actor].send_text_message(self.result)
                else:
                    self.bot.log.debug(f'send_feed: error text_actor: "{text_actor}"')
            # To channel
            rss_channel.send_text_message(self.result)
        else:
            # To specific user
            self.bot.mumble.users[text_actor].send_text_message(self.result)

    def get_latest(self, skip_prev=True):
        len_entries = len(self.queued_entries)
        self.get_feeds()
        self.bot.log.debug(f'get_latest: queue/entries: {len(self.queued_entries)}/{len_entries}')
        for i in self.queued_entries:
            self.bot.log.debug(f"\t{i[1]['updated']}")
            self.bot.log.debug(f"\t{i[1]['title']}")
            self.bot.log.debug(f"\t{i[0]}\n")

        # Prepare first entry on list as self.result
        if not len_entries == 0:
            if skip_prev:
                entry = self.queued_entries.reverse()

            entry = self.queued_entries[len_entries-1]
            title = entry[1]['title']
            updated = entry[1]['updated']
            summary = entry[1]['summary']
            link = entry[1]['link']
            domain = urlparse(self.rss_url).netloc
            read_more = trl('read_more', 'rsslib' )

            # Save entry result and remove from queue
            self.result = f'<br><i>{updated}</i><br><b>{title}</b><br><br>{summary}<br><br>{read_more} <a href="{link}">{domain}</a>'
            self.bot.log.debug(f'get_latest: RSS entry : {self.result}')

            self.prev_hash = entry[0]
            self.previous_entry = self.prev_hash
            self.config.set('feeds','previous_entry', self.previous_entry)
            self.save_config()

            # Just walk list, until skip_prev*(a way to get rid of long list spam at first initial run of feed)
            self.queued_entries.remove(entry)
            if skip_prev:
                self.queued_entries = []
                return True

            if len(self.queued_entries) >= 1:
                return True
            else:
                return False
        else:
            self.bot.log.debug(f'get_latest: RSS nothing new')
            return False

    def get_feeds(self):
        if len(self.queued_entries) == 0:
            new_entries = {}
            self.bot.log.debug(f'get_feeds: obtain new RSS entry list...')
            NewsFeed = feedparser.parse(self.rss_url)
            if NewsFeed.status == 200:
                for entry in NewsFeed.entries:
                    title = entry['title']
                    sha1_title = hashlib.sha1(title.encode('utf-8')).hexdigest()
                    new_entries[sha1_title] = entry
                # Filter entries up to known last item sha1
                for entry in new_entries:
                    if entry == self.previous_entry:
                        # skip the rest
                        self.bot.log.debug(f'get_feeds: skipping all the left over entries at entry : {entry}')
                        break
                    elif entry not in self.queued_entries:
                        self.queued_entries.append([entry, new_entries[entry]])
                # Make entry list old to new.
                self.queued_entries.reverse()
                return True
            else:
                self.bot.log.debug(f'get_feeds: Some connection error {NewsFeed.status}')
            return False

    def track_channel(self): # *mv => class util TrackChannelIdent()
        # Keep track of channel name changes, deletion, creation
        def channel_resolver(channels, channel, ident):
            def name_exist(channels, name):
                if name == '':
                    return False
                if name == False:
                    return False
                for obj in channels:
                    if channels[obj]['name'] == name:
                        return channels[obj]
                return False

            def id_exist(channels, ident):
                if ident == '':
                    return False
                if ident == False:
                    return False
                if ident in channels:
                    return channels[ident]
                else:
                    return False

            cname, cid = name_exist(channels, channel), id_exist(channels, ident)
            if cname and not cid:
                return 'resolved_id', cname['name'], cname['channel_id']
            elif not cname and cid:
                return 'resolved_name', cid['name'], cid['channel_id']
            elif cname and cid:
                if (cname['name'] == cid['name']) and (cname['channel_id'] == cid['channel_id']):
                    return 'ok', cname['name'], cname['channel_id']
                else:
                    self.bot.log.debug(f'channel_resolver: param_err cname/cid\n{cname}\n / \n{cid}')
                    return 'param_err', False, False
            elif not cname and not cid:
                return 'removed', False, False

        status, channel, channel_id = channel_resolver(self.bot.mumble.channels, self.rss_channel, self.rss_channel_id)
        if status == 'resolved_id':
            self.rss_channel_id = channel_id
            self.config.set('config','rss_channel_id',str(channel_id))
            self.save_config()
            return True
        elif status == 'resolved_name':
            self.rss_channel = channel
            self.config.set('config','rss_channel', channel)
            self.save_config()
            return True
        elif status == 'removed':
            if self.rss_channel_id != '':
                self.rss_channel_id = channel_id
                self.config.set('config','rss_channel_id', '')
                self.save_config()
            return False
        elif status == 'ok':
            return True

    def load_config(self):
        cfgdef = 'local-lib/rsslib/libconfiguration.default.ini'
        self.cfg = 'local-lib/rsslib/libconfiguration.ini'
        self.config = configparser.ConfigParser(interpolation=None, allow_no_value=True)
        parsed_configs = self.config.read([util.solve_filepath(cfgdef), util.solve_filepath(self.cfg)],
                                      encoding='utf-8')
        if len(parsed_configs) == 0:
            self.bot.log.error(f'load_config: Could not read configuration from {self.cfg}')

        self.autostart = self.config.getboolean('config','autostart')
        self.rss_channel = self.config.get('config','rss_channel')
        if self.rss_channel == '':
            self.bot.log.info(f'\n[RSSLib] rss_channel not set in libconfiguration.ini')
        self.checkrss = self.autostart

        # Obtain integer from configuration string
        try:
            self.rss_channel_id = self.config.getint('config','rss_channel_id')
        except ValueError:
            self.rss_channel_id = ''

        self.rss_url = self.config.get('feeds','rssfeed')
        self.previous_entry = self.config.get('feeds','previous_entry')
        self.interval = self.config.getint('feeds','interval_mins')
        self.subbed_users = json.loads(self.config.get('subscriptions','subbed_users'))
        self.bot.log.info(f'\n[RSSLib]\nfeed:\n\t{self.rss_url}\ninterval:\n\t{self.interval}mins.\nautostart:\n\t{self.autostart}')

    def save_config(self):
        with open(self.cfg, 'w') as configfile:
            self.config.write(configfile)

    def task_rss(self, state):
        self.bot.log.debug(f'task_rss: initialized...')
        while True:
            try:
                if state[0] == util.TaskState.started:
                    self.bot.log.debug(f'task_rss: idle, waiting for release...')
                elif state[0] == util.TaskState.released:
                    if self.checkrss:
                        if self.track_channel():
                            if self.get_latest(skip_prev=False):
                                self.send_feed()
                    else:
                        state[0] = util.TaskState.paused
                elif state[0] == util.TaskState.paused:
                    self.bot.log.debug(f'task_rss: idle/paused, waiting for release')
                    # Resume requests by command
                    if self.checkrss:
                        state[0] = util.TaskState.released
                else:
                    self.bot.log.debug(f'task_rss: ending...')
                    state[0] = util.TaskState.stopped
                    break
            except Exception as loop_error:
                self.bot.log.debug(f'task_rss: exception:\n {loop_error}')
                state[0] = util.TaskState.stopped
                break
            time.sleep(self.interval*60)


def load_mod(bot):
    if feedparser is None:
        raise NameError(f'rsslib.typical.loadmod: feedparser required, `venv/bin/python -m pip install feedparser`')
    lib = Rss(bot)
    lib_name=type(lib).__name__
    bot.register_lib(lib_name=lib_name, handle=lib, route_map=route_map)

    # Create rss task
    task_name=lib.task_rss.__name__
    bot.create_task(task_name, lib.task_rss)

