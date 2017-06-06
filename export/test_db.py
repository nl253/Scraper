import sqlite3
import unittest
from typing import List, Tuple, Iterator

import faker
from db import SQLite

# TODO finish it off
# think of scenarios where it could go wrong

Row = Tuple[Union[str, float, int, None], ...]
Entry = Union[str, float, int, None]


class SQLiteTester(unittest.TestCase):
    def setUp(self):
        self.db = SQLite()
        self.gen = faker.Faker()

    def tearDown(self):
        self.db.rollback()
        self.db._connection.close()

    def add_row(self):

        fake_row_list: Tuple[str, float, int] = \
            (self.gen.name(), self.gen.pyfloat(), self.gen.pyint())

        fake_row_tuple: List[str] = [self.gen.name() for i in range(10)]

        fake_row_iter: Iterator[str] = (self.gen.name() for i in range(10))

        self.db.add_row(fake_row_list)

        self.db.add_row(fake_row_tuple)

        self.db.add_row(fake_row_iter)

    def bad_type(self):
        badly_typed_tuple = (self.gen.pydecimal(), dict(), set())
        badly_typed_list = [(object(), map(lambda x: x, [])) for i in range(10)]

        with self.assertRaises:
            for entry in badly_typed_list:
                self.db.add_row(entry)

            for entry in badly_typed_tuple:
                self.db.add_row(entry)

    def add_many_rows(self):

        fake_rows: List[Entry] = [
            (self.gen.name(), self.gen.pyint(), self.gen.pyfloat()) \
            for i in range(100)]

        self.db.add_rows(fake_rows)

        with self.assertRaises(sqlite3.Error):
            fake_rows: List[Entry] = [
                (self.gen.pydecimal(), self.gen.pydict()) for i in range(100)]

        self.db.add_rows(fake_rows)

    def clear_table(self):
        pass

    def execute_script(self):
        pass

    def rollback(self):
        pass

    def invalid_input(self):
        pass

    def create_table(self):
        pass

    def drop_table(self):
        pass

    def replace_table(self):
        pass

    def test(self):
        self.setUp()
        self.add_row()
        self.bad_type()
        self.add_many_rows()
        self.clear_table()
        self.execute_script()
        self.rollback()
        self.invalid_input()
        self.create_table()
        self.replace_table()
        self.tearDown()
