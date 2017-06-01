#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Tuple, Union
import sqlite3
import os

Row = Tuple[Union[str, float, int, None], ...]

class SQLite():
    def __init__(self, db_path='~/.sqlite'):
        self._db = os.path.expanduser(db_path)
        self._connection = sqlite3.connect(self._db)
        self._cursor = self._connection.cursor()

    def close_connection(self) -> bool:
        try:
            self._connection.commit()
            self._connection.close()
        except:
            print("Something went wrong.")
            return False

    # performs the query quickly, saves the state automatically
    def query(self, query_str: str, data=None, pprint_results=True, commit=True):

        if data:
            self._cursor.execute(query_str, data)
        else:
            self._cursor.execute(query_str)

        if commit:
            self._connection.commit()

        if pprint_results:
            for i in self._cursor.fetchall():
                if i:
                    print(i)
