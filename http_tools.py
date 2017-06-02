#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from urllib.request import urlopen
from urllib.parse import urljoin, urlparse
import logging
from typing import Iterator, Tuple, Union, List
from bs4 import BeautifulSoup
# from preprocessing import HTMLSanitizer

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger(name=__name__)

class HTMLWrapper():
    def __init__(self, URL: str):
        self._response = urlopen(URL, timeout=5)
        self._html = None
        self._peeked = None
        self._text = None
        self._info = self._response.info()
        self._url_regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            # domain...
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def _validate_url(self, URL: str) -> bool:
        assert type(URL) is str, 'URL is not str.'
        # l.info('Filtering links that end with ".zip" or ".rar"')
        # l.info('Filtering links through Django regex')
        if self._url_regex.search(URL) and not re.compile(
            '(\.((zip)|(png)|(jpg)|(jpeg)|(tar)|(docx)|(tex)|(css)|(js)|(rar)|(pdf)|(docx)))$').search(URL):
            return True
        return False

    @property
    def URLs(self) -> Iterator[str]:
        # l.info('Retrieving and filtering links')
        links = list(set(re.compile(r'(?<=href=").*?(?=")', flags=re.UNICODE).findall(self.HTML)))
        parsed_focus_url = urlparse(self.URL)
        for i in range(len(links)):
            parsed = urlparse(links[i])
            if parsed.path and not parsed.netloc and not parsed.scheme:
                links[i] = urljoin(parsed_focus_url.scheme + "://www." + parsed_focus_url.netloc, parsed.path)
        return filter(self._validate_url, links)

    @property
    def code_status(self) -> int:
        return self._response.getcode()

    @property
    def URL(self) -> str:
        return self._response.url

    @property
    def peek_title(self) -> str:
        return re.compile("(?<=<title>).*(?=</title>)").search(self._response.peek().decode('utf-8')).group(0)

    @property
    def peek_lang(self) -> str:
        return self._response.getheader("Content-language")
        # return re.compile("(?<=lang=['\"])\w+(?=['\"])").search(self.peek).group(0)

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
        if type(self._text) is not str:
            self._text = BeautifulSoup(self.HTML, 'html.parser').get_text()
        return self._text


    @property
    def charsets(self) -> List[str]:
        return self._info.get_charsets()

    @property
    def content_type(self) -> str:
        return self._info.get_content_maintype()

    @property
    def content_subtype(self) -> str:
        return self._info.get_content_subtype()

    @property
    def headers(self) -> List[Tuple[str, str]]:
        return self._response.getheaders()

    @property
    def length(self) -> int:
        return self._response.length

    def __len__(self) -> int:
        return self._response.length

    def __str__(self) -> int:
        return self.HTML

    def __contains__(self, item: Union[int, str]) -> bool:
        if item in self.HTML:
            return True
        else:
            return False

