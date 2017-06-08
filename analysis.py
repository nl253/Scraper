#!/usr/bin/env python
# -*- coding: utf-8 -*-

# DEPENDENCIES:
# - textblob
# - bs4
# - lxml

"""
This module helps to preprocess and analyse the data collected using a Spider.
HTTPAnalyser inherits from HTTPWrapper from the http_tools module.
It will allow for:
- analysing sentiment ie polarity and subjectivity
- couting patterns
- selecting
"""

import logging
import re
from itertools import islice
from typing import List, Optional, Iterable, Iterator, Union

from bs4 import BeautifulSoup
from http_tools import HTMLWrapper
from nltk import sent_tokenize
# from preprocessing import StringSanitizer
from textblob.en import polarity, subjectivity

Pattern = Union[str, bytes]

logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s:%(asctime)s  %(message)s')


class ChunkAnalyser:
    """
    Role: analyse small chunks of text max paragraph, min a few words.
    Allows for:
    - counting matches (regexp)
    - generating polarity and subjectivity score
    - generating lexical diversity score
    - iteration over words
    Additionally it can be used with str() and
    produces the text passed to it in the constructor.
    """
    def __init__(self, text: str):
        self._text: str = text
        assert text, 'Passed text seems to be an empty string.'

    @property
    def text(self) -> str:
        """
        >>> string = 'My chunk of text is chunky and chunk is a chunk as is a chunk.'
        >>> analyser = ChunkAnalyser(string)
        >>> analyser.text == string
        True
        >>> # Same as passed string to the constructor.
        """
        return self._text

    def regex_match_count(self, patterns: Iterable[Pattern]) -> int:
        """
        Count the number regular expression matches in a Chunk.
        >>> analyser = ChunkAnalyser('This particular chunk will chunk test the patterns in patterns.')
        >>> analyser.regex_match_count(['test'])
        1
        >>> analyser.regex_match_count(['patterns', 'test'])
        3
        >>> analyser.regex_match_count(['patterns']) + analyser.regex_match_count(['test']) == 3
        True
        """
        count: int = 0
        for theme in patterns:
            results: List[str] = re.compile(theme).findall(self.text)
            if results:
                count += len(results)
        return count

    @property
    def polarity(self) -> float:
        """
        >>> analyser = ChunkAnalyser('My chunk of text is chunky and chunk is a chunk as is a chunk.')
        >>> type(analyser.polarity) is float
        True
        >>> analyser.polarity >= 0 and analyser.polarity <= 1
        True
        """
        return polarity(self.text)

    @property
    def subjectivity(self) -> float:
        return subjectivity(self.text)

    @property
    def lexical_diversity(self) -> float:
        """
        Calculate a score between 0 and 1 of how much diversity is in the text
        based on how often the same words are used.

        >>> string: str = 'My chunk of text is chunky and chunk is a chunk as is a chunk.'

        >>> analyser = ChunkAnalyser(string)

        >>> type(analyser.lexical_diversity) is float or analyser.lexical_diversity == 0
        True

        >>> analyser.lexical_diversity <= 1
        True

        """
        words: Iterator[str] = self.iwords
        try:
            len(set(words)) / len(words)
        except (TypeError):
            return 0

    @property
    def iwords(self) -> Iterator[str]:
        """
        >>> analyser = ChunkAnalyser('My chunk of text is chunky.')
        >>> list(analyser.iwords)
        ['My', 'chunk', 'of', 'text', 'is', 'chunky']
        >>> next(analyser.iwords)
        'My'
        """
        return (word.group(0) for word in re.compile('[A-Za-z]{2,}').finditer(self.text) if word.group(0) is not None)

    def __str__(self) -> str:
        """
        >>> analyser = ChunkAnalyser('My chunk of text is chunky and chunk is a chunk as is a chunk.')
        >>> analyser.text == str(analyser)
        True
        """
        return self._text


class DocumentAnalyzer(ChunkAnalyser):
    def __init__(self, text: str):
        super().__init__(text)

    def isents(
            self,
            patterns: Optional[Iterable[Union[str, bytes]]] = None,
            context=500) -> List[Optional[str]]:
        """
        Iterator over sentences that match patterns passed as a list.

        For example,
        >>> text = "As your collection of doctest’ed modules grows, " \
        "you’ll want a way to run all their doctests systematically." \
        " Doctest provides two functions that can be used to create " \
        "unittest test suites from modules and text files containing doctests. "
        >>> analyser = DocumentAnalyzer(text)
        >>> list(analyser.isents(patterns=["doctest"]))
        ['As your collection of doctest’ed modules grows, you’ll want a way to run all their doctests systematically.', 'Doctest provides two functions that can be used to create unittest test suites from modules and text files containing doctests.']

        Also, if you choose not to provide patterns, it will yield all sentences.

        >>> text = "As your collection of doctest’ed modules grows, " \
        "you’ll want a way to run all their doctests systematically." \
        " Doctest provides two functions that can be used to create " \
        "unittest test suites from modules and text files containing doctests. "

        >>> analyser = DocumentAnalyzer(text)
        >>> list(analyser.isents())
        ['As your collection of doctest’ed modules grows, you’ll want a way to run all their doctests systematically.', 'Doctest provides two functions that can be used to create unittest test suites from modules and text files containing doctests.']
        """
        if patterns and list(islice(filter(bool, set(patterns)), 0, 1)):
            # Check if after removing empty strings and duplicates
            # there is anything to iterate over.
            # This is done by:
            # - removing duplicates with set(),
            # - using filter() with bool() to remove empty strings "" (they evaluate to false),
            # - taking the islice() of the outcome to produce the first element (slice form the 0th index to 1st),
            # - converting the first element (which is a string and thus an iterable) to list()
            # - checking if it evaluates to true (it will if it's len() > 0)
            # iterate over unique lowercased strings (patterns)
            # case-insensitive search,
            # on each iteration,
            # define a new pattern depending on the 'theme'
            return [sent for sent in sent_tokenize(self.text) if
                    any(map(lambda theme: re.compile(theme).search(sent), patterns))]
        else:
            # in case patters are not provided
            return sent_tokenize(self.text)


class HTMLAnalyser(HTMLWrapper, DocumentAnalyzer):
    def __init__(self, URL: str):
        super().__init__(URL)
        self._soup = BeautifulSoup(self.HTML, 'lxml')
        super().__init__(self._soup.get_text())

    def tag_count(self, tag: str) -> int:
        """
        Convenience method to return the number of divs ps or any other tags.

        url = "https://docs.python.org/3.6/library/itertools.html#itertools.islice"
        analyser = HTMLAnalyser(url)
        var: int = count = analyser.tag_count('div')
        """
        result = len(self.get_tags(tag))
        return len(result) if result else 0

    def get_tags(self, tag: str) -> Optional[List[str]]:
        """
        Return a list of tags as specified by the 'tag' parameter.
        Regexp-based so it's fast.
        """
        return re.compile(
            "<{}[ >].*?</{}>".format(tag, tag), flags=re.I | re.M).findall(self.HTML)

    def get_class(self, class_name: str):
        raise NotImplementedError

    def __getitem__(self, key: str) -> Optional[List[str]]:
        """
        Allows to use BeautifulSoup-style indexing.
        Utilises get_class() - look above.

        Look at get_tags() for description.
        """
        return self.get_tags(key)


if __name__ == '__main__':
    import doctest

    doctest.testmod()
