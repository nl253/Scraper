#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spiders import Spider
import db
# import lxml
# import lxml.html
# from lxml.html.clean import clean_html


database = db.SQLite()

themes = ["[Pp]ython"]

urls = [ "https://docs.python.org/3/library/csv.html" ]

for row in Spider(themes=themes, starting_urls=urls, timeout=12, max_threads=8).crawl():
    # for sent in DocumentAnalayzer(extractor.text, themes=self._themes).matching_sents:
    print(row)
