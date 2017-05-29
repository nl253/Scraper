#!/usr/bin/env python
# -*- coding: utf-8 -*-

from textblob.en import polarity, subjectivity
from typing import Iterator, List
from nltk import sent_tokenize
import logging
from shlex import split
from nltk import word_tokenize
import re
from preprocessing import StringSanitizer

logging.basicConfig(
    level=logging.DEBUG,
	format='%(levelname)s:%(asctime)s  %(message)s')

class DocumentAnalayzer():
    def __init__(self, text: str, theme: str):
        self._text = text
        self._theme = theme

    @property
    def sentences(self) -> Iterator[str]:
        sentences = sent_tokenize(self._text)
        sentences = filter(lambda sent: len(sent) < 1500 \
                           and re.compile(self._theme.lower(),
                                          flags=re.IGNORECASE).search(str(sent)), sentences)
        return (StringSanitizer(sent).sanitize().text for sent in sentences)

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

