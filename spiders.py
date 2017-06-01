#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Tuple, Union, List
from urllib.error import HTTPError, URLError
from http.client import RemoteDisconnected, IncompleteRead
import logging
from http_tools import HTMLExtractor
from lexical import HTMLAnalyser, DocumentAnalayzer
from socket import timeout
from ssl import CertificateError
from multiprocessing import cpu_count, Process
from multiprocessing import Queue as SharedQueue
from multiprocessing import Semaphore, current_process, Lock
from time import sleep

logging.basicConfig(
    level=logging.DEBUG,
    format='%(threadName)s %(module)s %(levelname)s : %(asctime)s : %(lineno)s : %(message)s.',
    datefmt="%M:%S")

l = logging.getLogger(name=__name__)
file_handler = logging.FileHandler('scraped.log')
file_handler.setLevel(logging.WARNING)
file_log_formatter = logging.Formatter('%(message)s.')
critical_handler = logging.StreamHandler()
critical_handler.setLevel(logging.CRITICAL)
error_handler = logging.StreamHandler()
error_handler.setLevel(logging.ERROR)
file_handler.setFormatter(file_log_formatter)
l.addHandler(file_handler)
l.addHandler(error_handler)
l.addHandler(critical_handler)

# crawl_log = logging.getLogger(name="crawl_logger", )

Entry = Tuple[Union[str, float, float, str], ...]

class Spider():
    def __init__(self, starting_urls: List[str], themes: List[str],
                 max_entries=2000, match_threshold=18, max_threads=cpu_count(),
                 process_results_with=None, function_args=[]):
        # settings
        self._max_entries = max_entries
        self._max_threads = max_threads
        self._themes = themes
        self._entry_access_lock = Lock()
        # min matches on a page to add entries and links
        self._match_threshold = match_threshold
        # stack to store scraped data as tuples
        self._entries = SharedQueue()
        self._to_be_scraped = SharedQueue(20000)
        self._jobs = []
        for url in starting_urls:
            self._to_be_scraped.put(url)
        # efficient lookup
        self._processed_urls = set()
        self._counting_semaphore = Semaphore(self._max_threads)
        self._finished = False  # initialise to False
        self._function = process_results_with
        self._function_args = function_args
        assert type(function_args) is list, 'Extra args need to be passed as list.'
        l.info('Spider created')
        l.info("Max entries set to {}".format(max_entries))
        l.info("Themes set to {}".format(themes))
        l.info("Max threads set to {}".format(max_threads))
        l.info("Match threshold set to {}".format(match_threshold))

    def _add_entry(self, *entry: Entry):
        curr_proc = current_process().name
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
        l.info('{}: Adding an entry'.format(curr_proc))
        self._entries.put(entry)
        l.info('{}: No Entries: {}'.format(curr_proc, self._entries.qsize()))

    @property
    def ientries(self) -> Entry:

        # you cannot call it before calling scrape()

        # while not self.finished:
            # sleep(10)


        self._entry_access_lock.acquire()

        import pudb; pudb.set_trace()  # XXX BREAKPOINT

        while not self._entries.empty():
            yield self._entries.get()
        self._entry_access_lock.release()

    def scrape(self):

        self._entry_access_lock.acquire()

        while self._entries.qsize() < self._max_entries and self._to_be_scraped.qsize() > 0:

            if self._counting_semaphore.acquire():
                l.info('Starting another job')
                job = Process(target=self._scrape)
                self._jobs.append(job)
                self._jobs[len(self._jobs) - 1].start()

            else:
                l.info('Going to sleep')
                sleep(10)

        # once we have enough entries
        l.info('Setting finished to True')
        while not all(map(lambda job: not job.is_alive(), self._jobs)):
            for job in self._jobs:
                if job.is_alive():
                    job.terminate()
                    self._jobs.remove(job)
            sleep(10)

        # set finished when esceped from the loop
        self._finished = True
        self._entry_access_lock.acquire()

    @property
    def finished(self) -> bool:
        return self._finished

    def _scrape(self):
        """To be run by each process thread.
        At the end the semaphore is realsed and process terminates itself.
        """
        # loop until the queue is empty
        # assert type(self._to_be_scraped) is , 'Type of self._to_be_scraped is not Counter!'
        while self._entries.qsize() < self._max_entries and self._to_be_scraped.qsize() > 0:

            proc_name = current_process().name

            l.info('{}: {} URLs to scrape'.format(proc_name, self._to_be_scraped.qsize()))
            l.info('{}: {} already processed'.format(proc_name, len(self._processed_urls)))

            # get next from from queue
            focus_url = self._to_be_scraped.get()

            if focus_url in self._processed_urls:
                l.info('{}: current URL {} has already been processed, continuing'.format(proc_name, focus_url))
                continue

            l.info('{}: Focus URL: {}'.format(proc_name, focus_url))

            # add to traversed to prevent visitng twice
            self._processed_urls.add(focus_url)

            try:
                # instantiate an extractor object
                extractor = HTMLExtractor(focus_url)
                # get no matches in html
                matches = HTMLAnalyser(extractor.HTML, self._themes).theme_count

            except (IncompleteRead,HTTPError,URLError,RemoteDisconnected,UnicodeDecodeError,UnicodeEncodeError,timeout,CertificateError):
                l.debug('{}: Error while requesting a response for {}'.format(proc_name, focus_url))
                l.debug('{}: Continuing'.format(proc_name))
                continue


            # count matches on the focus page
            l.info('{}: Found {} matches in the content of {}'.format(proc_name, matches, focus_url))

            if matches >= self._match_threshold:

                l.info('Enough matches, adding results and extracting links')

                l.info('{}: Adding results from {} to entries'.format(proc_name, focus_url))
                for sent in DocumentAnalayzer(extractor.text, themes=self._themes).matching_sents:
                    self._add_entry(focus_url, sent)

                # ensure you only traverse once
                l.info('{}: Filetering extracted links'.format(proc_name))

                # check for titles if they match any of the themes
                links = filter(lambda link: link not in self._processed_urls, extractor.URLs)

                for link in links:
                    self._to_be_scraped.put(link)

            else:
                l.info('{}: Not enough matches in {}, continuing'.format(proc_name, focus_url))

        self._counting_semaphore.release()
        # current_process().terminate()
