#!/usr/bin/env python
# -*- coding: utf-8 -*-

# DEPENDENCIES:
# - textblob
# - bs4
# - lxml

import logging
import re
from typing import List, Optional, Iterable, Iterator

from bs4 import BeautifulSoup
from http_tools import HTMLWrapper
from preprocessing import StringSanitizer
from textblob.en import polarity, subjectivity

logging.basicConfig(
    level=logging.DEBUG,
	format='%(levelname)s:%(asctime)s  %(message)s')

class ChunkAnalyser():
    def __init__(self, text: str):
        self._text: str = text

    @property
    def text(self) -> str:
        return self._text

    def theme_count(self, themes: Iterable[str]) -> int:
        count: int = 0
        for theme in themes:
            results: List[str] = re.compile(theme).findall(self.text)
            if results:
                count += len(results)
        return count

    @property
    def polarity(self) -> float:
        return polarity(self.text)

    @property
    def subjectivity(self) -> float:
        return subjectivity(self.text)

    @property
    def lexical_diversity(self) -> float:
        words: List[str] = list(self.iwords)
        try:
            len(set(words)) / len(words)
        except ArithmeticError:
            return 0


class DocumentAnalayzer(ChunkAnalyser):
    def __init__(self, text: str):
        super().__init__(text)

    def imatching_sents(self, themes: List[str], context=500) -> Iterator[Optional[str]]:
        for theme in set(map(str.lower, themes)):
            for matching_str in re.compile(
                '(?:\.[\n\t ]{1,2})[A-Z].{,' + str(
                    context) + '}' + theme + '.{,' + str(
                        context) + '}\.(?=[ \t\n]{1,2})',
                flags=re.IGNORECASE|re.DOTALL).finditer(self._text):
                yield StringSanitizer(matching_str.group(0)).sanitize().text


class HTMLAnalyser(HTMLWrapper, DocumentAnalayzer):
    def __init__(self, URL: str):
        super().__init__(URL)
        self._soup = BeautifulSoup(self.HTML, 'lxml')
        super().__init__(self._soup.get_text())

    def tag_count(self, tag: str) -> int:
        result = len(self.get_tags(tag))
        return len(result) if result else 0

    def get_tags(self, tag: str) -> Optional[List[str]]:
        return re.compile(
            "<{}[ >].*?</{}>".format(tag, tag), flags=re.I | re.M).findall(self.html)

    def get_class(self, class_name: str):
        raise NotImplementedError

    def __getitem__(self, key: str) -> Optional[List[str]]:
        return self.get_tags(key)
