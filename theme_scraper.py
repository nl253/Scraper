#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spiders import Spider
import db
from time import sleep

database = db.SQLite()

themes=["A. Turing",
        "computer science",
        "Turing",
        "k",
        "A Turing",
        "Turing Machine",
        "finate automata"]

starting_urls = ["https://en.wikipedia.org/wiki/Alan_Turing",
                 "http://www.bbc.co.uk/timelines/z8bgr82",
                 "http://www.turing.org.uk/publications/dnb.html"]

spider = Spider(starting_urls=starting_urls,
                themes=themes, max_entries=100,
                match_threshold=6)

spider.scrape()

for i in spider.ientries:
    print(i)

# for row in spider.ientries:
    # database.query("INSERT INTO turing VALUES (?, ?)", data=row)
