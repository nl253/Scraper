#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spiders import Spider
import db
import multiprocessing
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

spider = Spider(max_entries=100, match_threshold=6, themes=themes)

jobs = map(lambda url: multiprocessing.Process(target=spider.scrape, args=([url],)), starting_urls)

for job in jobs:
    job.start()

while not all(map(lambda job: job.read(), jobs)):
    sleep(30)

for row in spider.ientries:
    database.query("INSERT INTO turing VALUES (?, ?)", data=row)
