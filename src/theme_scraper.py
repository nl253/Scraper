#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db import create_table
from utils.scraping import Spider

db_path = "~/.sqlite"

cols = ["sent", "polarity", "subjectivity", "url"]

spider = Spider('https://en.wikipedia.org/wiki/Hillary_Clinton',
                'Hillary Clinton')

rows = spider.breadth_first_scrape()

rows = spider.results

create_table(rows, 'clinton', db_path, cols, delete_existing=True)
