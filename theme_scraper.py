#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spiders import Spider
import db

database = db.SQLite()

themes=["A. Turing",
        "computer science",
        "computing",
        "Turing",
        "A Turing",
        "Turing Machine",
        "finate automata"]


spider = Spider()



for row in spider.crawl():
    # for sent in DocumentAnalayzer(extractor.text, themes=self._themes).matching_sents:
    print(row)
