#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spiders import Spider
from db import SQLite

spider = Spider(
    starting_url="https://en.wikipedia.org/wiki/Donald_Trump",
    themes=["Trump",
            "Donald Trump",
            "D Trump",
            "D. Trump",
            "Trump's"],
    max_entries=50,
    match_threshold=10)

spider.scrape()

sqlite = SQLite()

for entry in spider.ientries():
    sqlite.query('INSERT INTO websites VALUES (?, ?)', entry)

sqlite.close_connection()
