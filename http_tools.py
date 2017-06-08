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
from urllib.response import addinfourl

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger(name=__name__)


class HTMLWrapper:

    # static variables
    _url_neg_regex: Pattern = re.compile(
        '(\.((zip)|(png)|(jpg)|(jpeg)|(tar)|(tex)|(css)|(js)|(rar)|(pdf)|(docx)))$')

    _url_regex: Pattern = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        # domain...
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def __init__(self, URL: str):
        self._response: Union[HTTPResponse, addinfourl] = urlopen(URL, timeout=15)
        self._html = None
        self._info: HTTPMessage = self._response.info()

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
        return filter(validate_URL, links)

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


def validate_URL(URL: str) -> bool:
    """
    For the sake of flexibility ie being able to use it without requesting a page
    (which is what happens when you pass a URL to the constructor), this is left to be static.
    It allows to validate a URL (not perfect but good enough).

    For instance,
    >>> url = "something"
    >>> validate_HTML(url)
    False
    >>> url = "https://stackoverflow.com/questions/68645/static-class-variables-in-python"
    >>> validate_HTML(url)
    True
    """
    if len(URL) > 5 and HTMLWrapper._url_regex.search(URL) and \
            not HTMLWrapper._url_neg_regex.search(URL):
        return True
    else:
        return False


def validate_HTML(HTML: str) -> bool:
    """
    For the sake of flexibility ie being able to use it without requesting a page
    (which is what happens when you pass a URL to the constructor),
     this is a allows method that allows to check if a given HTML page (passed as a string) is valid.
     >>> HTML_string: str = "<html>WOOO</html>"
     >>> HTMLWrapper.validate_HTML(HTML_string)
     False
     >>> # too short to be valid!
    """
    return len(HTML) > 30
