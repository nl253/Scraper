#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spiders import Spider
import db

database = db.SQLite()

themes = ["A. Turing",
          "computer science",
          "computing",
          "Turing",
          "A Turing",
          "Turing Machine",
          "finate automata"]

urls = [ "https://en.wikipedia.org/wiki/Alan_Turing" ]

for row in Spider(themes=themes, starting_urls=urls).crawl():
    # for sent in DocumentAnalayzer(extractor.text, themes=self._themes).matching_sents:
    print(row)
