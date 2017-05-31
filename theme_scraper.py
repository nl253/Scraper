#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spiders import Spider
import db

database = db.SQLite()

# database.query("CREATE TABLE scraping ( url TEXT, chunk TEXT )")

spider = Spider(
    starting_urls=["https://en.wikipedia.org/wiki/Web_scraping",
                   "http://python-guide-pt-br.readthedocs.io/en/latest/scenarios/scrape/"],
    themes=["scraping",
            "extraction",
            "extract data",
            "spider",
            "data mining"],
    max_entries=1500,
    match_threshold=6)

spider.scrape()

for row in spider.ientries:
    database.query("INSERT INTO scraping VALUES (?, ?)", data=row)
