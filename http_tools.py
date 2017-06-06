#!/usr/bin/env python
# -*- coding: utf-8 -*-

# NO DEPENDENCIES

import re
from typing import Pattern, Dict, Optional
from urllib.request import urlopen
from urllib.parse import urljoin, urlparse
import logging
from http.client import HTTPMessage, HTTPResponse
from typing import Iterator, Tuple, Union, List

# from preprocessing import HTMLSanitizer

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger(name=__name__)


class HTTPValidator:
    def __init__(self):
        self._url_regex: Pattern = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            # domain...
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        self._url_neg_regex: Pattern = re.compile(
            '(\.((zip)|(png)|(jpg)|(jpeg)|(tar)|(docx)|(tex)|(css)|(js)|(rar)|(pdf)|(docx)))$')

    @staticmethod
    def validate_URL(self, URL: str) -> bool:
        if self._url_regex.search(URL) and not self._url_neg_regex.search(URL):
            return True
        return False


class HTMLWrapper:
    def __init__(self, URL: str):
        self._response: Union[HTTPResponse, addinfourl] = urlopen(URL, timeout=15)
        self._html = None
        self._info: HTTPMessage = self._response.info()
        self._validator: HTTPValidator = HTTPValidator()

    @property
    def iURLs(self) -> Iterator[str]:
        # l.info('Retrieving and filtering links')
        links: List[str] = list(set(re.compile(r'(?<=href=").*?(?=")',
                                               flags=re.UNICODE).findall(self.HTML)))
        parsed_focus_url = urlparse(self.URL)
        for i in range(len(links)):
            parsed = urlparse(links[i])
            if parsed.path and not parsed.netloc and not parsed.scheme:
                links[i] = urljoin(
                    parsed_focus_url.scheme + "://www." + parsed_focus_url.netloc,
                    parsed.path)
        return filter(self._validator.validate_URL, links)

    @property
    def code_status(self) -> int:
        return self._response.getcode()

    @property
    def URL(self) -> str:
        return self._response.url

    @property
    def title(self) -> Optional[str]:
        return re.compile("(?<=<title>).*?(?=</title>)").search(
            self._response.peek().decode('utf-8')).group(0)

    @property
    def lang(self) -> str:
        return self._response.getheader("Content-language")

    @property
    def message(self) -> str:
        return self._response.msg

    @property
    def HTML(self) -> str:
        if not self._html:
            self._html = self._response.read().decode('utf-8')
        return self._html

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
    def headers(self) -> Dict[str, str]:
        return dict(self._response.getheaders())

    @property
    def length(self) -> int:
        return self._response.length

    def __len__(self) -> int:
        return self._response.length

    def __str__(self) -> int:
        return self.HTML

    def __contains__(self, item: Union[int, str]) -> bool:
        return True if item in self.HTML else False
