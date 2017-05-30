#!/usr/bin/env python
# -*- coding: utf-8 -*-

from textblob.en import polarity, subjectivity
from typing import Iterator, List
# from nltk import sent_tokenize
import logging
from nltk import word_tokenize
from queue import LifoQueue
import re
from preprocessing import StringSanitizer
# from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.DEBUG,
	format='%(levelname)s:%(asctime)s  %(message)s')

class DocumentAnalayzer():
    def __init__(self, text: str, themes: List[str]):
        self._text = text
        self._themes = themes

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
        words = self.words
        return len(set(words)) / len(words)

    @property
    def words(self) -> List[str]:
        return word_tokenize(self._text)

    def matching_chunks(self, context=400) -> Iterator[str]:
        accumulator = LifoQueue()
        for theme in self._themes:
            for matching_str in re.compile('.{,' + str(context) + '}' + theme + '.{,' + str(context) + '}',
                flags=re.IGNORECASE|re.DOTALL).finditer(self._text):
                accumulator.put(matching_str)
        while not accumulator.empty():
            yield StringSanitizer(accumulator.get()).sanitize().text

class HTMLAnalyser():
    def __init__(self, HTML: str, themes: List[str]):
        assert type(themes) is list, 'Themes is not List[str].'
        self._themes = themes
        self._html = HTML

    @property
    def theme_count(self) -> int:
        count = 0
        for theme in self._themes:
            count += self._html.count(theme)
        return count
