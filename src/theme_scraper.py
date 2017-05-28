#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db import create_table
import utils
import utils.spiders
from utils.spiders import Spider

db_path = "~/.sqlite"

cols = ["sent", "polarity", "subjectivity", "url"]


try:
    spider = Spider('https://en.wikipedia.org/wiki/Hillary_Clinton',
                    'Hillary Clinton')
    rows = spider.scrape()
except KeyboardInterrupt:
    print('Interrupted, no data was saved.')

rows = list(spider.ientries())

create_table(rows, 'clinton', db_path, cols, delete_existing=True)
