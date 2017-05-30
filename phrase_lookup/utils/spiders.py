#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Tuple, Union
from urllib.error import HTTPError, URLError
from http_tools.client import RemoteDisconnected
import logging
from queue import LifoQueue
from collections import deque
from http_tools import HTMLRegexExtractor, request_html
from lexical import DocumentAnalayzer
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
    def __init__(self, starting_url: str, theme: str, max_entries=2000, match_threshold=10):
        self._max = max_entries
        self._theme = theme
        self._focus_url = starting_url
        self._match_threshold = match_threshold
        self._entries = LifoQueue()
        self._traversed = deque()
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
        to_be_scraped = deque()

        # put the firs (starting URL)
        to_be_scraped.appendleft(self._focus_url)

        # loop until the queue is empty
        while len(to_be_scraped) > 0 and self._entries.qsize() < self._max:

            l.info('Length of queue of items to be scraped: {}'.format(len(to_be_scraped)))

            self._focus_url = to_be_scraped.popleft()

            self._traversed.append(self._focus_url)

            l.info('Focus URL: {}'.format(self._focus_url))


            l.info('No Entries: {}'.format(self._entries.qsize()))

            try:
                html = request_html(self._focus_url)

                extractor = HTMLRegexExtractor(html)

                matching_sents = extractor.matching_sents(self._theme)

                matches = len(matching_sents)


                for sent in matching_sents:
                    sent_analyzer = DocumentAnalayzer(sent, self._theme)
                    self._add_entry(sent, sent_analyzer.polarity, sent_analyzer.subjectivity, self._focus_url)

                if matches < self._match_threshold:
                    print('Too few matches, continuing')
                    continue

                # count matches on the focus page
                l.info('found {} matches in the content of {}'.format(matches, self._focus_url))

                links = extractor.URLs

            except (HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError):
                l.debug('Error while requesting HTML: possible exceptions:\n \
                        HTTPError, \nURLError, \nRemoteDisconnected, \nUnicodeDecodeError, \
                        \n UnicodeEncodeError, \nCertificateError')
                continue

            # populate the queue
            # add to queue if less than max
            if self._entries.qsize() < self._max:
                for link in [i for i in links if i not in self._traversed and i not in to_be_scraped]:
                    l.info('Appending {} to to_be_scraped'.format(link))
                    to_be_scraped.appendleft(link)

            l.info('End of this loop, continuing')
