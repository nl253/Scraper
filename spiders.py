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
from multiprocessing import cpu_count, Process
# from asyncio import Semaphore
from time import sleep

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%I:%M:%S")

l = logging.getLogger(name=__name__)

Entry = Tuple[Union[str, float, float, str], ...]

class Spider():
    def __init__(self, starting_urls: List[str], themes: List[str],
                 max_entries=2000, match_threshold=18, max_threads=cpu_count(),
                 process_results_with=None, function_args=[]):
        self._max_entries = max_entries
        self._max_threads = max_threads
        self._themes = themes
        # min matches on a page to add entries and links
        self._match_threshold = match_threshold
        # stack
        self._entries = LifoQueue()
        self._to_be_scraped = Counter()
        self._to_be_scraped.update(starting_urls)
        self._processed_urls = set()
        self._function = process_results_with
        # self._counting_semaphore = Semaphore(value=self._max_threads)
        self._counting_semaphore = self._max_threads
        self._jobs = []
        self._function_args = function_args
        self._finished = False
        assert type(function_args) is list, 'Extra args need to be passed as list.'
        l.info('Spider created')
        l.info("Max set to {}".format(max_entries))
        l.info("Themes set to {}".format(themes))

    def _add_entry(self, *entry: Entry):
        if self._function:
            if self._function_args:
                # if you supply your own funct to process the data, you need to
                # make sure it outputs a tuple
                entry = self._processing_func(*entry, *self._function_args)
            else:
                entry = self._processing_func(*entry)
        else:
            entry = tuple(entry)
        assert type(entry) is tuple, 'Type of entry is not tuple.'
        l.info('Adding an entry')
        self._entries.put(entry)
        l.info('No Entries: {}'.format(self._entries.qsize()))

    @property
    def ientries(self) -> Entry:
        # you cannot call it before calling scrape()
        while not self.finished:
            sleep(10)
        while not self._entries.empty():
            yield self._entries.get()

    def scrape(self):
        while len(self._to_be_scraped) > 0 and self._entries.qsize() < self._max_entries:

            # import pudb; pudb.set_trace()  # XXX BREAKPOINT

            # if self._counting_semaphore.acquire():
                # job = Process(target=self._scrape)
                # job.start()
                # import pudb; pudb.set_trace()  # XXX BREAKPOINT
            # else:
                # sleep(10)
            if self._counting_semaphore > 0 and self._counting_semaphore < 5:
                l.info('Starting another job')
                self._jobs.append(Process(target=self._scrape))
                self._counting_semaphore -= 1
                self._jobs[len(self._jobs) - 1].start()
            else:
                l.info('Going to sleep')
                sleep(10)
                for job in self._jobs:
                    if job is None or not job.is_alive():
                        self._counting_semaphore += 1
                        self._jobs.remove(job)
                        l.info('Removing a dead job')

        # set finished when esceped from the loop
        l.info('Setting finished to True')
        self._finished = True

    @property
    def finished(self) -> bool:
        return self._finished

    def _scrape(self):

        # loop until the queue is empty
        while self._to_be_scraped is not None and len(self._to_be_scraped) > 0 and self._entries.qsize() < self._max_entries:

            l.info('{} URLs to scrape'.format(len(self._to_be_scraped)))
            l.info('{} already processed'.format(len(self._processed_urls)))

            # get next from from queue
            focus_url = self._to_be_scraped.most_common(1)[0][0]

            self._to_be_scraped.pop(focus_url)

            l.info('Focus URL: {}'.format(focus_url))

            # add to traversed to prevent visitng twice
            self._processed_urls.add(focus_url)

            try:
                # instantiate an extractor object
                extractor = HTMLExtractor(focus_url)
                # get no matches in html
                matches = HTMLAnalyser(extractor.HTML, self._themes).theme_count

            except (IncompleteRead,HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError):
                l.debug('Error while requesting a response for {}'.format(focus_url))
                l.debug('Continuing')
                continue


            # count matches on the focus page
            l.info('Found {} matches in the content of {}'.format(matches, focus_url))

            if matches >= self._match_threshold:

                l.info('Enough matches, adding results and extracting links')

                l.info('Adding results from {} to entries'.format(focus_url))
                for sent in DocumentAnalayzer(extractor.text, themes=self._themes).matching_sents:
                    self._add_entry(focus_url, sent)

                # ensure you only traverse once
                l.info('Filetering extracted links')

                # check for titles if they match any of the themes
                links = filter(lambda link: link not in self._processed_urls, extractor.URLs)

                # populate the queue
                l.info('Adding links from {} to to_be_scraped'.format(focus_url))
                self._to_be_scraped = self._to_be_scraped.update(links)

                # l.info('To be scraped at the end of loop: {}'.format(self._to_be_scraped))
                # l.info('Len of to be scraped at the end of loop: {}'.format(len(self._to_be_scraped)))

            else:
                l.info('Not enough matches in {}, continuing'.format(focus_url))

