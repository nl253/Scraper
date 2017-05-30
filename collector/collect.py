#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.abspath('../'))
import db
from db import create_table
import utils
import utils.spiders
from utils.spiders import Spider
from argparse import ArgumentParser

parser = ArgumentParser()

parser.add_argument('-d',
                    '--database',
                    '--db',
                    dest='database',
                    metavar='PATH',
                    default='~/.sqlite')

args = parser.parse_args()

db_path = args.database

cols = [
    "url",
    "no_matches",
    "no_links",
    "chunk",
    'polarity',
    "subjectivity",
    'diversity',
    "text_length"
    "no_words"
    "no_sents" ]


try:
    spider = Spider('https://en.wikipedia.org/wiki/Natural_language_processing',
                    'language')
    rows = spider.scrape()
except KeyboardInterrupt:
    print('Interrupted, no data was saved.')

rows = list(spider.ientries())

create_table(rows, 'clinton', db_path, cols, delete_existing=True)
