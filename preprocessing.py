#!/usr/bin/env python
# -*- coding: utf-8 -*-

from re import compile
import re

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
        return self._clean_javascript()._clean_css()

    @property
    def html(self):
        return self._html

