#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from urllib.request import urlopen
import logging
from typing import Iterator
from bs4 import BeautifulSoup
from preprocessing import HTMLSanitizer

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger()


def validate_url(URL: str) -> bool:
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        # domain...
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    l.info('Filtering links that end with ".zip" or ".rar"')
    l.info('Filtering links through Django regex')
    if regex.search(URL) and not re.compile('(\.((zip)|(rar)|(pdf)|(docx)))$').search(URL):
        return True
    return False


def request_html(URL: str) -> str:
    return urlopen(URL, timeout=8).read().decode('utf-8')


class HTMLRegexExtractor():
    def __init__(self, HTML: str):
        self._html = HTML

    @property
    def URLs(self) -> Iterator[str]:
        return [link for link in re.compile("(?<=href=\")https?.*?(?=\")").findall(self._html) if validate_url(link)]

    @property
    def title(self):
        return re.compile("(?<=<title>).*?(?=</title>)").search(self._html)

    @property
    def text(self) -> str:
        self._html = HTMLSanitizer(self._html).sanitize.html
        return BeautifulSoup(self._html, 'html.parser').get_text()

    @property
    def matching_sents(self, theme: str) -> Iterator[str]:
        return [BeautifulSoup(sent, 'html.parser').get_text() for sent in re.compile('.{,1800}' + theme + '.{,1800}', flags=re.IGNORECASE).findall(self._html)]
