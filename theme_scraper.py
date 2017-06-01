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

starting_urls = ["https://en.wikipedia.org/wiki/Alan_Turing",
                 "http://www.bbc.co.uk/timelines/z8bgr82",
                 "http://www.bbc.co.uk/timelines/z8bgr82",
                 "http://www.turing.org.uk/publications/dnb.html"]

spider = Spider(starting_urls=starting_urls,
                themes=themes,
                max_entries=2500,
                match_threshold=6)



for row in spider.crawl():
    # for sent in DocumentAnalayzer(extractor.text, themes=self._themes).matching_sents:
    print(row)
