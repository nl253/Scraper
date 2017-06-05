#!/usr/bin/env python
# -*- coding: utf-8 -*-

# NO DEPENDENCIES

"""High level, simple convenience wrapper for SQLite3 from the
standard library.
"""

import os
from copy import copy
import re
import sqlite3
from itertools import islice
from typing import Tuple, Union

Row = Tuple[Union[str, float, int, None], ...]

class SQLite:
    def __init__(self, db_path='~/.sqlite'):
        self._db = os.path.expanduser(db_path)
        self._connection = sqlite3.connect(self._db)
        self._connection.create_function("regex", 2, self._regex)
        self._cursor = self._connection.cursor()

    def close_connection(self) -> bool:
        try:
            self._connection.commit()
            self._connection.close()
            return True
        except sqlite3.Error as e:
            print(f"Something went wrong. {e}")
            return False

    # performs the query quickly, saves the state automatically
    def query(self, query_str: str, data=None, pprint_results=True, commit=True):
        try:
            if data:
                self._cursor.execute(query_str, data)
            else:
                self._cursor.execute(query_str)

            if commit:
                self._connection.commit()

            if pprint_results:
                for row in self._cursor.fetchall():
                    if row: print(row)
            return True

        except sqlite3.Error as e:
            print(f"{e} occured.")
            return False

    @staticmethod
    def _regex(string: str, pattern: str) -> bool:
        return bool(re.compile(pattern).fullmatch(string))

    @property
    def busy(self) -> bool:
        return self._connection.in_transaction

    def create_table(self, table_name, commit=True) -> bool:
        return self.query(f"CREATE TABLE {table_name}" ,commit=commit)

    def drop_table(self, table_name: str, commit=True):
        return self.query(f"DROP TABLE {table_name}", commit=commit)

    @staticmethod
    def _determine_format(
            sample_row: Iterable[Union[str, float, int, None]]):
        head: str = "("
        tail: str = ""
        middle: str = "?)"
        for _ in range(len(copy(sample_row)) - 1):
            middle += "?, "
        return head + middle + tail

    def add_row(self,
                table_name: str,
                commit: bool = True,
                *data: Union[str, int, float, None]):
        return self.query(
            f"INSERT INTO {table_name} "
            f"VALUES {SQLite._determine_format(data)}",
            data=data, commit=commit)

    def add_rows(self, rows: Iterable[Union[str, float, int, None]]):
        len_first: int = len(list(itertools.islice(1)))
        assert all(map(lambda row: len(row) == len_first,rows)), \
            "Rows have different sizes"

        for row in rows:
            self.add_row(row)
        return True

    def clear_table(self, table_name: str, commit=True):
        return self.query(f"DELETE FROM {table_name}", commit=commit)

    def rollback(self) -> bool:
        try:
            self._connection.rollback()
            return True

        except sqlite3.Error as e:
            print(f"Something went wrong. {e}")
            return False


    def execute_script(self, script_path: Union[bytes, str]) -> bool:
        assert os.path.isfile(script_path), \
            "The path doesn't point to an existing file."
        return self._cursor.executescript(script_path)


    def _test_input(self, *data) -> Optional[bool]:
        for datum in data:
            if type(datum) not in [str, float, None, int]:
                self.rollback()
                 print('SQLite only works with floats, ints, strings and None.')
                raise sqlite3.Error
        return True


