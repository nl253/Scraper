#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Tuple, Union, List
from urllib.error import HTTPError, URLError
from http.client import RemoteDisconnected, IncompleteRead
import logging
from queue import LifoQueue
from collections import Counter
from http_tools import HTMLExtractor
from lexical import HTMLAnalyser, DocumentAnalayzer
from socket import timeout
from ssl import CertificateError

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger(name=__name__)

Entry = Tuple[Union[str, float, float, str], ...]

class Spider():
    def __init__(self, starting_urls: List[str], themes: List[str], max_entries=2000, match_threshold=18):
        self._max_entries = max_entries
        self._themes = themes
        self._focus_url = ""
        self._match_threshold = match_threshold
        self._entries = LifoQueue()
        self._to_be_scraped = Counter()
        self._to_be_scraped.update(starting_urls)
        self._processed_urls = set()
        l.info('Spider created')
        l.info("Max set to {}".format(max_entries))
        l.info("Themes set to {}".format(themes))
        l.info("Starting URLs set to {}".format(starting_urls))

    def _add_entry(self, *entry: Entry):
        self._entries.put(tuple(entry))
        l.info('Adding an entry')
        l.info('No Entries: {}'.format(self._entries.qsize()))

    @property
    def ientries(self) -> Entry:
        while not self._entries.empty():
            yield self._entries.get()

    def scrape(self):

        # import pudb; pudb.set_trace()  # XXX BREAKPOINT

        # loop until the queue is empty
        while len(self._to_be_scraped) > 0 and self._entries.qsize() < self._max_entries:

            l.info('{} URLs to scrape'.format(len(self._to_be_scraped)))
            l.info('{} already processed'.format(len(self._processed_urls)))

            # get next from from queue
            self._focus_url = self._to_be_scraped.most_common(1)[0][0]

            self._to_be_scraped.pop(self._focus_url)

            l.info('Focus URL: {}'.format(self._focus_url))

            # add to traversed to prevent visitng twice
            self._processed_urls.add(self._focus_url)

            try:
                # instantiate an extractor object
                extractor = HTMLExtractor(self._focus_url)
                # get no matches in html
                matches = HTMLAnalyser(extractor.HTML, self._themes).theme_count

            except (IncompleteRead,HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError):
                l.debug('Error while requesting a response for {}'.format(self._focus_url))
                l.debug('Continuing')
                continue


            # count matches on the focus page
            l.info('Found {} matches in the content of {}'.format(matches, self._focus_url))

            if matches >= self._match_threshold:

                l.info('Enough matches, adding results and extracting links')

                l.info('Adding results from {} to entries'.format(self._focus_url))
                for sent in DocumentAnalayzer(extractor.text, themes=self._themes).matching_sents:
                    self._add_entry(self._focus_url, sent)

                # ensure you only traverse once
                l.info('Filetering extracted links')

                # check for titles if they match any of the themes
                links = filter(lambda link: link not in self._processed_urls, extractor.URLs)

                # populate the queue
                l.info('Adding links from {} to to_be_scraped'.format(self._focus_url))
                self._to_be_scraped = Counter(links) | self._to_be_scraped

                # l.info('To be scraped at the end of loop: {}'.format(self._to_be_scraped))
                # l.info('Len of to be scraped at the end of loop: {}'.format(len(self._to_be_scraped)))

            else:
                l.info('Not enough matches in {}, continuing'.format(self._focus_url))
