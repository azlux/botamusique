import sqlite3
import json
import datetime

class DatabaseError(Exception):
    pass

class SettingsDatabase:
    version = 1
    def __init__(self, db_path):
        self.db_path = db_path

        # connect
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        self.db_version_check_and_create()

        conn.commit()
        conn.close()

    def has_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='botamusique';").fetchall()
        conn.close()
        if len(tables) == 0:
            return False
        return True

    def db_version_check_and_create(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if self.has_table():
            # check version
            result = cursor.execute("SELECT value FROM botamusique WHERE section=? AND option=?",
                                    ("bot", "db_version")).fetchall()

            if len(result) == 0 or int(result[0][0]) != self.version:
                old_name = "botamusique_old_%s" % datetime.datetime.now().strftime("%Y%m%d")
                cursor.execute("ALTER TABLE botamusique RENAME TO %s" % old_name)
                conn.commit()
                self.create_table()
                self.set("bot", "old_db_name", old_name)
        else:
            self.create_table()

        conn.close()

    def create_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS botamusique ("
                       "section TEXT, "
                       "option TEXT, "
                       "value TEXT, "
                       "UNIQUE(section, option))")
        cursor.execute("INSERT INTO botamusique (section, option, value) "
                       "VALUES (?, ?, ?)" , ("bot", "db_version", "1"))
        cursor.execute("INSERT INTO botamusique (section, option, value) "
                       "VALUES (?, ?, ?)" , ("bot", "music_db_version", "0"))
        conn.commit()
        conn.close()

    def get(self, section, option, **kwargs):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        result = cursor.execute("SELECT value FROM botamusique WHERE section=? AND option=?", (section, option)).fetchall()
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
                       "VALUES (?, ?, ?)" , (section, option, value))
        conn.commit()
        conn.close()

    def has_option(self, section, option):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        result = cursor.execute("SELECT value FROM botamusique WHERE section=? AND option=?", (section, option)).fetchall()
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
        cursor.execute("DELETE FROM botamusique WHERE section=?", (section, ))
        conn.commit()
        conn.close()

    def items(self, section):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT option, value FROM botamusique WHERE section=?", (section, )).fetchall()
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

        # connect
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # check if table exists, or create one
        cursor.execute("CREATE TABLE IF NOT EXISTS music ("
                       "id TEXT PRIMARY KEY, "
                       "type TEXT, "
                       "title TEXT, "
                       "metadata TEXT, "
                       "tags TEXT)")
        conn.commit()
        conn.close()

    def insert_music(self, music_dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        id = music_dict['id']
        title = music_dict['title']
        type = music_dict['type']
        tags = ",".join(music_dict['tags'])
        del music_dict['id']
        del music_dict['title']
        del music_dict['type']
        del music_dict['tags']

        cursor.execute("INSERT OR REPLACE INTO music (id, type, title, metadata, tags) VALUES (?, ?, ?, ?, ?)",
                       (id,
                        type,
                        title,
                        json.dumps(music_dict),
                        tags))

        conn.commit()
        conn.close()

    def query_all_ids(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT id FROM music").fetchall()
        conn.close()
        return list(map(lambda i: i[0], results))

    def query_music(self, **kwargs):
        condition = []
        filler = []

        for key, value in kwargs.items():
            if isinstance(value, str):
                condition.append(key + "=?")
                filler.append(value)
            else:
                condition.append(key + " " + value[0] + " ?")
                filler.append(value[1])

        condition_str = " AND ".join(condition)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT id, type, title, metadata, tags FROM music "
                                "WHERE %s" % condition_str, filler).fetchall()
        conn.close()

        if len(results) > 0:
            music_dicts = []
            for result in results:
                music_dict = json.loads(result[3])
                music_dict['type'] = result[1]
                music_dict['title'] = result[2]
                music_dict['tags'] = result[4].split(",")
                music_dict['id'] = result[0]
                music_dicts.append(music_dict)

            return music_dicts
        else:
            return None

    def delete_music(self, **kwargs):
        condition = []
        filler = []

        for key, value in kwargs.items():
            if isinstance(value, str):
                condition.append(key + "=?")
                filler.append(value)
            else:
                condition.append(key + " " + value[0] + " ?")
                filler.append(value[1])

        condition_str = " AND ".join(condition)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM music "
                                 "WHERE %s" % condition_str, filler)
        conn.commit()
        conn.close()
