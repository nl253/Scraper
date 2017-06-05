#!/usr/bin/env python
# -*- coding: utf-8 -*-

from export.db import SQLite
from spiders import ThemeSpider as Spider

database = SQLite()

themes: List[str] = ["[Pp]ython"]

urls: List[str] = [ "https://www.whitehouse.gov/",
                   "http://www.trump.com/",
                   "http://www.independent.co.uk/",
                   "http://www.telegraph.co.uk/"]

for row in Spider(
    themes=themes,
    starting_urls=urls,
    timeout=1200,
    max_threads=8,
    max_child_processes=4).crawl():
        print(row)
