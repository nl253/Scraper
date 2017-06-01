#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from urllib.request import urlopen
from urllib.parse import urljoin, uses_relative, urlparse
import logging
from typing import Iterator
from bs4 import BeautifulSoup
# from preprocessing import HTMLSanitizer

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger(name=__name__)

class URLHelper():
    def __init__(self):
        self.url_regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            # domain...
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def validate_url(self, URL: str) -> bool:
        assert type(URL) is str, 'URL is not str.'
        # l.info('Filtering links that end with ".zip" or ".rar"')
        # l.info('Filtering links through Django regex')
        if self.url_regex.search(URL) and not re.compile('(\.((zip)|(css)|(js)|(rar)|(pdf)|(docx)))$').search(URL):
            return True
        return False

    def make_url_absolute(self, URL: str) -> str:
        pass


class HTMLExtractor():
    def __init__(self, URL: str):
        self._response = urlopen(URL, timeout=5)
        self._html = None
        self._peeked = None
        self._url_helper = URLHelper()

    @property
    def URLs(self) -> Iterator[str]:
        l.info('Retrieving and filtering links')
        return filter(self._url_helper.validate_url, map(lambda regex_object: regex_object.group(0), re.compile("(?<=href=\")https?.*?(?=\")").finditer(self.HTML)))

    @property
    def code_status(self) -> int:
        return self._response.getcode()

    @property
    def peek(self) -> str:
        if not self._peeked:
            self._peeked = self._response.peek().decode('utf-8')
        return self._peeked

    @property
    def URL(self) -> str:
        return self._response.url

    @property
    def peek_title(self) -> str:
        return re.compile("(?<=<title>).*(?=</title>)").search(self.peek).group(0)

    @property
    def peek_lang(self) -> str:
        return re.compile("(?<=lang=['\"])\w+(?=['\"])").search(self.peek).group(0)

    @property
    def message(self) -> str:
        return self._response.msg

    @property
    def HTML(self) -> str:
        if not self._html:
            self._html = self._response.read().decode('utf-8')
        return self._html

    @property
    def text(self) -> str:
        return BeautifulSoup(self.HTML, 'html.parser').get_text()


