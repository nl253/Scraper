#!/usr/bin/env python
# -*- coding: utf-8 -*-

from re import compile
from bs4 import BeautifulSoup


punctuation = "£%$![]{}~#-+=>^&*`¬</"

class StringSanitizer():
    def __init__(self, text: str):
        self._text = text

    def _remove_punct(self):
        translator = str.maketrans(self._text, self._text, "£%$!()[]{}~#-+=>^&*`¬</")
        self._text.translate(translator)

    def _remove_references(self):
        self._text = compile("\[\d+\]+").sub("", self._text)

    def _beautify(self):
        self._text = compile("[\n\t ]{2,}").sub(" ", self._text)

    def sanitize(self):
        self._beautify()
        self._remove_punct()
        self._remove_references()
        return self._text

class SoupSanitizer():
    def __init__(self, soup: BeautifulSoup):
        self._soup = soup

    def _clean_javascript(self) -> BeautifulSoup:
        for script_tag in self._soup.find_all('script'):
            try:
                self._soup.script.extract()
            except AttributeError:
                break

    def sanitize(self) -> BeautifulSoup:
        self._clean_javascript()
        return self._soup

