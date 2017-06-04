#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spiders import ThemeSpider as Spider
import db
# import lxml
# import lxml.html
# from lxml.html.clean import clean_html
#


database = db.SQLite()

themes = ["[Pp]ython"]

urls = [ "https://www.whitehouse.gov/",
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
