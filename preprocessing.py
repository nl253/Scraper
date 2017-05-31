#!/usr/bin/env python
# -*- coding: utf-8 -*-

from re import compile
import re

punctuation = "£%$![]{}~#-+=>^&*`¬</"

class StringSanitizer():
    def __init__(self, text: str):
        assert type(text) is str, 'Type of text not str'
        self._text = text

    def _remove_punct(self):
        translator = str.maketrans(self._text, self._text, "#\~|£%$!()[]{}~#-+=>^&*`¬</")
        self._text.translate(translator)
        # self._text = re.compile("(([\n^])|(\\xa0?\n?\^?))+").sub(" ", self._text)
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


class HTMLSanitizer():
    def __init__(self, html: str):
        self._html = html

    def _clean_javascript(self):
        pat = re.compile("<script.*?</script>")
        self._html = pat.sub("", self._html)
        return self

    def _clean_css(self):
        pat = re.compile("<style.*?</style>")
        self._html = pat.sub("", self._html)
        return self

    def sanitize(self):
        self._clean_javascript()
        self._clean_css()
        return self

    @property
    def html(self):
        return self._html

