#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from urllib.request import urlopen
import logging
from typing import Iterator
from bs4 import BeautifulSoup
# from preprocessing import HTMLSanitizer

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger(name=__name__)

url_regex = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    # domain...
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def _validate_url(URL: str) -> bool:
    assert type(URL) is str, 'URL is not str.'
    # l.info('Filtering links that end with ".zip" or ".rar"')
    # l.info('Filtering links through Django regex')
    if url_regex.search(URL) and not re.compile('(\.((zip)|(rar)|(pdf)|(docx)))$').search(URL):
        return True
    return False


class HTMLExtractor():
    def __init__(self, URL: str):
        self._html = urlopen(URL, timeout=5).read().decode('utf-8')
        self._url = URL

    @property
    def URLs(self) -> Iterator[str]:
        l.info('Retrieving and filtering links')
        return filter(_validate_url, map(lambda regex_object: regex_object.group(0), re.compile("(?<=href=\")https?.*?(?=\")").finditer(self._html)))

    @property
    def title(self):
        return re.compile("(?<=<title>).*?(?=</title>)").search(self._html)

    @property
    def HTML(self) -> str:
        return self._html

    @property
    def text(self) -> str:
        return BeautifulSoup(self._html, 'html.parser').get_text()


