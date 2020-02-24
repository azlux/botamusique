import sqlite3

class DatabaseError(Exception):
    pass

class Database:
    def __init__(self, db_path):
        self.db_path = db_path

        # connect
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # check if table exists, or create one
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='botamusique';").fetchall()
        if len(tables) == 0:
            cursor.execute("CREATE TABLE botamusique (section text, option text, value text, UNIQUE(section, option))")
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
        cursor.execute('''
            INSERT OR REPLACE INTO botamusique (section, option, value)
            VALUES (?, ?, ?)
        ''', (section, option, value))
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

        return map(lambda v: (v[0], v[1]), results)

    def drop_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE botamusique")
        conn.close()


