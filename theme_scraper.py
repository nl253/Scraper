#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spiders import Spider
import db

database = db.SQLite()

spider = Spider(
    starting_urls=["https://en.wikipedia.org/wiki/Donald_Trump"],
    themes=["election",
            "Trump",
            "D. Trump",
            "Donald Trump",
            "sexual harrasment",
            "rape",
            "accused"],
    max_entries=2500,
    match_threshold=6)

spider.scrape()

for row in spider.ientries:
    database.query("INSERT INTO trump VALUES (?, ?)", data=row)
