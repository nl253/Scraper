#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.argv.append(os.path.abspath('..'))

from typing import Tuple, Union, List
from urllib.error import HTTPError, URLError
from http.client import RemoteDisconnected
import logging
from queue import Queue, LifoQueue
from http_tools import HTMLExtractor
from lexical import HTMLAnalyser
from socket import timeout
from ssl import CertificateError

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger(name=__name__)

Entry = Tuple[Union[str, float, float, str], ...]

class Spider():
    def __init__(self, starting_url: str, themes: List[str], max_entries=2000, match_threshold=18):
        self._max = max_entries
        self._themes = themes
        self._focus_url = starting_url
        self._match_threshold = match_threshold
        self._entries = LifoQueue()
        self._processed_urls = set()
        l.info('Spider created')
        l.info("Max set to {}".format(max_entries))
        l.info("Themes set to {}".format(themes))
        l.info("Starting URL set to {}".format(starting_url))

    def _add_entry(self, *entry: Entry):
        self._entries.put(tuple(entry))
        l.info('Adding an entry')
        l.info('No Entries: {}'.format(self._entries.qsize()))

    def ientries(self) -> Entry:
        while not self._entries.empty():
            yield self._entries.get()

    def scrape(self):

        # initialise
        to_be_scraped = Queue()

        # put the firs (starting URL)
        to_be_scraped.put(self._focus_url)

        # loop until the queue is empty
        while not to_be_scraped.empty() and self._entries.qsize() < self._max:

            l.info('{} URLs to scrape'.format(to_be_scraped.qsize()))

            self._focus_url = to_be_scraped.get()

            l.info('Focus URL: {}'.format(self._focus_url))

            # add to traversed to prevent visitng twice
            self._processed_urls.add(self._focus_url)

            try:
                # instantiate an extractor object
                # try because it will automatically attempt to request the page
                extractor = HTMLExtractor(self._focus_url)

            except (HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError):
                l.debug('Error while requesting HTML: possible exceptions:\n \
                        HTTPError, \nURLError, \nRemoteDisconnected, \nUnicodeDecodeError, \
                        \n UnicodeEncodeError, \nCertificateError')
                continue

            # count matches on the focus page
            matches = HTMLAnalyser(extractor.HTML, self._themes).theme_count
            l.info('Found {} matches in the content of {}'.format(matches, self._focus_url))

            if matches >= self._match_threshold:

                # get links
                links = extractor.URLs

                l.info('Adding {} and it\'t HTML to database'.format(self._focus_url))

                self._add_entry(self._focus_url, extractor.text)

                # populate the queue
                # add to queue if less than max
                if self._entries.qsize() < self._max:
                    for link in filter(lambda l: l not in self._processed_urls, links):
                        l.info('Appending {} to to_be_scraped'.format(link))
                        to_be_scraped.put(link)
                        self._processed_urls.add(link)
                else:
                    l.info('Enough data gathered')

                l.info('Enough matches to delve deeper, continuing')

            else:
                l.info('Not enough matches continuing')
