import os
import re
import sqlite3
import json
import datetime
import time
import logging

log = logging.getLogger("bot")


class DatabaseError(Exception):
    pass


class Condition:
    def __init__(self):
        self.filler = []
        self._sql = ""
        self._limit = 0
        self._offset = 0
        self._order_by = ""
        self._desc = ""
        self.has_regex = False
        pass

    def sql(self, conn: sqlite3.Connection = None):
        sql = self._sql
        if not self._sql:
            sql = "1"
        if self._order_by:
            sql += f" ORDER BY {self._order_by}"
            if self._desc:
                sql += " DESC"
        if self._limit:
            sql += f" LIMIT {self._limit}"
        if self._offset:
            sql += f" OFFSET {self._offset}"
        if self.has_regex and conn:
            conn.create_function("REGEXP", 2, self._regexp)

        return sql

    @staticmethod
    def _regexp(expr, item):
        if not item:
            return False
        reg = re.compile(expr)
        return reg.search(item) is not None

    def or_equal(self, column, equals_to, case_sensitive=True):
        if not case_sensitive:
            column = f"LOWER({column})"
            equals_to = equals_to.lower()

        if self._sql:
            self._sql += f" OR {column}=?"
        else:
            self._sql += f"{column}=?"

        self.filler.append(equals_to)

        return self

    def and_equal(self, column, equals_to, case_sensitive=True):
        if not case_sensitive:
            column = f"LOWER({column})"
            equals_to = equals_to.lower()

        if self._sql:
            self._sql += f" AND {column}=?"
        else:
            self._sql += f"{column}=?"

        self.filler.append(equals_to)

        return self

    def or_like(self, column, equals_to, case_sensitive=True):
        if not case_sensitive:
            column = f"LOWER({column})"
            equals_to = equals_to.lower()

        if self._sql:
            self._sql += f" OR {column} LIKE ?"
        else:
            self._sql += f"{column} LIKE ?"

        self.filler.append(equals_to)

        return self

    def and_like(self, column, equals_to, case_sensitive=True):
        if not case_sensitive:
            column = f"LOWER({column})"
            equals_to = equals_to.lower()

        if self._sql:
            self._sql += f" AND {column} LIKE ?"
        else:
            self._sql += f"{column} LIKE ?"

        self.filler.append(equals_to)

        return self

    def and_regexp(self, column, regex):
        self.has_regex = True

        if self._sql:
            self._sql += f" AND {column} REGEXP ?"
        else:
            self._sql += f"{column} REGEXP ?"

        self.filler.append(regex)

        return self

    def or_regexp(self, column, regex):
        self.has_regex = True

        if self._sql:
            self._sql += f" OR {column} REGEXP ?"
        else:
            self._sql += f"{column} REGEXP ?"

        self.filler.append(regex)

        return self

    def or_sub_condition(self, sub_condition):
        if sub_condition.has_regex:
            self.has_regex = True

        self.filler.extend(sub_condition.filler)
        if self._sql:
            self._sql += f" OR ({sub_condition.sql(None)})"
        else:
            self._sql += f"({sub_condition.sql(None)})"

        return self

    def or_not_sub_condition(self, sub_condition):
        if sub_condition.has_regex:
            self.has_regex = True

        self.filler.extend(sub_condition.filler)
        if self._sql:
            self._sql += f" OR NOT ({sub_condition.sql(None)})"
        else:
            self._sql += f"NOT ({sub_condition.sql(None)})"

        return self

    def and_sub_condition(self, sub_condition):
        if sub_condition.has_regex:
            self.has_regex = True

        self.filler.extend(sub_condition.filler)
        if self._sql:
            self._sql += f" AND ({sub_condition.sql(None)})"
        else:
            self._sql += f"({sub_condition.sql(None)})"

        return self

    def and_not_sub_condition(self, sub_condition):
        if sub_condition.has_regex:
            self.has_regex = True

        self.filler.extend(sub_condition.filler)
        if self._sql:
            self._sql += f" AND NOT({sub_condition.sql(None)})"
        else:
            self._sql += f"NOT ({sub_condition.sql(None)})"

        return self

    def limit(self, limit):
        self._limit = limit

        return self

    def offset(self, offset):
        self._offset = offset

        return self

    def order_by(self, order_by, desc=False):
        self._order_by = order_by
        self._desc = desc

        return self


SETTING_DB_VERSION = 2
MUSIC_DB_VERSION = 2


class SettingsDatabase:
    def __init__(self, db_path):
        self.db_path = db_path

    def get(self, section, option, **kwargs):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        result = cursor.execute("SELECT value FROM botamusique WHERE section=? AND option=?",
                                (section, option)).fetchall()
        conn.close()

        if len(result) > 0:
            return result[0][0]
        else:
            if 'fallback' in kwargs:
                return kwargs['fallback']
            else:
                raise DatabaseError("Item not found")

    def getboolean(self, section, option, **kwargs):
        return bool(int(self.get(section, option, **kwargs)))

    def getfloat(self, section, option, **kwargs):
        return float(self.get(section, option, **kwargs))

    def getint(self, section, option, **kwargs):
        return int(self.get(section, option, **kwargs))

    def set(self, section, option, value):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO botamusique (section, option, value) "
                       "VALUES (?, ?, ?)", (section, option, value))
        conn.commit()
        conn.close()

    def has_option(self, section, option):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        result = cursor.execute("SELECT value FROM botamusique WHERE section=? AND option=?",
                                (section, option)).fetchall()
        conn.close()
        if len(result) > 0:
            return True
        else:
            return False

    def remove_option(self, section, option):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM botamusique WHERE section=? AND option=?", (section, option))
        conn.commit()
        conn.close()

    def remove_section(self, section):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM botamusique WHERE section=?", (section,))
        conn.commit()
        conn.close()

    def items(self, section):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT option, value FROM botamusique WHERE section=?", (section,)).fetchall()
        conn.close()

        if len(results) > 0:
            return list(map(lambda v: (v[0], v[1]), results))
        else:
            return []

    def drop_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE botamusique")
        conn.close()


class MusicDatabase:
    def __init__(self, db_path):
        self.db_path = db_path

    def insert_music(self, music_dict, _conn=None):
        conn = sqlite3.connect(self.db_path) if _conn is None else _conn
        cursor = conn.cursor()

        id = music_dict['id']
        title = music_dict['title']
        type = music_dict['type']
        path = music_dict['path'] if 'path' in music_dict else ''
        keywords = music_dict['keywords']

        tags_list = list(dict.fromkeys(music_dict['tags']))
        tags = ''
        if tags_list:
            tags = ",".join(tags_list) + ","

        del music_dict['id']
        del music_dict['title']
        del music_dict['type']
        del music_dict['tags']
        if 'path' in music_dict:
            del music_dict['path']
        del music_dict['keywords']

        existed = cursor.execute("SELECT 1 FROM music WHERE id=?", (id,)).fetchall()
        if len(existed) == 0:
            cursor.execute(
                "INSERT INTO music (id, type, title, metadata, tags, path, keywords) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (id,
                 type,
                 title,
                 json.dumps(music_dict),
                 tags,
                 path,
                 keywords))
        else:
            cursor.execute("UPDATE music SET type=:type, title=:title, metadata=:metadata, tags=:tags, "
                           "path=:path, keywords=:keywords WHERE id=:id",
                           {'id': id,
                            'type': type,
                            'title': title,
                            'metadata': json.dumps(music_dict),
                            'tags': tags,
                            'path': path,
                            'keywords': keywords})

        if not _conn:
            conn.commit()
            conn.close()

    def query_music_ids(self, condition: Condition):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT id FROM music WHERE id != 'info' AND %s" %
                                 condition.sql(conn), condition.filler).fetchall()
        conn.close()
        return list(map(lambda i: i[0], results))

    def query_all_paths(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT path FROM music WHERE id != 'info' AND type = 'file'").fetchall()
        conn.close()
        paths = []
        for result in results:
            if result and result[0]:
                paths.append(result[0])

        return paths

    def query_all_tags(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT tags FROM music WHERE id != 'info'").fetchall()
        tags = []
        for result in results:
            for tag in result[0].strip(",").split(","):
                if tag and tag not in tags:
                    tags.append(tag)
        conn.close()
        return tags

    def query_music_count(self, condition: Condition):
        filler = condition.filler

        conn = sqlite3.connect(self.db_path)
        condition_str = condition.sql(conn)
        cursor = conn.cursor()
        results = cursor.execute("SELECT COUNT(*) FROM music "
                                 "WHERE id != 'info' AND %s" % condition_str, filler).fetchall()
        conn.close()

        return results[0][0]

    def query_music(self, condition: Condition, _conn=None):
        filler = condition.filler

        conn = sqlite3.connect(self.db_path) if _conn is None else _conn
        condition_str = condition.sql(conn)
        cursor = conn.cursor()
        results = cursor.execute("SELECT id, type, title, metadata, tags, path, keywords FROM music "
                                 "WHERE id != 'info' AND %s" % condition_str, filler).fetchall()
        if not _conn:
            conn.close()

        return self._result_to_dict(results)

    def _query_music_by_plain_sql_cond(self, sql_cond, _conn=None):
        conn = sqlite3.connect(self.db_path) if _conn is None else _conn
        cursor = conn.cursor()
        results = cursor.execute("SELECT id, type, title, metadata, tags, path, keywords FROM music "
                                 "WHERE id != 'info' AND %s" % sql_cond).fetchall()
        if not _conn:
            conn.close()

        return self._result_to_dict(results)

    def query_music_by_id(self, _id, _conn=None):
        results = self.query_music(Condition().and_equal("id", _id), _conn)
        if results:
            return results[0]
        else:
            return None

    def query_music_by_keywords(self, keywords, _conn=None):
        condition = Condition()

        for keyword in keywords:
            condition.and_like("title", f"%{keyword}%", case_sensitive=False)

        return self.query_music(condition, _conn)

    def query_music_by_tags(self, tags, _conn=None):
        condition = Condition()

        for tag in tags:
            condition.and_like("tags", f"%{tag},%", case_sensitive=False)

        return self.query_music(condition, _conn)

    def manage_special_tags(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE music SET tags=REPLACE(tags, 'recent added,', '') WHERE tags LIKE '%recent added,%' "
                       "AND create_at <= DATETIME('now', '-1 day') AND id != 'info'")
        cursor.execute("UPDATE music SET tags=tags||'recent added,' WHERE tags NOT LIKE '%recent added,%' "
                       "AND create_at > DATETIME('now', '-1 day') AND id != 'info'")
        conn.commit()
        conn.close()

    def query_tags(self, condition: Condition):
        # TODO: Can we keep a index of tags?
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT id, tags FROM music "
                                 "WHERE id != 'info' AND %s" % condition.sql(conn), condition.filler).fetchall()

        conn.close()

        lookup = {}
        if len(results) > 0:
            for result in results:
                id = result[0]
                tags = result[1].strip(",").split(",")
                lookup[id] = tags if tags[0] else []

        return lookup

    def query_random_music(self, count, condition: Condition = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = []

        if condition is None:
            condition = Condition().and_not_sub_condition(Condition().and_equal('id', 'info'))

        results = cursor.execute("SELECT id, type, title, metadata, tags, path, keywords FROM music "
                                 "WHERE id IN (SELECT id FROM music WHERE %s ORDER BY RANDOM() LIMIT ?) "
                                 "ORDER BY RANDOM()"
                                 % condition.sql(conn), condition.filler + [count]).fetchall()
        conn.close()

        return self._result_to_dict(results)

    def _result_to_dict(self, results):
        if len(results) > 0:
            music_dicts = []
            for result in results:
                music_dict = json.loads(result[3])
                music_dict['type'] = result[1]
                music_dict['title'] = result[2]
                music_dict['id'] = result[0]
                music_dict['tags'] = result[4].strip(",").split(",") if result[4] else []
                music_dict['path'] = result[5]
                music_dict['keywords'] = result[6]

                music_dicts.append(music_dict)

            return music_dicts
        else:
            return []

    def delete_music(self, condition: Condition):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM music "
                       "WHERE %s" % condition.sql(conn), condition.filler)
        conn.commit()
        conn.close()

    def drop_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE music")
        conn.close()


class DatabaseMigration:
    def __init__(self, settings_db: SettingsDatabase, music_db: MusicDatabase):
        self.settings_db = settings_db
        self.music_db = music_db
        self.settings_table_migrate_func = {0: self.settings_table_migrate_from_0_to_1,
                                            1: self.settings_table_migrate_from_1_to_2}
        self.music_table_migrate_func = {0: self.music_table_migrate_from_0_to_1,
                                         1: self.music_table_migrate_from_1_to_2}

    def migrate(self):
        self.settings_database_migrate()
        self.music_database_migrate()

    def settings_database_migrate(self):
        conn = sqlite3.connect(self.settings_db.db_path)
        cursor = conn.cursor()
        if self.has_table('botamusique', conn):
            current_version = 0
            ver = cursor.execute("SELECT value FROM botamusique WHERE section='bot' "
                                 "AND option='db_version'").fetchone()
            if ver:
                current_version = int(ver[0])

            if current_version == SETTING_DB_VERSION:
                conn.close()
                return
            else:
                log.info(
                    f"database: migrating from settings table version {current_version} to {SETTING_DB_VERSION}...")
                while current_version < SETTING_DB_VERSION:
                    log.debug(f"database: migrate step {current_version}/{SETTING_DB_VERSION - 1}")
                    current_version = self.settings_table_migrate_func[current_version](conn)
                log.info(f"database: migration done.")

                cursor.execute("UPDATE botamusique SET value=? "
                               "WHERE section='bot' AND option='db_version'", (SETTING_DB_VERSION,))

        else:
            log.info(f"database: no settings table found. Creating settings table version {SETTING_DB_VERSION}.")
            self.create_settings_table_version_2(conn)

        conn.commit()
        conn.close()

    def music_database_migrate(self):
        conn = sqlite3.connect(self.music_db.db_path)
        cursor = conn.cursor()
        if self.has_table('music', conn):
            current_version = 0
            ver = cursor.execute("SELECT title FROM music WHERE id='info'").fetchone()
            if ver:
                current_version = int(ver[0])

            if current_version == MUSIC_DB_VERSION:
                conn.close()
                return
            else:
                log.info(f"database: migrating from music table version {current_version} to {MUSIC_DB_VERSION}...")
                while current_version < MUSIC_DB_VERSION:
                    log.debug(f"database: migrate step {current_version}/{MUSIC_DB_VERSION - 1}")
                    current_version = self.music_table_migrate_func[current_version](conn)
                log.info(f"database: migration done.")

                cursor.execute("UPDATE music SET title=? "
                               "WHERE id='info'", (MUSIC_DB_VERSION,))

        else:
            log.info(f"database: no music table found. Creating music table version {MUSIC_DB_VERSION}.")
            self.create_music_table_version_2(conn)

        conn.commit()
        conn.close()

    def has_table(self, table, conn):
        cursor = conn.cursor()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,)).fetchall()
        if len(tables) == 0:
            return False
        return True

    def create_settings_table_version_2(self, conn):
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS botamusique ("
                       "section TEXT, "
                       "option TEXT, "
                       "value TEXT, "
                       "UNIQUE(section, option))")
        cursor.execute("INSERT INTO botamusique (section, option, value) "
                       "VALUES (?, ?, ?)", ("bot", "db_version", 2))
        conn.commit()

        return 1

    def create_music_table_version_1(self, conn):
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE music ("
                       "id TEXT PRIMARY KEY, "
                       "type TEXT, "
                       "title TEXT, "
                       "keywords TEXT, "
                       "metadata TEXT, "
                       "tags TEXT, "
                       "path TEXT, "
                       "create_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                       ")")
        cursor.execute("INSERT INTO music (id, title) "
                       "VALUES ('info', ?)", (MUSIC_DB_VERSION,))

        conn.commit()

    def create_music_table_version_2(self, conn):
        self.create_music_table_version_1(conn)

    def settings_table_migrate_from_0_to_1(self, conn):
        cursor = conn.cursor()
        cursor.execute("DROP TABLE botamusique")
        conn.commit()
        self.create_settings_table_version_2(conn)
        return 2  # return new version number

    def settings_table_migrate_from_1_to_2(self, conn):
        cursor = conn.cursor()
        # move music database into a separated file
        if self.has_table('music', conn) and not os.path.exists(self.music_db.db_path):
            log.info(f"database: move music db into separated file.")
            cursor.execute(f"ATTACH DATABASE '{self.music_db.db_path}' AS music_db")
            cursor.execute(f"SELECT sql FROM sqlite_master "
                           f"WHERE type='table' AND name='music'")
            sql_create_table = cursor.fetchone()[0]
            sql_create_table = sql_create_table.replace("music", "music_db.music")
            cursor.execute(sql_create_table)
            cursor.execute("INSERT INTO music_db.music SELECT * FROM music")
            conn.commit()
            cursor.execute("DETACH DATABASE music_db")

            cursor.execute("DROP TABLE music")

        cursor.execute("UPDATE botamusique SET value=2 "
                       "WHERE section='bot' AND option='db_version'")
        return 2  # return new version number

    def music_table_migrate_from_0_to_1(self, conn):
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE music RENAME TO music_old")
        conn.commit()

        self.create_music_table_version_1(conn)

        cursor.execute("INSERT INTO music (id, type, title, metadata, tags)"
                       "SELECT id, type, title, metadata, tags FROM music_old")
        cursor.execute("DROP TABLE music_old")
        conn.commit()

        return 1  # return new version number

    def music_table_migrate_from_1_to_2(self, conn):
        items_to_update = self.music_db.query_music(Condition(), conn)
        for item in items_to_update:
            item['keywords'] = item['title']
            if 'artist' in item:
                item['keywords'] += ' ' + item['artist']

            tags = []
            for tag in item['tags']:
                if tag:
                    tags.append(tag)
            item['tags'] = tags

            self.music_db.insert_music(item)
        conn.commit()

        return 2  # return new version number
