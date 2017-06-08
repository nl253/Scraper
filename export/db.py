#!/usr/bin/env python
# -*- coding: utf-8 -*-

# NO DEPENDENCIES

"""High level, simple convenience wrapper for SQLite3 from the
standard library.
"""

import os
import re
import sqlite3
from copy import copy
from typing import Tuple, Union, Iterable, Optional
from pathlib import Path

import itertools

SQLiteDataType = Union[str, float, int, None]
Row = Tuple[SQLiteDataType, ...]


# Helper functions
def _regex(string: str, pattern: str) -> bool:
    return bool(re.compile(pattern).fullmatch(string))


def _test_input(*data) -> Optional[bool]:
    """
    Test input befor performing queries such as inserion.
    For example,
    >>> # Valid input
    >>> sample_input: Row = (11, "somthing", None, 211.22)
    >>> _test_input(sample_input)
    True
    >>> # Now invalid input
    >>> sample_input: Tuple[dict, set, None, None ] = (dict(), set(), None, None)
    >>> _test_input(sample_input)
    >>> # TODO paste traceback
    """
    for datum in data:
        if type(datum) not in [str, float, None, int]:
            print('SQLite only works with floats, ints, strings and None.')
            raise sqlite3.Error
    return True


def _determine_format(sample_row: Row) -> str:
    """
    Enables to add data to a table without using the (?, ?, ?, ... ) notation.
    It outputs the (?, ?, ?, ... ) with as many quesionmarks as are needed to insert.
    To do that it takes as a parameter a row and creates it's copy.
    Using it's length is creates a string with approparate format.

    For example,

    >>> row: Row = (1, None, 'Something', 'Someone')
    >>> _determine_format(row)
    '(?, ?, ?, ?)'
    """
    head: str = "("
    tail: str = ""
    middle: str = "?)"
    # because the last question mark is provided only iterate until n-1
    for _ in range(len(copy(sample_row)) - 1):
        middle += "?, "
    return head + middle + tail


class SQLite:
    def __init__(self, db_path='~/.sqlite'):
        self._db = os.path.expanduser(db_path)
        self._connection = sqlite3.connect(self._db)
        self._connection.create_function("regex", 2, _regex)
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
    def query(self, query_str: str, data=None, pprint_results=True, commit=True, try_catch=False) -> Optional[bool]:
        if try_catch:
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
        else:
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

    @property
    def busy(self) -> bool:
        return self._connection.in_transaction

    def create_table(self, table_name, commit=True, delete_existing=True) -> Optional[bool]:
        """
        Convenience method to create a table with a given name,
        optionally you can specify that an existing table with the same name would be deleted.
        """
        try:
            return self.query(f"CREATE TABLE {table_name}", commit=commit)
        except sqlite3.Error as e:
            if delete_existing:
                self.drop_table(table_name=table_name, commit=commit)
                return self.create_table(table_name, commit, delete_existing=False)
            else:
                raise sqlite3.Error

    def drop_table(self,
                   table_name: str,
                   commit=True):
        return self.query(f"DROP TABLE {table_name}", commit=commit)

    def add_row(self,
                table_name: str,
                commit: bool = True,
                *data: Union[str, int, float, None]):
        """
        Insert a single row into a table.
        """
        return self.query(
            f"INSERT INTO {table_name} "
            f"VALUES {_determine_format(data)} ",
            data=data, commit=commit)

    def add_rows(self,
                 rows: Iterable[Row],
                 table_name: str):
        """
        Add many rows to a specified table.
        Commit only after all rows have been successfully added,
        check that they are all of the same length.
        Use add_row() as a helper method.
        """
        len_first: int = \
            len(list(
                itertools.islice(
                    copy(rows), 0, 1)))

        # make sure all rows are of the same size
        # do this by comparing to the length of the first one
        assert all(map(lambda row: len(row) == len_first, copy(rows))), \
            "Rows have different sizes"

        for row in rows:
            self.add_row(table_name=table_name,
                         data=row,
                         commit=False)
        self._connection.commit()
        return True

    def clear_table(self, table_name: str, commit=True):
        return self.query(f"DELETE FROM {table_name}", commit=commit)

    def rollback(self) -> Optional[bool]:
        self._connection.rollback()
        return True

    def execute_script(self, script_path: Union[bytes, str]) -> Optional[bool]:
        """
        Execute an SQL script from a text file.
        You need to specify the path.
        """
        assert os.path.isfile(script_path), \
            "The path doesn't point to an existing file."
        path: Path = Path(script_path)
        text: str = path.read_text(encoding="utf-8")
        self._cursor.executescript(text)
        return True
