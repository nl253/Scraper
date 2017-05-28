#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Tuple, Union
from urllib.error import HTTPError, URLError
from http.client import RemoteDisconnected
import logging
from queue import Queue, LifoQueue
from .webtools import HTMLExtractor
from .lexical import DocumentAnalayzer
from typing import List
from socket import timeout
from ssl import CertificateError

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger()

Entry = Tuple[Union[str, float, float, str], ...]

class Spider():
    def __init__(self, starting_url: str, theme: str, max_entries=2000, match_threshold=8):
        self._max = max_entries
        self._theme = theme
        self._focus_url = starting_url
        self._match_threshold = match_threshold
        self._entries = LifoQueue()
        l.info('Spider created')
        l.info("Max set to {}".format(max_entries))
        l.info("Theme set to {}".format(theme))
        l.info("Starting URL set to {}".format(starting_url))

    def _add_entry(self, *entry: Entry):
        self._entries.put(tuple(entry))
        l.info('Adding an entry')
        l.info('No Entries: {}'.format(self._entries.qsize()))

    def entries(self) -> List[Entry]:
        l = []
        while not self._entries.empty():
            l.append(self._entries.get())
        return l

    def ientries(self):
        while not self._entries.empty():
            yield self._entries.get()

    def scrape(self):

        # initialise
        to_be_scraped = Queue()

        # put the firs (starting URL)
        to_be_scraped.put(self._focus_url)

        # loop until the queue is empty
        while not to_be_scraped.empty() and self._entries.qsize() < self._max:

            l.info('Length of queue of items to be scraped: {}'.format(to_be_scraped.qsize()))

            self._focus_url = to_be_scraped.get()

            l.info('Focus URL: {}'.format(self._focus_url))

            try:
                extractor = HTMLExtractor(self._focus_url, self._theme)
                text = extractor.text
                links = extractor.links

            except (HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError):
                l.debug('Error while requesting HTML: possible exceptions:\n \
                        HTTPError, \nURLError, \nRemoteDisconnected, \nUnicodeDecodeError, \
                        \n UnicodeEncodeError, \nCertificateError')
                continue

            analyzer = DocumentAnalayzer(text, self._theme)

            matches = analyzer.theme_count

            for sent in analyzer.sentences:
                sent_analyzer = DocumentAnalayzer(sent, self._theme)
                self._add_entry(sent, sent_analyzer.polarity, sent_analyzer.subjectivity, self._focus_url)

            # count matches on the focus page

            l.info('found {} matches in the content of {}'.format(matches, self._focus_url))

            # populate the queue
            # add to queue if less than max
            if self._entries.qsize() < self._max and matches >= self._match_threshold:
                for link in links:
                    l.info('Appending {} to to_be_scraped'.format(link))
                    to_be_scraped.put(link)

            l.info('End of this loop, continuing')
