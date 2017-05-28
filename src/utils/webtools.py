#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from re import compile
from urllib.request import urlopen
import logging
from typing import List
from bs4 import BeautifulSoup
from .preprocessing import SoupSanitizer

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger()

regex = compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    # domain...
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def validate_url(URL: str) -> bool:
    l.info('Filtering links that end with ".zip" or ".rar"')
    l.info('Filtering links through Django regex')
    if regex.search(URL) and not compile('(\.((zip)|(rar)|(pdf)|(docx)))$').search(URL):
        return True
    return False


def request_html(URL: str) -> str:
    return urlopen(URL, timeout=8).read().decode('utf-8')


class HTMLExtractor():
    def __init__(self, URL: str, theme: str):
        self._html = request_html(URL)
        self._soup = BeautifulSoup(self._html, 'html.parser')
        self._soup = SoupSanitizer(self._soup).sanitize().soup
        self._theme = theme

    @property
    def links(self) -> List[str]:
        anchors = self._soup.find_all('a')
        l.info('Parsed {} anchor tags'.format(len(anchors)))
        links = []
        for i in range(len(anchors)):
            try:
                if self._theme in anchors[i].get_text() or \
                        self._theme in anchors[i].parent.get_text() or \
                        self._theme in anchors[i].parent.parent.get_text() or \
                        self._theme in anchors[i].parent.parent.parent.get_text():
                    links.append(anchors[i]['href'])
            except (KeyError,ValueError,AttributeError):
                l.debug('KeyError or ValueError occured when trying to access the href attribute')
                l.debug('Most likely there was no href attribute with a valid URL')
        l.info('Filtering links using Django regexp and removing those already traversed')
        links = filter(lambda link: validate_url(link), links)
        return links

    @property
    def text(self) -> str:
        return self._soup.get_text()

    @property
    def title(self) -> str:
        return self._soup.title.get_text()
