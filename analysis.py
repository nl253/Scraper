#!/usr/bin/env python
# -*- coding: utf-8 -*-

# DEPENDENCIES:
# - textblob
# - bs4

from textblob.en import polarity, subjectivity
from typing import List, Generator
import logging
import re
from preprocessing import StringSanitizer
from http_tools import HTMLWrapper
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.DEBUG,
	format='%(levelname)s:%(asctime)s  %(message)s')

class ChunkAnalyser():
    def __init__(self, text: str, themes: List[str]):
        self._text: str = text
        self._themes: List[str] = themes

    @property
    def theme_count(self) -> int:
        return self._text.count(self._theme)

    @property
    def polarity(self) -> float:
        return polarity(self._text)

    @property
    def subjectivity(self) -> float:
        return subjectivity(self._text)

    @property
    def lexical_diversity(self) -> float:
        words: List[str] = list(self.iwords)
        return len(set(words)) / len(words)

    @property
    def iwords(self) -> Generator[str, None, None]:
        for word in re.finditer("[A-Za-z]{2,}", self._text):
            yield word.group(0)


class DocumentAnalayzer(ChunkAnalyser):

    def __init__(self, text: str, themes: List[str]):
        super().__init__(text, themes)

    @property
    def imatching_sents(self, context=500) -> str:
        for theme in set(map(str.lower, self._themes)):
            for matching_str in re.compile(
                '(?:\.[\n\t ]{1,2})[A-Z].{,' + str(
                    context) + '}' + theme + '.{,' + str(
                        context) + '}\.(?=[ \t\n]{1,2})',
                flags=re.IGNORECASE|re.DOTALL).finditer(self._text):
                yield StringSanitizer(matching_str.group(0)).sanitize().text


class HTMLAnalyser(HTMLWrapper):
    def __init__(self, URL: str, themes: List[str]):
        assert type(themes) is list and len(themes) > 0 and type(themes[0]) is str, \
            'Themes is not List[str].'
        super().__init__(URL)
        self._themes: List[str] = themes
        self._text = None

    @property
    def text(self) -> str:
        if type(self._text) is not str:
            self._text: str = BeautifulSoup(self.HTML, 'html.parser').get_text()
        return self._text

    @property
    def theme_count(self) -> int:
        count: int = 0
        for theme in self._themes:
            results: List[str] = re.compile(theme).findall(self.HTML)
            if results:
                count += len(results)
        return count

    @property
    def tag_count(self, tag: str) -> int:
        return len(self.get_tags(tag))

    def get_tags(self, tag: str) -> List[str]:
        return re.compile(
            "<{}[ >].*?</{}>".format(tag, tag), flags=re.I | re.M).findall(self._html)

    def get_class(self, class_name: str):
        return [i.group(0) for i in re.compile(r"<([a-zA-Z]+) ([a-zA-Z]{2,}=['\"]\w{2,}['\"]) )*?class=[\"']{}[\"'].*?</\1>".format(class_name), flags=re.I).finditer(self._html)]

    def __getitem__(self, key: str) -> List[str]:
        return self.get_tags(key)
