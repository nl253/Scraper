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
        return self

    def _remove_references(self):
        self._text = compile("\[\d+\]+").sub("", self._text)
        return self

    def _beautify(self):
        self._text = compile("[\n\t ]{2,}").sub(" ", self._text)
        return self

    def sanitize(self):
        return self._beautify()._remove_punct()._remove_references()

    @property
    def text(self):
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
        return self

    def _clean_css(self) -> BeautifulSoup:
        for style_tag in self._soup.find_all('style'):
            try:
                self._soup.style.extract()
            except AttributeError:
                break
        return self

    def sanitize(self) -> BeautifulSoup:
        self._clean_javascript()
        self._clean_css()
        return self

    @property
    def soup(self):
        return self._soup

