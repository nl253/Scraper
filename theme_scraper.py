#!/usr/bin/env python
# -*- coding: utf-8 -*-

from spiders import Spider

spider = Spider(
    starting_url="https://en.wikipedia.org/wiki/Donald_Trump",
    themes=["Trump",
            "Donald Trump",
            "D Trump",
            "D. Trump",
            "Trump's"],
    max_entries=50,
    match_threshold=10)

spider.scrape()
