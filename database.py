import sqlite3
import json
import datetime


class DatabaseError(Exception):
    pass

class Condition:
    def __init__(self):
        self.filler = []
        self._sql = ""
        self._limit = 0
        self._offset = 0
        self._order_by = ""
        pass

    def sql(self):
        sql = self._sql
        if not self._sql:
            sql = "TRUE"
        if self._limit:
            sql += f" LIMIT {self._limit}"
        if self._offset:
            sql += f" OFFSET {self._offset}"
        if self._order_by:
            sql += f" ORDEY BY {self._order_by}"

        return sql

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

    def or_sub_condition(self, sub_condition):
        self.filler.extend(sub_condition.filler)
        if self._sql:
            self._sql += f"OR ({sub_condition.sql()})"
        else:
            self._sql += f"({sub_condition.sql()})"

        return self

    def and_sub_condition(self, sub_condition):
        self.filler.extend(sub_condition.filler)
        if self._sql:
            self._sql += f"AND ({sub_condition.sql()})"
        else:
            self._sql += f"({sub_condition.sql()})"

        return self

    def limit(self, limit):
        self._limit = limit

        return self

    def offset(self, offset):
        self._offset = offset

        return self

SETTING_DB_VERSION = 1
MUSIC_DB_VERSION = 1

class SettingsDatabase:
    def __init__(self, db_path):
        self.db_path = db_path

        # connect
        conn = sqlite3.connect(self.db_path)

        self.db_version_check_and_create()

        conn.commit()
        conn.close()

    def has_table(self, table):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,)).fetchall()
        conn.close()
        if len(tables) == 0:
            return False
        return True

    def db_version_check_and_create(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if self.has_table('botamusique'):
            # check version
            ver = self.getint("bot", "db_version", fallback=None)

            if ver is None or ver != SETTING_DB_VERSION:
                # old_name = "botamusique_old_%s" % datetime.datetime.now().strftime("%Y%m%d")
                # cursor.execute("ALTER TABLE botamusique RENAME TO %s" % old_name)
                cursor.execute("DROP TABLE botamusique")
                conn.commit()
                self.create_table()
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
                       "VALUES (?, ?, ?)", ("bot", "db_version", SETTING_DB_VERSION))
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
                       "VALUES (?, ?, ?)", (section, option, value))
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

        self.db_version_check_and_create()
        self.manage_special_tags() # This is super time comsuming!

    def has_table(self, table):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,)).fetchall()
        conn.close()
        if len(tables) == 0:
            return False
        return True

    def create_table(self):
        conn = sqlite3.connect(self.db_path)
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
        conn.close()

    def db_version_check_and_create(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if self.has_table('music'):
            ver = cursor.execute("SELECT title FROM music WHERE id='info'").fetchone()
            if ver and int(ver[0]) == MUSIC_DB_VERSION:
                conn.close()
                return True
            else:
                cursor.execute("ALTER TABLE music RENAME TO music_old")
                conn.commit()

                self.create_table()
                
                cursor.execute("INSERT INTO music (id, type, title, metadata, tags)"
                               "SELECT id, type, title, metadata, tags FROM music_old")
                cursor.execute("DROP TABLE music_old")
                conn.commit()
                conn.close()
        else:
            self.create_table()

    def insert_music(self, music_dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        id = music_dict['id']
        title = music_dict['title']
        type = music_dict['type']
        path = music_dict['path'] if 'path' in music_dict else ''
        keywords = music_dict['keywords']
        tags = ",".join(list(dict.fromkeys(music_dict['tags']))) + ","

        del music_dict['id']
        del music_dict['title']
        del music_dict['type']
        del music_dict['tags']
        if 'path' in music_dict:
            del music_dict['path']
        del music_dict['keywords']

        cursor.execute("INSERT OR REPLACE INTO music (id, type, title, metadata, tags, path, keywords) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (id,
                        type,
                        title,
                        json.dumps(music_dict),
                        tags,
                        path,
                        keywords))

        conn.commit()
        conn.close()

    def query_all_ids(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT id FROM music WHERE id != 'info'").fetchall()
        conn.close()
        return list(map(lambda i: i[0], results))

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
        condition_str = condition.sql()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT COUNT(*) FROM music "
                                 "WHERE id != 'info' AND %s" % condition_str, filler).fetchall()
        conn.close()

        return results[0][0]

    def query_music(self, condition: Condition):
        filler = condition.filler
        condition_str = condition.sql()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT id, type, title, metadata, tags, path, keywords FROM music "
                                 "WHERE id != 'info' AND %s" % condition_str, filler).fetchall()
        conn.close()

        return self._result_to_dict(results)

    def _query_music_by_plain_sql_cond(self, sql_cond):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT id, type, title, metadata, tags, path, keywords FROM music "
                                 "WHERE id != 'info' AND %s" % sql_cond).fetchall()
        conn.close()

        return self._result_to_dict(results)

    def query_music_by_id(self, _id):
        results = self.query_music(Condition().and_equal("id", _id))
        if results:
            return self.query_music(Condition().and_equal("id", _id))[0]
        else:
            return None

    def query_music_by_keywords(self, keywords):
        condition = Condition()

        for keyword in keywords:
            condition.and_like("title", f"%{keyword}%", case_sensitive=False)

        return self.query_music(condition)

    def query_music_by_tags(self, tags):
        condition = Condition()

        for tag in tags:
            condition.and_like("tags", f"%{tag},%", case_sensitive=False)

        return self.query_music(condition)

    def manage_special_tags(self):
        for tagged_recent in self.query_music_by_tags(['recent added']):
            tagged_recent['tags'].remove('recent added')
            self.insert_music(tagged_recent)
        recent_items = self._query_music_by_plain_sql_cond("create_at > date('now', '-1 day')")
        for recent_item in recent_items:
            recent_item['tags'].append('recent added')
            self.insert_music(recent_item)

    def query_tags(self, condition):
        # TODO: Can we keep a index of tags?
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT id, tags FROM music "
                                  "WHERE id != 'info' AND %s" % condition.sql(), condition.filler).fetchall()

        conn.close()

        lookup = {}
        if len(results) > 0:
            for result in results:
                id = result[0]
                tags = result[1].strip(",").split(",")
                lookup[id] = tags if tags[0] else []

        return lookup

    def query_random_music(self, count):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = cursor.execute("SELECT id, type, title, metadata, tags, path, keywords FROM music "
                                 "WHERE id IN (SELECT id FROM music WHERE id != 'info' ORDER BY RANDOM() LIMIT ?)", (count,)).fetchall()
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
                music_dict['tags'] = result[4].strip(",").split(",")
                if result[5]:
                    music_dict['path'] = result[5]
                music_dict['keywords'] = result[6]
                if not music_dict['tags'][0]:
                    music_dict['tags'] = []

                music_dicts.append(music_dict)

            return music_dicts
        else:
            return []

    def delete_music(self, condition: Condition):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM music "
                       "WHERE %s" % condition.sql(), condition.filler)
        conn.commit()
        conn.close()

    def drop_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE music")
        conn.close()
