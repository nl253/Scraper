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
    def __init__(self, starting_url: str, themes: List[str], max_entries=2000, match_threshold=18, context=500):
        self._max_entries = max_entries
        self._themes = themes
        self._focus_url = ""
        self._context = context
        self._match_threshold = match_threshold
        self._entries = LifoQueue()
        self._to_be_scraped = Queue()
        self._to_be_scraped.put(starting_url)
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

        # loop until the queue is empty
        while not self._to_be_scraped.empty() and self._entries.qsize() < self._max_entries:

            l.info('{} URLs to scrape'.format(self._to_be_scraped.qsize()))

            # get next from from queue
            self._focus_url = self._to_be_scraped.get()

            l.info('Focus URL: {}'.format(self._focus_url))

            # add to traversed to prevent visitng twice
            self._processed_urls.add(self._focus_url)

            try:
                # instantiate an extractor object
                extractor = HTMLExtractor(self._focus_url)
                matches = HTMLAnalyser(extractor.HTML, self._themes).theme_count

            except (HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError):
                l.debug('Error while requesting HTML: possible exceptions:\n \
                        HTTPError, \nURLError, \nRemoteDisconnected, \nUnicodeDecodeError, \
                        \n UnicodeEncodeError, \nCertificateError')
                continue

            # count matches on the focus page
            l.info('Found {} matches in the content of {}'.format(matches, self._focus_url))

            if matches >= self._match_threshold and self._entries.qsize() < self._max_entries:

                l.info('Enough matches, adding results and extracting links')

                for chunk in DocumentAnalayzer(extractor.text, themes=self._themes).matching_chunks(context=self._context):
                    self._add_entry(self._focus_url, chunk)

                # get links
                # ensure you only traverse once
                l.info('Filetering extracted links')
                links = filter(lambda l: l not in self._processed_urls, extractor.URLs)

                link_holder = LifoQueue()

                # check for titles if they match any of the themes
                try:  # general http errors
                    for link in links:
                        try:  # in case match is None
                            if any(map(lambda theme: theme.lower() in HTMLExtractor(link).peek_title.lower(),  self._themes)):
                                link_holder.put(link)
                        except AttributeError:
                            l.info('{} didn\'t have any of {} in it'.format(link, self._themes))
                except (HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError):
                    l.debug('Error while title-peeking: \
                            possible exceptions:\n \
                            HTTPError, \nURLError, \
                            \nRemoteDisconnected, \
                            \nUnicodeDecodeError, \
                            \n UnicodeEncodeError, \
                            \nCertificateError')

                l.info('{} links after filtering'.format(link_holder.qsize()))

                l.info('Adding results from {} to entries'.format(self._focus_url))

                # populate the queue
                # add to queue if less than max
                while not link_holder.empty():
                    l.info('Appending {} to to_be_scraped'.format(link))
                    current_link = link_holder.get()
                    self._to_be_scraped.put(current_link)
                    self._processed_urls.add(current_link)
            else:
                pass
                l.info('Enough data gathered or not enough matches')
                # l.info('Not enough matches continuing')


